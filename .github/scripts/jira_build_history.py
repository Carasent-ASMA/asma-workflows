#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import json
import os
import re
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from urllib import error, parse, request

ISSUE_KEY_PATTERN = re.compile(r"\b(ASMA)[ -](\d+)\b", re.IGNORECASE)
FIELD_ID_ENV = "JIRA_BUILD_HISTORY_FIELD_ID"
BASE_URL_ENV = "JIRA_BASE_URL"
EMAIL_ENV = "JIRA_EMAIL"
EMAIL_ALIAS_ENV = "JIRA_USER_EMAIL"
API_TOKEN_ENV = "JIRA_API_TOKEN"
SERVICE_HEADING_LEVEL = 3
VERSION_HEADING_LEVEL = 2
VERSION_PREFIX = "Version: "
TITLE_COLOR = "#C9372C"
SUMMARY_COLOR = "#216E4E"
TECHNICAL_COLOR = "#C25100"


def write_output(key: str, value: str) -> None:
    """Write a GitHub Actions output when the runtime provides GITHUB_OUTPUT."""

    output_path = os.getenv("GITHUB_OUTPUT", "").strip()
    if not output_path:
        return
    with Path(output_path).open("a", encoding="utf-8") as output_file:
        output_file.write(f"{key}={value}\n")


def append_summary(lines: list[str]) -> None:
    """Append formatted lines to the GitHub step summary when available."""

    summary_path = os.getenv("GITHUB_STEP_SUMMARY", "").strip()
    if not summary_path:
        return
    with Path(summary_path).open("a", encoding="utf-8") as summary_file:
        summary_file.write("\n".join(lines).rstrip())
        summary_file.write("\n")


@dataclass(frozen=True)
class JiraConfig:
    """Jira connection settings resolved from GitHub Actions secrets."""

    base_url: str
    email: str
    api_token: str
    field_id: str


@dataclass(frozen=True)
class BuildHistoryEntry:
    """Normalized build-history payload used for Jira serialization."""

    service_name: str
    version: str
    release_kind: str
    status: str
    recorded_at_utc: str
    entry_id: str
    family: str
    repository: str
    workflow_name: str
    workflow_file: str
    run_url: str
    event_name: str
    ref_name: str
    commit_sha: str
    commit_url: str
    job_results: str
    jira_key: str | None = None
    pr_number: str | None = None
    pr_url: str | None = None
    git_tag: str | None = None
    git_tag_url: str | None = None
    artifact_url: str | None = None
    image_ref: str | None = None


@dataclass(frozen=True)
class SegmentIdentity:
    """Managed block identity used for smart replacement."""

    service_name: str
    version: str


@dataclass(frozen=True)
class PublishOutcome:
    """Summarize the result of publishing to a single Jira issue."""

    jira_key: str
    updated: bool
    replaced: bool
    collapsed_duplicates: int


class JiraApiError(RuntimeError):
    """Raise for Jira API failures that should be reported in summaries."""


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments for the Jira build history publisher."""

    parser = argparse.ArgumentParser(
        description="Publish GitHub Actions build history to Jira textarea fields."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    publish_parser = subparsers.add_parser(
        "publish",
        help="Read, merge, and update Jira build history for resolved issue keys.",
    )
    publish_parser.add_argument("--service-name", required=True)
    publish_parser.add_argument("--version", required=True)
    publish_parser.add_argument("--release-kind", required=True)
    publish_parser.add_argument("--family", required=True)
    publish_parser.add_argument("--workflow-name", required=True)
    publish_parser.add_argument("--workflow-file", required=True)
    publish_parser.add_argument("--repository", required=True)
    publish_parser.add_argument("--server-url", required=True)
    publish_parser.add_argument("--run-id", required=True)
    publish_parser.add_argument("--run-attempt", required=True)
    publish_parser.add_argument("--event-name", required=True)
    publish_parser.add_argument("--ref-name", required=True)
    publish_parser.add_argument("--commit-sha", required=True)
    publish_parser.add_argument("--job-results", required=True)
    publish_parser.add_argument("--status", default="success")
    publish_parser.add_argument("--jira-key", action="append", default=[])
    publish_parser.add_argument("--jira-source", action="append", default=[])
    publish_parser.add_argument("--pr-number", default="")
    publish_parser.add_argument("--git-tag", default="")
    publish_parser.add_argument("--artifact-url", default="")
    publish_parser.add_argument("--image-ref", default="")
    publish_parser.add_argument("--recorded-at-utc", default="")

    return parser.parse_args(argv)


def resolve_config_from_env() -> JiraConfig:
    """Resolve Jira configuration from workflow environment variables."""

    base_url = os.getenv(BASE_URL_ENV, "").strip().rstrip("/")
    email = os.getenv(EMAIL_ENV, "").strip() or os.getenv(EMAIL_ALIAS_ENV, "").strip()
    api_token = os.getenv(API_TOKEN_ENV, "").strip()
    field_id = os.getenv(FIELD_ID_ENV, "customfield_11607").strip()

    if not base_url:
        raise ValueError(f"Missing required environment variable: {BASE_URL_ENV}")
    if not email:
        raise ValueError(f"Missing required environment variable: {EMAIL_ENV}")
    if not api_token:
        raise ValueError(f"Missing required environment variable: {API_TOKEN_ENV}")
    if not field_id:
        raise ValueError(f"Missing required environment variable: {FIELD_ID_ENV}")

    return JiraConfig(
        base_url=base_url,
        email=email,
        api_token=api_token,
        field_id=field_id,
    )


def build_auth_header(email: str, api_token: str) -> str:
    """Build the Jira Cloud basic auth header payload."""

    credentials = f"{email}:{api_token}".encode("utf-8")
    encoded = base64.b64encode(credentials).decode("ascii")
    return f"Basic {encoded}"


def jira_headers(config: JiraConfig) -> dict[str, str]:
    """Build shared Jira request headers."""

    return {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": build_auth_header(config.email, config.api_token),
    }


def jira_issue_url(config: JiraConfig, jira_key: str, *, read: bool) -> str:
    """Build the Jira issue endpoint for reads or writes."""

    escaped_key = parse.quote(jira_key, safe="")
    if read:
        query = parse.urlencode({"fields": config.field_id})
    else:
        query = parse.urlencode({"notifyUsers": "false"})
    return f"{config.base_url}/rest/api/3/issue/{escaped_key}?{query}"


def jira_request(
    config: JiraConfig,
    url: str,
    *,
    method: str,
    payload: dict[str, object] | None = None,
) -> dict[str, object] | None:
    """Execute a Jira HTTP request and decode JSON when present."""

    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")

    request_obj = request.Request(
        url,
        data=data,
        headers=jira_headers(config),
        method=method,
    )
    try:
        with request.urlopen(request_obj, timeout=30) as response:
            raw_body = response.read().decode("utf-8").strip()
    except error.HTTPError as exc:
        try:
            details = exc.read().decode("utf-8", errors="replace").strip()
        finally:
            exc.close()
        raise JiraApiError(
            f"Jira API returned HTTP {exc.code} for {url}: {details or exc.reason}"
        ) from exc
    except error.URLError as exc:
        raise JiraApiError(f"Jira request failed for {url}: {exc.reason}") from exc

    if not raw_body:
        return None

    decoded = json.loads(raw_body)
    if not isinstance(decoded, dict):
        raise JiraApiError(f"Unexpected Jira response payload for {url}")
    return decoded


def find_jira_keys(text: str) -> list[str]:
    """Extract Jira issue keys from a free-form string."""

    if not text:
        return []
    # Find all matches and normalize to 'ASMA-1234' format
    matches = ISSUE_KEY_PATTERN.findall(text)
    normalized = [f"ASMA-{num}" for _, num in matches]
    return normalized


def resolve_jira_keys(explicit_keys: list[str], sources: list[str]) -> list[str]:
    """Resolve a stable, unique Jira key set from explicit and inferred sources."""

    resolved: list[str] = []
    seen: set[str] = set()

    for key in explicit_keys:
        normalized = key.strip().upper()
        if normalized and normalized not in seen:
            seen.add(normalized)
            resolved.append(normalized)

    for source in sources:
        for key in find_jira_keys(source):
            if key not in seen:
                seen.add(key)
                resolved.append(key)

    return resolved


def now_utc_timestamp() -> str:
    """Return the current UTC timestamp formatted for human readability."""

    return datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")


def short_sha(commit_sha: str) -> str:
    """Return the short Git commit SHA used in rendered output."""

    return commit_sha[:7]


def text_node(
    text: str,
    *,
    link: str | None = None,
    strong: bool = False,
    color: str | None = None,
) -> dict[str, object]:
    """Build an ADF text node with optional link and strong formatting."""

    node: dict[str, object] = {"type": "text", "text": text}
    marks: list[dict[str, object]] = []
    if strong:
        marks.append({"type": "strong"})
    if color:
        marks.append({"type": "textColor", "attrs": {"color": color}})
    if link:
        marks.append({"type": "link", "attrs": {"href": link}})
    if marks:
        node["marks"] = marks
    return node


def paragraph_node(content: list[dict[str, object]]) -> dict[str, object]:
    """Build an ADF paragraph node."""

    return {"type": "paragraph", "content": content}


def heading_content_node(
    level: int,
    content: list[dict[str, object]],
) -> dict[str, object]:
    """Build an ADF heading from pre-built content nodes."""

    return {
        "type": "heading",
        "attrs": {"level": level},
        "content": content,
    }


def heading_node(level: int, text: str) -> dict[str, object]:
    """Build an ADF heading node."""

    return heading_content_node(level, [text_node(text)])


def bullet_list_node(items: list[list[dict[str, object]]]) -> dict[str, object]:
    """Build an ADF bullet list node from paragraph node content lists."""

    content: list[dict[str, object]] = []
    for item_content in items:
        content.append(
            {
                "type": "listItem",
                "content": [paragraph_node(item_content)],
            }
        )
    return {"type": "bulletList", "content": content}


def build_entry_title(entry: BuildHistoryEntry) -> tuple[str, str]:
    """Return the human-readable title and preferred link for one entry."""

    title = f"{entry.service_name} - {entry.version}"
    link = entry.run_url

    if entry.pr_number and entry.pr_url:
        link = entry.pr_url
    elif entry.git_tag:
        if entry.git_tag_url:
            link = entry.git_tag_url

    return title, link


def human_preview(entry: BuildHistoryEntry) -> str:
    """Build a markdown-like preview text for logs and step summaries."""

    title, title_link = build_entry_title(entry)
    rendered_title = f"[{title}]({title_link})" if title_link else title

    preview_lines = [
        "---",
        "",
        f"### {rendered_title}",
        "",
        f"Version: {entry.version}",
        "",
        "**Summary For Non-Technical Readers**",
        "",
        f"- Release: {entry.release_kind}",
        f"- Status: {entry.status}",
        f"- Recorded: {entry.recorded_at_utc}",
        "",
        "**Technical Details**",
        "",
        f"- Run: {entry.run_url}",
        f"- Repository: {entry.repository}",
        f"- Workflow: {entry.workflow_name}",
    ]
    if entry.pr_number and entry.pr_url:
        preview_lines.append(f"- PR: #{entry.pr_number} ({entry.pr_url})")
    preview_lines.extend(
        [
            f"- Commit: {short_sha(entry.commit_sha)} ({entry.commit_url})",
        ]
    )
    if entry.git_tag:
        preview_lines.append(f"- Planned git tag: {entry.git_tag}")
    if entry.artifact_url:
        preview_lines.append(f"- Artifact: {entry.artifact_url}")
    if entry.image_ref:
        preview_lines.append(f"- Image: {entry.image_ref}")
    preview_lines.extend(
        [
            f"- Build key: {entry.entry_id}",
            f"- Job results: {entry.job_results}",
        ]
    )
    return "\n".join(preview_lines)


def build_block_nodes(entry: BuildHistoryEntry) -> list[dict[str, object]]:
    """Build the managed ADF block for one Jira build-history entry."""

    title, title_link = build_entry_title(entry)

    summary_items = [
        [
            text_node("Release: ", strong=True, color=SUMMARY_COLOR),
            text_node(entry.release_kind, color=SUMMARY_COLOR),
        ],
        [
            text_node("Status: ", strong=True, color=SUMMARY_COLOR),
            text_node(entry.status, color=SUMMARY_COLOR),
        ],
        [
            text_node("Recorded: ", strong=True, color=SUMMARY_COLOR),
            text_node(entry.recorded_at_utc, color=SUMMARY_COLOR),
        ],
    ]

    technical_items: list[list[dict[str, object]]] = [
        [
            text_node("Run: ", strong=True, color=TECHNICAL_COLOR),
            text_node("GitHub Actions run", link=entry.run_url),
        ],
        [
            text_node("Repository: ", strong=True, color=TECHNICAL_COLOR),
            text_node(entry.repository, color=TECHNICAL_COLOR),
        ],
        [
            text_node("Workflow: ", strong=True, color=TECHNICAL_COLOR),
            text_node(entry.workflow_name, color=TECHNICAL_COLOR),
        ],
    ]

    if entry.pr_number and entry.pr_url:
        technical_items.append(
            [
                text_node("PR: ", strong=True, color=TECHNICAL_COLOR),
                text_node(f"#{entry.pr_number}", link=entry.pr_url),
            ]
        )

    technical_items.extend(
        [
            [
                text_node("Commit: ", strong=True, color=TECHNICAL_COLOR),
                text_node(short_sha(entry.commit_sha), link=entry.commit_url),
            ],
        ]
    )

    if entry.git_tag:
        if entry.git_tag_url:
            technical_items.append(
                [
                    text_node(
                        "Planned git tag: ",
                        strong=True,
                        color=TECHNICAL_COLOR,
                    ),
                    text_node(entry.git_tag, link=entry.git_tag_url),
                ]
            )
        else:
            technical_items.append(
                [
                    text_node(
                        "Planned git tag: ",
                        strong=True,
                        color=TECHNICAL_COLOR,
                    ),
                    text_node(entry.git_tag, color=TECHNICAL_COLOR),
                ]
            )

    if entry.artifact_url:
        technical_items.append(
            [
                text_node("Artifact: ", strong=True, color=TECHNICAL_COLOR),
                text_node("Artifact", link=entry.artifact_url),
            ]
        )

    if entry.image_ref:
        technical_items.append(
            [
                text_node("Image: ", strong=True, color=TECHNICAL_COLOR),
                text_node(entry.image_ref, color=TECHNICAL_COLOR),
            ]
        )

    technical_items.extend(
        [
            [
                text_node("Build key: ", strong=True, color=TECHNICAL_COLOR),
                text_node(entry.entry_id, color=TECHNICAL_COLOR),
            ],
            [
                text_node("Job results: ", strong=True, color=TECHNICAL_COLOR),
                text_node(entry.job_results, color=TECHNICAL_COLOR),
            ],
        ]
    )

    return [
        heading_content_node(
            SERVICE_HEADING_LEVEL,
            [
                text_node(
                    title,
                    link=title_link,
                    strong=True,
                    color=TITLE_COLOR,
                )
            ],
        ),
        paragraph_node(
            [text_node("Version: ", strong=True), text_node(entry.version)]
        ),
        paragraph_node(
            [
                text_node(
                    "Summary For Non-Technical Readers",
                    strong=True,
                    color=SUMMARY_COLOR,
                )
            ]
        ),
        bullet_list_node(summary_items),
        paragraph_node(
            [
                text_node(
                    "Technical Details",
                    strong=True,
                    color=TECHNICAL_COLOR,
                )
            ]
        ),
        bullet_list_node(technical_items),
    ]


def build_single_block_document(entry: BuildHistoryEntry) -> dict[str, object]:
    """Build a full ADF document containing only the managed block."""

    return {"type": "doc", "version": 1, "content": build_block_nodes(entry)}


def build_text_document(text: str) -> dict[str, object]:
    """Wrap fallback text inside a minimal ADF document."""

    return {
        "type": "doc",
        "version": 1,
        "content": [paragraph_node([text_node(text)])],
    }


def coerce_existing_document(value: object) -> dict[str, object]:
    """Normalize Jira field content into an ADF document representation."""

    if value is None:
        return {"type": "doc", "version": 1, "content": []}
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return {"type": "doc", "version": 1, "content": []}
        return build_text_document(stripped)
    if not isinstance(value, dict):
        return build_text_document(json.dumps(value, sort_keys=True))

    content_value = value.get("content")
    node_type = value.get("type")
    version = value.get("version")
    if (
        node_type == "doc"
        and isinstance(version, int)
        and isinstance(content_value, list)
    ):
        return {
            "type": "doc",
            "version": version,
            "content": [node for node in content_value if isinstance(node, dict)],
        }
    return build_text_document(json.dumps(value, sort_keys=True))


def segment_document(content: list[dict[str, object]]) -> list[list[dict[str, object]]]:
    """Split top-level ADF content into segments using horizontal rules."""

    segments: list[list[dict[str, object]]] = []
    current: list[dict[str, object]] = []
    for node in content:
        if node.get("type") == "horizontalRule":
            if current:
                segments.append(current)
                current = []
            continue
        current.append(node)
    if current:
        segments.append(current)
    return segments


def node_text(node: dict[str, object]) -> str:
    """Extract text content from a limited subset of ADF nodes."""

    content = node.get("content")
    if not isinstance(content, list):
        return ""
    parts: list[str] = []
    for child in content:
        if not isinstance(child, dict):
            continue
        child_type = child.get("type")
        if child_type == "text":
            text_value = child.get("text")
            if isinstance(text_value, str):
                parts.append(text_value)
        elif child_type == "hardBreak":
            parts.append("\n")
    return "".join(parts)


def identify_segment(segment: list[dict[str, object]]) -> SegmentIdentity | None:
    """Return the managed block identity for a known Jira history segment."""

    if len(segment) < 2:
        return None

    service_node = segment[0]

    if service_node.get("type") != "heading":
        return None
    service_attrs = service_node.get("attrs")
    if not isinstance(service_attrs, dict):
        return None
    if service_attrs.get("level") != SERVICE_HEADING_LEVEL:
        return None

    raw_service_name = node_text(service_node).strip()
    service_name = raw_service_name.partition(" - ")[0].strip()
    if not service_name:
        return None

    version = ""
    for node in segment[1:4]:
        version_text = node_text(node).strip()
        if version_text.startswith(VERSION_PREFIX):
            version = version_text.removeprefix(VERSION_PREFIX).strip()
            break

    if not version:
        return None

    return SegmentIdentity(service_name=service_name, version=version)


def join_segments(segments: list[list[dict[str, object]]]) -> list[dict[str, object]]:
    """Join normalized segments back into top-level ADF content."""

    content: list[dict[str, object]] = []
    for index, segment in enumerate(segments):
        if not segment:
            continue
        if content and index >= 0:
            content.append({"type": "horizontalRule"})
        content.extend(segment)
    return content


def merge_entry_document(
    existing_document: dict[str, object],
    entry: BuildHistoryEntry,
) -> tuple[dict[str, object], bool, int]:
    """Merge a build-history block into an existing Jira ADF document."""

    content_value = existing_document.get("content")
    if not isinstance(content_value, list):
        content_value = []

    existing_content = [node for node in content_value if isinstance(node, dict)]
    segments = segment_document(existing_content)
    new_segment = build_block_nodes(entry)

    replaced = False
    duplicate_count = 0
    updated_segments: list[list[dict[str, object]]] = []
    target_identity = SegmentIdentity(entry.service_name, entry.version)

    for segment in segments:
        identity = identify_segment(segment)
        if identity == target_identity:
            if not replaced:
                updated_segments.append(new_segment)
                replaced = True
            else:
                duplicate_count += 1
            continue
        updated_segments.append(segment)

    if not replaced:
        updated_segments.append(new_segment)

    return (
        {
            "type": "doc",
            "version": 1,
            "content": join_segments(updated_segments),
        },
        replaced,
        duplicate_count,
    )


def fetch_issue_document(config: JiraConfig, jira_key: str) -> dict[str, object]:
    """Fetch the current Jira custom field document for one issue."""

    payload = jira_request(
        config,
        jira_issue_url(config, jira_key, read=True),
        method="GET",
    )
    if payload is None:
        return {"type": "doc", "version": 1, "content": []}

    fields_value = payload.get("fields")
    if not isinstance(fields_value, dict):
        raise JiraApiError(f"Jira issue payload for {jira_key} did not contain fields")
    return coerce_existing_document(fields_value.get(config.field_id))


def update_issue_document(
    config: JiraConfig,
    jira_key: str,
    document: dict[str, object],
) -> None:
    """Write the merged Jira custom field document back to an issue."""

    jira_request(
        config,
        jira_issue_url(config, jira_key, read=False),
        method="PUT",
        payload={"fields": {config.field_id: document}},
    )


def build_entry_from_args(args: argparse.Namespace) -> BuildHistoryEntry:
    """Convert parsed CLI arguments into a normalized build-history entry."""

    run_url = (
        f"{args.server_url.rstrip('/')}/{args.repository}/actions/runs/{args.run_id}"
    )
    commit_url = (
        f"{args.server_url.rstrip('/')}/{args.repository}/commit/{args.commit_sha}"
    )

    pr_number = args.pr_number.strip() or None
    pr_url = None
    if pr_number:
        pr_url = f"{args.server_url.rstrip('/')}/{args.repository}/pull/{pr_number}"

    git_tag = args.git_tag.strip() or None
    git_tag_url = None
    if git_tag:
        git_tag_url = (
            f"{args.server_url.rstrip('/')}/{args.repository}/releases/tag/{git_tag}"
        )

    recorded_at_utc = args.recorded_at_utc.strip() or now_utc_timestamp()

    return BuildHistoryEntry(
        service_name=args.service_name,
        version=args.version,
        release_kind=args.release_kind,
        status=args.status,
        recorded_at_utc=recorded_at_utc,
        entry_id=(
            f"github:{args.repository}:{args.run_id}:{args.run_attempt}"
        ),
        family=args.family,
        repository=args.repository,
        workflow_name=args.workflow_name,
        workflow_file=args.workflow_file,
        run_url=run_url,
        event_name=args.event_name,
        ref_name=args.ref_name,
        commit_sha=args.commit_sha,
        commit_url=commit_url,
        job_results=args.job_results,
        pr_number=pr_number,
        pr_url=pr_url,
        git_tag=git_tag,
        git_tag_url=git_tag_url,
        artifact_url=args.artifact_url.strip() or None,
        image_ref=args.image_ref.strip() or None,
    )


def build_summary_lines(
    *,
    status: str,
    resolved_keys: list[str],
    updated_keys: list[str],
    failed_keys: list[str],
    preview_text: str,
    warnings: list[str],
) -> list[str]:
    """Build markdown summary lines for the GitHub step summary."""

    lines = ["## Jira Build History", "", f"Status: {status}"]

    if resolved_keys:
        lines.extend(["", f"Resolved Jira keys: {', '.join(resolved_keys)}"])
    if updated_keys:
        lines.extend(["", f"Updated Jira keys: {', '.join(updated_keys)}"])
    if failed_keys:
        lines.extend(["", f"Failed Jira keys: {', '.join(failed_keys)}"])

    for warning in warnings:
        lines.extend(["", warning])

    lines.extend(["", "Preview:", "", "```md", preview_text, "```"])
    return lines


def publish_build_history(args: argparse.Namespace) -> int:
    """Publish one build-history entry to every resolved Jira issue key."""

    entry = build_entry_from_args(args)
    preview_text = human_preview(entry)
    resolved_keys = resolve_jira_keys(args.jira_key, args.jira_source)

    if not resolved_keys:
        warning = (
            "Warning: no Jira key could be resolved; skipped Jira update and "
            "printed the preview text below."
        )
        print(warning, file=sys.stderr)
        print(preview_text)
        write_output("update_status", "skipped_no_jira_key")
        write_output("resolved_jira_keys", "")
        write_output("updated_jira_keys", "")
        write_output("failed_jira_keys", "")
        append_summary(
            build_summary_lines(
                status="skipped_no_jira_key",
                resolved_keys=[],
                updated_keys=[],
                failed_keys=[],
                preview_text=preview_text,
                warnings=[warning],
            )
        )
        return 0

    try:
        config = resolve_config_from_env()
    except ValueError as exc:
        warning = f"Warning: {exc}; skipped Jira update and printed the preview."
        print(warning, file=sys.stderr)
        print(preview_text)
        write_output("update_status", "skipped_missing_config")
        write_output("resolved_jira_keys", ",".join(resolved_keys))
        write_output("updated_jira_keys", "")
        write_output("failed_jira_keys", "")
        append_summary(
            build_summary_lines(
                status="skipped_missing_config",
                resolved_keys=resolved_keys,
                updated_keys=[],
                failed_keys=[],
                preview_text=preview_text,
                warnings=[warning],
            )
        )
        return 0

    updated_keys: list[str] = []
    failed_keys: list[str] = []
    warnings: list[str] = []

    for jira_key in resolved_keys:
        try:
            existing_document = fetch_issue_document(config, jira_key)
            document, replaced, collapsed_duplicates = merge_entry_document(
                existing_document,
                entry,
            )
            update_issue_document(config, jira_key, document)
            updated_keys.append(jira_key)
            message = f"Updated Jira build history for {jira_key}."
            if replaced:
                message = f"Replaced Jira build history block for {jira_key}."
            if collapsed_duplicates > 0:
                message = (
                    f"Collapsed {collapsed_duplicates + 1} matching build history "
                    f"blocks into one latest block for {jira_key}."
                )
            print(message)
        except JiraApiError as exc:
            warning = f"Warning: {jira_key}: {exc}"
            warnings.append(warning)
            failed_keys.append(jira_key)
            print(warning, file=sys.stderr)

    if updated_keys and not failed_keys:
        status = "updated"
    elif updated_keys:
        status = "partial_failure"
    else:
        status = "failed_all"

    print(preview_text)
    write_output("update_status", status)
    write_output("resolved_jira_keys", ",".join(resolved_keys))
    write_output("updated_jira_keys", ",".join(updated_keys))
    write_output("failed_jira_keys", ",".join(failed_keys))
    append_summary(
        build_summary_lines(
            status=status,
            resolved_keys=resolved_keys,
            updated_keys=updated_keys,
            failed_keys=failed_keys,
            preview_text=preview_text,
            warnings=warnings,
        )
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    """Run the CLI program for Jira build-history publishing."""

    args = parse_args(argv)
    if args.command == "publish":
        return publish_build_history(args)
    raise ValueError(f"Unsupported command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())