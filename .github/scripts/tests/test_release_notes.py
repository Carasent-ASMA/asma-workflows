from __future__ import annotations

import importlib.util
import os
import sys
import unittest
from pathlib import Path
from types import ModuleType
from unittest import mock


SCRIPTS_DIR = Path(__file__).resolve().parents[1]
MODULE_PATH = SCRIPTS_DIR / "npm_publish" / "release_notes.py"


def load_module() -> ModuleType:
    added_paths: list[str] = []
    npm_publish_dir = SCRIPTS_DIR / "npm_publish"
    for search_path in (SCRIPTS_DIR, npm_publish_dir):
        resolved_path = str(search_path)
        if resolved_path not in sys.path:
            sys.path.insert(0, resolved_path)
            added_paths.append(resolved_path)

    spec = importlib.util.spec_from_file_location("release_notes", MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load module spec for {MODULE_PATH}")
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    finally:
        for added_path in reversed(added_paths):
            sys.path.remove(added_path)
    return module


release_notes = load_module()


class ReleaseNotesTokenTests(unittest.TestCase):
    def test_resolve_ai_token_prefers_gh_token(self) -> None:
        with mock.patch.dict(
            os.environ,
            {
                "GH_TOKEN": "gh-token",
                "COPILOT_TOKEN": "copilot-token",
                "GITHUB_TOKEN": "github-token",
            },
            clear=False,
        ):
            token, source = release_notes._resolve_ai_token()

        self.assertEqual(token, "gh-token")
        self.assertEqual(source, "GH_TOKEN")

    def test_resolve_ai_token_falls_back_to_copilot_token(self) -> None:
        with mock.patch.dict(
            os.environ,
            {
                "GH_TOKEN": "",
                "COPILOT_TOKEN": "copilot-token",
                "GITHUB_TOKEN": "github-token",
            },
            clear=False,
        ):
            token, source = release_notes._resolve_ai_token()

        self.assertEqual(token, "copilot-token")
        self.assertEqual(source, "COPILOT_TOKEN")

    def test_resolve_ai_token_does_not_fall_back_to_github_token(self) -> None:
        with mock.patch.dict(
            os.environ,
            {
                "GH_TOKEN": "",
                "COPILOT_TOKEN": "",
                "GITHUB_TOKEN": "github-token",
            },
            clear=False,
        ):
            token, source = release_notes._resolve_ai_token()

        self.assertEqual(token, "")
        self.assertEqual(source, "none")

    def test_generate_release_notes_removes_github_token_from_ai_env(self) -> None:
        completed_process = mock.Mock(returncode=0, stdout="notes", stderr="")

        with mock.patch.object(
            release_notes.Path,
            "exists",
            return_value=True,
        ), mock.patch.object(
            release_notes.Path,
            "read_text",
            return_value="{{PACKAGE_NAME}} {{VERSION}} {{COMMITS}} {{FILES}} {{AST_CONTEXT}}",
        ), mock.patch.dict(
            os.environ,
            {"GH_TOKEN": "gh-token", "GITHUB_TOKEN": "github-token"},
            clear=False,
        ), mock.patch.object(
            release_notes.subprocess,
            "run",
            return_value=completed_process,
        ) as run_mock:
            release_notes.generate_release_notes(
                package_name="test-package",
                version="1.2.3",
                previous_tag="v1.2.2",
                current_tag="v1.2.3",
                commit_lines=["- feat: change"],
                file_lines=["src/index.ts"],
            )

        env = run_mock.call_args.kwargs["env"]
        self.assertEqual(env["GH_TOKEN"], "gh-token")
        self.assertNotIn("COPILOT_GITHUB_TOKEN", env)
        self.assertNotIn("GITHUB_TOKEN", env)

    def test_generate_release_notes_reports_missing_gh_token(self) -> None:
        with mock.patch.object(
            release_notes.Path,
            "exists",
            return_value=True,
        ), mock.patch.object(
            release_notes.Path,
            "read_text",
            return_value="{{PACKAGE_NAME}} {{VERSION}} {{COMMITS}} {{FILES}} {{AST_CONTEXT}}",
        ), mock.patch.dict(
            os.environ,
            {
                "GH_TOKEN": "",
                "COPILOT_TOKEN": "",
                "GITHUB_TOKEN": "github-token",
            },
            clear=False,
        ), mock.patch.object(
            release_notes.subprocess,
            "run",
            return_value=mock.Mock(returncode=1, stderr="boom", stdout=""),
        ):
            with self.assertRaisesRegex(
                RuntimeError,
                "no dedicated GH_TOKEN or COPILOT_TOKEN",
            ):
                release_notes.generate_release_notes(
                    package_name="test-package",
                    version="1.2.3",
                    previous_tag="v1.2.2",
                    current_tag="v1.2.3",
                    commit_lines=["- feat: change"],
                    file_lines=["src/index.ts"],
                )


if __name__ == "__main__":
    unittest.main()