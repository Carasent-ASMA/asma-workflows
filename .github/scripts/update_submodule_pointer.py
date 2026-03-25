#!/usr/bin/env python3
from __future__ import annotations

import argparse
import configparser
import importlib.util
import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent


def load_script_module(module_name: str):
    """Load a sibling shared helper module from the scripts directory."""

    module_spec = importlib.util.spec_from_file_location(
        module_name,
        SCRIPT_DIR / f"{module_name}.py",
    )
    if module_spec is None or module_spec.loader is None:
        raise ImportError(f"Could not load {module_name}.py")
    module = importlib.util.module_from_spec(module_spec)
    sys.modules[module_name] = module
    module_spec.loader.exec_module(module)
    return module


github_pr_shared = load_script_module("github_pr_shared")


def write_output(key: str, value: str) -> None:
    """Write a GitHub Actions step output when available."""
    output_path = os.environ.get("GITHUB_OUTPUT")
    if not output_path:
        return
    with Path(output_path).open("a", encoding="utf-8") as output_file:
        output_file.write(f"{key}={value}\n")


@dataclass(frozen=True)
class RepoCoordinates:
    """Normalized repository coordinates used for matching."""

    owner: str
    repo: str

    @property
    def slug(self) -> str:
        """Return the repository slug in owner/name form."""

        return f"{self.owner}/{self.repo}"


@dataclass(frozen=True)
class SubmoduleMapping:
    """Describe a submodule entry from .gitmodules."""

    name: str
    path: str
    url: str
    coordinates: RepoCoordinates | None


@dataclass(frozen=True)
class PointerUpdateResult:
    """Represent the outcome of a pointer update attempt."""

    status: str
    submodule_path: str | None
    target_sha: str | None
    message: str
    branch_name: str | None = None
    pr_number: str | None = None
    pr_url: str | None = None

    @property
    def updated(self) -> bool:
        """Return whether the pointer was updated in asma-modules."""
        return self.status in {"updated", "already-open"}

PullRequestInfo = github_pr_shared.PullRequestInfo
PullRequestMergeAttempt = github_pr_shared.PullRequestMergeAttempt


class GitCommandError(RuntimeError):
    """Raise when a git command fails."""

def run_git(
    args: list[str],
    *,
    cwd: Path | None = None,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    """Run a git command and optionally raise on failure."""
    result = subprocess.run(
        args,
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )
    if check and result.returncode != 0:
        raise GitCommandError(result.stderr.strip() or result.stdout.strip())
    return result


def parse_repo_coordinates(value: str) -> RepoCoordinates | None:
    """Parse owner/name coordinates from a git URL or slug."""

    parsed = github_pr_shared.parse_repo_coordinates(value)
    if parsed is None:
        return None
    return RepoCoordinates(owner=parsed.owner, repo=parsed.repo)


def load_submodule_mappings(gitmodules_path: Path) -> list[SubmoduleMapping]:
    """Load submodule path and URL mappings from .gitmodules."""
    def preserve_option_name(optionstr: str) -> str:
        """Preserve original git config option casing."""
        return optionstr

    parser = configparser.ConfigParser(interpolation=None)
    parser.optionxform = preserve_option_name
    parser.read(gitmodules_path, encoding="utf-8")

    mappings: list[SubmoduleMapping] = []
    for section_name in parser.sections():
        if not section_name.startswith('submodule '):
            continue
        path = parser.get(section_name, 'path', fallback='').strip()
        url = parser.get(section_name, 'url', fallback='').strip()
        if not path or not url:
            continue
        name = section_name.removeprefix('submodule ').strip().strip('"')
        mappings.append(
            SubmoduleMapping(
                name=name,
                path=path,
                url=url,
                coordinates=parse_repo_coordinates(url),
            )
        )
    return mappings


def resolve_submodule_path(
    mappings: list[SubmoduleMapping],
    caller_repository: str,
    explicit_submodule_path: str | None,
) -> str | None:
    """Resolve the asma-modules path for the caller repository."""
    if explicit_submodule_path:
        return explicit_submodule_path

    caller_coordinates = parse_repo_coordinates(caller_repository)
    if caller_coordinates is None:
        raise RuntimeError(f"Unsupported caller repository value: {caller_repository}")

    exact_matches = [
        mapping.path
        for mapping in mappings
        if mapping.coordinates is not None
        and mapping.coordinates.slug == caller_coordinates.slug
    ]
    if len(exact_matches) == 1:
        return exact_matches[0]
    if len(exact_matches) > 1:
        raise RuntimeError(
            f"Ambiguous submodule mapping for {caller_repository}: {', '.join(exact_matches)}"
        )

    repo_name_matches = [
        mapping.path
        for mapping in mappings
        if mapping.coordinates is not None
        and mapping.coordinates.repo == caller_coordinates.repo
    ]
    if len(repo_name_matches) == 1:
        return repo_name_matches[0]
    if len(repo_name_matches) > 1:
        raise RuntimeError(
            f"Ambiguous repo-name mapping for {caller_repository}: {', '.join(repo_name_matches)}"
        )

    path_name_matches = [
        mapping.path
        for mapping in mappings
        if Path(mapping.path).name == caller_coordinates.repo
    ]
    if len(path_name_matches) == 1:
        return path_name_matches[0]
    if len(path_name_matches) > 1:
        raise RuntimeError(
            f"Ambiguous path-name mapping for {caller_repository}: {', '.join(path_name_matches)}"
        )

    return None


def resolve_remote_branch_head(repo_path: Path, branch_name: str) -> str:
    """Resolve the current origin branch head SHA for a repository checkout."""
    result = run_git(
        ["git", "ls-remote", "origin", f"refs/heads/{branch_name}"],
        cwd=repo_path,
    )
    output = result.stdout.strip()
    if not output:
        raise RuntimeError(f"Unable to resolve origin/{branch_name} for {repo_path}")
    return output.split()[0]


def build_github_remote_url(repository: str, token: str) -> str:
    """Build an authenticated GitHub HTTPS URL for the target repository."""
    return f"https://x-access-token:{token}@github.com/{repository}.git"



def build_pointer_branch_name(submodule_path: str, target_sha: str) -> str:
    """Build a deterministic branch name for a pointer update using the shared helper."""
    return github_pr_shared.build_bot_branch_name(
        prefix="bot/pointer/",
        name_component=submodule_path,
        sha=target_sha,
        fallback="submodule",
    )


def clone_repository(remote_url: str, branch_name: str, destination: Path) -> Path:
    """Clone the target repository at the requested branch."""
    repo_path = destination / "repo"
    run_git(
        [
            "git",
            "clone",
            "--depth",
            "1",
            "--branch",
            branch_name,
            "--filter=blob:none",
            remote_url,
            str(repo_path),
        ]
    )
    return repo_path


def read_gitlink_sha(repo_path: Path, submodule_path: str) -> str | None:
    """Read the gitlink SHA currently stored for a submodule path."""
    result = run_git(
        ["git", "ls-tree", "HEAD", submodule_path],
        cwd=repo_path,
        check=False,
    )
    output = result.stdout.strip()
    if not output:
        return None
    fields = output.split()
    if len(fields) < 3:
        return None
    return fields[2]


def configure_commit_identity(repo_path: Path, user_name: str, user_email: str) -> None:
    """Configure the git identity used for pointer commits."""
    run_git(["git", "config", "user.name", user_name], cwd=repo_path)
    run_git(["git", "config", "user.email", user_email], cwd=repo_path)


def checkout_pointer_branch(repo_path: Path, branch_name: str) -> None:
    """Create a fresh local branch for the pointer update commit."""
    run_git(["git", "checkout", "-b", branch_name], cwd=repo_path)


def create_pointer_commit(repo_path: Path, submodule_path: str, target_sha: str) -> None:
    """Stage and commit a gitlink update for the resolved submodule path."""
    run_git(
        [
            "git",
            "update-index",
            "--cacheinfo",
            f"160000,{target_sha},{submodule_path}",
        ],
        cwd=repo_path,
    )
    short_sha = target_sha[:12]
    message = (
        f"chore(pointer): advance {submodule_path} to {short_sha} [skip ci]\n\n"
        f"Source: {target_sha}"
    )
    run_git(["git", "commit", "-m", message], cwd=repo_path)


def push_pointer_commit(repo_path: Path, branch_name: str) -> subprocess.CompletedProcess[str]:
    """Push the current HEAD to a deterministic bot branch."""
    return run_git(
        ["git", "push", "--force", "origin", f"HEAD:{branch_name}"],
        cwd=repo_path,
        check=False,
    )


def ensure_branch_allows_auto_merge(
    repository: str,
    branch_name: str,
    token: str,
    pull_request_url: str,
) -> None:
    """Fail early when branch rules would leave the pointer PR auto-merge blocked."""
    github_pr_shared.ensure_branch_allows_auto_merge(
        repository,
        branch_name,
        token,
        pull_request_url,
        subject_label="Pointer PR",
    )

parse_pull_request_info = github_pr_shared.parse_pull_request_info
find_open_pointer_pull_request = github_pr_shared.find_open_pull_request



def create_pointer_pull_request(
    repository: str,
    branch_name: str,
    base_branch: str,
    submodule_path: str,
    target_sha: str,
    caller_repository: str,
    token: str,
) -> PullRequestInfo:
    """Create a pointer PR or reuse an existing open PR for the deterministic branch."""
    title = f"chore(pointer): advance {submodule_path} to {target_sha[:12]}"
    body = github_pr_shared.build_metadata_body(
        "Automated pointer update generated by the shared submodule updater.",
        [
            ("submodule path", submodule_path),
            ("source repository", caller_repository),
            ("source sha", target_sha),
            ("target branch", base_branch),
        ],
    )
    return github_pr_shared.create_or_reuse_pull_request(
        repository,
        branch_name,
        base_branch,
        title,
        body,
        token,
        subject_label="Pointer PR",
    )

enable_pull_request_auto_merge = github_pr_shared.enable_pull_request_auto_merge
try_merge_pull_request_immediately = github_pr_shared.try_merge_pull_request_immediately


def update_pointer_for_latest_master(
    *,
    caller_repo_path: Path,
    caller_repository: str,
    caller_sha: str,
    caller_ref_name: str,
    expected_branch: str,
    asma_modules_repository: str | None = None,
    asma_modules_token: str | None = None,
    asma_modules_remote_url: str | None = None,
    asma_modules_branch: str,
    explicit_submodule_path: str | None,
    fail_if_unmapped: bool,
    git_user_name: str,
    git_user_email: str,
    auto_merge_method: str,
) -> PointerUpdateResult:
    """Open or refresh a pointer PR when the caller SHA is the latest master SHA."""
    should_manage_github_pull_request = (
        asma_modules_remote_url is None
        and asma_modules_repository is not None
        and asma_modules_token is not None
    )

    if caller_ref_name != expected_branch:
        return PointerUpdateResult(
            status="skipped-non-target-branch",
            submodule_path=explicit_submodule_path,
            target_sha=caller_sha,
            message=f"Branch {caller_ref_name} does not match {expected_branch}",
        )

    if asma_modules_remote_url is None and not asma_modules_token:
        return PointerUpdateResult(
            status="skipped-missing-token",
            submodule_path=explicit_submodule_path,
            target_sha=caller_sha,
            message="ASMA_MODULES_TOKEN is not configured; skipping pointer update",
        )

    latest_caller_sha = resolve_remote_branch_head(caller_repo_path, expected_branch)
    if latest_caller_sha != caller_sha:
        return PointerUpdateResult(
            status="skipped-not-latest-master",
            submodule_path=explicit_submodule_path,
            target_sha=caller_sha,
            message=(
                f"Caller SHA {caller_sha} is stale; latest {expected_branch} SHA is {latest_caller_sha}"
            ),
        )

    if asma_modules_remote_url is None:
        if asma_modules_repository is None or asma_modules_token is None:
            raise RuntimeError("Target repository and token are required")
        asma_modules_remote_url = build_github_remote_url(
            asma_modules_repository,
            asma_modules_token,
        )

    with tempfile.TemporaryDirectory(prefix="asma-modules-pointer-") as temp_dir:
        asma_repo_path = clone_repository(
            asma_modules_remote_url,
            asma_modules_branch,
            Path(temp_dir),
        )
        configure_commit_identity(asma_repo_path, git_user_name, git_user_email)

        mappings = load_submodule_mappings(asma_repo_path / ".gitmodules")
        submodule_path = resolve_submodule_path(
            mappings,
            caller_repository,
            explicit_submodule_path,
        )
        if submodule_path is None:
            if fail_if_unmapped:
                raise RuntimeError(
                    f"Unable to resolve submodule path for {caller_repository}"
                )
            return PointerUpdateResult(
                status="skipped-unmapped",
                submodule_path=None,
                target_sha=caller_sha,
                message=f"No submodule mapping found for {caller_repository}",
            )

        current_pointer_sha = read_gitlink_sha(asma_repo_path, submodule_path)
        if current_pointer_sha == caller_sha:
            return PointerUpdateResult(
                status="skipped-pointer-current",
                submodule_path=submodule_path,
                target_sha=caller_sha,
                message=f"Pointer already set to {caller_sha}",
            )

        latest_caller_sha = resolve_remote_branch_head(caller_repo_path, expected_branch)
        if latest_caller_sha != caller_sha:
            return PointerUpdateResult(
                status="skipped-not-latest-master",
                submodule_path=submodule_path,
                target_sha=caller_sha,
                message=(
                    f"Caller SHA {caller_sha} is stale before push; latest {expected_branch} SHA is {latest_caller_sha}"
                ),
            )

        if asma_modules_repository is None or asma_modules_token is None:
            raise RuntimeError(
                "Target repository slug and token are required for pointer PR creation"
            )

        branch_name = build_pointer_branch_name(submodule_path, caller_sha)
        checkout_pointer_branch(asma_repo_path, branch_name)
        create_pointer_commit(asma_repo_path, submodule_path, caller_sha)
        push_result = push_pointer_commit(asma_repo_path, branch_name)
        if push_result.returncode != 0:
            raise RuntimeError(
                "Failed to push pointer branch to asma-modules: "
                + (push_result.stderr.strip() or push_result.stdout.strip())
            )

        pull_request = find_open_pointer_pull_request(
            asma_modules_repository,
            branch_name,
            asma_modules_branch,
            asma_modules_token,
        )
        if pull_request is None:
            pull_request = create_pointer_pull_request(
                asma_modules_repository,
                branch_name,
                asma_modules_branch,
                submodule_path,
                caller_sha,
                caller_repository,
                asma_modules_token,
            )

        if should_manage_github_pull_request:
            ensure_branch_allows_auto_merge(
                asma_modules_repository,
                asma_modules_branch,
                asma_modules_token,
                pull_request.url,
            )

            merge_attempt = try_merge_pull_request_immediately(
                asma_modules_repository,
                pull_request,
                asma_modules_token,
                auto_merge_method,
            )
            if merge_attempt.merged:
                return PointerUpdateResult(
                    status="updated",
                    submodule_path=submodule_path,
                    target_sha=caller_sha,
                    message=(
                        f"Merged pointer PR #{pull_request.number} for {submodule_path} "
                        f"to {caller_sha[:12]} immediately"
                    ),
                    branch_name=branch_name,
                    pr_number=str(pull_request.number),
                    pr_url=pull_request.url,
                )

        enable_pull_request_auto_merge(
            pull_request,
            asma_modules_token,
            auto_merge_method,
        )
        return PointerUpdateResult(
            status="updated",
            submodule_path=submodule_path,
            target_sha=caller_sha,
            message=(
                f"Opened or refreshed pointer PR #{pull_request.number} for {submodule_path} "
                f"to {caller_sha[:12]} with auto-merge enabled"
            ),
            branch_name=branch_name,
            pr_number=str(pull_request.number),
            pr_url=pull_request.url,
        )


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line parser for pointer updates."""
    parser = argparse.ArgumentParser(description="Update asma-modules submodule pointers")
    subparsers = parser.add_subparsers(dest="command", required=True)

    update_parser = subparsers.add_parser("update-pointer")
    update_parser.add_argument("--caller-repo-path", required=True)
    update_parser.add_argument("--caller-repository", required=True)
    update_parser.add_argument("--caller-sha", required=True)
    update_parser.add_argument("--caller-ref-name", required=True)
    update_parser.add_argument("--expected-branch", default="master")
    update_parser.add_argument("--asma-modules-repository", default="Carasent-ASMA/asma-modules")
    update_parser.add_argument("--asma-modules-branch", default="master")
    update_parser.add_argument("--auto-merge-method", default="squash")
    update_parser.add_argument("--submodule-path", default="")
    update_parser.add_argument("--git-user-name", default="github-actions[bot]")
    update_parser.add_argument(
        "--git-user-email",
        default="github-actions[bot]@users.noreply.github.com",
    )
    update_parser.add_argument(
        "--fail-if-unmapped",
        choices=["true", "false"],
        default="true",
    )
    return parser


def cmd_update_pointer(args: argparse.Namespace) -> int:
    """Execute the pointer update command and write GitHub step outputs."""
    token = os.environ.get("ASMA_MODULES_TOKEN", "")
    result = update_pointer_for_latest_master(
        caller_repo_path=Path(args.caller_repo_path).resolve(),
        caller_repository=args.caller_repository,
        caller_sha=args.caller_sha,
        caller_ref_name=args.caller_ref_name,
        expected_branch=args.expected_branch,
        asma_modules_repository=args.asma_modules_repository,
        asma_modules_token=token,
        asma_modules_branch=args.asma_modules_branch,
        explicit_submodule_path=args.submodule_path or None,
        fail_if_unmapped=args.fail_if_unmapped == "true",
        git_user_name=args.git_user_name,
        git_user_email=args.git_user_email,
        auto_merge_method=args.auto_merge_method,
    )

    print(result.message)
    write_output("status", result.status)
    write_output("updated", "true" if result.updated else "false")
    write_output("submodule_path", result.submodule_path or "")
    write_output("target_sha", result.target_sha or "")
    write_output("branch_name", result.branch_name or "")
    write_output("pr_number", result.pr_number or "")
    write_output("pr_url", result.pr_url or "")
    return 0


def main() -> int:
    """Run the pointer update CLI."""
    parser = build_parser()
    args = parser.parse_args()
    if args.command == "update-pointer":
        return cmd_update_pointer(args)
    raise RuntimeError(f"Unsupported command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
