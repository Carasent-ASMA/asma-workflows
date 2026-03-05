import argparse
import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile
from pathlib import Path


def run_capture(cmd: list[str], allow_fail: bool = False) -> str:
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0 and not allow_fail:
        raise RuntimeError(f"Command failed: {' '.join(cmd)}\n{result.stderr}")
    return result.stdout.strip()


def run(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess[bytes]:
    print("+", " ".join(cmd))
    return subprocess.run(cmd, check=check)


def write_output(key: str, value: str) -> None:
    output_path = os.environ.get("GITHUB_OUTPUT")
    if not output_path:
        return
    with Path(output_path).open("a", encoding="utf-8") as output_file:
        output_file.write(f"{key}={value}\n")


def cmd_validate_package_name() -> None:
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


def cmd_check_changes() -> None:
    last_tag = run_capture(["git", "describe", "--tags", "--abbrev=0"], allow_fail=True)
    if not last_tag:
        last_tag = run_capture(["git", "rev-list", "--max-parents=0", "HEAD"])

    changed_files_raw = run_capture(
        ["git", "diff", "--name-only", f"{last_tag}..HEAD"], allow_fail=True
    )
    changed_files = [
        line.strip() for line in changed_files_raw.splitlines() if line.strip()
    ]

    print(f"Changed files since {last_tag}:")
    for file_path in changed_files:
        print(file_path)

    patterns = [
        re.compile(r"^src/"),
        re.compile(r"^package\.json$"),
        re.compile(r"^pnpm-lock\.yaml$"),
        re.compile(r"^tsconfig\.json$"),
        re.compile(r"^\.npmignore$"),
    ]

    code_changed = False
    for file_path in changed_files:
        if any(pattern.search(file_path) for pattern in patterns):
            code_changed = True
            print(f"✓ Code change detected: {file_path}")
            break

    write_output("code_changed", "true" if code_changed else "false")

    if code_changed:
        print("✅ Code changes detected - will build and potentially publish")
    else:
        print("⏭️  No code changes - skipping build/publish (only docs/config changed)")


def cmd_remove_legacy_npm_config() -> None:
    run(["npm", "config", "delete", "always-auth", "--location=user"], check=False)


def cmd_analyze_commits() -> None:
    last_tag = run_capture(["git", "describe", "--tags", "--abbrev=0"], allow_fail=True)

    if last_tag:
        commits_raw = run_capture(
            ["git", "log", f"{last_tag}..HEAD", "--format=%s"], allow_fail=True
        )
    else:
        has_origin_master = (
            subprocess.run(
                ["git", "rev-parse", "--verify", "origin/master"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            ).returncode
            == 0
        )
        if has_origin_master:
            commits_raw = run_capture(
                ["git", "log", "origin/master", "--format=%s"], allow_fail=True
            )
        else:
            commits_raw = run_capture(
                ["git", "log", "HEAD", "--format=%s"], allow_fail=True
            )

    commits = [line.strip() for line in commits_raw.splitlines() if line.strip()]

    print("Analyzing commits for version bump...")
    for commit in commits:
        print(commit)

    bump_type = "none"
    should_publish = False

    for commit in commits:
        if re.search(r"^[a-z]+!(\([^)]*\))?:", commit):
            bump_type = "major"
            should_publish = True
            print(f"Found breaking change: {commit}")
            continue

        if bump_type != "major" and re.search(r"^feat(\([^)]*\))?:", commit):
            bump_type = "minor"
            should_publish = True
            print(f"Found feature: {commit}")
            continue

        if bump_type not in {"major", "minor"} and re.search(
            r"^(fix|perf)(\([^)]*\))?:", commit
        ):
            bump_type = "patch"
            should_publish = True
            print(f"Found fix/perf: {commit}")

    write_output("should_publish", "true" if should_publish else "false")
    write_output("bump_type", bump_type)

    if should_publish:
        print(f"✅ Will publish with {bump_type} version bump")
    else:
        print("⏭️  No version bump needed (no feat/fix/perf/breaking commits)")


def cmd_configure_git() -> None:
    github_token = os.environ["GITHUB_TOKEN"]
    github_repository = os.environ["GITHUB_REPOSITORY"]

    run(["git", "config", "--global", "user.name", "github-actions[bot]"])
    run(
        [
            "git",
            "config",
            "--global",
            "user.email",
            "github-actions[bot]@users.noreply.github.com",
        ]
    )
    run(
        [
            "git",
            "remote",
            "set-url",
            "origin",
            f"https://x-access-token:{github_token}@github.com/{github_repository}.git",
        ]
    )


def tag_exists(tag: str) -> bool:
    result = subprocess.run(
        ["git", "rev-parse", "-q", "--verify", f"refs/tags/{tag}"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return result.returncode == 0


def cmd_bump_version() -> None:
    run(["git", "fetch", "--tags", "--force"])

    bump_type = os.environ["BUMP_TYPE"]
    max_attempts = 10
    version: str | None = None
    tag: str | None = None

    for _ in range(max_attempts):
        run(["npm", "version", bump_type, "--no-git-tag-version"])

        with open("package.json", "r", encoding="utf-8") as package_file:
            version = json.load(package_file)["version"]
        tag = f"v{version}"

        if tag_exists(tag):
            print(f"Tag {tag} already exists, bumping again...")
            continue

        break
    else:
        print(f"Unable to find a free version tag after {max_attempts} attempts")
        sys.exit(1)

    files_to_add = ["package.json"]
    for candidate in ("pnpm-lock.yaml", "package-lock.json"):
        if pathlib.Path(candidate).exists():
            files_to_add.append(candidate)

    run(["git", "add", *files_to_add])
    run(["git", "commit", "-m", f"chore: bump version to {tag} [skip ci]"])
    run(
        [
            "git",
            "tag",
            "-a",
            str(tag),
            "-m",
            f"chore: bump version to {version} [skip ci]",
        ]
    )
    run(["git", "push", "--follow-tags"])

    write_output("version", str(version))


def cmd_create_release() -> None:
    version = os.environ["VERSION"]
    bump_type = os.environ.get("BUMP_TYPE", "patch")
    package_name = os.environ.get("PACKAGE_NAME", "package")
    ai_enabled = os.environ.get("AI_RELEASE_NOTES_ENABLED", "true").lower() == "true"
    ai_model = os.environ.get("AI_RELEASE_NOTES_MODEL", "").strip()
    current_tag = f"v{version}"

    tags_raw = run_capture(["git", "tag", "--sort=-creatordate"], allow_fail=True)
    tags = [tag.strip() for tag in tags_raw.splitlines() if tag.strip()]
    previous_tag = next((tag for tag in tags if tag != current_tag), "")

    if previous_tag:
        commit_range = f"{previous_tag}..{current_tag}"
    else:
        commit_range = current_tag

    commits_raw = run_capture(
        ["git", "log", commit_range, "--pretty=format:- %s (%h)"], allow_fail=True
    )
    commit_lines = [line for line in commits_raw.splitlines() if line.strip()]
    files_raw = run_capture(
        ["git", "diff", "--name-only", commit_range], allow_fail=True
    )
    file_lines = [line for line in files_raw.splitlines() if line.strip()][:200]

    custom_lines = [f"## Commit Summary ({bump_type})"]
    if commit_lines:
        custom_lines.extend(commit_lines)
    else:
        custom_lines.append("- No commits found for summary")

    custom_notes = "\n".join(custom_lines)

    def generate_ai_release_notes() -> str:
        prompt_path = Path(__file__).with_name("release_notes_prompt.md")
        if not prompt_path.exists():
            raise RuntimeError(f"Prompt template not found: {prompt_path}")

        prompt_template = prompt_path.read_text(encoding="utf-8")
        filled_prompt = (
            prompt_template.replace("__PACKAGE_NAME__", package_name)
            .replace("__VERSION__", version)
            .replace("__BUMP_TYPE__", bump_type)
            .replace("__PREVIOUS_TAG__", previous_tag or "none")
            .replace("__CURRENT_TAG__", current_tag)
            .replace(
                "__COMMITS__", "\n".join(commit_lines) if commit_lines else "- none"
            )
            .replace("__FILES__", "\n".join(file_lines) if file_lines else "- none")
        )

        copilot_command = ["gh", "copilot", "--"]
        if ai_model:
            copilot_command.extend(["--model", ai_model])
        copilot_command.extend(["-p", filled_prompt, "--silent"])

        gh_token = (
            os.environ.get("COPILOT_GITHUB_TOKEN", "").strip()
            or os.environ.get("GH_TOKEN", "").strip()
            or os.environ.get("GITHUB_TOKEN", "").strip()
        )
        copilot_env = dict(os.environ)
        if gh_token:
            copilot_env["COPILOT_GITHUB_TOKEN"] = gh_token
            copilot_env["GH_TOKEN"] = gh_token
            copilot_env["GITHUB_TOKEN"] = gh_token

        result = subprocess.run(
            copilot_command,
            capture_output=True,
            text=True,
            check=False,
            timeout=90,
            env=copilot_env,
        )

        if result.returncode != 0:
            reason = (result.stderr or result.stdout or "unknown error").strip()
            raise RuntimeError(f"gh copilot failed: {reason}")

        content = (result.stdout or "").strip()
        if not content:
            raise RuntimeError("gh copilot returned empty output")
        return content

    if ai_enabled:
        try:
            ai_notes = generate_ai_release_notes()
            custom_notes = f"## AI Release Notes\n\n{ai_notes}\n\n---\n\n{custom_notes}"
            print("✅ AI-generated release notes enabled (gh copilot)")
        except (RuntimeError, TimeoutError, FileNotFoundError) as err:
            print(
                f"⚠️ AI release notes generation failed, falling back to commit summary: {err}"
            )
    else:
        print("ℹ️ AI release notes disabled, using commit summary")

    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", delete=False
    ) as notes_file:
        notes_file.write(custom_notes + "\n")
        notes_path = notes_file.name

    run(
        [
            "gh",
            "release",
            "create",
            current_tag,
            "--title",
            f"Release v{version}",
            "--generate-notes",
            "--notes-file",
            notes_path,
            "--verify-tag",
        ]
    )

    Path(notes_path).unlink(missing_ok=True)


def cmd_build_summary() -> None:
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
    parser = argparse.ArgumentParser(description="Reusable npm publish workflow helper")
    parser.add_argument(
        "command",
        choices=[
            "validate-package-name",
            "check-changes",
            "remove-legacy-npm-config",
            "analyze-commits",
            "configure-git",
            "bump-version",
            "create-release",
            "build-summary",
        ],
    )
    args = parser.parse_args()

    command_handlers = {
        "validate-package-name": cmd_validate_package_name,
        "check-changes": cmd_check_changes,
        "remove-legacy-npm-config": cmd_remove_legacy_npm_config,
        "analyze-commits": cmd_analyze_commits,
        "configure-git": cmd_configure_git,
        "bump-version": cmd_bump_version,
        "create-release": cmd_create_release,
        "build-summary": cmd_build_summary,
    }
    command_handlers[args.command]()


if __name__ == "__main__":
    main()
