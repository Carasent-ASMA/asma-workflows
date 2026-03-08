from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import ModuleType
from unittest import mock


SCRIPTS_DIR = Path(__file__).resolve().parents[1]


def load_module(module_name: str, file_name: str) -> ModuleType:
    added_paths: list[str] = []
    for search_path in (SCRIPTS_DIR, SCRIPTS_DIR / "npm_publish"):
        resolved_path = str(search_path)
        if resolved_path not in sys.path:
            sys.path.insert(0, resolved_path)
            added_paths.append(resolved_path)

    spec = importlib.util.spec_from_file_location(
        module_name,
        SCRIPTS_DIR / file_name,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load module spec for {file_name}")
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    finally:
        for added_path in reversed(added_paths):
            sys.path.remove(added_path)
    return module


git_tagging_ops = load_module("git_tagging_ops", "git_tagging_ops.py")
git_tagging_plan = load_module("git_tagging_plan", "git_tagging_plan.py")
git_tagging_shared = load_module("git_tagging_shared", "git_tagging_shared.py")


class GitRepoTestCase(unittest.TestCase):
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

    def create_commit(self, message: str, filename: str, content: str) -> None:
        (self.repo_path / filename).write_text(content, encoding="utf-8")
        subprocess.run(["git", "add", filename], cwd=self.repo_path, check=True)
        subprocess.run(["git", "commit", "-m", message], cwd=self.repo_path, check=True)


class GitTaggingTests(GitRepoTestCase):
    def test_bump_version_minor_resets_patch(self) -> None:
        self.assertEqual(git_tagging_shared.bump_version("0.2.1", "minor"), "0.3.0")

    def test_bump_version_major_resets_minor_and_patch(self) -> None:
        self.assertEqual(git_tagging_shared.bump_version("0.2.1", "major"), "1.0.0")

    def test_tag_exists_detects_existing_and_missing_tags(self) -> None:
        subprocess.run(["git", "tag", "v1.0.0"], cwd=self.repo_path, check=True)
        self.assertTrue(git_tagging_plan.tag_exists("v1.0.0"))
        self.assertFalse(git_tagging_plan.tag_exists("v1.0.1"))

    def test_resolve_free_stable_tag_skips_existing_tags(self) -> None:
        subprocess.run(["git", "tag", "v1.2.4"], cwd=self.repo_path, check=True)
        version, tag = git_tagging_plan.resolve_free_stable_tag(
            "1.2.4", "patch", max_attempts=3
        )
        self.assertEqual(version, "1.2.5")
        self.assertEqual(tag, "v1.2.5")

    def test_resolve_next_stable_release_uses_latest_stable_tag(self) -> None:
        subprocess.run(["git", "tag", "v1.2.3"], cwd=self.repo_path, check=True)

        version, tag = git_tagging_plan.resolve_next_stable_release(
            "minor", "0.1.0"
        )

        self.assertEqual(version, "1.3.0")
        self.assertEqual(tag, "v1.3.0")

    def test_resolve_hotpatch_tag_rejects_invalid_branch_name(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "required format"):
            git_tagging_plan.resolve_hotpatch_tag("feature/login")

    def test_resolve_hotpatch_tag_uses_highest_existing_suffix(self) -> None:
        subprocess.run(["git", "tag", "v1.2.3"], cwd=self.repo_path, check=True)
        self.create_commit("fix: patch one", "one.txt", "1\n")
        subprocess.run(["git", "tag", "v1.2.3-1"], cwd=self.repo_path, check=True)
        self.create_commit("fix: patch two", "two.txt", "2\n")
        subprocess.run(["git", "tag", "v1.2.3-2"], cwd=self.repo_path, check=True)

        version, tag = git_tagging_plan.resolve_hotpatch_tag("releases/v1.2.3")

        self.assertEqual(version, "1.2.3-3")
        self.assertEqual(tag, "v1.2.3-3")

    def test_resolve_hotpatch_tag_returns_first_free_suffix(self) -> None:
        subprocess.run(["git", "tag", "v1.2.3"], cwd=self.repo_path, check=True)
        self.create_commit("fix: patch one", "one.txt", "1\n")
        subprocess.run(["git", "tag", "v1.2.3-1"], cwd=self.repo_path, check=True)
        self.create_commit("fix: patch three", "three.txt", "3\n")
        subprocess.run(["git", "tag", "v1.2.3-3"], cwd=self.repo_path, check=True)

        version, tag = git_tagging_plan.resolve_hotpatch_tag("releases/v1.2.3")

        self.assertEqual(version, "1.2.3-2")
        self.assertEqual(tag, "v1.2.3-2")

    def test_commit_and_push_follow_tags_builds_expected_git_commands(self) -> None:
        with mock.patch.object(git_tagging_ops, "run") as run_mock, mock.patch.object(
            git_tagging_ops, "create_annotated_tag"
        ) as create_tag_mock:
            git_tagging_ops.commit_and_push_follow_tags(
                files=["package.json", "pnpm-lock.yaml"],
                commit_message="chore: bump version to v1.2.3 [skip ci]",
                tag="v1.2.3",
                tag_message="chore: bump version to 1.2.3 [skip ci]",
                remote_name="origin",
            )

        commands = [call.args[0] for call in run_mock.call_args_list]
        create_tag_mock.assert_called_once_with(
            "v1.2.3",
            "chore: bump version to 1.2.3 [skip ci]",
        )
        self.assertEqual(
            commands,
            [
                ["git", "add", "package.json", "pnpm-lock.yaml"],
                ["git", "commit", "-m", "chore: bump version to v1.2.3 [skip ci]"],
                ["git", "push", "origin", "--follow-tags"],
            ],
        )


if __name__ == "__main__":
    unittest.main()