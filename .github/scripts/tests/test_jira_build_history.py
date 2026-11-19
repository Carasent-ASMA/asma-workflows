from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
import unittest
from collections.abc import Mapping
from email.message import Message
from io import BytesIO
from pathlib import Path
from types import ModuleType
from unittest import mock
from urllib.error import HTTPError

SCRIPTS_DIR = Path(__file__).resolve().parents[1]


def load_module(module_name: str, file_name: str) -> ModuleType:
    script_path = str(SCRIPTS_DIR)
    if script_path not in sys.path:
        sys.path.insert(0, script_path)

    spec = importlib.util.spec_from_file_location(module_name, SCRIPTS_DIR / file_name)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load module spec for {file_name}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


jira_build_history = load_module("jira_build_history", "jira_build_history.py")


class FakeHttpResponse:
    def __init__(self, payload: Mapping[str, object] | None = None) -> None:
        self.payload = payload

    def __enter__(self) -> FakeHttpResponse:
        return self

    def __exit__(self, exc_type, exc, exc_tb) -> None:
        return None

    def read(self) -> bytes:
        if self.payload is None:
            return b""
        return json.dumps(self.payload).encode("utf-8")


class JiraBuildHistoryTests(unittest.TestCase):
    def test_resolve_jira_keys_deduplicates_explicit_and_inferred_values(self) -> None:
        resolved = jira_build_history.resolve_jira_keys(
            ["ASMA-10", "asma-10", "ASMA-20"],
            ["Implement ASMA-20 and ASMA-30", "Release for asma-10"],
        )

        self.assertEqual(resolved, ["ASMA-10", "ASMA-20", "ASMA-30"])

    def test_build_block_nodes_use_human_readable_linked_title(self) -> None:
        entry = jira_build_history.BuildHistoryEntry(
            service_name="asma-app-directory",
            version="pr47",
            release_kind="preview build",
            status="success",
            recorded_at_utc="2026-05-22 07:49 UTC",
            entry_id="github:Carasent-ASMA/asma-app-directory:26275344532:1",
            family="app",
            repository="Carasent-ASMA/asma-app-directory",
            workflow_name="Reusable App PR Preview",
            workflow_file=".github/workflows/reusable-app-pr-preview.yml",
            run_url="https://github.com/Carasent-ASMA/asma-app-directory/actions/runs/26275344532",
            event_name="pull_request",
            ref_name="fix/ASMA-7349-regressions",
            commit_sha="ac8bc7f1234567890",
            commit_url="https://github.com/Carasent-ASMA/asma-app-directory/commit/ac8bc7f1234567890",
            job_results="assess_preview=success, build_artifact=success",
            pr_number="47",
            pr_url="https://github.com/Carasent-ASMA/asma-app-directory/pull/47",
        )

        nodes = jira_build_history.build_block_nodes(entry)

        self.assertEqual(nodes[0]["type"], "heading")
        title_text = jira_build_history.node_text(nodes[0])
        self.assertEqual(title_text, "asma-app-directory - pr47")
        title_marks = nodes[0]["content"][0]["marks"]
        self.assertTrue(any(mark["type"] == "link" for mark in title_marks))
        self.assertTrue(any(mark["type"] == "textColor" for mark in title_marks))
        self.assertEqual(jira_build_history.node_text(nodes[1]), "Version: pr47")

    def test_resolve_config_from_env_accepts_jira_user_email_alias(self) -> None:
        env = {
            "JIRA_BASE_URL": "https://example.atlassian.net",
            "JIRA_USER_EMAIL": "jira@example.com",
            "JIRA_API_TOKEN": "secret",
        }

        with mock.patch.dict(os.environ, env, clear=False):
            config = jira_build_history.resolve_config_from_env()

        self.assertEqual(config.base_url, "https://example.atlassian.net")
        self.assertEqual(config.email, "jira@example.com")
        self.assertEqual(config.api_token, "secret")

    def test_merge_entry_document_collapses_duplicate_matching_blocks(self) -> None:
        entry = jira_build_history.BuildHistoryEntry(
            service_name="asma-app-shell",
            version="1.2.3",
            release_kind="app master build",
            status="success",
            recorded_at_utc="2026-05-21 18:10 UTC",
            entry_id="github:Carasent-ASMA/asma-app-shell:1:1",
            family="app",
            repository="Carasent-ASMA/asma-app-shell",
            workflow_name="Reusable App Master Release",
            workflow_file=".github/workflows/reusable-app-master-release.yml",
            run_url="https://github.com/Carasent-ASMA/asma-app-shell/actions/runs/1",
            event_name="push",
            ref_name="master",
            commit_sha="abcdef1234567890",
            commit_url="https://github.com/Carasent-ASMA/asma-app-shell/commit/abcdef1234567890",
            job_results="assess_release=success, build_artifact=success",
        )
        other_entry = jira_build_history.BuildHistoryEntry(
            service_name="asma-app-directory",
            version="2.0.0",
            release_kind="app master build",
            status="success",
            recorded_at_utc="2026-05-21 18:00 UTC",
            entry_id="github:Carasent-ASMA/asma-app-directory:2:1",
            family="app",
            repository="Carasent-ASMA/asma-app-directory",
            workflow_name="Reusable App Master Release",
            workflow_file=".github/workflows/reusable-app-master-release.yml",
            run_url="https://github.com/Carasent-ASMA/asma-app-directory/actions/runs/2",
            event_name="push",
            ref_name="master",
            commit_sha="fedcba0987654321",
            commit_url="https://github.com/Carasent-ASMA/asma-app-directory/commit/fedcba0987654321",
            job_results="assess_release=success, build_artifact=success",
        )

        duplicate_segment = jira_build_history.build_block_nodes(entry)
        existing_document = {
            "type": "doc",
            "version": 1,
            "content": jira_build_history.join_segments(
                [
                    jira_build_history.build_block_nodes(other_entry),
                    duplicate_segment,
                    duplicate_segment,
                ]
            ),
        }

        merged_document, replaced, duplicate_count = (
            jira_build_history.merge_entry_document(existing_document, entry)
        )

        self.assertTrue(replaced)
        self.assertEqual(duplicate_count, 1)
        segments = jira_build_history.segment_document(merged_document["content"])
        identities = [
            jira_build_history.identify_segment(segment) for segment in segments
        ]
        self.assertEqual(
            identities,
            [
                jira_build_history.SegmentIdentity("asma-app-directory", "2.0.0"),
                jira_build_history.SegmentIdentity("asma-app-shell", "1.2.3"),
            ],
        )

    def test_merge_entry_document_appends_without_horizontal_rules(self) -> None:
        existing_entry = jira_build_history.BuildHistoryEntry(
            service_name="asma-app-directory",
            version="2.0.0",
            release_kind="app master build",
            status="success",
            recorded_at_utc="2026-05-21 18:00 UTC",
            entry_id="github:Carasent-ASMA/asma-app-directory:2:1",
            family="app",
            repository="Carasent-ASMA/asma-app-directory",
            workflow_name="Reusable App Master Release",
            workflow_file=".github/workflows/reusable-app-master-release.yml",
            run_url="https://github.com/Carasent-ASMA/asma-app-directory/actions/runs/2",
            event_name="push",
            ref_name="master",
            commit_sha="fedcba0987654321",
            commit_url="https://github.com/Carasent-ASMA/asma-app-directory/commit/fedcba0987654321",
            job_results="assess_release=success, build_artifact=success",
        )
        new_entry = jira_build_history.BuildHistoryEntry(
            service_name="asma-app-shell",
            version="1.2.3",
            release_kind="app master build",
            status="success",
            recorded_at_utc="2026-05-21 18:10 UTC",
            entry_id="github:Carasent-ASMA/asma-app-shell:1:1",
            family="app",
            repository="Carasent-ASMA/asma-app-shell",
            workflow_name="Reusable App Master Release",
            workflow_file=".github/workflows/reusable-app-master-release.yml",
            run_url="https://github.com/Carasent-ASMA/asma-app-shell/actions/runs/1",
            event_name="push",
            ref_name="master",
            commit_sha="abcdef1234567890",
            commit_url="https://github.com/Carasent-ASMA/asma-app-shell/commit/abcdef1234567890",
            job_results="assess_release=success, build_artifact=success",
        )

        existing_document = {
            "type": "doc",
            "version": 1,
            "content": jira_build_history.build_block_nodes(existing_entry),
        }

        merged_document, replaced, duplicate_count = (
            jira_build_history.merge_entry_document(existing_document, new_entry)
        )

        self.assertFalse(replaced)
        self.assertEqual(duplicate_count, 0)
        self.assertFalse(
            any(
                node.get("type") == "horizontalRule"
                for node in merged_document["content"]
            )
        )
        self.assertEqual(
            len(jira_build_history.segment_document(merged_document["content"])),
            2,
        )

    def test_merge_entry_document_replaces_preview_for_same_service_and_pr(self) -> None:
        preview_entry = jira_build_history.BuildHistoryEntry(
            service_name="asma-app-shell",
            version="pr33",
            release_kind="preview build",
            status="success",
            recorded_at_utc="2026-05-22 08:10 UTC",
            entry_id="github:Carasent-ASMA/asma-app-shell:26270000000:1",
            family="app",
            repository="Carasent-ASMA/asma-app-shell",
            workflow_name="Reusable App PR Preview",
            workflow_file=".github/workflows/reusable-app-pr-preview.yml",
            run_url="https://github.com/Carasent-ASMA/asma-app-shell/actions/runs/26270000000",
            event_name="pull_request",
            ref_name="feature/ASMA-7352-release-history",
            commit_sha="1234567890abcdef",
            commit_url="https://github.com/Carasent-ASMA/asma-app-shell/commit/1234567890abcdef",
            job_results="assess_preview=success, build_artifact=success",
            pr_number="33",
            pr_url="https://github.com/Carasent-ASMA/asma-app-shell/pull/33",
        )
        release_entry = jira_build_history.BuildHistoryEntry(
            service_name="asma-app-shell",
            version="0.71.1",
            release_kind="app master build",
            status="success",
            recorded_at_utc="2026-05-22 08:50 UTC",
            entry_id="github:Carasent-ASMA/asma-app-shell:26278026199:1",
            family="app",
            repository="Carasent-ASMA/asma-app-shell",
            workflow_name="Reusable App Master Release",
            workflow_file=".github/workflows/reusable-app-master-release.yml",
            run_url="https://github.com/Carasent-ASMA/asma-app-shell/actions/runs/26278026199",
            event_name="push",
            ref_name="master",
            commit_sha="9fe24e092f6dde5938c18b5148b5560a489668fc",
            commit_url="https://github.com/Carasent-ASMA/asma-app-shell/commit/9fe24e092f6dde5938c18b5148b5560a489668fc",
            job_results="assess_release=success, build_artifact=success",
            pr_number="33",
            pr_url="https://github.com/Carasent-ASMA/asma-app-shell/pull/33",
            git_tag="v0.71.1",
        )

        existing_document = {
            "type": "doc",
            "version": 1,
            "content": jira_build_history.build_block_nodes(preview_entry),
        }

        merged_document, replaced, duplicate_count = (
            jira_build_history.merge_entry_document(existing_document, release_entry)
        )

        self.assertTrue(replaced)
        self.assertEqual(duplicate_count, 0)
        segments = jira_build_history.segment_document(merged_document["content"])
        self.assertEqual(len(segments), 1)
        self.assertEqual(
            jira_build_history.identify_segment(segments[0]),
            jira_build_history.SegmentIdentity("asma-app-shell", "0.71.1"),
        )

    def test_publish_skips_without_jira_keys_and_writes_preview(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "output.txt"
            summary_path = Path(temp_dir) / "summary.md"
            env = {
                "GITHUB_OUTPUT": str(output_path),
                "GITHUB_STEP_SUMMARY": str(summary_path),
            }
            with mock.patch.dict(os.environ, env, clear=False):
                exit_code = jira_build_history.main(
                    [
                        "publish",
                        "--service-name",
                        "asma-app-shell",
                        "--version",
                        "1.2.3",
                        "--release-kind",
                        "app master build",
                        "--family",
                        "app",
                        "--workflow-name",
                        "Reusable App Master Release",
                        "--workflow-file",
                        ".github/workflows/reusable-app-master-release.yml",
                        "--repository",
                        "Carasent-ASMA/asma-app-shell",
                        "--server-url",
                        "https://github.com",
                        "--run-id",
                        "123",
                        "--run-attempt",
                        "1",
                        "--event-name",
                        "push",
                        "--ref-name",
                        "master",
                        "--commit-sha",
                        "abcdef1234567890",
                        "--job-results",
                        "assess_release=success, build_artifact=success",
                        "--jira-source",
                        "No issue key here",
                    ]
                )

                written = output_path.read_text(encoding="utf-8")
                summary = summary_path.read_text(encoding="utf-8")

        self.assertEqual(exit_code, 0)
        self.assertIn("update_status=skipped_no_jira_key", written)
        self.assertIn("Preview:", summary)

    @mock.patch.object(jira_build_history.request, "urlopen")
    def test_publish_updates_all_resolved_jira_keys_end_to_end(
        self,
        mock_urlopen: mock.Mock,
    ) -> None:
        get_issue_response = {
            "fields": {"customfield_11607": None},
        }
        put_response = None
        mock_urlopen.side_effect = [
            FakeHttpResponse(get_issue_response),
            FakeHttpResponse(put_response),
            FakeHttpResponse(get_issue_response),
            FakeHttpResponse(put_response),
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "output.txt"
            summary_path = Path(temp_dir) / "summary.md"
            env = {
                "GITHUB_OUTPUT": str(output_path),
                "GITHUB_STEP_SUMMARY": str(summary_path),
                "JIRA_BASE_URL": "https://example.atlassian.net",
                "JIRA_EMAIL": "jira@example.com",
                "JIRA_API_TOKEN": "secret",
                "JIRA_BUILD_HISTORY_FIELD_ID": "customfield_11607",
            }
            with mock.patch.dict(os.environ, env, clear=False):
                exit_code = jira_build_history.main(
                    [
                        "publish",
                        "--service-name",
                        "asma-app-shell",
                        "--version",
                        "1.2.3",
                        "--release-kind",
                        "app master build",
                        "--family",
                        "app",
                        "--workflow-name",
                        "Reusable App Master Release",
                        "--workflow-file",
                        ".github/workflows/reusable-app-master-release.yml",
                        "--repository",
                        "Carasent-ASMA/asma-app-shell",
                        "--server-url",
                        "https://github.com",
                        "--run-id",
                        "123",
                        "--run-attempt",
                        "1",
                        "--event-name",
                        "push",
                        "--ref-name",
                        "master",
                        "--commit-sha",
                        "abcdef1234567890",
                        "--job-results",
                        "assess_release=success, build_artifact=success",
                        "--jira-source",
                        "ASMA-100 fix",
                        "--jira-source",
                        "also ASMA-200",
                    ]
                )

                written = output_path.read_text(encoding="utf-8")
                summary = summary_path.read_text(encoding="utf-8")

        self.assertEqual(exit_code, 0)
        self.assertIn("update_status=updated", written)
        self.assertIn("resolved_jira_keys=ASMA-100,ASMA-200", written)
        self.assertIn("updated_jira_keys=ASMA-100,ASMA-200", written)
        self.assertIn("Updated Jira keys: ASMA-100, ASMA-200", summary)

        get_request = mock_urlopen.call_args_list[0].args[0]
        put_request = mock_urlopen.call_args_list[1].args[0]
        self.assertIn("fields=customfield_11607", get_request.full_url)
        self.assertIn("notifyUsers=false", put_request.full_url)
        payload = json.loads(put_request.data.decode("utf-8"))
        field_value = payload["fields"]["customfield_11607"]
        self.assertEqual(field_value["type"], "doc")

    @mock.patch.object(jira_build_history.request, "urlopen")
    def test_publish_continues_when_one_jira_issue_fails(
        self,
        mock_urlopen: mock.Mock,
    ) -> None:
        mock_urlopen.side_effect = [
            FakeHttpResponse({"fields": {"customfield_11607": None}}),
            FakeHttpResponse(None),
            HTTPError(
                url="https://example.atlassian.net/rest/api/3/issue/ASMA-2",
                code=403,
                msg="Forbidden",
                hdrs=Message(),
                fp=BytesIO(b'{"errorMessages":["Forbidden"]}'),
            ),
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "output.txt"
            summary_path = Path(temp_dir) / "summary.md"
            env = {
                "GITHUB_OUTPUT": str(output_path),
                "GITHUB_STEP_SUMMARY": str(summary_path),
                "JIRA_BASE_URL": "https://example.atlassian.net",
                "JIRA_EMAIL": "jira@example.com",
                "JIRA_API_TOKEN": "secret",
            }
            with mock.patch.dict(os.environ, env, clear=False):
                exit_code = jira_build_history.main(
                    [
                        "publish",
                        "--service-name",
                        "asma-app-shell",
                        "--version",
                        "1.2.3",
                        "--release-kind",
                        "app master build",
                        "--family",
                        "app",
                        "--workflow-name",
                        "Reusable App Master Release",
                        "--workflow-file",
                        ".github/workflows/reusable-app-master-release.yml",
                        "--repository",
                        "Carasent-ASMA/asma-app-shell",
                        "--server-url",
                        "https://github.com",
                        "--run-id",
                        "123",
                        "--run-attempt",
                        "1",
                        "--event-name",
                        "push",
                        "--ref-name",
                        "master",
                        "--commit-sha",
                        "abcdef1234567890",
                        "--job-results",
                        "assess_release=success, build_artifact=success",
                        "--jira-source",
                        "ASMA-1 ASMA-2",
                    ]
                )

                written = output_path.read_text(encoding="utf-8")
                summary = summary_path.read_text(encoding="utf-8")

        self.assertEqual(exit_code, 0)
        self.assertIn("update_status=partial_failure", written)
        self.assertIn("updated_jira_keys=ASMA-1", written)
        self.assertIn("failed_jira_keys=ASMA-2", written)
        self.assertIn("Failed Jira keys: ASMA-2", summary)

    def _entry(self, service_name: str, version: str, run_id: str) -> object:
        return jira_build_history.BuildHistoryEntry(
            service_name=service_name,
            version=version,
            release_kind="app hotpatch build",
            status="success",
            recorded_at_utc="2026-11-06 14:38 UTC",
            entry_id=f"github:Carasent-ASMA/{service_name}:{run_id}:1",
            family="app",
            repository=f"Carasent-ASMA/{service_name}",
            workflow_name="Reusable App Hotpatch Release",
            workflow_file=".github/workflows/reusable-app-hotpatch-release.yml",
            run_url=f"https://github.com/Carasent-ASMA/{service_name}/actions/runs/{run_id}",
            event_name="push",
            ref_name="releases/v0.1.0",
            commit_sha="abcdef1234567890",
            commit_url=f"https://github.com/Carasent-ASMA/{service_name}/commit/abcdef1234567890",
            job_results="assess_release=success, build_artifact=success",
            git_tag=f"v{version}",
            git_tag_url=f"https://github.com/Carasent-ASMA/{service_name}/releases/tag/v{version}",
        )

    def _document(self, *entries: object) -> dict[str, object]:
        content: list[dict[str, object]] = []
        for entry in entries:
            content.extend(jira_build_history.build_block_nodes(entry))
        return {"type": "doc", "version": 1, "content": content}

    def _publish_args(self, version: str, run_id: str) -> list[str]:
        return [
            "publish",
            "--service-name",
            "asma-app-chat",
            "--version",
            version,
            "--release-kind",
            "app hotpatch build",
            "--family",
            "app",
            "--workflow-name",
            "Reusable App Hotpatch Release",
            "--workflow-file",
            ".github/workflows/reusable-app-hotpatch-release.yml",
            "--repository",
            "Carasent-ASMA/asma-app-chat",
            "--server-url",
            "https://github.com",
            "--run-id",
            run_id,
            "--run-attempt",
            "1",
            "--event-name",
            "push",
            "--ref-name",
            "releases/v0.1.0",
            "--commit-sha",
            "abcdef1234567890",
            "--job-results",
            "assess_release=success, build_artifact=success",
            "--jira-source",
            "ASMA-1 hotpatch",
        ]

    @staticmethod
    def _content_limit_error() -> HTTPError:
        return HTTPError(
            url="https://example.atlassian.net/rest/api/3/issue/ASMA-1",
            code=400,
            msg="Bad Request",
            hdrs=Message(),
            fp=BytesIO(
                b'{"errorMessages":[],"errors":{"customfield_11607":"CONTENT_LIMIT_EXCEEDED"}}'
            ),
        )

    def test_compact_document_folds_oldest_blocks_into_one_list(self) -> None:
        oldest = self._entry("asma-app-chat", "0.1.0-1", "1")
        middle = self._entry("asma-app-chat", "0.1.0-2", "2")
        newest = self._entry("asma-app-chat", "0.1.0-3", "3")
        document = self._document(oldest, middle, newest)

        compacted_document, compacted = jira_build_history.compact_document(
            document,
            protect=jira_build_history.SegmentIdentity("asma-app-chat", "0.1.0-3"),
            limit=5,
        )

        self.assertEqual(compacted, 2)
        content = compacted_document["content"]
        self.assertEqual(
            jira_build_history.node_text(content[0]),
            jira_build_history.COMPACT_HEADING_TEXT,
        )
        self.assertEqual(content[1]["type"], "bulletList")
        items = jira_build_history.list_item_texts(content[1])
        self.assertEqual(len(items), 2)
        self.assertTrue(items[0].startswith("asma-app-chat - 0.1.0-1"))
        self.assertIn("app hotpatch build", items[0])
        self.assertIn("2026-11-06 14:38 UTC", items[0])
        self.assertIn("abcdef1", items[0])
        self.assertIn("v0.1.0-1", items[0])
        self.assertTrue(items[1].startswith("asma-app-chat - 0.1.0-2"))
        # The protected (newest) block survives in full right after the list.
        self.assertEqual(
            jira_build_history.identify_segment(content[2:]),
            jira_build_history.SegmentIdentity("asma-app-chat", "0.1.0-3"),
        )
        self.assertLess(
            len(json.dumps(compacted_document)),
            len(json.dumps(document)),
        )

    def test_compact_document_reuses_existing_compact_list_and_honours_limit(
        self,
    ) -> None:
        entries = [
            self._entry("asma-app-chat", f"0.1.0-{index}", str(index))
            for index in range(1, 5)
        ]
        document = self._document(*entries)
        protect = jira_build_history.SegmentIdentity("asma-app-chat", "0.1.0-4")

        first_pass, first_count = jira_build_history.compact_document(
            document, protect=protect, limit=1
        )
        second_pass, second_count = jira_build_history.compact_document(
            first_pass, protect=protect, limit=5
        )

        self.assertEqual((first_count, second_count), (1, 2))
        headings = [
            jira_build_history.node_text(node)
            for node in second_pass["content"]
            if node.get("type") == "heading"
        ]
        self.assertEqual(
            headings,
            [jira_build_history.COMPACT_HEADING_TEXT, "asma-app-chat - 0.1.0-4"],
        )
        items = jira_build_history.list_item_texts(second_pass["content"][1])
        self.assertEqual(len(items), 3)

        nothing_left, count = jira_build_history.compact_document(
            second_pass, protect=protect, limit=5
        )
        self.assertEqual(count, 0)
        self.assertIs(nothing_left, second_pass)

    @mock.patch.object(jira_build_history.request, "urlopen")
    def test_publish_compacts_when_jira_reports_content_limit(
        self,
        mock_urlopen: mock.Mock,
    ) -> None:
        existing = self._document(
            self._entry("asma-app-chat", "0.1.0-1", "1"),
            self._entry("asma-app-chat", "0.1.0-2", "2"),
        )
        mock_urlopen.side_effect = [
            FakeHttpResponse({"fields": {"customfield_11607": existing}}),
            self._content_limit_error(),
            FakeHttpResponse(None),
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "output.txt"
            summary_path = Path(temp_dir) / "summary.md"
            env = {
                "GITHUB_OUTPUT": str(output_path),
                "GITHUB_STEP_SUMMARY": str(summary_path),
                "JIRA_BASE_URL": "https://example.atlassian.net",
                "JIRA_EMAIL": "jira@example.com",
                "JIRA_API_TOKEN": "secret",
            }
            with mock.patch.dict(os.environ, env, clear=False):
                exit_code = jira_build_history.main(self._publish_args("0.1.0-3", "3"))
                written = output_path.read_text(encoding="utf-8")
                summary = summary_path.read_text(encoding="utf-8")

        self.assertEqual(exit_code, 0)
        self.assertIn("update_status=updated", written)
        self.assertIn("updated_jira_keys=ASMA-1", written)
        self.assertIn("failed_jira_keys=\n", written)
        self.assertIn("Compacted 2 earlier build history blocks for ASMA-1", summary)

        self.assertEqual(mock_urlopen.call_count, 3)
        retry_request = mock_urlopen.call_args_list[2].args[0]
        payload = json.loads(retry_request.data.decode("utf-8"))
        content = payload["fields"]["customfield_11607"]["content"]
        self.assertEqual(
            jira_build_history.node_text(content[0]),
            jira_build_history.COMPACT_HEADING_TEXT,
        )
        self.assertEqual(len(jira_build_history.list_item_texts(content[1])), 2)
        self.assertEqual(
            jira_build_history.identify_segment(content[2:]),
            jira_build_history.SegmentIdentity("asma-app-chat", "0.1.0-3"),
        )

    @mock.patch.object(jira_build_history.request, "urlopen")
    def test_publish_reports_failure_when_nothing_is_left_to_compact(
        self,
        mock_urlopen: mock.Mock,
    ) -> None:
        mock_urlopen.side_effect = [
            FakeHttpResponse({"fields": {"customfield_11607": None}}),
            self._content_limit_error(),
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "output.txt"
            env = {
                "GITHUB_OUTPUT": str(output_path),
                "JIRA_BASE_URL": "https://example.atlassian.net",
                "JIRA_EMAIL": "jira@example.com",
                "JIRA_API_TOKEN": "secret",
            }
            with mock.patch.dict(os.environ, env, clear=False):
                exit_code = jira_build_history.main(self._publish_args("0.1.0-1", "1"))
                written = output_path.read_text(encoding="utf-8")

        self.assertEqual(exit_code, 0)
        self.assertIn("update_status=failed_all", written)
        self.assertIn("failed_jira_keys=ASMA-1", written)
        self.assertEqual(mock_urlopen.call_count, 2)

if __name__ == "__main__":
    unittest.main()
