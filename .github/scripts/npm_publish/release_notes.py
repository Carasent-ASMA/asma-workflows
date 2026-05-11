#!/usr/bin/env python3
"""Self-contained release-notes generator and GitHub Release creator.

Can be called directly from a GitHub Actions workflow:

    python release_notes.py

Or imported as a library:

    from release_notes import generate_release_notes
"""

from __future__ import annotations

import base64
import json
import os
import re
import subprocess
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

DEFAULT_AI_BASE_URL = "https://web.dev.adopus.no/api/editor"
DEFAULT_AI_SYSTEM_USER = "asma.system_user"

_NOISE_COMMIT_RE = re.compile(
    r"chore.*bump version|\[skip ci\]|chore.*release",
    re.IGNORECASE,
)

_DEFAULT_PROMPT_PATH = Path(__file__).with_name("release_notes_prompt.md")

MAX_COMMITS_IN_PROMPT = 80
MAX_FILES_IN_PROMPT = 120
MAX_AST_CONTEXT_CHARS = 12_000
MAX_PROMPT_CHARS = 32_000


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


def _truncate_multiline(value: str, limit: int, label: str) -> str:
    """Trim long multiline content while preserving the leading context."""
    if len(value) <= limit:
        return value

    suffix = f"\n... [{label} truncated, {len(value) - limit} chars omitted]"
    trimmed_limit = max(0, limit - len(suffix))
    trimmed = value[:trimmed_limit].rstrip()
    return f"{trimmed}{suffix}"


def _build_release_notes_prompt(
    *,
    template: str,
    package_name: str,
    version: str,
    previous_tag: str,
    current_tag: str,
    commit_lines: list[str],
    file_lines: list[str],
    ast_context: str,
) -> str:
    """Build a bounded prompt payload for the Copilot CLI."""
    meaningful = [line for line in commit_lines if not _NOISE_COMMIT_RE.search(line)]
    commits_text = "\n".join(meaningful[:MAX_COMMITS_IN_PROMPT]) if meaningful else "- none"

    if len(meaningful) > MAX_COMMITS_IN_PROMPT:
        commits_text += (
            f"\n- ... truncated {len(meaningful) - MAX_COMMITS_IN_PROMPT} older commit lines"
        )

    files_text = "\n".join(file_lines[:MAX_FILES_IN_PROMPT]) if file_lines else "- none"
    if len(file_lines) > MAX_FILES_IN_PROMPT:
        files_text += (
            f"\n- ... truncated {len(file_lines) - MAX_FILES_IN_PROMPT} additional changed files"
        )

    ast_text = ast_context if ast_context else "Not available."
    ast_text = _truncate_multiline(ast_text, MAX_AST_CONTEXT_CHARS, "AST context")

    prompt = (
        template.replace("{{PACKAGE_NAME}}", package_name)
        .replace("{{VERSION}}", version)
        .replace("{{PREVIOUS_TAG}}", previous_tag or "none")
        .replace("{{CURRENT_TAG}}", current_tag)
        .replace("{{COMMITS}}", commits_text)
        .replace("{{FILES}}", files_text)
        .replace("{{AST_CONTEXT}}", ast_text)
    )

    return _truncate_multiline(prompt, MAX_PROMPT_CHARS, "release-notes prompt")


def _resolve_ai_backend_config() -> tuple[str, str, str]:
    """Resolve AI backend base URL, system user, and shared API token."""

    base_url = os.environ.get("ASMA_AI_BASE_URL", "").strip() or DEFAULT_AI_BASE_URL
    system_user = os.environ.get("ASMA_SYSTEM_USER", "").strip() or DEFAULT_AI_SYSTEM_USER
    api_token = os.environ.get("ASMA_AI_API_TOKEN", "").strip()
    return base_url.rstrip("/"), system_user, api_token


def _build_ai_auth_header(system_user: str, api_token: str) -> str:
    encoded = base64.b64encode(f"{system_user}:{api_token}".encode("utf-8")).decode(
        "utf-8"
    )
    return f"Bearer {encoded}"


def _extract_ai_error(exc: urllib.error.HTTPError) -> str:
    response_body = exc.read().decode("utf-8", errors="ignore")
    if response_body:
        try:
            payload = json.loads(response_body)
        except json.JSONDecodeError:
            return _truncate_detail(response_body)
        if isinstance(payload, dict):
            message = payload.get("message")
            if isinstance(message, str) and message.strip():
                return _truncate_detail(message)
    return f"HTTP {exc.code}"


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
    prompt_path: Path | None = None,
    timeout: int = 90,
) -> str:
    """Generate AI release notes via the ASMA AI backend.

    Raises ``RuntimeError`` on failure (missing template, HTTP error, empty output).
    """
    prompt_path = prompt_path or _DEFAULT_PROMPT_PATH
    if not prompt_path.exists():
        raise RuntimeError(f"Prompt template not found: {prompt_path}")

    prompt = _build_release_notes_prompt(
        template=prompt_path.read_text(encoding="utf-8"),
        package_name=package_name,
        version=version,
        previous_tag=previous_tag,
        current_tag=current_tag,
        commit_lines=commit_lines,
        file_lines=file_lines,
        ast_context=ast_context,
    )

    base_url, system_user, api_token = _resolve_ai_backend_config()
    if not api_token:
        raise RuntimeError("ASMA_AI_API_TOKEN is required for AI release note generation")

    request = urllib.request.Request(
        f"{base_url}/ai/asma-cli/generate-release-notes",
        data=json.dumps({"prompt": prompt}).encode("utf-8"),
        headers={
            "Authorization": _build_ai_auth_header(system_user, api_token),
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as err:
        raise RuntimeError(
            "ASMA AI backend request failed; "
            f"base URL: {base_url}; "
            f"detail: {_extract_ai_error(err)}"
        ) from err
    except (urllib.error.URLError, TimeoutError, OSError) as err:
        raise RuntimeError(
            "ASMA AI backend request failed; "
            f"base URL: {base_url}; "
            f"detail: {_truncate_detail(str(err))}"
        ) from err

    if not isinstance(payload, dict):
        raise RuntimeError("ASMA AI backend returned an unexpected payload")

    content = payload.get("content")
    if isinstance(content, str):
        content = content.strip()
    if not content:
        raise RuntimeError(
            "ASMA AI backend returned empty output; "
            f"base URL: {base_url}"
        )
    return content


# ── CLI: create GitHub Release ────────────────────────────────────────────────


def create_release() -> None:
    """Gather commits, generate notes (AI or fallback), and create a GitHub Release.

    Reads configuration from environment variables:
        VERSION, BUMP_TYPE, PACKAGE_NAME,
        AI_RELEASE_NOTES_ENABLED,
        ASMA_AI_BASE_URL, ASMA_SYSTEM_USER, ASMA_AI_API_TOKEN,
        GITHUB_TOKEN for standard GitHub Actions operations
    """
    version = os.environ["VERSION"]
    bump_type = os.environ.get("BUMP_TYPE", "patch")
    package_name = os.environ.get("PACKAGE_NAME", "package")
    ai_enabled = os.environ.get("AI_RELEASE_NOTES_ENABLED", "true").lower() == "true"
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
            )
            print("✅ AI release notes generated (ASMA AI backend)")
        except (RuntimeError, TimeoutError, FileNotFoundError) as err:
            ai_warning_message = (
                "Stage: AI release note generation. "
                f"Tag: {current_tag}. "
                f"Package: {package_name}. "
                "Model: backend-managed. "
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
                    "- Model: backend-managed",
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
