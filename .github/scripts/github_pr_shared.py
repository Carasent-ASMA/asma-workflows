from __future__ import annotations

import json
import re
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import cast
from urllib import parse, request
from urllib.error import HTTPError
from urllib.parse import urlsplit


# Shared helper for bot branch naming
def build_bot_branch_name(
    prefix: str, name_component: str, sha: str, fallback: str = "branch"
) -> str:
    """Build a deterministic bot branch name with a prefix, sanitized component, and short SHA."""
    sanitized = sanitize_branch_component(name_component, fallback=fallback)
    return f"{prefix}{sanitized}-{sha[:12]}"


def build_metadata_body(summary: str, metadata_items: list[tuple[str, str]]) -> str:
    """Build a stable markdown body for workflow-generated pull requests."""

    metadata_lines = [f"- {label}: {value}" for label, value in metadata_items]
    return f"{summary}\n\n" + "\n".join(metadata_lines) + "\n"


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
class PullRequestInfo:
    """Represent a GitHub pull request used by workflow automation."""

    number: int
    node_id: str
    url: str
    head_ref: str


@dataclass(frozen=True)
class PullRequestMergeAttempt:
    """Represent the result of an immediate pull request merge attempt."""

    merged: bool
    message: str


@dataclass(frozen=True)
class ProtectedBranchSyncResult:
    """Describe the outcome of syncing local HEAD via a protected-branch PR."""

    already_synced: bool
    pull_request: PullRequestInfo | None = None
    merged_immediately: bool = False
    pushed_directly: bool = False


GITHUB_API_BASE_URL = "https://api.github.com"
GRAPHQL_AUTOMERGE_MUTATION = """
mutation EnableWorkflowAutoMerge($pullRequestId: ID!, $mergeMethod: PullRequestMergeMethod!) {
    enablePullRequestAutoMerge(
        input: {
            pullRequestId: $pullRequestId
            mergeMethod: $mergeMethod
        }
    ) {
        pullRequest {
            number
        }
    }
}
""".strip()


def parse_repo_coordinates(value: str) -> RepoCoordinates | None:
    """Parse owner/name coordinates from a git URL or slug."""

    text = value.strip()
    if not text:
        return None

    if text.startswith("git@"):
        _, remainder = text.split(":", 1)
        path_part = remainder
    elif text.startswith("https://") or text.startswith("http://"):
        split_url = urlsplit(text)
        if not split_url.path:
            return None
        path_part = split_url.path
    else:
        path_part = text

    normalized = path_part.strip("/")
    if normalized.endswith(".git"):
        normalized = normalized[:-4]

    parts = [part for part in normalized.split("/") if part]
    if len(parts) < 2:
        return None
    return RepoCoordinates(owner=parts[-2].lower(), repo=parts[-1].lower())


def extract_token_from_authenticated_remote_url(remote_url: str) -> str:
    """Extract an access token from an authenticated HTTPS remote URL."""

    split_url = urlsplit(remote_url)
    token = split_url.password or ""
    if token:
        return token
    raise RuntimeError(f"Could not resolve token from remote URL: {remote_url}")


def parse_repo_slug_from_remote_url(remote_url: str) -> str:
    """Extract owner/repo coordinates from a git remote URL."""

    coordinates = parse_repo_coordinates(remote_url)
    if coordinates is None:
        raise RuntimeError(f"Could not parse GitHub repo slug from: {remote_url}")
    return coordinates.slug


def parse_repo_slug_from_pull_request_url(pull_request_url: str) -> str:
    """Extract owner/repo coordinates from a GitHub pull request URL."""

    split_url = urlsplit(pull_request_url)
    parts = [part for part in split_url.path.strip("/").split("/") if part]
    if len(parts) < 4 or parts[2] != "pull":
        raise RuntimeError(
            f"Could not parse GitHub repo slug from pull request URL: {pull_request_url}"
        )
    return f"{parts[0].lower()}/{parts[1].lower()}"


def sanitize_branch_component(value: str, fallback: str = "branch") -> str:
    """Normalize a branch-name component for bot-generated branches."""

    normalized = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return normalized or fallback


def get_local_head_sha(
    repo_dir: Path,
    run_command: Callable[..., subprocess.CompletedProcess[str]],
) -> str:
    """Return the current local HEAD SHA."""

    return run_command(
        ["git", "-C", str(repo_dir), "rev-parse", "HEAD"],
        capture_output=True,
    ).stdout.strip()


def get_local_head_subject(
    repo_dir: Path,
    run_command: Callable[..., subprocess.CompletedProcess[str]],
    fallback_subject: str,
) -> str:
    """Return the current local HEAD commit subject."""

    subject = run_command(
        ["git", "-C", str(repo_dir), "log", "-1", "--pretty=%s"],
        capture_output=True,
    ).stdout.strip()
    return subject or fallback_subject


def remote_branch_contains_local_head(
    repo_dir: Path,
    remote_name: str,
    branch_name: str,
    run_command: Callable[..., subprocess.CompletedProcess[str]],
) -> bool:
    """Return whether the target remote branch already contains local HEAD."""

    result = run_command(
        [
            "git",
            "-C",
            str(repo_dir),
            "merge-base",
            "--is-ancestor",
            "HEAD",
            f"{remote_name}/{branch_name}",
        ],
        check=False,
    )
    return result.returncode == 0


def push_failure_allows_pull_request_fallback(output: str) -> bool:
    """Return whether a direct branch push failed for an expected policy reason."""

    normalized_output = output.lower()
    expected_markers = (
        "protected branch update failed",
        "changes must be made through a pull request",
        "cannot update this protected ref",
        "non-fast-forward",
        "[rejected]",
        "fetch first",
    )
    return any(marker in normalized_output for marker in expected_markers)


def try_direct_push_to_branch(
    repo_dir: Path,
    remote_name: str,
    target_branch: str,
    run_command: Callable[..., subprocess.CompletedProcess[str]],
) -> bool:
    """Try to update the target branch directly and return whether it succeeded."""

    push_result = run_command(
        [
            "git",
            "-C",
            str(repo_dir),
            "push",
            remote_name,
            f"HEAD:refs/heads/{target_branch}",
        ],
        check=False,
        capture_output=True,
    )
    if push_result.returncode == 0:
        return True

    combined_output = "\n".join(
        part
        for part in (push_result.stdout, push_result.stderr)
        if isinstance(part, str) and part
    )
    if push_failure_allows_pull_request_fallback(combined_output):
        return False

    raise RuntimeError(
        "Direct branch push failed before PR fallback: "
        f"{combined_output or 'no error output returned'}"
    )


def github_request(
    method: str,
    url: str,
    token: str,
    payload: dict[str, object] | None = None,
) -> object:
    """Call the GitHub REST or GraphQL API using the provided token."""

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "asma-workflow-automation",
    }
    body = None
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    api_request = request.Request(url, data=body, headers=headers, method=method)
    try:
        with request.urlopen(api_request) as response:
            content = response.read().decode("utf-8")
    except HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"GitHub API request failed ({exc.code} {exc.reason}): {error_body}"
        ) from exc

    if not content:
        return {}
    return json.loads(content)


def get_branch_rules(
    repository: str,
    branch_name: str,
    token: str,
) -> list[dict[str, object]]:
    """Return the active GitHub rules that apply to the target branch."""

    encoded_branch_name = parse.quote(branch_name, safe="")
    response = github_request(
        "GET",
        f"{GITHUB_API_BASE_URL}/repos/{repository}/rules/branches/{encoded_branch_name}",
        token,
    )
    if not isinstance(response, list):
        raise RuntimeError(f"Unexpected GitHub branch rules payload: {response}")

    rules: list[dict[str, object]] = []
    for item in response:
        if not isinstance(item, dict):
            raise RuntimeError(f"Unexpected GitHub branch rule item: {item}")
        rules.append(cast(dict[str, object], item))
    return rules


def describe_update_rules(rules: list[dict[str, object]]) -> list[str]:
    """Describe branch update rules that can block workflow PR auto-merge."""

    descriptions: list[str] = []
    for rule in rules:
        if rule.get("type") != "update":
            continue

        source = rule.get("ruleset_source")
        source_type = rule.get("ruleset_source_type")
        ruleset_id = rule.get("ruleset_id")

        parts: list[str] = []
        if isinstance(source, str) and source:
            parts.append(source)
        if isinstance(source_type, str) and source_type:
            parts.append(source_type.lower())
        if isinstance(ruleset_id, int):
            parts.append(f"ruleset {ruleset_id}")

        descriptions.append(" / ".join(parts) if parts else "unknown ruleset")

    return descriptions


def ensure_branch_allows_auto_merge(
    repository: str,
    branch_name: str,
    token: str,
    pull_request_url: str,
    subject_label: str = "Workflow PR",
) -> None:
    """Fail early when branch rules would leave the workflow PR blocked."""

    update_rule_descriptions = describe_update_rules(
        get_branch_rules(repository, branch_name, token)
    )
    if not update_rule_descriptions:
        return

    joined_rules = ", ".join(update_rule_descriptions)
    raise RuntimeError(
        f"{subject_label} was created, but auto-merge was not enabled because the target branch "
        f"{repository}:{branch_name} has active Restrict updates rules ({joined_rules}). "
        "This configuration leaves the PR blocked with 'Cannot update this protected ref' "
        "even after auto-merge is enabled in the UI. Disable Restrict updates for the target "
        "branch or merge the PR manually with a bypass-capable actor. "
        f"PR: {pull_request_url}"
    )


def parse_pull_request_info(payload: dict[str, object]) -> PullRequestInfo:
    """Build a typed pull request record from a GitHub API payload."""

    number = payload.get("number")
    node_id = payload.get("node_id")
    html_url = payload.get("html_url")
    head = payload.get("head")
    if not isinstance(number, int):
        raise RuntimeError(f"GitHub PR payload missing integer number: {payload}")
    if not isinstance(node_id, str) or not node_id:
        raise RuntimeError(f"GitHub PR payload missing node_id: {payload}")
    if not isinstance(html_url, str) or not html_url:
        raise RuntimeError(f"GitHub PR payload missing html_url: {payload}")
    if not isinstance(head, dict):
        raise RuntimeError(f"GitHub PR payload missing head ref: {payload}")
    head_ref = head.get("ref")
    if not isinstance(head_ref, str) or not head_ref:
        raise RuntimeError(f"GitHub PR payload missing head ref string: {payload}")
    return PullRequestInfo(
        number=number,
        node_id=node_id,
        url=html_url,
        head_ref=head_ref,
    )


def get_pull_request_state(
    repository: str,
    pull_request_number: int,
    token: str,
) -> tuple[str, bool]:
    """Return the current GitHub pull request state and merged flag."""

    response = github_request(
        "GET",
        f"{GITHUB_API_BASE_URL}/repos/{repository}/pulls/{pull_request_number}",
        token,
    )
    if not isinstance(response, dict):
        raise RuntimeError(f"Unexpected GitHub PR payload: {response}")

    state = response.get("state")
    merged = response.get("merged")
    if not isinstance(state, str):
        raise RuntimeError(f"GitHub PR payload missing state: {response}")
    if not isinstance(merged, bool):
        raise RuntimeError(f"GitHub PR payload missing merged flag: {response}")
    return state, merged


def find_open_pull_request(
    repository: str,
    branch_name: str,
    base_branch: str,
    token: str,
) -> PullRequestInfo | None:
    """Return an existing open PR for the deterministic branch if one exists."""

    coordinates = parse_repo_coordinates(repository)
    if coordinates is None:
        raise RuntimeError(f"Unsupported repository value for PR lookup: {repository}")
    head_ref = parse.quote(f"{coordinates.owner}:{branch_name}", safe=":")
    base_ref = parse.quote(base_branch, safe="")
    response = github_request(
        "GET",
        f"{GITHUB_API_BASE_URL}/repos/{repository}/pulls?state=open&head={head_ref}&base={base_ref}",
        token,
    )
    if not isinstance(response, list):
        raise RuntimeError(f"Unexpected GitHub PR list payload: {response}")
    if not response:
        return None
    first_item = response[0]
    if not isinstance(first_item, dict):
        raise RuntimeError(f"Unexpected GitHub PR item payload: {first_item}")
    return parse_pull_request_info(cast(dict[str, object], first_item))


def create_or_reuse_pull_request(
    repository: str,
    branch_name: str,
    base_branch: str,
    title: str,
    body: str,
    token: str,
    subject_label: str,
) -> PullRequestInfo:
    """Create a workflow PR or reuse an existing open PR for the branch."""

    try:
        response = github_request(
            "POST",
            f"{GITHUB_API_BASE_URL}/repos/{repository}/pulls",
            token,
            {
                "title": title,
                "head": branch_name,
                "base": base_branch,
                "body": body,
                "maintainer_can_modify": False,
            },
        )
        if not isinstance(response, dict):
            raise RuntimeError(f"Unexpected GitHub create PR payload: {response}")
        return parse_pull_request_info(cast(dict[str, object], response))
    except RuntimeError as exc:
        if "A pull request already exists" not in str(exc):
            raise
    existing = find_open_pull_request(repository, branch_name, base_branch, token)
    if existing is None:
        raise RuntimeError(
            f"{subject_label} already exists for branch {branch_name}, but it could not be resolved"
        )
    return existing


def enable_pull_request_auto_merge(
    pull_request: PullRequestInfo,
    token: str,
    merge_method: str,
) -> None:
    """Enable auto-merge for a workflow PR using GitHub GraphQL."""

    response = github_request(
        "POST",
        f"{GITHUB_API_BASE_URL}/graphql",
        token,
        {
            "query": GRAPHQL_AUTOMERGE_MUTATION,
            "variables": {
                "pullRequestId": pull_request.node_id,
                "mergeMethod": merge_method.upper(),
            },
        },
    )
    if not isinstance(response, dict):
        raise RuntimeError(f"Unexpected GitHub GraphQL payload: {response}")
    errors = response.get("errors")
    if not isinstance(errors, list) or not errors:
        return
    messages = [
        error.get("message", "unknown GraphQL error")
        for error in errors
        if isinstance(error, dict)
    ]
    combined = "; ".join(message for message in messages if isinstance(message, str))

    normalized = combined.lower()
    repository: str | None = None
    try:
        repository = parse_repo_slug_from_pull_request_url(pull_request.url)
    except RuntimeError:
        repository = None

    if "clean status" in normalized and repository is not None:
        merge_attempt = try_merge_pull_request_immediately(
            repository,
            pull_request,
            token,
            merge_method,
        )
        if merge_attempt.merged:
            return

        state, merged = get_pull_request_state(
            repository,
            pull_request.number,
            token,
        )
        if merged or state.lower() == "closed":
            return

    raise RuntimeError(
        f"Failed to enable auto-merge for PR #{pull_request.number}: {combined}"
    )


def try_merge_pull_request_immediately(
    repository: str,
    pull_request: PullRequestInfo,
    token: str,
    merge_method: str,
) -> PullRequestMergeAttempt:
    """Try to merge the workflow PR immediately when GitHub considers it ready."""

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "asma-workflow-automation",
        "Content-Type": "application/json",
    }
    body = json.dumps({"merge_method": merge_method.lower()}).encode("utf-8")
    api_request = request.Request(
        f"{GITHUB_API_BASE_URL}/repos/{repository}/pulls/{pull_request.number}/merge",
        data=body,
        headers=headers,
        method="PUT",
    )

    try:
        with request.urlopen(api_request) as response:
            content = response.read().decode("utf-8")
    except HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace")
        if exc.code in {405, 409, 422}:
            return PullRequestMergeAttempt(
                merged=False,
                message=error_body or exc.reason,
            )
        raise RuntimeError(
            f"GitHub merge request failed ({exc.code} {exc.reason}): {error_body}"
        ) from exc

    if not content:
        return PullRequestMergeAttempt(merged=True, message="Merged successfully")

    payload = json.loads(content)
    if not isinstance(payload, dict):
        raise RuntimeError(f"Unexpected GitHub merge payload: {payload}")

    merged = payload.get("merged")
    message = payload.get("message")
    if not isinstance(merged, bool):
        raise RuntimeError(f"GitHub merge payload missing merged flag: {payload}")
    return PullRequestMergeAttempt(
        merged=merged,
        message=message
        if isinstance(message, str) and message
        else "Merged successfully",
    )


def sync_current_head_to_protected_branch_via_pull_request(
    repo_dir: Path,
    remote_name: str,
    target_branch: str,
    remote_url: str,
    source_branch_name: str,
    title: str,
    body: str,
    merge_method: str,
    subject_label: str,
    run_command: Callable[..., subprocess.CompletedProcess[str]],
) -> ProtectedBranchSyncResult:
    """Push local HEAD to a bot branch and sync it through a protected-branch PR."""

    if remote_branch_contains_local_head(
        repo_dir,
        remote_name,
        target_branch,
        run_command,
    ):
        return ProtectedBranchSyncResult(already_synced=True)

    token = extract_token_from_authenticated_remote_url(remote_url)
    repository = parse_repo_slug_from_remote_url(remote_url)

    if try_direct_push_to_branch(
        repo_dir,
        remote_name,
        target_branch,
        run_command,
    ):
        return ProtectedBranchSyncResult(
            already_synced=False,
            pushed_directly=True,
        )

    run_command(
        [
            "git",
            "-C",
            str(repo_dir),
            "push",
            "--force",
            remote_name,
            f"HEAD:{source_branch_name}",
        ]
    )

    pull_request = create_or_reuse_pull_request(
        repository,
        source_branch_name,
        target_branch,
        title,
        body,
        token,
        subject_label=subject_label,
    )

    merge_attempt = try_merge_pull_request_immediately(
        repository,
        pull_request,
        token,
        merge_method,
    )
    if merge_attempt.merged:
        return ProtectedBranchSyncResult(
            already_synced=False,
            pull_request=pull_request,
            merged_immediately=True,
        )

    ensure_branch_allows_auto_merge(
        repository,
        target_branch,
        token,
        pull_request.url,
        subject_label=subject_label,
    )

    enable_pull_request_auto_merge(
        pull_request,
        token,
        merge_method,
    )
    return ProtectedBranchSyncResult(
        already_synced=False,
        pull_request=pull_request,
        merged_immediately=False,
    )
