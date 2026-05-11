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
    def test_resolve_ai_backend_config_prefers_explicit_values(self) -> None:
        with mock.patch.dict(
            os.environ,
            {
                "ASMA_AI_BASE_URL": "https://example.com/api/editor",
                "ASMA_SYSTEM_USER": "asma.workflow",
                "ASMA_AI_API_TOKEN": "shared-token",
            },
            clear=False,
        ):
            base_url, system_user, api_token = release_notes._resolve_ai_backend_config()

        self.assertEqual(base_url, "https://example.com/api/editor")
        self.assertEqual(system_user, "asma.workflow")
        self.assertEqual(api_token, "shared-token")

    def test_resolve_ai_backend_config_uses_defaults_when_optional_values_missing(self) -> None:
        with mock.patch.dict(
            os.environ,
            {
                "ASMA_AI_BASE_URL": "",
                "ASMA_SYSTEM_USER": "",
                "ASMA_AI_API_TOKEN": "shared-token",
            },
            clear=False,
        ):
            base_url, system_user, api_token = release_notes._resolve_ai_backend_config()

        self.assertEqual(base_url, release_notes.DEFAULT_AI_BASE_URL)
        self.assertEqual(system_user, release_notes.DEFAULT_AI_SYSTEM_USER)
        self.assertEqual(api_token, "shared-token")

    def test_build_ai_auth_header_uses_bearer_base64_payload(self) -> None:
        header = release_notes._build_ai_auth_header("asma.system_user", "secret-token")

        self.assertEqual(
            header,
            "Bearer YXNtYS5zeXN0ZW1fdXNlcjpzZWNyZXQtdG9rZW4=",
        )

    def test_generate_release_notes_posts_json_to_backend(self) -> None:
        response = mock.MagicMock()
        response.read.return_value = b'{"content":"notes"}'
        response.__enter__.return_value = response

        with mock.patch.dict(
            os.environ,
            {
                "ASMA_AI_BASE_URL": "https://example.com/api/editor",
                "ASMA_SYSTEM_USER": "asma.system_user",
                "ASMA_AI_API_TOKEN": "shared-token",
            },
            clear=False,
        ), mock.patch.object(
            release_notes.Path,
            "exists",
            return_value=True,
        ), mock.patch.object(
            release_notes.Path,
            "read_text",
            return_value="{{PACKAGE_NAME}} {{VERSION}} {{COMMITS}} {{FILES}} {{AST_CONTEXT}}",
        ), mock.patch.object(
            release_notes.urllib.request,
            "urlopen",
            return_value=response,
        ) as urlopen_mock:
            release_notes.generate_release_notes(
                package_name="test-package",
                version="1.2.3",
                previous_tag="v1.2.2",
                current_tag="v1.2.3",
                commit_lines=["- feat: change"],
                file_lines=["src/index.ts"],
            )

        request = urlopen_mock.call_args.args[0]
        self.assertEqual(
            request.full_url,
            "https://example.com/api/editor/ai/asma-cli/generate-release-notes",
        )
        self.assertEqual(
            request.get_header("Authorization"),
            "Bearer YXNtYS5zeXN0ZW1fdXNlcjpzaGFyZWQtdG9rZW4=",
        )
        self.assertEqual(request.get_method(), "POST")
        self.assertIn('"prompt":', request.data.decode("utf-8"))

    def test_generate_release_notes_reports_missing_ai_token(self) -> None:
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
                "ASMA_AI_BASE_URL": "https://example.com/api/editor",
                "ASMA_AI_API_TOKEN": "",
            },
            clear=False,
        ):
            with self.assertRaisesRegex(
                RuntimeError,
                "ASMA_AI_API_TOKEN is required",
            ):
                release_notes.generate_release_notes(
                    package_name="test-package",
                    version="1.2.3",
                    previous_tag="v1.2.2",
                    current_tag="v1.2.3",
                    commit_lines=["- feat: change"],
                    file_lines=["src/index.ts"],
                )

    def test_build_release_notes_prompt_truncates_large_sections(self) -> None:
        template = "{{COMMITS}}\n---\n{{FILES}}\n---\n{{AST_CONTEXT}}"
        commit_lines = [f"- feat: change {index}" for index in range(120)]
        file_lines = [f"src/file_{index}.ts" for index in range(150)]
        ast_context = "A" * (release_notes.MAX_AST_CONTEXT_CHARS + 250)

        prompt = release_notes._build_release_notes_prompt(
            template=template,
            package_name="test-package",
            version="1.2.3",
            previous_tag="v1.2.2",
            current_tag="v1.2.3",
            commit_lines=commit_lines,
            file_lines=file_lines,
            ast_context=ast_context,
        )

        self.assertLessEqual(len(prompt), release_notes.MAX_PROMPT_CHARS)
        self.assertIn("truncated 40 older commit lines", prompt)
        self.assertIn("truncated 30 additional changed files", prompt)
        self.assertIn("AST context truncated", prompt)

    def test_generate_release_notes_wraps_oserror(self) -> None:
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
                "ASMA_AI_BASE_URL": "https://example.com/api/editor",
                "ASMA_AI_API_TOKEN": "shared-token",
            },
            clear=False,
        ), mock.patch.object(
            release_notes.urllib.request,
            "urlopen",
            side_effect=OSError(7, "Argument list too long", "gh"),
        ):
            with self.assertRaisesRegex(RuntimeError, "Argument list too long"):
                release_notes.generate_release_notes(
                    package_name="test-package",
                    version="1.2.3",
                    previous_tag="v1.2.2",
                    current_tag="v1.2.3",
                    commit_lines=["- feat: change"],
                    file_lines=["src/index.ts"],
                    ast_context="AST" * 100,
                )


if __name__ == "__main__":
    unittest.main()