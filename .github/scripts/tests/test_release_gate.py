from __future__ import annotations

import importlib.util
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from types import ModuleType
from unittest import mock


MODULE_PATH = Path(__file__).resolve().parents[1] / "release_gate.py"


def load_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("release_gate", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load module spec for {MODULE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


release_gate = load_module()


class ReleaseGateTests(unittest.TestCase):
    def test_determine_bump_type_prefers_highest_severity(self) -> None:
        bump_type, should_publish = release_gate.determine_bump_type(
            ["fix: patch", "feat: feature", "refactor!: breaking"]
        )

        self.assertEqual(bump_type, "major")
        self.assertTrue(should_publish)

    def test_determine_bump_type_treats_style_refactor_and_chore_as_patch(self) -> None:
        for commit in [
            "style: Update tailwind classes",
            "refactor: Simplify cache invalidation",
            "chore: Refresh generated assets",
        ]:
            with self.subTest(commit=commit):
                bump_type, should_publish = release_gate.determine_bump_type([commit])

                self.assertEqual(bump_type, "patch")
                self.assertTrue(should_publish)

    def test_determine_bump_type_reads_squash_commit_details(self) -> None:
        bump_type, should_publish = release_gate.determine_bump_type(
            [
                "Release login improvements (#42)\n\n"
                "* fix: resolve token refresh\n"
                "* feat: add silent login"
            ]
        )

        self.assertEqual(bump_type, "minor")
        self.assertTrue(should_publish)

    def test_determine_bump_type_treats_docs_and_merge_commits_as_patch(self) -> None:
        for commit in [
            "docs: update release runbook",
            "Merged in feature/asma-123 (pull request #44)",
        ]:
            with self.subTest(commit=commit):
                bump_type, should_publish = release_gate.determine_bump_type([commit])

                self.assertEqual(bump_type, "patch")
                self.assertTrue(should_publish)

    def test_determine_bump_type_treats_docs_breaking_change_as_major(self) -> None:
        bump_type, should_publish = release_gate.determine_bump_type(
            ["docs!: reset migration guide"]
        )

        self.assertEqual(bump_type, "major")
        self.assertTrue(should_publish)

    def test_has_matching_changes_matches_regex_patterns(self) -> None:
        changed, first_match = release_gate.has_matching_changes(
            ["README.md", "src/index.ts"],
            [r"^src/", r"^package\.json$"],
        )

        self.assertTrue(changed)
        self.assertEqual(first_match, "src/index.ts")

    def test_has_matching_changes_ignores_non_matching_paths(self) -> None:
        changed, first_match = release_gate.has_matching_changes(
            ["README.md", "docs/guide.md"],
            [r"^src/", r"^package\.json$"],
        )

        self.assertFalse(changed)
        self.assertIsNone(first_match)

    def test_check_path_changes_writes_custom_result_output_key(self) -> None:
        args = SimpleNamespace(
            base_ref="v1.0.0",
            patterns=[r"^src/"],
            result_output_key="code_changed",
        )

        with mock.patch.object(
            release_gate, "list_changed_files", return_value=["src/index.ts"]
        ), mock.patch.object(release_gate, "write_output") as write_output_mock:
            release_gate.cmd_check_path_changes(args)

        write_output_mock.assert_any_call("changed", "true")
        write_output_mock.assert_any_call("code_changed", "true")

    def test_release_gate_stops_when_no_release_commit_messages_exist(self) -> None:
        args = SimpleNamespace(
            base_ref="v1.0.0",
            patterns=[r"^src/"],
            strategy=release_gate.ANALYSIS_STRATEGY_ALL_COMMITS,
        )

        with mock.patch.object(
            release_gate,
            "load_commit_messages",
            return_value=["Update release docs"],
        ), mock.patch.object(release_gate, "write_output") as write_output_mock:
            release_gate.cmd_release_gate(args)

        write_output_mock.assert_any_call("code_changed", "false")
        write_output_mock.assert_any_call("should_publish", "false")
        write_output_mock.assert_any_call("should_continue", "false")

    def test_release_gate_sets_should_continue_for_release_changes(self) -> None:
        args = SimpleNamespace(
            base_ref="v1.0.0",
            patterns=[r"^src/"],
            strategy=release_gate.ANALYSIS_STRATEGY_ALL_COMMITS,
        )

        with mock.patch.object(
            release_gate, "list_changed_files", return_value=["src/index.ts"]
        ), mock.patch.object(
            release_gate, "load_commit_messages", return_value=["feat: add source"]
        ), mock.patch.object(release_gate, "write_output") as write_output_mock:
            release_gate.cmd_release_gate(args)

        write_output_mock.assert_any_call("code_changed", "true")
        write_output_mock.assert_any_call("should_publish", "true")
        write_output_mock.assert_any_call("bump_type", "minor")
        write_output_mock.assert_any_call("should_continue", "true")

    def test_release_gate_force_release_marker_bypasses_commit_prefix_checks(
        self,
    ) -> None:
        args = SimpleNamespace(
            base_ref="v1.0.0",
            patterns=[r"^src/"],
            strategy=release_gate.ANALYSIS_STRATEGY_ALL_COMMITS,
        )

        with mock.patch.object(
            release_gate,
            "load_commit_messages",
            return_value=["release ui icons --force-release"],
        ), mock.patch.object(release_gate, "write_output") as write_output_mock:
            release_gate.cmd_release_gate(args)

        write_output_mock.assert_any_call("code_changed", "true")
        write_output_mock.assert_any_call("should_publish", "true")
        write_output_mock.assert_any_call("bump_type", "patch")
        write_output_mock.assert_any_call("should_continue", "true")

    def test_release_gate_writes_expected_summary_outputs(self) -> None:
        args = SimpleNamespace(
            base_ref="v1.0.0",
            patterns=[r"^src/"],
            strategy=release_gate.ANALYSIS_STRATEGY_ALL_COMMITS,
        )

        with mock.patch.object(
            release_gate,
            "load_commit_messages",
            return_value=["docs: update release docs"],
        ), mock.patch.object(release_gate, "write_output") as write_output_mock:
            release_gate.cmd_release_gate(args)

        write_output_mock.assert_any_call("bump_type", "patch")
        write_output_mock.assert_any_call("should_continue", "true")

class ReleaseGateGitRepoTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.repo_path = Path(self.temp_dir.name)
        self.previous_cwd = Path.cwd()
        subprocess.run(["git", "init", "-b", "main"], cwd=self.repo_path, check=True)
        subprocess.run(
            ["git", "config", "user.name", "Test User"], cwd=self.repo_path, check=True
        )
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=self.repo_path,
            check=True,
        )
        (self.repo_path / "README.md").write_text("initial\n", encoding="utf-8")
        subprocess.run(["git", "add", "README.md"], cwd=self.repo_path, check=True)
        subprocess.run(
            ["git", "commit", "-m", "chore: initial commit"],
            cwd=self.repo_path,
            check=True,
        )
        os.chdir(self.repo_path)

    def tearDown(self) -> None:
        os.chdir(self.previous_cwd)
        self.temp_dir.cleanup()

    def test_list_changed_files_uses_base_ref(self) -> None:
        subprocess.run(["git", "tag", "v1.0.0"], cwd=self.repo_path, check=True)
        src_dir = self.repo_path / "src"
        src_dir.mkdir()
        (src_dir / "index.ts").write_text("export const x = 1;\n", encoding="utf-8")
        subprocess.run(["git", "add", "src/index.ts"], cwd=self.repo_path, check=True)
        subprocess.run(
            ["git", "commit", "-m", "feat: add source"],
            cwd=self.repo_path,
            check=True,
        )

        changed_files = release_gate.list_changed_files("v1.0.0")

        self.assertEqual(changed_files, ["src/index.ts"])

    def test_list_changed_files_without_tag_returns_tracked_files(self) -> None:
        src_dir = self.repo_path / "src"
        src_dir.mkdir()
        (src_dir / "index.ts").write_text("export const x = 1;\n", encoding="utf-8")
        subprocess.run(["git", "add", "src/index.ts"], cwd=self.repo_path, check=True)
        subprocess.run(
            ["git", "commit", "-m", "feat: add source"],
            cwd=self.repo_path,
            check=True,
        )

        changed_files = release_gate.list_changed_files(None)

        self.assertEqual(changed_files, ["README.md", "src/index.ts"])

    def test_load_commit_messages_without_tag_reads_full_history(self) -> None:
        src_dir = self.repo_path / "src"
        src_dir.mkdir()
        (src_dir / "index.ts").write_text("export const x = 1;\n", encoding="utf-8")
        subprocess.run(["git", "add", "src/index.ts"], cwd=self.repo_path, check=True)
        subprocess.run(
            ["git", "commit", "-m", "feat: add source"],
            cwd=self.repo_path,
            check=True,
        )

        commits = release_gate.load_commit_messages(
            release_gate.ANALYSIS_STRATEGY_ALL_COMMITS,
            None,
        )

        self.assertEqual(commits, ["feat: add source", "chore: initial commit"])


if __name__ == "__main__":
    unittest.main()