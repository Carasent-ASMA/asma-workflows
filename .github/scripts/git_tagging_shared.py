#!/usr/bin/env python3
from __future__ import annotations

import os
import re
import subprocess
from collections.abc import Callable
from pathlib import Path

SEMVER_TAG_RE = re.compile(r"^v(\d+)\.(\d+)\.(\d+)$")
SEMVER_VERSION_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")
HOTPATCH_TAG_RE = re.compile(r"^v(\d+)\.(\d+)\.(\d+)-(\d+)$")
RELEASE_BRANCH_RE = re.compile(r"^(?:.+/)?(v\d+\.\d+\.\d+)$")
BREAKING_CHANGE_RE = re.compile(r"^[a-z]+!(\([^)]*\))?:")
FEATURE_RE = re.compile(r"^feat(\([^)]*\))?:")
PATCH_RE = re.compile(
    r"^(fix|docs|style|refactor|hotfix|chore|revert|ci)(\([^)]*\))?:|^Merged |^Merge"
)
BULLET_PREFIX_RE = re.compile(r"^(?:[-*+]\s+|\d+\.\s+)+")

ANALYSIS_STRATEGY_ALL_COMMITS = "all_commits_since_last_stable_tag"
ANALYSIS_STRATEGY_LAST_COMMIT = "last_commit_only"
VALID_ANALYSIS_STRATEGIES = {
    ANALYSIS_STRATEGY_ALL_COMMITS,
    ANALYSIS_STRATEGY_LAST_COMMIT,
}


def run_capture(
    cmd: list[str], allow_fail: bool = False, env: dict[str, str] | None = None
) -> str:
    """Run a command and return stripped stdout."""
    result = subprocess.run(cmd, capture_output=True, text=True, env=env)
    if result.returncode != 0 and not allow_fail:
        raise RuntimeError(f"Command failed: {' '.join(cmd)}\n{result.stderr}")
    return result.stdout.strip()


def run(
    cmd: list[str], check: bool = True, env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[bytes]:
    """Run a command while echoing it for CI logs."""
    print("+", " ".join(cmd))
    return subprocess.run(cmd, check=check, env=env)


def write_output(key: str, value: str) -> None:
    """Write a named step output when running inside GitHub Actions."""
    output_path = os.environ.get("GITHUB_OUTPUT")
    if not output_path:
        return

    # GitHub output commands require heredoc syntax for multiline values.
    delimiter = "__GITHUB_OUTPUT_EOF__"
    while delimiter in value:
        delimiter = f"{delimiter}_X"

    with Path(output_path).open("a", encoding="utf-8") as output_file:
        if "\n" not in value and "\r" not in value:
            output_file.write(f"{key}={value}\n")
            return

        output_file.write(f"{key}<<{delimiter}\n")
        output_file.write(f"{value}\n")
        output_file.write(f"{delimiter}\n")


def parse_version(version: str) -> tuple[int, int, int]:
    """Parse a semantic version string without the leading v prefix."""
    match = SEMVER_VERSION_RE.fullmatch(version)
    if not match:
        raise RuntimeError(f"Invalid semantic version: {version}")
    major, minor, patch = match.groups()
    return int(major), int(minor), int(patch)


def parse_stable_tag(tag: str) -> tuple[int, int, int] | None:
    """Parse a stable tag like v1.2.3 into numeric parts."""
    match = SEMVER_TAG_RE.fullmatch(tag)
    if not match:
        return None
    major, minor, patch = match.groups()
    return int(major), int(minor), int(patch)


def parse_hotpatch_tag(tag: str) -> tuple[int, int, int, int] | None:
    """Parse a hotpatch tag like v1.2.3-4 into numeric parts."""
    match = HOTPATCH_TAG_RE.fullmatch(tag)
    if not match:
        return None
    major, minor, patch, hotpatch = match.groups()
    return int(major), int(minor), int(patch), int(hotpatch)


def bump_version(version: str, bump_type: str) -> str:
    """Return the next semantic version for the given bump type."""
    major, minor, patch = parse_version(version)
    if bump_type == "major":
        major += 1
        minor = 0
        patch = 0
    elif bump_type == "minor":
        minor += 1
        patch = 0
    elif bump_type == "patch":
        patch += 1
    else:
        raise RuntimeError(f"Unsupported bump type: {bump_type}")
    return f"{major}.{minor}.{patch}"


def parse_non_empty_lines(raw_text: str) -> list[str]:
    """Return stripped non-empty lines from a command output string."""
    return [line.strip() for line in raw_text.splitlines() if line.strip()]


def parse_non_empty_chunks(raw_text: str, delimiter: str = "\x00") -> list[str]:
    """Return stripped non-empty chunks from a delimited command output."""
    return [chunk.strip() for chunk in raw_text.split(delimiter) if chunk.strip()]


def normalize_commit_message_line(line: str) -> str:
    """Normalize a commit line so conventional commit prefixes can be detected."""
    normalized_line = line.strip()
    while normalized_line:
        updated_line = BULLET_PREFIX_RE.sub("", normalized_line, count=1).strip()
        if updated_line == normalized_line:
            return normalized_line
        normalized_line = updated_line
    return ""


def extract_commit_message_candidates(commits: list[str]) -> list[str]:
    """Flatten commit messages into normalized candidate lines for analysis."""
    candidates: list[str] = []
    for commit in commits:
        for line in commit.splitlines():
            normalized_line = normalize_commit_message_line(line)
            if normalized_line:
                candidates.append(normalized_line)
    return candidates


def load_commit_subjects(
    strategy: str,
    *,
    base_ref: str | None = None,
    fallback_ref: str = "HEAD",
) -> list[str]:
    """Load commit subjects for release analysis.

    When `base_ref` is provided, commits are read from `base_ref..HEAD`.
    Otherwise, the function falls back to the supplied history reference.
    """
    if strategy not in VALID_ANALYSIS_STRATEGIES:
        raise RuntimeError(f"Unsupported analysis strategy: {strategy}")

    if strategy == ANALYSIS_STRATEGY_LAST_COMMIT:
        commits_raw = run_capture(["git", "log", "-1", "--format=%s"], allow_fail=True)
        return parse_non_empty_lines(commits_raw)

    history_ref = f"{base_ref}..HEAD" if base_ref else fallback_ref
    commits_raw = run_capture(
        ["git", "log", history_ref, "--format=%s"],
        allow_fail=True,
    )
    return parse_non_empty_lines(commits_raw)


def load_commit_messages(
    strategy: str,
    *,
    base_ref: str | None = None,
    fallback_ref: str = "HEAD",
) -> list[str]:
    """Load full commit messages for release analysis."""
    if strategy not in VALID_ANALYSIS_STRATEGIES:
        raise RuntimeError(f"Unsupported analysis strategy: {strategy}")

    if strategy == ANALYSIS_STRATEGY_LAST_COMMIT:
        commits_raw = run_capture(["git", "log", "-1", "--format=%B%x00"], allow_fail=True)
        return parse_non_empty_chunks(commits_raw)

    history_ref = f"{base_ref}..HEAD" if base_ref else fallback_ref
    commits_raw = run_capture(
        ["git", "log", history_ref, "--format=%B%x00"],
        allow_fail=True,
    )
    return parse_non_empty_chunks(commits_raw)


def determine_bump_type(commits: list[str]) -> tuple[str, bool]:
    """Determine semantic bump severity from conventional commit subjects."""
    bump_type = "none"
    should_publish = False

    for commit in extract_commit_message_candidates(commits):
        if BREAKING_CHANGE_RE.search(commit):
            bump_type = "major"
            should_publish = True
            continue

        if bump_type != "major" and FEATURE_RE.search(commit):
            bump_type = "minor"
            should_publish = True
            continue

        if bump_type not in {"major", "minor"} and PATCH_RE.search(commit):
            bump_type = "patch"
            should_publish = True

    return bump_type, should_publish


def find_bump_reason_commit(commits: list[str], bump_type: str) -> str | None:
    """Return the first commit that justifies the chosen bump type."""
    matcher_by_bump_type = {
        "major": BREAKING_CHANGE_RE,
        "minor": FEATURE_RE,
        "patch": PATCH_RE,
    }
    matcher = matcher_by_bump_type.get(bump_type)
    if matcher is None:
        return None

    for commit in extract_commit_message_candidates(commits):
        if matcher.search(commit):
            return commit
    return None


def list_tags(merged_only: bool = False) -> list[str]:
    """Return git tags visible from the current repository state."""
    cmd = ["git", "tag", "--merged"] if merged_only else ["git", "tag", "-l"]
    tags_raw = run_capture(cmd, allow_fail=True)
    return [line.strip() for line in tags_raw.splitlines() if line.strip()]


def get_latest_stable_tag(merged_only: bool = False) -> str | None:
    """Return the highest semantic stable tag in the repository."""
    stable_tags = [
        tag for tag in list_tags(merged_only=merged_only) if parse_stable_tag(tag)
    ]
    if not stable_tags:
        return None
    return max(stable_tags, key=lambda tag: parse_stable_tag(tag) or (0, 0, 0))


def get_latest_stable_version(merged_only: bool = False) -> str | None:
    """Return the latest stable version string without the v prefix."""
    latest_tag = get_latest_stable_tag(merged_only=merged_only)
    if not latest_tag:
        return None
    return latest_tag.removeprefix("v")


def tag_exists(tag: str) -> bool:
    """Return whether the exact git tag exists locally."""
    result = subprocess.run(
        ["git", "rev-parse", "-q", "--verify", f"refs/tags/{tag}"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return result.returncode == 0


def resolve_first_free_tag(
    initial_candidate: str,
    next_candidate: Callable[[str], str],
    build_tag: Callable[[str], str],
    *,
    max_attempts: int,
    error_message: str,
) -> tuple[str, str]:
    """Resolve the first free tag from an ordered sequence of candidates."""
    candidate = initial_candidate
    for _ in range(max_attempts):
        tag = build_tag(candidate)
        if not tag_exists(tag):
            return candidate, tag
        candidate = next_candidate(candidate)
    raise RuntimeError(error_message)