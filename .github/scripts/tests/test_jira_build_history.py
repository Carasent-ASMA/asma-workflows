from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
import unittest
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
    def __init__(self, payload: dict[str, object] | None = None) -> None:
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
                hdrs=None,
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


if __name__ == "__main__":
    unittest.main()