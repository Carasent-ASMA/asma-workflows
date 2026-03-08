from __future__ import annotations

import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path
from types import ModuleType
from unittest import mock


MODULE_PATH = Path(__file__).resolve().parents[1] / "npm_publish" / "package_json_npm_release.py"


def load_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "package_json_npm_release",
        MODULE_PATH,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load module spec for {MODULE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


package_release = load_module()


class WorkflowPackageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.repo_path = Path(self.temp_dir.name)
        self.previous_cwd = Path.cwd()
        (self.repo_path / "package.json").write_text(
            json.dumps({"name": "test-package", "version": "1.0.0"}),
            encoding="utf-8",
        )
        os.chdir(self.repo_path)

    def tearDown(self) -> None:
        os.chdir(self.previous_cwd)
        self.temp_dir.cleanup()

    def test_read_package_version_returns_package_json_version(self) -> None:
        self.assertEqual(package_release.read_package_version(), "1.0.0")

    def test_apply_version_uses_resolved_version(self) -> None:
        os.environ["VERSION"] = "1.2.3"

        with mock.patch.object(package_release, "run") as run_mock, mock.patch.object(
            package_release, "write_output"
        ) as write_output_mock:
            package_release.cmd_apply_version()

        run_mock.assert_called_once_with(
            [
                "npm",
                "version",
                "1.2.3",
                "--no-git-tag-version",
                "--allow-same-version",
            ]
        )
        write_output_mock.assert_any_call("version", "1.2.3")
        write_output_mock.assert_any_call("files_to_commit", "package.json")


if __name__ == "__main__":
    unittest.main()