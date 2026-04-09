#!/usr/bin/env python3
"""Self-contained release-notes generator and GitHub Release creator.

Can be called directly from a GitHub Actions workflow:

    python release_notes.py

Or imported as a library:

    from release_notes import generate_release_notes
"""

from __future__ import annotations

import os
import re
import subprocess
import tempfile
from pathlib import Path

# ── Model configuration ──────────────────────────────────────────────────────

DEFAULT_AI_MODEL = "gpt-5-mini"

ALLOWED_AI_MODELS: frozenset[str] = frozenset(
    {
        "gpt-5-mini",
        "gpt-5",
        "gpt-5.1",
        "gpt-4.1",
        "gpt-4o",
        "gpt-4o-mini",
    }
)

_NOISE_COMMIT_RE = re.compile(
    r"chore.*bump version|\[skip ci\]|chore.*release",
    re.IGNORECASE,
)

_DEFAULT_PROMPT_PATH = Path(__file__).with_name("release_notes_prompt.md")


# ── Helpers ───────────────────────────────────────────────────────────────────


def _run_capture(cmd: list[str]) -> str:
    return subprocess.run(cmd, capture_output=True, text=True).stdout.strip()


def _run(cmd: list[str]) -> None:
    print("+", " ".join(cmd))
    subprocess.run(cmd, check=True)


def _escape_actions_message(value: str) -> str:
    """Escape a message so it can be emitted as a GitHub Actions annotation."""
    return value.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


def _emit_warning(title: str, message: str) -> None:
    """Emit a warning annotation when running inside GitHub Actions."""
    escaped_title = _escape_actions_message(title)
    escaped_message = _escape_actions_message(message)
    print(f"::warning title={escaped_title}::{escaped_message}")


def _append_step_summary(lines: list[str]) -> None:
    """Append diagnostic lines to the GitHub Actions step summary when present."""
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY", "").strip()
    if not summary_path:
        return
    with Path(summary_path).open("a", encoding="utf-8") as summary_file:
        summary_file.write("\n".join(lines) + "\n")


def _truncate_detail(value: str, limit: int = 500) -> str:
    """Return a single-line diagnostic detail trimmed to a safe log length."""
    normalized = " ".join(value.split())
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 3] + "..."


def _resolve_ai_token() -> tuple[str, str]:
    """Return the first available AI token and the environment variable name."""
    token = os.environ.get("GH_TOKEN", "").strip()
    if token:
        return token, "GH_TOKEN"
    token = os.environ.get("COPILOT_TOKEN", "").strip()
    if token:
        return token, "COPILOT_TOKEN"
    return "", "none"


def validate_model(model: str) -> str:
    """Return *model* lowered if in the allow-list, otherwise ``""``."""
    normalised = model.strip().lower()
    if normalised and normalised not in ALLOWED_AI_MODELS:
        print(
            f"⚠️ AI model '{normalised}' is not supported; using Copilot account default"
        )
        return ""
    return normalised


# ── AI generation (importable) ────────────────────────────────────────────────


def generate_release_notes(
    *,
    package_name: str,
    version: str,
    previous_tag: str,
    current_tag: str,
    commit_lines: list[str],
    file_lines: list[str],
    ast_context: str = "",
    model: str = "",
    prompt_path: Path | None = None,
    timeout: int = 90,
) -> str:
    """Generate AI release notes via ``gh copilot``.

    Raises ``RuntimeError`` on failure (missing template, CLI error, empty output).
    """
    prompt_path = prompt_path or _DEFAULT_PROMPT_PATH
    if not prompt_path.exists():
        raise RuntimeError(f"Prompt template not found: {prompt_path}")

    model = validate_model(model)

    meaningful = [line for line in commit_lines if not _NOISE_COMMIT_RE.search(line)]

    prompt = (
        prompt_path.read_text(encoding="utf-8")
        .replace("{{PACKAGE_NAME}}", package_name)
        .replace("{{VERSION}}", version)
        .replace("{{PREVIOUS_TAG}}", previous_tag or "none")
        .replace("{{CURRENT_TAG}}", current_tag)
        .replace("{{COMMITS}}", "\n".join(meaningful) if meaningful else "- none")
        .replace("{{FILES}}", "\n".join(file_lines) if file_lines else "- none")
        .replace("{{AST_CONTEXT}}", ast_context if ast_context else "Not available.")
    )

    cmd: list[str] = ["gh", "copilot", "--"]
    if model:
        cmd.extend(["--model", model])
    cmd.extend(["-p", prompt, "--silent"])

    gh_token, token_source = _resolve_ai_token()
    env = dict(os.environ)
    env.pop("GITHUB_TOKEN", None)
    if gh_token:
        env["GH_TOKEN"] = gh_token

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=False,
        timeout=timeout,
        env=env,
    )

    if result.returncode != 0:
        stderr_detail = _truncate_detail(result.stderr or "")
        stdout_detail = _truncate_detail(result.stdout or "")
        detail_parts = [
            f"gh copilot exited with code {result.returncode}",
            f"token source: {token_source}",
            f"model: {model or 'copilot-account-default'}",
        ]
        if stderr_detail:
            detail_parts.append(f"stderr: {stderr_detail}")
        if stdout_detail:
            detail_parts.append(f"stdout: {stdout_detail}")
        if token_source not in {"GH_TOKEN", "COPILOT_TOKEN"}:
            detail_parts.append(
                "possible cause: no dedicated GH_TOKEN or COPILOT_TOKEN was provided, so the CLI used a fallback token source"
            )
        raise RuntimeError("; ".join(detail_parts))

    content = (result.stdout or "").strip()
    if not content:
        raise RuntimeError(
            "gh copilot returned empty output; "
            f"token source: {token_source}; "
            f"model: {model or 'copilot-account-default'}"
        )
    return content


# ── CLI: create GitHub Release ────────────────────────────────────────────────


def create_release() -> None:
    """Gather commits, generate notes (AI or fallback), and create a GitHub Release.

    Reads configuration from environment variables:
        VERSION, BUMP_TYPE, PACKAGE_NAME,
        AI_RELEASE_NOTES_ENABLED, AI_RELEASE_NOTES_MODEL,
        GH_TOKEN or COPILOT_TOKEN for AI generation,
        GITHUB_TOKEN for standard GitHub Actions operations
    """
    version = os.environ["VERSION"]
    bump_type = os.environ.get("BUMP_TYPE", "patch")
    package_name = os.environ.get("PACKAGE_NAME", "package")
    ai_enabled = os.environ.get("AI_RELEASE_NOTES_ENABLED", "true").lower() == "true"
    ai_model = validate_model(
        os.environ.get("AI_RELEASE_NOTES_MODEL", DEFAULT_AI_MODEL)
    )
    resolved_model = ai_model or "copilot-account-default"
    current_tag = f"v{version}"

    # Determine commit range
    tags_raw = _run_capture(["git", "tag", "--sort=-creatordate"])
    tags = [t.strip() for t in tags_raw.splitlines() if t.strip()]
    previous_tag = next((t for t in tags if t != current_tag), "")
    commit_range = f"{previous_tag}..{current_tag}" if previous_tag else current_tag

    # Gather commits and changed files
    commits_raw = _run_capture(
        ["git", "log", commit_range, "--pretty=format:- %s (%h)"]
    )
    commit_lines = [line for line in commits_raw.splitlines() if line.strip()]

    files_raw = _run_capture(["git", "diff", "--name-only", commit_range])
    file_lines = [line for line in files_raw.splitlines() if line.strip()][:200]

    # AST context: parse changed symbols from the diff (optional, needs tree-sitter)
    ast_context: str = ""
    try:
        import importlib
        import sys

        sys.path.insert(0, str(Path(__file__).resolve().parent))
        diff_ast = importlib.import_module("diff_ast")
        ast_context = diff_ast.extract_diff_ast(commit_range, file_lines)
        if ast_context:
            print(f"✅ AST context extracted ({ast_context.count(chr(10)) + 1} lines)")
    except Exception as err:
        print(f"ℹ️ AST context skipped: {err}")

    # Deterministic fallback notes
    fallback_lines = [f"## Commit Summary ({bump_type})"]
    fallback_lines.extend(commit_lines if commit_lines else ["- No commits found"])
    notes = "\n".join(fallback_lines)
    ai_warning_message: str | None = None

    # Try AI generation
    if ai_enabled:
        try:
            notes = generate_release_notes(
                package_name=package_name,
                version=version,
                previous_tag=previous_tag,
                current_tag=current_tag,
                commit_lines=commit_lines,
                file_lines=file_lines,
                ast_context=ast_context,
                model=ai_model,
            )
            print("✅ AI release notes generated (gh copilot)")
        except (RuntimeError, TimeoutError, FileNotFoundError) as err:
            ai_warning_message = (
                "Stage: AI release note generation. "
                f"Tag: {current_tag}. "
                f"Package: {package_name}. "
                f"Model: {resolved_model}. "
                f"Cause: {err}. "
                "Fallback: using commit summary notes; release creation will continue."
            )
            print("⚠️ AI release notes failed; using commit summary fallback")
            print(ai_warning_message)
            _emit_warning("AI release notes fallback", ai_warning_message)
            _append_step_summary(
                [
                    "### AI Release Notes Fallback",
                    f"- Tag: {current_tag}",
                    f"- Package: {package_name}",
                    f"- Model: {resolved_model}",
                    f"- Cause: {err}",
                    "- Result: commit summary notes were used and release creation continued",
                ]
            )
    else:
        print("ℹ️ AI release notes disabled, using commit summary")

    # Write notes and create the release
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", delete=False) as tmp:
        tmp.write(notes + "\n")
        notes_path = tmp.name

    try:
        _run(
            [
                "gh",
                "release",
                "create",
                current_tag,
                "--title",
                f"Release v{version}",
                "--generate-notes",
                "--notes-file",
                notes_path,
                "--verify-tag",
            ]
        )
    except subprocess.CalledProcessError as err:
        raise RuntimeError(
            "Stage: GitHub release creation. "
            f"Tag: {current_tag}. "
            f"Package: {package_name}. "
            f"Command failed with exit code {err.returncode}. "
            "Check whether the tag already has a release or whether the tag is missing remotely."
        ) from err

    Path(notes_path).unlink(missing_ok=True)

    if ai_warning_message is not None:
        print(
            "✅ GitHub release created successfully with commit-summary fallback notes"
        )


if __name__ == "__main__":
    create_release()
