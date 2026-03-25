#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import sys
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
    def run(
        self,
        cmd: list[str],
        check: bool = True,
        env: dict[str, str] | None = None,
    ) -> object: ...

    def run_capture(
        self,
        cmd: list[str],
        allow_fail: bool = False,
        env: dict[str, str] | None = None,
    ) -> str: ...

    def tag_exists(self, tag: str) -> bool: ...


_SHARED = cast(GitTaggingSharedProtocol, _load_shared_module())
run = _SHARED.run
run_capture = _SHARED.run_capture
tag_exists = _SHARED.tag_exists


def get_current_commit() -> str:
    """Return the commit SHA currently checked out in the repository."""
    return run_capture(["git", "rev-parse", "HEAD"])


def get_tag_target_commit(tag: str) -> str:
    """Return the peeled commit SHA referenced by a tag."""
    return run_capture(["git", "rev-list", "-n", "1", tag])


def configure_remote_auth(
    *,
    remote_name: str,
    remote_url: str,
    user_name: str,
    user_email: str,
) -> None:
    """Configure git identity and remote URL for later push operations."""
    run(["git", "config", "--global", "user.name", user_name])
    run(["git", "config", "--global", "user.email", user_email])
    run(["git", "remote", "set-url", remote_name, remote_url])


def fetch_tags(remote_name: str | None = None) -> None:
    """Refresh local tag state from the selected remote."""
    cmd = ["git", "fetch"]
    if remote_name:
        cmd.append(remote_name)
    cmd.extend(["--tags", "--force"])
    run(cmd)


def create_annotated_tag(tag: str, message: str) -> None:
    """Create an annotated tag in the local repository.

    If the tag already exists and points to the current commit, treat the
    operation as a no-op so rerunning a release workflow remains safe.
    """
    if tag_exists(tag):
        tag_commit = get_tag_target_commit(tag)
        current_commit = get_current_commit()
        if tag_commit == current_commit:
            print(
                f"Tag {tag} already exists on the current commit {current_commit}; skipping creation"
            )
            return
        raise RuntimeError(
            f"Tag {tag} already exists on commit {tag_commit}, current commit is {current_commit}"
        )

    run(["git", "tag", "-a", tag, "-m", message])


def delete_tag_if_exists(tag: str, remote_name: str | None = None) -> None:
    """Delete a local tag and optionally delete it on a remote."""
    if tag_exists(tag):
        run(["git", "tag", "-d", tag])
    if remote_name:
        run(["git", "push", remote_name, f":refs/tags/{tag}"], check=False)


def push_tag(tag: str, remote_name: str = "origin") -> None:
    """Push a single tag to the selected remote."""
    run(["git", "push", remote_name, f"refs/tags/{tag}"])


def commit_and_push_follow_tags(
    *,
    files: list[str],
    commit_message: str,
    tag: str,
    tag_message: str,
    remote_name: str = "origin",
) -> None:
    """Commit files, create the release tag, and push commit plus tags."""
    run(["git", "add", *files])
    run(["git", "commit", "-m", commit_message])
    create_annotated_tag(tag, tag_message)
    run(["git", "push", remote_name, "--follow-tags"])


def cmd_configure_remote_auth(args: argparse.Namespace) -> None:
    """CLI wrapper for configuring remote authentication."""
    configure_remote_auth(
        remote_name=args.remote_name,
        remote_url=args.remote_url,
        user_name=args.user_name,
        user_email=args.user_email,
    )


def cmd_fetch_tags(args: argparse.Namespace) -> None:
    """CLI wrapper for refreshing remote tags."""
    fetch_tags(remote_name=args.remote_name)


def cmd_create_annotated_tag(args: argparse.Namespace) -> None:
    """CLI wrapper for creating an annotated tag."""
    create_annotated_tag(args.tag, args.message)


def cmd_delete_tag_if_exists(args: argparse.Namespace) -> None:
    """CLI wrapper for deleting a tag locally and optionally remotely."""
    delete_tag_if_exists(args.tag, remote_name=args.remote_name)


def cmd_push_tag(args: argparse.Namespace) -> None:
    """CLI wrapper for pushing a single tag."""
    push_tag(args.tag, remote_name=args.remote_name)


def cmd_commit_and_push_follow_tags(args: argparse.Namespace) -> None:
    """CLI wrapper for commit-plus-tag release operations."""
    commit_and_push_follow_tags(
        files=args.files,
        commit_message=args.commit_message,
        tag=args.tag,
        tag_message=args.tag_message,
        remote_name=args.remote_name,
    )


def register_subcommands(subparsers: Any) -> None:
    """Register git mutation subcommands on a parser."""
    configure_parser = subparsers.add_parser("configure-remote-auth")
    configure_parser.add_argument("--remote-name", default="origin")
    configure_parser.add_argument("--remote-url", required=True)
    configure_parser.add_argument("--user-name", default="github-actions[bot]")
    configure_parser.add_argument(
        "--user-email", default="github-actions[bot]@users.noreply.github.com"
    )
    configure_parser.set_defaults(func=cmd_configure_remote_auth)

    fetch_parser = subparsers.add_parser("fetch-tags")
    fetch_parser.add_argument("--remote-name")
    fetch_parser.set_defaults(func=cmd_fetch_tags)

    create_tag_parser = subparsers.add_parser("create-annotated-tag")
    create_tag_parser.add_argument("--tag", required=True)
    create_tag_parser.add_argument("--message", required=True)
    create_tag_parser.set_defaults(func=cmd_create_annotated_tag)

    delete_tag_parser = subparsers.add_parser("delete-tag-if-exists")
    delete_tag_parser.add_argument("--tag", required=True)
    delete_tag_parser.add_argument("--remote-name")
    delete_tag_parser.set_defaults(func=cmd_delete_tag_if_exists)

    push_tag_parser = subparsers.add_parser("push-tag")
    push_tag_parser.add_argument("--tag", required=True)
    push_tag_parser.add_argument("--remote-name", default="origin")
    push_tag_parser.set_defaults(func=cmd_push_tag)

    commit_push_parser = subparsers.add_parser("commit-and-push-follow-tags")
    commit_push_parser.add_argument("--files", nargs="+", required=True)
    commit_push_parser.add_argument("--commit-message", required=True)
    commit_push_parser.add_argument("--tag", required=True)
    commit_push_parser.add_argument("--tag-message", required=True)
    commit_push_parser.add_argument("--remote-name", default="origin")
    commit_push_parser.set_defaults(func=cmd_commit_and_push_follow_tags)


def build_parser() -> argparse.ArgumentParser:
    """Build the git mutation parser."""
    parser = argparse.ArgumentParser(description="Shared git tag operations helper")
    subparsers = parser.add_subparsers(dest="command", required=True)
    register_subcommands(subparsers)
    return parser


def main() -> None:
    """Dispatch git mutation subcommands."""
    parser = build_parser()
    args = parser.parse_args()
    try:
        args.func(args)
    except RuntimeError as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()