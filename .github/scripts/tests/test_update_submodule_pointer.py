from __future__ import annotations

import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import ModuleType


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
                asma_modules_branch="master",
                explicit_submodule_path=None,
                fail_if_unmapped=True,
                git_user_name="Test User",
                git_user_email="test@example.com",
            )

            self.assertEqual(result.status, "skipped-not-latest-master")

    def test_update_pointer_commits_latest_master_sha(self) -> None:
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

            result = update_submodule_pointer.update_pointer_for_latest_master(
                caller_repo_path=caller_repo,
                caller_repository="Carasent-ASMA/asma-core-helpers",
                caller_sha=latest_sha,
                caller_ref_name="master",
                expected_branch="master",
                asma_modules_remote_url=str(asma_remote),
                asma_modules_branch="master",
                explicit_submodule_path=None,
                fail_if_unmapped=True,
                git_user_name="Test User",
                git_user_email="test@example.com",
            )

            self.assertEqual(result.status, "updated")

            verification_repo = root / "verify"
            subprocess.run(
                [
                    "git",
                    "clone",
                    "--branch",
                    "master",
                    str(asma_remote),
                    str(verification_repo),
                ],
                check=True,
            )
            pointer_sha = run_git(
                ["git", "ls-tree", "HEAD", "shared/asma-core-helpers"],
                verification_repo,
            ).split()[2]
            self.assertEqual(pointer_sha, latest_sha)


if __name__ == "__main__":
    unittest.main()
