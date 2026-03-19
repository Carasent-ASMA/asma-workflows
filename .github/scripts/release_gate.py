#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import re
import sys
from pathlib import Path
from types import ModuleType
from typing import Protocol
from typing import cast


def _load_shared_module() -> ModuleType:
    """Load the shared tagging helpers from the sibling file."""
    module_path = Path(__file__).resolve().with_name("git_tagging_shared.py")
    spec = importlib.util.spec_from_file_location("git_tagging_shared", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load module spec for {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class GitTaggingSharedProtocol(Protocol):
    ANALYSIS_STRATEGY_ALL_COMMITS: str
    ANALYSIS_STRATEGY_LAST_COMMIT: str
    FORCE_RELEASE_MARKER: str
    VALID_ANALYSIS_STRATEGIES: set[str]

    def determine_bump_type(self, commits: list[str]) -> tuple[str, bool]: ...

    def find_bump_reason_commit(self, commits: list[str], bump_type: str) -> str | None: ...

    def has_forced_release_marker(self, commits: list[str]) -> bool: ...

    def find_forced_release_reason_commit(self, commits: list[str]) -> str | None: ...

    def get_latest_stable_tag(self, merged_only: bool = False) -> str | None: ...

    def load_commit_messages(
        self,
        strategy: str,
        *,
        base_ref: str | None = None,
        fallback_ref: str = "HEAD",
    ) -> list[str]: ...

    def parse_non_empty_lines(self, raw_text: str) -> list[str]: ...

    def run_capture(
        self,
        cmd: list[str],
        allow_fail: bool = False,
        env: dict[str, str] | None = None,
    ) -> str: ...

    def write_output(self, key: str, value: str) -> None: ...


_SHARED = cast(GitTaggingSharedProtocol, _load_shared_module())

ANALYSIS_STRATEGY_ALL_COMMITS: str = _SHARED.ANALYSIS_STRATEGY_ALL_COMMITS
ANALYSIS_STRATEGY_LAST_COMMIT: str = _SHARED.ANALYSIS_STRATEGY_LAST_COMMIT
FORCE_RELEASE_MARKER: str = _SHARED.FORCE_RELEASE_MARKER
VALID_ANALYSIS_STRATEGIES: set[str] = _SHARED.VALID_ANALYSIS_STRATEGIES
determine_bump_type = _SHARED.determine_bump_type
find_bump_reason_commit = _SHARED.find_bump_reason_commit
find_forced_release_reason_commit = _SHARED.find_forced_release_reason_commit
get_latest_stable_tag = _SHARED.get_latest_stable_tag
has_forced_release_marker = _SHARED.has_forced_release_marker
load_commit_messages_from_shared = _SHARED.load_commit_messages
parse_non_empty_lines = _SHARED.parse_non_empty_lines
run_capture = _SHARED.run_capture
write_output = _SHARED.write_output


def list_changed_files(base_ref: str | None) -> list[str]:
    """List changed files between a base ref and HEAD.

    When no stable tag exists yet, treat the current tracked tree as eligible for the
    first release decision.
    """
    if base_ref is None:
        changed_files_raw = run_capture(
            ["git", "ls-tree", "-r", "--name-only", "HEAD"], allow_fail=True
        )
        return parse_non_empty_lines(changed_files_raw)

    changed_files_raw = run_capture(
        ["git", "diff", "--name-only", f"{base_ref}..HEAD"], allow_fail=True
    )
    return parse_non_empty_lines(changed_files_raw)


def has_matching_changes(
    changed_files: list[str], patterns: list[str]
) -> tuple[bool, str | None]:
    """Return whether any changed file matches the supplied regex patterns."""
    compiled_patterns = [re.compile(pattern) for pattern in patterns]
    for file_path in changed_files:
        if any(pattern.search(file_path) for pattern in compiled_patterns):
            return True, file_path
    return False, None


def load_commit_messages(strategy: str, base_ref: str | None) -> list[str]:
    """Load full commit messages for release analysis."""
    return load_commit_messages_from_shared(
        strategy,
        base_ref=base_ref,
        fallback_ref="HEAD",
    )


def cmd_check_path_changes(args: argparse.Namespace) -> None:
    """Check whether any changed file path matches the supplied regex patterns."""
    base_ref = args.base_ref or get_latest_stable_tag()
    changed_files = list_changed_files(base_ref)
    has_changes, first_match = has_matching_changes(changed_files, args.patterns)

    print(f"Changed files since {base_ref or 'repository start'}:")
    for file_path in changed_files:
        print(file_path)

    if first_match:
        print(f"Matched eligible file: {first_match}")

    write_output("base_ref", base_ref or "")
    write_output("changed", "true" if has_changes else "false")
    write_output(args.result_output_key, "true" if has_changes else "false")
    write_output("changed_files", "\n".join(changed_files))

    if has_changes:
        print("✅ Eligible file changes detected")
    else:
        print("⏭️  No eligible file changes detected")


def cmd_release_gate(args: argparse.Namespace) -> None:
    """Check whether the workflow should continue toward a release."""
    base_ref = args.base_ref or get_latest_stable_tag()

    # Path-based gating is intentionally disabled. Keep the old logic commented so
    # it can be restored quickly if the workflow needs file-pattern gating again.
    # changed_files = list_changed_files(base_ref)
    # code_changed, first_match = has_matching_changes(changed_files, args.patterns)
    changed_files: list[str] = []
    first_match: str | None = None

    commits = load_commit_messages(args.strategy, base_ref)
    bump_type, should_publish = determine_bump_type(commits)
    forced_release = has_forced_release_marker(commits)
    reason_commit = find_bump_reason_commit(commits, bump_type)

    if forced_release and not should_publish:
        bump_type = "patch"
        should_publish = True
        reason_commit = find_forced_release_reason_commit(commits)

    code_changed = should_publish
    should_continue = should_publish

    print(
        f"Release gate analyzed full commit messages since {base_ref or 'repository start'}"
    )

    if first_match:
        print(f"Matched eligible file: {first_match}")

    if commits:
        print("Analyzed commit messages:")
        for commit in commits:
            print(commit)

    if reason_commit:
        print(f"Matched release commit: {reason_commit}")

    if forced_release:
        print(
            f"Release gate override active via {FORCE_RELEASE_MARKER}; continuing with {bump_type} release"
        )

    write_output("base_ref", base_ref or "")
    write_output("changed", "true" if code_changed else "false")
    write_output("code_changed", "true" if code_changed else "false")
    write_output("changed_files", "\n".join(changed_files))
    write_output("analysis_strategy", args.strategy)
    write_output("should_publish", "true" if should_publish else "false")
    write_output("bump_type", bump_type)
    write_output("should_continue", "true" if should_continue else "false")
    if reason_commit:
        write_output("reason_commit", reason_commit)

    if should_continue:
        print(f"✅ Continue workflow with {bump_type} release")
        return

    if not commits:
        print("⏭️  Stop early: no commits found for release analysis")
        return

    print("⏭️  Stop early: no release-worthy commit messages found")


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""
    parser = argparse.ArgumentParser(description="Shared build gating helper")
    subparsers = parser.add_subparsers(dest="command", required=True)

    check_changes_parser = subparsers.add_parser("check-path-changes")
    check_changes_parser.add_argument("--base-ref")
    check_changes_parser.add_argument("--patterns", nargs="+", required=True)
    check_changes_parser.add_argument(
        "--result-output-key",
        default="changed",
        help="Workflow output key for the boolean gate result",
    )
    check_changes_parser.set_defaults(func=cmd_check_path_changes)

    release_gate_parser = subparsers.add_parser("release-gate")
    release_gate_parser.add_argument("--base-ref")
    release_gate_parser.add_argument("--patterns", nargs="+", required=True)
    release_gate_parser.add_argument(
        "--strategy",
        default=ANALYSIS_STRATEGY_ALL_COMMITS,
        choices=sorted(VALID_ANALYSIS_STRATEGIES),
    )
    release_gate_parser.set_defaults(func=cmd_release_gate)

    return parser


def main() -> None:
    """Dispatch change gating helper commands."""
    parser = build_parser()
    args = parser.parse_args()
    try:
        args.func(args)
    except RuntimeError as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()