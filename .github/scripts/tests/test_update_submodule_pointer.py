from __future__ import annotations

import importlib.util
import subprocess
import sys
import tempfile
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


update_submodule_pointer = load_module(
    "update_submodule_pointer",
    "update_submodule_pointer.py",
)
github_pr_shared = load_module(
    "github_pr_shared",
    "github_pr_shared.py",
)


def run_git(args: list[str], cwd: Path) -> str:
    result = subprocess.run(
        args,
        cwd=cwd,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def init_repo(path: Path, branch_name: str = "master") -> None:
    subprocess.run(["git", "init", "-b", branch_name], cwd=path, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=path, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=path,
        check=True,
    )


class UpdateSubmodulePointerTests(unittest.TestCase):
    def test_try_merge_pull_request_immediately_returns_false_for_conflict_statuses(self) -> None:
        pull_request = update_submodule_pointer.PullRequestInfo(
            number=42,
            node_id="PR_kwDOAAABBB4",
            url="https://github.com/Carasent-ASMA/asma-modules/pull/42",
            head_ref="bot/pointer/shared-asma-workflows-abc123",
        )

        with patch.object(
            update_submodule_pointer.github_pr_shared.request,
            "urlopen",
            side_effect=update_submodule_pointer.github_pr_shared.HTTPError(
                url="https://api.github.com/repos/Carasent-ASMA/asma-modules/pulls/42/merge",
                code=405,
                msg="Method Not Allowed",
                hdrs=None,
                fp=None,
            ),
        ):
            result = update_submodule_pointer.try_merge_pull_request_immediately(
                "Carasent-ASMA/asma-modules",
                pull_request,
                "token",
                "squash",
            )

        self.assertFalse(result.merged)

    @patch.object(update_submodule_pointer, "enable_pull_request_auto_merge")
    @patch.object(update_submodule_pointer, "try_merge_pull_request_immediately")
    @patch.object(update_submodule_pointer, "ensure_branch_allows_auto_merge")
    @patch.object(update_submodule_pointer, "find_open_pointer_pull_request")
    @patch.object(update_submodule_pointer, "create_pointer_pull_request")
    @patch.object(update_submodule_pointer, "push_pointer_commit")
    @patch.object(update_submodule_pointer, "create_pointer_commit")
    @patch.object(update_submodule_pointer, "checkout_pointer_branch")
    @patch.object(update_submodule_pointer, "configure_commit_identity")
    @patch.object(update_submodule_pointer, "clone_repository")
    @patch.object(update_submodule_pointer, "read_gitlink_sha")
    @patch.object(update_submodule_pointer, "load_submodule_mappings")
    @patch.object(update_submodule_pointer, "resolve_remote_branch_head")
    def test_update_pointer_merges_immediately_when_pull_request_is_ready(
        self,
        mock_resolve_remote_branch_head: Mock,
        mock_load_submodule_mappings: Mock,
        mock_read_gitlink_sha: Mock,
        mock_clone_repository: Mock,
        mock_configure_commit_identity: Mock,
        mock_checkout_pointer_branch: Mock,
        mock_create_pointer_commit: Mock,
        mock_push_pointer_commit: Mock,
        mock_create_pr: Mock,
        mock_find_pr: Mock,
        mock_ensure_branch_allows_auto_merge: Mock,
        mock_try_merge_pull_request_immediately: Mock,
        mock_enable_auto_merge: Mock,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            caller_repo = Path(temp_dir) / "caller"
            caller_repo.mkdir()
            repo_checkout = Path(temp_dir) / "asma-modules"
            repo_checkout.mkdir()
            (repo_checkout / ".gitmodules").write_text("", encoding="utf-8")

            target_sha = "a" * 40
            mock_resolve_remote_branch_head.return_value = target_sha
            mock_load_submodule_mappings.return_value = [
                update_submodule_pointer.SubmoduleMapping(
                    name="shared/asma-workflows",
                    path="shared/asma-workflows",
                    url="git@github.com:Carasent-ASMA/asma-workflows.git",
                    coordinates=update_submodule_pointer.parse_repo_coordinates(
                        "git@github.com:Carasent-ASMA/asma-workflows.git"
                    ),
                )
            ]
            mock_read_gitlink_sha.return_value = "b" * 40
            mock_clone_repository.return_value = repo_checkout
            mock_push_pointer_commit.return_value = subprocess.CompletedProcess(
                args=["git", "push"],
                returncode=0,
                stdout="",
                stderr="",
            )
            mock_find_pr.return_value = None
            mock_create_pr.return_value = update_submodule_pointer.PullRequestInfo(
                number=42,
                node_id="PR_kwDOAAABBB4",
                url="https://github.com/Carasent-ASMA/asma-modules/pull/42",
                head_ref="bot/pointer/shared-asma-workflows-aaaaaaaaaaaa",
            )
            mock_try_merge_pull_request_immediately.return_value = (
                update_submodule_pointer.PullRequestMergeAttempt(
                    merged=True,
                    message="Merged",
                )
            )

            result = update_submodule_pointer.update_pointer_for_latest_master(
                caller_repo_path=caller_repo,
                caller_repository="Carasent-ASMA/asma-workflows",
                caller_sha=target_sha,
                caller_ref_name="master",
                expected_branch="master",
                asma_modules_repository="Carasent-ASMA/asma-modules",
                asma_modules_token="token",
                asma_modules_branch="master",
                explicit_submodule_path=None,
                fail_if_unmapped=True,
                git_user_name="Test User",
                git_user_email="test@example.com",
                auto_merge_method="squash",
            )

        self.assertEqual(result.status, "updated")
        self.assertEqual(result.pr_number, "42")
        self.assertIn("Merged pointer PR #42", result.message)
        mock_ensure_branch_allows_auto_merge.assert_called_once()
        mock_try_merge_pull_request_immediately.assert_called_once()
        mock_enable_auto_merge.assert_not_called()

    @patch.object(update_submodule_pointer.github_pr_shared, "github_request")
    def test_ensure_branch_allows_auto_merge_raises_for_update_rule(
        self,
        mock_github_request: Mock,
    ) -> None:
        mock_github_request.return_value = [
            {
                "type": "pull_request",
                "ruleset_source": "Carasent-ASMA",
                "ruleset_source_type": "Organization",
                "ruleset_id": 14201319,
            },
            {
                "type": "update",
                "ruleset_source": "Carasent-ASMA/asma-modules",
                "ruleset_source_type": "Repository",
                "ruleset_id": 13925765,
            },
        ]

        with self.assertRaisesRegex(RuntimeError, "Cannot update this protected ref"):
            update_submodule_pointer.ensure_branch_allows_auto_merge(
                "Carasent-ASMA/asma-modules",
                "master",
                "token",
                "https://github.com/Carasent-ASMA/asma-modules/pull/42",
            )

    def test_resolve_submodule_path_prefers_exact_slug_match(self) -> None:
        mappings = [
            update_submodule_pointer.SubmoduleMapping(
                name="shared/asma-core-helpers",
                path="shared/asma-core-helpers",
                url="git@github.com:Carasent-ASMA/asma-core-helpers.git",
                coordinates=update_submodule_pointer.parse_repo_coordinates(
                    "git@github.com:Carasent-ASMA/asma-core-helpers.git"
                ),
            )
        ]

        resolved = update_submodule_pointer.resolve_submodule_path(
            mappings,
            "Carasent-ASMA/asma-core-helpers",
            None,
        )

        self.assertEqual(resolved, "shared/asma-core-helpers")

    def test_resolve_submodule_path_falls_back_to_path_name(self) -> None:
        mappings = [
            update_submodule_pointer.SubmoduleMapping(
                name="shared/asma-ui-core",
                path="shared/asma-ui-core",
                url="git@github.com:Carasent-ASMA/asma-core-ui.git",
                coordinates=update_submodule_pointer.parse_repo_coordinates(
                    "git@github.com:Carasent-ASMA/asma-core-ui.git"
                ),
            )
        ]

        resolved = update_submodule_pointer.resolve_submodule_path(
            mappings,
            "Carasent-ASMA/asma-ui-core",
            None,
        )

        self.assertEqual(resolved, "shared/asma-ui-core")

    def test_update_pointer_skips_when_caller_sha_is_not_latest(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            caller_remote = root / "caller-remote.git"
            caller_remote.mkdir()
            subprocess.run(["git", "init", "--bare"], cwd=caller_remote, check=True)

            caller_repo = root / "caller"
            caller_repo.mkdir()
            init_repo(caller_repo)
            (caller_repo / "README.md").write_text("one\n", encoding="utf-8")
            subprocess.run(["git", "add", "README.md"], cwd=caller_repo, check=True)
            subprocess.run(
                ["git", "commit", "-m", "chore: initial"],
                cwd=caller_repo,
                check=True,
            )
            subprocess.run(
                ["git", "remote", "add", "origin", str(caller_remote)],
                cwd=caller_repo,
                check=True,
            )
            subprocess.run(["git", "push", "-u", "origin", "master"], cwd=caller_repo, check=True)
            initial_sha = run_git(["git", "rev-parse", "HEAD"], caller_repo)

            (caller_repo / "README.md").write_text("two\n", encoding="utf-8")
            subprocess.run(["git", "add", "README.md"], cwd=caller_repo, check=True)
            subprocess.run(
                ["git", "commit", "-m", "feat: later change"],
                cwd=caller_repo,
                check=True,
            )
            subprocess.run(["git", "push", "origin", "master"], cwd=caller_repo, check=True)

            asma_remote = root / "asma-modules-remote.git"
            asma_remote.mkdir()
            subprocess.run(["git", "init", "--bare"], cwd=asma_remote, check=True)

            asma_repo = root / "asma-modules"
            asma_repo.mkdir()
            init_repo(asma_repo)
            (asma_repo / ".gitmodules").write_text(
                '[submodule "shared/asma-core-helpers"]\n'
                'path = shared/asma-core-helpers\n'
                f'url = {caller_remote.as_posix()}\n',
                encoding="utf-8",
            )
            subprocess.run(["git", "add", ".gitmodules"], cwd=asma_repo, check=True)
            subprocess.run(
                [
                    "git",
                    "update-index",
                    "--add",
                    "--cacheinfo",
                    f"160000,{initial_sha},shared/asma-core-helpers",
                ],
                cwd=asma_repo,
                check=True,
            )
            subprocess.run(
                ["git", "commit", "-m", "chore: initial pointer"],
                cwd=asma_repo,
                check=True,
            )
            subprocess.run(
                ["git", "remote", "add", "origin", str(asma_remote)],
                cwd=asma_repo,
                check=True,
            )
            subprocess.run(["git", "push", "-u", "origin", "master"], cwd=asma_repo, check=True)

            result = update_submodule_pointer.update_pointer_for_latest_master(
                caller_repo_path=caller_repo,
                caller_repository="Carasent-ASMA/asma-core-helpers",
                caller_sha=initial_sha,
                caller_ref_name="master",
                expected_branch="master",
                asma_modules_remote_url=str(asma_remote),
                asma_modules_repository="Carasent-ASMA/asma-modules",
                asma_modules_token="token",
                asma_modules_branch="master",
                explicit_submodule_path=None,
                fail_if_unmapped=True,
                git_user_name="Test User",
                git_user_email="test@example.com",
                auto_merge_method="squash",
            )

            self.assertEqual(result.status, "skipped-not-latest-master")

    @patch.object(update_submodule_pointer, "enable_pull_request_auto_merge")
    @patch.object(update_submodule_pointer, "find_open_pointer_pull_request")
    @patch.object(update_submodule_pointer, "create_pointer_pull_request")
    def test_update_pointer_opens_pull_request_for_latest_master_sha(
        self,
        mock_create_pr: Mock,
        mock_find_pr: Mock,
        mock_enable_auto_merge: Mock,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            caller_remote = root / "caller-remote.git"
            caller_remote.mkdir()
            subprocess.run(["git", "init", "--bare"], cwd=caller_remote, check=True)

            caller_repo = root / "caller"
            caller_repo.mkdir()
            init_repo(caller_repo)
            (caller_repo / "README.md").write_text("one\n", encoding="utf-8")
            subprocess.run(["git", "add", "README.md"], cwd=caller_repo, check=True)
            subprocess.run(
                ["git", "commit", "-m", "chore: initial"],
                cwd=caller_repo,
                check=True,
            )
            subprocess.run(
                ["git", "remote", "add", "origin", str(caller_remote)],
                cwd=caller_repo,
                check=True,
            )
            subprocess.run(["git", "push", "-u", "origin", "master"], cwd=caller_repo, check=True)

            (caller_repo / "README.md").write_text("two\n", encoding="utf-8")
            subprocess.run(["git", "add", "README.md"], cwd=caller_repo, check=True)
            subprocess.run(
                ["git", "commit", "-m", "feat: latest change"],
                cwd=caller_repo,
                check=True,
            )
            subprocess.run(["git", "push", "origin", "master"], cwd=caller_repo, check=True)
            latest_sha = run_git(["git", "rev-parse", "HEAD"], caller_repo)

            asma_remote = root / "asma-modules-remote.git"
            asma_remote.mkdir()
            subprocess.run(["git", "init", "--bare"], cwd=asma_remote, check=True)

            asma_repo = root / "asma-modules"
            asma_repo.mkdir()
            init_repo(asma_repo)
            (asma_repo / ".gitmodules").write_text(
                '[submodule "shared/asma-core-helpers"]\n'
                'path = shared/asma-core-helpers\n'
                'url = git@github.com:Carasent-ASMA/asma-core-helpers.git\n',
                encoding="utf-8",
            )
            subprocess.run(["git", "add", ".gitmodules"], cwd=asma_repo, check=True)
            subprocess.run(
                [
                    "git",
                    "update-index",
                    "--add",
                    "--cacheinfo",
                    f"160000,{latest_sha[:-1] + ('0' if latest_sha[-1] != '0' else '1')},shared/asma-core-helpers",
                ],
                cwd=asma_repo,
                check=True,
            )
            subprocess.run(
                ["git", "commit", "-m", "chore: initial pointer"],
                cwd=asma_repo,
                check=True,
            )
            subprocess.run(
                ["git", "remote", "add", "origin", str(asma_remote)],
                cwd=asma_repo,
                check=True,
            )
            subprocess.run(["git", "push", "-u", "origin", "master"], cwd=asma_repo, check=True)

            mock_find_pr.return_value = None
            mock_create_pr.return_value = update_submodule_pointer.PullRequestInfo(
                number=42,
                node_id="PR_kwDOAAABBB4",
                url="https://github.com/Carasent-ASMA/asma-modules/pull/42",
                head_ref="bot/pointer/shared-asma-core-helpers",
            )

            result = update_submodule_pointer.update_pointer_for_latest_master(
                caller_repo_path=caller_repo,
                caller_repository="Carasent-ASMA/asma-core-helpers",
                caller_sha=latest_sha,
                caller_ref_name="master",
                expected_branch="master",
                asma_modules_repository="Carasent-ASMA/asma-modules",
                asma_modules_token="token",
                asma_modules_remote_url=str(asma_remote),
                asma_modules_branch="master",
                explicit_submodule_path=None,
                fail_if_unmapped=True,
                git_user_name="Test User",
                git_user_email="test@example.com",
                auto_merge_method="squash",
            )

            self.assertEqual(result.status, "updated")
            self.assertEqual(result.pr_number, "42")
            self.assertEqual(
                result.pr_url,
                "https://github.com/Carasent-ASMA/asma-modules/pull/42",
            )
            mock_create_pr.assert_called_once()
            mock_enable_auto_merge.assert_called_once()

            verification_repo = root / "verify"
            subprocess.run(
                [
                    "git",
                    "clone",
                    str(asma_remote),
                    str(verification_repo),
                ],
                check=True,
            )
            branch_name = update_submodule_pointer.build_pointer_branch_name(
                "shared/asma-core-helpers",
                latest_sha,
            )
            run_git(["git", "checkout", branch_name], verification_repo)
            pointer_sha = run_git(
                ["git", "ls-tree", "HEAD", "shared/asma-core-helpers"],
                verification_repo,
            ).split()[2]
            self.assertEqual(pointer_sha, latest_sha)

    @patch.object(update_submodule_pointer, "enable_pull_request_auto_merge")
    @patch.object(update_submodule_pointer, "find_open_pointer_pull_request")
    @patch.object(update_submodule_pointer, "create_pointer_pull_request")
    def test_update_pointer_reuses_existing_open_pull_request(
        self,
        mock_create_pr: Mock,
        mock_find_pr: Mock,
        mock_enable_auto_merge: Mock,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            caller_remote = root / "caller-remote.git"
            caller_remote.mkdir()
            subprocess.run(["git", "init", "--bare"], cwd=caller_remote, check=True)

            caller_repo = root / "caller"
            caller_repo.mkdir()
            init_repo(caller_repo)
            (caller_repo / "README.md").write_text("one\n", encoding="utf-8")
            subprocess.run(["git", "add", "README.md"], cwd=caller_repo, check=True)
            subprocess.run(["git", "commit", "-m", "feat: latest change"], cwd=caller_repo, check=True)
            subprocess.run(["git", "remote", "add", "origin", str(caller_remote)], cwd=caller_repo, check=True)
            subprocess.run(["git", "push", "-u", "origin", "master"], cwd=caller_repo, check=True)
            latest_sha = run_git(["git", "rev-parse", "HEAD"], caller_repo)

            asma_remote = root / "asma-modules-remote.git"
            asma_remote.mkdir()
            subprocess.run(["git", "init", "--bare"], cwd=asma_remote, check=True)

            asma_repo = root / "asma-modules"
            asma_repo.mkdir()
            init_repo(asma_repo)
            (asma_repo / ".gitmodules").write_text(
                '[submodule "shared/asma-core-helpers"]\n'
                'path = shared/asma-core-helpers\n'
                'url = git@github.com:Carasent-ASMA/asma-core-helpers.git\n',
                encoding="utf-8",
            )
            subprocess.run(["git", "add", ".gitmodules"], cwd=asma_repo, check=True)
            subprocess.run(
                [
                    "git",
                    "update-index",
                    "--add",
                    "--cacheinfo",
                    f"160000,{latest_sha[:-1] + ('0' if latest_sha[-1] != '0' else '1')},shared/asma-core-helpers",
                ],
                cwd=asma_repo,
                check=True,
            )
            subprocess.run(["git", "commit", "-m", "chore: initial pointer"], cwd=asma_repo, check=True)
            subprocess.run(["git", "remote", "add", "origin", str(asma_remote)], cwd=asma_repo, check=True)
            subprocess.run(["git", "push", "-u", "origin", "master"], cwd=asma_repo, check=True)

            mock_find_pr.return_value = update_submodule_pointer.PullRequestInfo(
                number=42,
                node_id="PR_kwDOAAABBB4",
                url="https://github.com/Carasent-ASMA/asma-modules/pull/42",
                head_ref=update_submodule_pointer.build_pointer_branch_name(
                    "shared/asma-core-helpers",
                    latest_sha,
                ),
            )

            result = update_submodule_pointer.update_pointer_for_latest_master(
                caller_repo_path=caller_repo,
                caller_repository="Carasent-ASMA/asma-core-helpers",
                caller_sha=latest_sha,
                caller_ref_name="master",
                expected_branch="master",
                asma_modules_repository="Carasent-ASMA/asma-modules",
                asma_modules_token="token",
                asma_modules_remote_url=str(asma_remote),
                asma_modules_branch="master",
                explicit_submodule_path=None,
                fail_if_unmapped=True,
                git_user_name="Test User",
                git_user_email="test@example.com",
                auto_merge_method="squash",
            )

            self.assertEqual(result.status, "updated")
            mock_create_pr.assert_not_called()
            mock_enable_auto_merge.assert_called_once()


if __name__ == "__main__":
    unittest.main()
