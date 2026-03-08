#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import re
import sys
from collections.abc import Callable
from pathlib import Path
from types import ModuleType
from typing import Any
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
    RELEASE_BRANCH_RE: re.Pattern[str]

    def bump_version(self, version: str, bump_type: str) -> str: ...

    def get_latest_stable_tag(self, merged_only: bool = False) -> str | None: ...

    def get_latest_stable_version(
        self, merged_only: bool = False
    ) -> str | None: ...

    def resolve_first_free_tag(
        self,
        initial_candidate: str,
        next_candidate: Callable[[str], str],
        build_tag: Callable[[str], str],
        *,
        max_attempts: int,
        error_message: str,
    ) -> tuple[str, str]: ...

    def tag_exists(self, tag: str) -> bool: ...

    def write_output(self, key: str, value: str) -> None: ...


_SHARED = cast(GitTaggingSharedProtocol, _load_shared_module())

RELEASE_BRANCH_RE: re.Pattern[str] = _SHARED.RELEASE_BRANCH_RE
bump_version = _SHARED.bump_version
get_latest_stable_tag = _SHARED.get_latest_stable_tag
get_latest_stable_version = _SHARED.get_latest_stable_version
resolve_first_free_tag = _SHARED.resolve_first_free_tag
tag_exists = _SHARED.tag_exists
write_output = _SHARED.write_output


def resolve_free_stable_tag(
    initial_version: str, bump_type: str, max_attempts: int = 10
) -> tuple[str, str]:
    """Return the first free stable tag reachable from the initial version."""
    return resolve_first_free_tag(
        initial_candidate=initial_version,
        next_candidate=lambda version: bump_version(version, bump_type),
        build_tag=lambda version: f"v{version}",
        max_attempts=max_attempts,
        error_message=(
            "Unable to find a free stable tag after "
            f"{max_attempts} attempts starting from v{initial_version}"
        ),
    )


def resolve_next_stable_release(
    bump_type: str, fallback_version: str, max_attempts: int = 10
) -> tuple[str, str]:
    """Resolve the next available stable version and tag for a release."""
    latest_stable_version = get_latest_stable_version()
    base_version = latest_stable_version or fallback_version
    initial_version = bump_version(base_version, bump_type)
    return resolve_free_stable_tag(initial_version, bump_type, max_attempts)


def extract_release_branch_tag(branch_name: str) -> str:
    """Extract the release base tag from a branch name like release/v1.2.3."""
    match = RELEASE_BRANCH_RE.fullmatch(branch_name.strip())
    if not match:
        raise RuntimeError(
            "Branch name does not comply with the required format */vN.N.N"
        )
    return match.group(1)


def resolve_hotpatch_tag(branch_name: str) -> tuple[str, str]:
    """Resolve the first free hotpatch tag for the release branch."""
    base_tag = extract_release_branch_tag(branch_name)
    latest_merged_stable_tag = get_latest_stable_tag(merged_only=True)
    if latest_merged_stable_tag != base_tag:
        raise RuntimeError(
            "Branch base version does not match the latest stable tag "
            "available on the current branch"
        )

    _, tag = resolve_first_free_tag(
        initial_candidate="1",
        next_candidate=lambda current: str(int(current) + 1),
        build_tag=lambda current: f"{base_tag}-{current}",
        max_attempts=10,
        error_message=(
            "Unable to find a free hotpatch tag after 10 attempts "
            f"starting from {base_tag}-1"
        ),
    )
    version = tag.removeprefix("v")
    return version, tag


def resolve_prerelease_tag(
    pr_number: str,
    branch_name: str | None = None,
    allowed_branch_prefixes: list[str] | None = None,
    enforce_branch_match: bool = False,
) -> str:
    """Resolve a pull-request tag like pr123 with optional branch checks."""
    if not pr_number.isdigit():
        raise RuntimeError("PR number must be numeric")
    if enforce_branch_match:
        if not branch_name:
            raise RuntimeError(
                "branch_name is required when enforce_branch_match is enabled"
            )
        prefixes = allowed_branch_prefixes or []
        if prefixes and not any(branch_name.startswith(prefix) for prefix in prefixes):
            raise RuntimeError(
                f"Branch '{branch_name}' does not match allowed prefixes: "
                f"{', '.join(prefixes)}"
            )
    return f"pr{pr_number}"


def cmd_tag_exists(args: argparse.Namespace) -> None:
    """Check whether a tag exists and export the boolean result."""
    exists = tag_exists(args.tag)
    print("true" if exists else "false")
    write_output("tag_exists", "true" if exists else "false")


def cmd_resolve_stable_tag(args: argparse.Namespace) -> None:
    """Resolve the first free stable tag from a provided starting version."""
    version, tag = resolve_free_stable_tag(
        initial_version=args.initial_version,
        bump_type=args.bump_type,
        max_attempts=args.max_attempts,
    )
    print(tag)
    write_output("version", version)
    write_output("tag", tag)


def cmd_resolve_next_stable_release(args: argparse.Namespace) -> None:
    """Resolve the next stable release tag and export the result."""
    version, tag = resolve_next_stable_release(
        bump_type=args.bump_type,
        fallback_version=args.fallback_version,
        max_attempts=args.max_attempts,
    )
    print(tag)
    write_output("version", version)
    write_output("tag", tag)


def cmd_resolve_hotpatch_tag(args: argparse.Namespace) -> None:
    """Resolve the next hotpatch tag for the current release branch."""
    version, tag = resolve_hotpatch_tag(args.branch_name)
    print(tag)
    write_output("version", version)
    write_output("tag", tag)


def cmd_resolve_prerelease_tag(args: argparse.Namespace) -> None:
    """Resolve a prerelease tag and export it for later workflow steps."""
    tag = resolve_prerelease_tag(
        pr_number=args.pr_number,
        branch_name=args.branch_name,
        allowed_branch_prefixes=args.allowed_branch_prefixes,
        enforce_branch_match=args.enforce_branch_match,
    )
    print(tag)
    write_output("tag", tag)


def register_subcommands(
    subparsers: Any,
) -> None:
    """Register read-only planning subcommands on a parser."""
    tag_exists_parser = subparsers.add_parser("tag-exists")
    tag_exists_parser.add_argument("--tag", required=True)
    tag_exists_parser.set_defaults(func=cmd_tag_exists)

    resolve_stable_parser = subparsers.add_parser("resolve-stable-tag")
    resolve_stable_parser.add_argument("--initial-version", required=True)
    resolve_stable_parser.add_argument(
        "--bump-type", required=True, choices=["major", "minor", "patch"]
    )
    resolve_stable_parser.add_argument("--max-attempts", type=int, default=10)
    resolve_stable_parser.set_defaults(func=cmd_resolve_stable_tag)

    resolve_next_stable_parser = subparsers.add_parser(
        "resolve-next-stable-release"
    )
    resolve_next_stable_parser.add_argument(
        "--bump-type", required=True, choices=["major", "minor", "patch"]
    )
    resolve_next_stable_parser.add_argument("--fallback-version", required=True)
    resolve_next_stable_parser.add_argument("--max-attempts", type=int, default=10)
    resolve_next_stable_parser.set_defaults(func=cmd_resolve_next_stable_release)

    resolve_hotpatch_parser = subparsers.add_parser("resolve-hotpatch-tag")
    resolve_hotpatch_parser.add_argument("--branch-name", required=True)
    resolve_hotpatch_parser.set_defaults(func=cmd_resolve_hotpatch_tag)

    resolve_prerelease_parser = subparsers.add_parser("resolve-prerelease-tag")
    resolve_prerelease_parser.add_argument("--pr-number", required=True)
    resolve_prerelease_parser.add_argument("--branch-name")
    resolve_prerelease_parser.add_argument(
        "--allowed-branch-prefixes", nargs="*", default=[]
    )
    resolve_prerelease_parser.add_argument(
        "--enforce-branch-match", action="store_true"
    )
    resolve_prerelease_parser.set_defaults(func=cmd_resolve_prerelease_tag)


def build_parser() -> argparse.ArgumentParser:
    """Build the read-only git release planning parser."""
    parser = argparse.ArgumentParser(description="Shared git release planning helper")
    subparsers = parser.add_subparsers(dest="command", required=True)
    register_subcommands(subparsers)
    return parser


def main() -> None:
    """Dispatch read-only release planning subcommands."""
    parser = build_parser()
    args = parser.parse_args()
    try:
        args.func(args)
    except RuntimeError as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()