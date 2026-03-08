import argparse
import json
import os
import pathlib
import subprocess
import sys
from pathlib import Path


def run_capture(
    cmd: list[str], allow_fail: bool = False, env: dict[str, str] | None = None
) -> str:
    result = subprocess.run(cmd, capture_output=True, text=True, env=env)
    if result.returncode != 0 and not allow_fail:
        raise RuntimeError(f"Command failed: {' '.join(cmd)}\n{result.stderr}")
    return result.stdout.strip()


def run(
    cmd: list[str], check: bool = True, env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[bytes]:
    print("+", " ".join(cmd))
    return subprocess.run(cmd, check=check, env=env)


def write_output(key: str, value: str) -> None:
    output_path = os.environ.get("GITHUB_OUTPUT")
    if not output_path:
        return
    with Path(output_path).open("a", encoding="utf-8") as output_file:
        output_file.write(f"{key}={value}\n")


def read_package_version() -> str:
    """Read the version field from package.json in the current directory."""
    with Path("package.json").open("r", encoding="utf-8") as package_file:
        return json.load(package_file)["version"]


def cmd_validate_package_name() -> None:
    """Validate that the expected package name matches package.json."""
    required_name = os.environ.get("PACKAGE_NAME", "").strip()
    if not required_name:
        print("PACKAGE_NAME is required and cannot be empty")
        sys.exit(1)

    package_json_path = Path("package.json")
    if not package_json_path.exists():
        print("package.json not found in repository root")
        sys.exit(1)

    with package_json_path.open("r", encoding="utf-8") as package_file:
        package_name = json.load(package_file).get("name", "").strip()

    if not package_name:
        print("package.json name field is missing or empty")
        sys.exit(1)

    if package_name != required_name:
        print(
            f"package_name input mismatch: expected '{required_name}', package.json has '{package_name}'"
        )
        sys.exit(1)

    print(f"✅ package_name validated: {package_name}")


def cmd_remove_legacy_npm_config() -> None:
    """Remove legacy user-scoped npm auth config that can break publish."""
    run(["npm", "config", "delete", "always-auth", "--location=user"], check=False)


def cmd_read_package_version() -> None:
    """Expose the current package.json version as a step output."""
    version = read_package_version()
    print(version)
    write_output("version", version)


def cmd_apply_version() -> None:
    """Apply a resolved version to package.json-related files."""
    version = os.environ["VERSION"].strip()
    files_to_commit = ["package.json"]
    for candidate in ("pnpm-lock.yaml", "package-lock.json"):
        if pathlib.Path(candidate).exists():
            files_to_commit.append(candidate)

    run(["npm", "version", version, "--no-git-tag-version", "--allow-same-version"])

    write_output("version", str(version))
    write_output("files_to_commit", " ".join(files_to_commit))


def cmd_build_summary() -> None:
    """Write the npm publish summary to the GitHub step summary file."""
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not summary_path:
        return

    package_name = os.environ.get("PACKAGE_NAME", "package")
    code_changed = os.environ.get("CODE_CHANGED", "false") == "true"
    should_publish = os.environ.get("SHOULD_PUBLISH", "false") == "true"
    publish_npm = os.environ.get("PUBLISH_NPM", "true") == "true"
    bump_type = os.environ.get("BUMP_TYPE", "none")
    version = os.environ.get("VERSION", "")

    lines: list[str] = [f"### Build Summary - {package_name}"]

    if not code_changed:
        lines.append("- ⏭️ No code changes detected (only docs/config changed)")
        lines.append("- ⏭️ Build and publish skipped")
    else:
        lines.append("- ✅ Code changes detected")
        lines.append("- ✅ Dependencies installed")
        lines.append("- ✅ Package built successfully")

        if should_publish:
            if version:
                lines.append(f"- ✅ Version bumped to v{version} ({bump_type})")
                lines.append("- ✅ GitHub Release created")
            if publish_npm:
                lines.append("- ✅ Published to npm")
            else:
                lines.append("- ⏭️ npm publish skipped (publish_npm=false)")
        else:
            lines.append(
                "- ⏭️ Publish skipped (no feat/fix/perf/breaking commits found)"
            )

    with Path(summary_path).open("a", encoding="utf-8") as summary_file:
        summary_file.write("\n".join(lines) + "\n")


def main() -> None:
    """Dispatch npm package release helper commands."""
    parser = argparse.ArgumentParser(
        description="package.json and npm-specific release workflow helper"
    )
    parser.add_argument(
        "command",
        choices=[
            "validate-package-name",
            "remove-legacy-npm-config",
            "read-package-version",
            "apply-version",
            "build-summary",
        ],
    )
    args = parser.parse_args()

    command_handlers = {
        "validate-package-name": cmd_validate_package_name,
        "remove-legacy-npm-config": cmd_remove_legacy_npm_config,
        "read-package-version": cmd_read_package_version,
        "apply-version": cmd_apply_version,
        "build-summary": cmd_build_summary,
    }
    command_handlers[args.command]()


if __name__ == "__main__":
    main()