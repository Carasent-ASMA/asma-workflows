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


def validate_model(model: str) -> str:
    """Return *model* lowered if in the allow-list, otherwise ``""``."""
    normalised = model.strip().lower()
    if normalised and normalised not in ALLOWED_AI_MODELS:
        print(f"⚠️ AI model '{normalised}' is not supported; using Copilot account default")
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

    gh_token = (
        os.environ.get("COPILOT_TOKEN", "").strip()
        or os.environ.get("GH_TOKEN", "").strip()
        or os.environ.get("GITHUB_TOKEN", "").strip()
    )
    env = dict(os.environ)
    if gh_token:
        env["COPILOT_GITHUB_TOKEN"] = gh_token
        env["GH_TOKEN"] = gh_token
        env["GITHUB_TOKEN"] = gh_token

    result = subprocess.run(
        cmd, capture_output=True, text=True, check=False, timeout=timeout, env=env,
    )

    if result.returncode != 0:
        reason = (result.stderr or result.stdout or "unknown error").strip()
        raise RuntimeError(f"gh copilot failed: {reason}")

    content = (result.stdout or "").strip()
    if not content:
        raise RuntimeError("gh copilot returned empty output")
    return content


# ── CLI: create GitHub Release ────────────────────────────────────────────────


def create_release() -> None:
    """Gather commits, generate notes (AI or fallback), and create a GitHub Release.

    Reads configuration from environment variables:
        VERSION, BUMP_TYPE, PACKAGE_NAME,
        AI_RELEASE_NOTES_ENABLED, AI_RELEASE_NOTES_MODEL,
        COPILOT_TOKEN / GH_TOKEN / GITHUB_TOKEN
    """
    version = os.environ["VERSION"]
    bump_type = os.environ.get("BUMP_TYPE", "patch")
    package_name = os.environ.get("PACKAGE_NAME", "package")
    ai_enabled = os.environ.get("AI_RELEASE_NOTES_ENABLED", "true").lower() == "true"
    ai_model = validate_model(
        os.environ.get("AI_RELEASE_NOTES_MODEL", DEFAULT_AI_MODEL)
    )
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

    # Try AI generation
    ai_failed = False
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
            ai_failed = True
            print(f"⚠️ AI release notes failed: {err}; using commit summary fallback")
    else:
        print("ℹ️ AI release notes disabled, using commit summary")

    # Write notes and create the release
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", delete=False) as tmp:
        tmp.write(notes + "\n")
        notes_path = tmp.name

    _run([
        "gh", "release", "create", current_tag,
        "--title", f"Release v{version}",
        "--generate-notes",
        "--notes-file", notes_path,
        "--verify-tag",
    ])

    Path(notes_path).unlink(missing_ok=True)

    if ai_failed:
        raise SystemExit(2)


if __name__ == "__main__":
    create_release()
