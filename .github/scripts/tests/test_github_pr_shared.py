from __future__ import annotations

import importlib.util
import subprocess
import sys
import unittest
from pathlib import Path
from types import ModuleType
from unittest.mock import Mock, patch


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


github_pr_shared = load_module("github_pr_shared_test_module", "github_pr_shared.py")


class GithubPrSharedTests(unittest.TestCase):
    @patch.object(github_pr_shared, "enable_pull_request_auto_merge")
    @patch.object(github_pr_shared, "try_merge_pull_request_immediately")
    @patch.object(github_pr_shared, "ensure_branch_allows_auto_merge")
    @patch.object(github_pr_shared, "create_or_reuse_pull_request")
    @patch.object(github_pr_shared, "find_open_pull_request")
    @patch.object(github_pr_shared, "parse_repo_slug_from_remote_url")
    @patch.object(github_pr_shared, "extract_token_from_authenticated_remote_url")
    @patch.object(github_pr_shared, "remote_branch_contains_local_head")
    def test_sync_current_head_to_protected_branch_via_pull_request_merges_immediately(
        self,
        mock_remote_contains_head: Mock,
        mock_extract_token: Mock,
        mock_parse_slug: Mock,
        mock_find_open_pull_request: Mock,
        mock_create_or_reuse_pull_request: Mock,
        mock_ensure_branch_allows_auto_merge: Mock,
        mock_try_merge_pull_request_immediately: Mock,
        mock_enable_pull_request_auto_merge: Mock,
    ) -> None:
        mock_remote_contains_head.return_value = False
        mock_extract_token.return_value = "test-token"
        mock_parse_slug.return_value = "carasent-asma/asma-argocd"
        mock_find_open_pull_request.return_value = None
        pull_request = github_pr_shared.PullRequestInfo(
            number=42,
            node_id="PR_kwDOAAABBB4",
            url="https://github.com/Carasent-ASMA/asma-argocd/pull/42",
            head_ref="bot/argocd-sync/master-1234567890ab",
        )
        mock_create_or_reuse_pull_request.return_value = pull_request
        mock_try_merge_pull_request_immediately.return_value = (
            github_pr_shared.PullRequestMergeAttempt(
                merged=True,
                message="Merged",
            )
        )
        run_command = Mock(
            return_value=subprocess.CompletedProcess(
                args=["git", "push"],
                returncode=0,
                stdout="",
                stderr="",
            )
        )

        result = github_pr_shared.sync_current_head_to_protected_branch_via_pull_request(
            repo_dir=Path("/tmp/asma-argocd"),
            remote_name="github",
            target_branch="master",
            remote_url="https://x-access-token:test-token@github.com/Carasent-ASMA/asma-argocd.git",
            source_branch_name="bot/argocd-sync/master-1234567890ab",
            title="asma-srv-auth.dev.version: 1234567.",
            body="sync body",
            merge_method="squash",
            subject_label="ArgoCD sync PR",
            run_command=run_command,
        )

        self.assertFalse(result.already_synced)
        self.assertTrue(result.merged_immediately)
        self.assertEqual(result.pull_request, pull_request)
        run_command.assert_called_once_with(
            [
                "git",
                "-C",
                "/tmp/asma-argocd",
                "push",
                "--force",
                "github",
                "HEAD:bot/argocd-sync/master-1234567890ab",
            ]
        )
        mock_create_or_reuse_pull_request.assert_called_once_with(
            "carasent-asma/asma-argocd",
            "bot/argocd-sync/master-1234567890ab",
            "master",
            "asma-srv-auth.dev.version: 1234567.",
            "sync body",
            "test-token",
            subject_label="ArgoCD sync PR",
        )
        mock_ensure_branch_allows_auto_merge.assert_called_once_with(
            "carasent-asma/asma-argocd",
            "master",
            "test-token",
            pull_request.url,
            subject_label="ArgoCD sync PR",
        )
        mock_enable_pull_request_auto_merge.assert_not_called()

    @patch.object(github_pr_shared, "remote_branch_contains_local_head")
    def test_sync_current_head_to_protected_branch_via_pull_request_skips_when_synced(
        self,
        mock_remote_contains_head: Mock,
    ) -> None:
        mock_remote_contains_head.return_value = True
        run_command = Mock()

        result = github_pr_shared.sync_current_head_to_protected_branch_via_pull_request(
            repo_dir=Path("/tmp/asma-argocd"),
            remote_name="github",
            target_branch="master",
            remote_url="https://x-access-token:test-token@github.com/Carasent-ASMA/asma-argocd.git",
            source_branch_name="bot/argocd-sync/master-1234567890ab",
            title="asma-srv-auth.dev.version: 1234567.",
            body="sync body",
            merge_method="squash",
            subject_label="ArgoCD sync PR",
            run_command=run_command,
        )

        self.assertTrue(result.already_synced)
        self.assertIsNone(result.pull_request)
        self.assertFalse(result.merged_immediately)
        run_command.assert_not_called()


if __name__ == "__main__":
    unittest.main()