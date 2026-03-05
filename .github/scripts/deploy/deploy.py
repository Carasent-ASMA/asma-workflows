#!/usr/bin/env python3

"""Deployment workflow helper commands for reusable GitHub Actions jobs."""

from __future__ import annotations

import argparse
import base64
import hashlib
import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

import requests

VALID_ENVIRONMENTS: tuple[str, ...] = (
    "dev",
    "test",
    "stage",
    "prod",
    "prod-adcuris",
)
ALL_ENVIRONMENTS_VALUE = "all"
DOCKER_NAMESPACE = "asmacarma"


@dataclass(frozen=True)
class CommandContext:
    """Holds common environment-derived values for commands."""

    commit_sha: str
    service_name: str
    workspace_dir: Path


def run(cmd: list[str], check: bool = True, capture_output: bool = False) -> subprocess.CompletedProcess[str]:
    """Run a command and print it for traceability."""

    print("+", " ".join(cmd))
    return subprocess.run(
        cmd,
        check=check,
        text=True,
        capture_output=capture_output,
    )


def write_output(key: str, value: str) -> None:
    """Write an output value to the GitHub Actions output file when available."""

    output_path = os.getenv("GITHUB_OUTPUT")
    if not output_path:
        return
    with Path(output_path).open("a", encoding="utf-8") as file_handle:
        file_handle.write(f"{key}={value}\n")


def get_required_env(name: str) -> str:
    """Return a required environment variable or fail with a clear error."""

    value = os.getenv(name, "").strip()
    if not value:
        raise ValueError(f"Missing required environment variable: {name}")
    return value


def get_commit_tag(commit_sha: str) -> str:
    """Return a short image tag derived from commit SHA."""

    return commit_sha[:7]


def make_context(service_name: str | None) -> CommandContext:
    """Create command context from environment and optional overrides."""

    commit_sha = get_required_env("COMMIT_SHA")
    default_service_name = os.getenv("SERVICE_NAME", "").strip()
    selected_service_name = (service_name or default_service_name).strip()
    if not selected_service_name:
        raise ValueError("SERVICE_NAME is required (or pass --service-name)")

    workspace_value = os.getenv("WORKSPACE_DIR") or os.getenv("GITHUB_WORKSPACE") or str(Path.cwd())
    workspace_dir = Path(workspace_value).resolve()
    return CommandContext(commit_sha=commit_sha, service_name=selected_service_name, workspace_dir=workspace_dir)


def docker_tag_exists(service_name: str, tag: str) -> bool:
    """Return whether the docker image tag already exists in Docker Hub."""

    username = get_required_env("DOCKER_HUB_USERNAME")
    password = get_required_env("DOCKER_HUB_PASSWORD")

    login_response = requests.post(
        "https://hub.docker.com/v2/users/login/",
        json={"username": username, "password": password},
        timeout=20,
    )
    login_response.raise_for_status()
    token = login_response.json().get("token")
    if not token:
        raise ValueError("Docker Hub login did not return a token")

    tags_response = requests.get(
        f"https://hub.docker.com/v2/namespaces/{DOCKER_NAMESPACE}/repositories/{service_name}/tags/{tag}",
        headers={"Authorization": f"Bearer {token}"},
        timeout=20,
    )

    if tags_response.status_code == 404:
        return False
    tags_response.raise_for_status()
    return True


def ensure_dockerfile_exists(dockerfile_path: Path, dockerfile_name: str) -> Path:
    """Validate dockerfile path and return the Dockerfile file path."""

    dockerfile = dockerfile_path / dockerfile_name
    if not dockerfile.exists():
        raise FileNotFoundError(f"Missing Dockerfile: {dockerfile}")
    return dockerfile


def build_and_push_image(service_name: str, tag: str, dockerfile_path: Path, dockerfile_name: str = "Dockerfile") -> None:
    """Build and push a Docker image with commit and latest tags."""

    dockerfile = ensure_dockerfile_exists(dockerfile_path, dockerfile_name)
    image_ref = f"{DOCKER_NAMESPACE}/{service_name}:{tag}"
    latest_ref = f"{DOCKER_NAMESPACE}/{service_name}:latest"

    run([
        "docker",
        "build",
        "-f",
        str(dockerfile),
        "-t",
        image_ref,
        "-t",
        latest_ref,
        str(dockerfile_path),
    ])
    run(["docker", "push", image_ref])
    run(["docker", "push", latest_ref])


def file_md5(path: Path) -> str:
    """Compute MD5 hash for a file content."""

    digest = hashlib.md5()
    with path.open("rb") as file_handle:
        for chunk in iter(lambda: file_handle.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()


def gh_release_exists(tag: str) -> bool:
    """Check if a GitHub release with tag exists."""

    result = run(["gh", "release", "view", tag], check=False, capture_output=True)
    return result.returncode == 0


def ensure_ci_artifacts_release() -> None:
    """Ensure a `ci-artifacts` release exists for artifact storage."""

    if gh_release_exists("ci-artifacts"):
        return
    run(["gh", "release", "create", "ci-artifacts", "--title", "ci-artifacts", "--notes", "CI artifacts storage"]) 


def gh_download_asset(release_tag: str, pattern: str, destination: Path) -> bool:
    """Download an asset pattern from a release and return success."""

    destination.mkdir(parents=True, exist_ok=True)
    result = run(
        [
            "gh",
            "release",
            "download",
            release_tag,
            "--pattern",
            pattern,
            "--dir",
            str(destination),
        ],
        check=False,
        capture_output=True,
    )
    return result.returncode == 0


def cmd_build_and_push_docker(args: argparse.Namespace) -> None:
    """Handle standard Docker build and push flow."""

    context = make_context(args.service_name)
    tag = get_commit_tag(context.commit_sha)
    dockerfile_path = Path(args.dockerfile_path or context.workspace_dir).resolve()

    if docker_tag_exists(context.service_name, tag):
        print(f"Image tag already exists: {DOCKER_NAMESPACE}/{context.service_name}:{tag}")
        write_output("skip_build", "true")
        write_output("image_tag", tag)
        return

    build_and_push_image(context.service_name, tag, dockerfile_path)
    write_output("skip_build", "false")
    write_output("image_tag", tag)


def cmd_build_and_push_docker_php(args: argparse.Namespace) -> None:
    """Handle PHP Docker build with optional base image rebuild."""

    context = make_context(args.service_name)
    tag = get_commit_tag(context.commit_sha)
    workspace = context.workspace_dir

    if docker_tag_exists(context.service_name, tag):
        print(f"Image tag already exists: {DOCKER_NAMESPACE}/{context.service_name}:{tag}")
        write_output("skip_build", "true")
        write_output("image_tag", tag)
        return

    composer_file = workspace / "composer.lock"
    base_file = workspace / "Dockerfile.k8s.base"
    dockerfile_k8s = workspace / "Dockerfile.k8s"
    for path in (composer_file, base_file, dockerfile_k8s):
        if not path.exists():
            raise FileNotFoundError(f"Required file missing: {path}")

    ensure_ci_artifacts_release()
    artifact_dir = workspace / "artifact"
    artifact_dir.mkdir(parents=True, exist_ok=True)

    downloaded_composer = gh_download_asset("ci-artifacts", f"{context.service_name}-composer.lock", artifact_dir)
    downloaded_base = gh_download_asset("ci-artifacts", f"{context.service_name}-Dockerfile.k8s.base", artifact_dir)

    rebuild_base = True
    if downloaded_composer and downloaded_base:
        artifact_composer = artifact_dir / f"{context.service_name}-composer.lock"
        artifact_base = artifact_dir / f"{context.service_name}-Dockerfile.k8s.base"
        rebuild_base = file_md5(composer_file) != file_md5(artifact_composer) or file_md5(base_file) != file_md5(artifact_base)

    if rebuild_base:
        base_ref = f"{DOCKER_NAMESPACE}/{context.service_name}-base:latest"
        run([
            "docker",
            "build",
            "-f",
            str(base_file),
            "-t",
            base_ref,
            str(workspace),
        ])
        run(["docker", "push", base_ref])

    build_and_push_image(context.service_name, tag, workspace, dockerfile_name="Dockerfile.k8s")

    composer_asset = artifact_dir / f"{context.service_name}-composer.lock"
    base_asset = artifact_dir / f"{context.service_name}-Dockerfile.k8s.base"
    shutil.copyfile(composer_file, composer_asset)
    shutil.copyfile(base_file, base_asset)
    run(["gh", "release", "upload", "ci-artifacts", str(composer_asset), str(base_asset), "--clobber"])

    write_output("skip_build", "false")
    write_output("image_tag", tag)


def validate_environment(environment: str) -> None:
    """Validate deployment environment input value."""

    if environment not in VALID_ENVIRONMENTS and environment != ALL_ENVIRONMENTS_VALUE:
        values = ", ".join((*VALID_ENVIRONMENTS, ALL_ENVIRONMENTS_VALUE))
        raise ValueError(f"Invalid environment '{environment}'. Allowed values: {values}")


def apply_image_tag(yaml_path: Path, image_tag: str) -> bool:
    """Update image tag in an env YAML file and return whether it changed."""

    content = yaml_path.read_text(encoding="utf-8")
    replacement_pattern = re.compile(r"(tag:\s*')([^']*)(')")
    if not replacement_pattern.search(content):
        raise ValueError(f"Could not find tag field in {yaml_path}")

    new_content = replacement_pattern.sub(rf"\g<1>{image_tag}\g<3>", content, count=1)
    if new_content == content:
        return False

    yaml_path.write_text(new_content, encoding="utf-8")
    return True


def prepare_argocd_repo(workspace_dir: Path) -> Path:
    """Clone and prepare the ArgoCD repository with dual remotes."""

    origin_url = os.getenv("ARGOCD_REPO_URL_ORIGIN", "git@github.com:Carasent-ASMA/asma-argocd.git")
    bitbucket_url = os.getenv("ARGOCD_REPO_URL_BITBUCKET", "git@bitbucket.org:carasent/asma-argocd.git")
    branch_name = os.getenv("ARGOCD_TARGET_BRANCH", "master")

    repo_dir = workspace_dir / "asma-argocd"
    if repo_dir.exists():
        shutil.rmtree(repo_dir)

    run(["git", "clone", "--branch", branch_name, origin_url, str(repo_dir)])
    run(["git", "-C", str(repo_dir), "remote", "remove", "bitbucket"], check=False)
    run(["git", "-C", str(repo_dir), "remote", "add", "bitbucket", bitbucket_url])

    run(["git", "-C", str(repo_dir), "fetch", "origin", branch_name])
    run(["git", "-C", str(repo_dir), "fetch", "bitbucket", branch_name])

    origin_head = run(["git", "-C", str(repo_dir), "rev-parse", f"origin/{branch_name}"], capture_output=True).stdout.strip()
    bitbucket_head = run(["git", "-C", str(repo_dir), "rev-parse", f"bitbucket/{branch_name}"], capture_output=True).stdout.strip()

    if origin_head != bitbucket_head:
        raise RuntimeError(
            "ArgoCD remotes diverged. Sync origin and bitbucket to same HEAD before editing files."
        )

    run(["git", "-C", str(repo_dir), "checkout", branch_name])
    run(["git", "-C", str(repo_dir), "config", "user.email", "github-actions[bot]@users.noreply.github.com"])
    run(["git", "-C", str(repo_dir), "config", "user.name", "github-actions[bot]"])
    return repo_dir


def create_or_replace_env_tag(environment: str, commit_sha: str) -> None:
    """Create or replace environment deployment tag in service repository."""

    tag_name = f"env.{environment}"
    remote_name = "origin"
    git_ssh_origin = os.getenv("GIT_SSH_ORIGIN", "").strip()
    if git_ssh_origin:
        run(["git", "remote", "set-url", remote_name, git_ssh_origin])

    run(["git", "tag", "-d", tag_name], check=False)
    run(["git", "push", remote_name, "--delete", tag_name], check=False)
    run(["git", "tag", tag_name, commit_sha])
    run(["git", "push", remote_name, tag_name])


def cmd_app_version_update(args: argparse.Namespace) -> None:
    """Update ArgoCD app image tags and push to both remotes."""

    validate_environment(args.environment)
    context = make_context(args.service_name)
    image_tag = get_commit_tag(context.commit_sha)

    argocd_repo = prepare_argocd_repo(context.workspace_dir)
    target_envs = VALID_ENVIRONMENTS if args.environment == ALL_ENVIRONMENTS_VALUE else (args.environment,)

    changed_files: list[Path] = []
    for target_env in target_envs:
        yaml_path = argocd_repo / "applications" / context.service_name / f"{target_env}.yaml"
        if not yaml_path.exists():
            raise FileNotFoundError(f"Missing environment file: {yaml_path}")
        if apply_image_tag(yaml_path, image_tag):
            changed_files.append(yaml_path)

    if not changed_files:
        print("No ArgoCD changes needed; skipping commit/push.")
        return

    run(["git", "-C", str(argocd_repo), "add", "."])
    commit_env = args.environment
    run(
        [
            "git",
            "-C",
            str(argocd_repo),
            "commit",
            "-m",
            f"{context.service_name}.{commit_env}.version: {image_tag}.",
        ]
    )

    branch_name = os.getenv("ARGOCD_TARGET_BRANCH", "master")
    run(["git", "-C", str(argocd_repo), "push", "origin", f"HEAD:{branch_name}"])
    run(["git", "-C", str(argocd_repo), "push", "bitbucket", f"HEAD:{branch_name}"])

    if args.create_tag:
        create_or_replace_env_tag(args.environment, context.commit_sha)


def kubeconfig_path_for_environment(environment: str, workspace_dir: Path) -> Path:
    """Build kubeconfig output path for selected environment."""

    if environment in ("prod", "prod-adcuris"):
        return workspace_dir / "kubeconfig_prod.yml"
    return workspace_dir / "kubeconfig_nonprod.yml"


def write_kubeconfig(environment: str, workspace_dir: Path) -> Path:
    """Decode kubeconfig secret for selected environment and persist it to disk."""

    if environment in ("prod", "prod-adcuris"):
        encoded = get_required_env("KUBE_CONFIG_PROD")
    else:
        encoded = get_required_env("KUBE_CONFIG_NONPROD")

    output_path = kubeconfig_path_for_environment(environment, workspace_dir)
    output_path.write_bytes(base64.b64decode(encoded))
    return output_path


def get_kubectl_value(args: list[str], kubeconfig: Path) -> str:
    """Execute kubectl jsonpath query and return trimmed string output."""

    env = os.environ.copy()
    env["KUBECONFIG"] = str(kubeconfig)
    result = subprocess.run(args, check=True, text=True, capture_output=True, env=env)
    return result.stdout.strip()


def redact_args(arguments: list[str], redact_keys: tuple[str, ...] = ("--admin-secret",)) -> list[str]:
    """Return a copy of argument list with values after redact_keys replaced by '***'."""

    result: list[str] = []
    skip_next = False
    for arg in arguments:
        if skip_next:
            result.append("***")
            skip_next = False
        elif arg in redact_keys:
            result.append(arg)
            skip_next = True
        else:
            result.append(arg)
    return result


def run_hasura_command(arguments: list[str], kubeconfig: Path, admin_secret: str | None = None) -> None:
    """Run a hasura command with selected kubeconfig environment."""

    env = os.environ.copy()
    env["KUBECONFIG"] = str(kubeconfig)
    if admin_secret:
        env["HASURA_GRAPHQL_ADMIN_SECRET"] = admin_secret
    print("+", " ".join(redact_args(arguments)))
    subprocess.run(arguments, check=True, env=env)


def cmd_hasura_migration(args: argparse.Namespace) -> None:
    """Run Hasura migration flow against environment endpoint."""

    validate_environment(args.environment)
    if args.environment == ALL_ENVIRONMENTS_VALUE:
        raise ValueError("Hasura migration does not support environment='all'")

    context = make_context(args.service_name)
    kubeconfig = write_kubeconfig(args.environment, context.workspace_dir)

    admin_secret = get_required_env("HASURA_ADMIN_SECRET")
    # Mask the secret in GitHub Actions logs so it is never printed
    print(f"::add-mask::{admin_secret}")

    endpoint = get_kubectl_value(
        [
            "kubectl",
            "-n",
            args.environment,
            "get",
            "ingress",
            context.service_name,
            "-o",
            "jsonpath={.spec.rules[0].host}{.spec.rules[0].http.paths[0].path}",
        ],
        kubeconfig,
    )
    endpoint = re.sub(r"\(.*\)", "", endpoint)

    hasura_endpoint = f"https://{endpoint}"
    run_hasura_command(
        [
            "hasura",
            "migrate",
            "apply",
            "--admin-secret",
            admin_secret,
            "--endpoint",
            hasura_endpoint,
            "--database-name",
            "default",
            "--insecure-skip-tls-verify",
            "true",
        ],
        kubeconfig,
        admin_secret=admin_secret,
    )
    run_hasura_command(
        [
            "hasura",
            "metadata",
            "apply",
            "--admin-secret",
            admin_secret,
            "--endpoint",
            hasura_endpoint,
            "--insecure-skip-tls-verify",
            "true",
        ],
        kubeconfig,
        admin_secret=admin_secret,
    )
    run_hasura_command(
        [
            "hasura",
            "metadata",
            "reload",
            "--admin-secret",
            admin_secret,
            "--endpoint",
            hasura_endpoint,
            "--insecure-skip-tls-verify",
            "true",
        ],
        kubeconfig,
        admin_secret=admin_secret,
    )

    if args.create_tag:
        create_or_replace_env_tag(args.environment, context.commit_sha)


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser for deploy commands."""

    parser = argparse.ArgumentParser(description="Deploy helper for reusable workflows")
    subparsers = parser.add_subparsers(dest="command", required=True)

    parser_build = subparsers.add_parser("build-and-push-docker")
    parser_build.add_argument("--service-name", required=False)
    parser_build.add_argument("--dockerfile-path", required=False)
    parser_build.set_defaults(handler=cmd_build_and_push_docker)

    parser_php = subparsers.add_parser("build-and-push-docker-php")
    parser_php.add_argument("--service-name", required=False)
    parser_php.set_defaults(handler=cmd_build_and_push_docker_php)

    parser_app = subparsers.add_parser("app-version-update")
    parser_app.add_argument("--environment", required=True)
    parser_app.add_argument("--service-name", required=False)
    parser_app.add_argument("--create-tag", action="store_true", default=False)
    parser_app.add_argument("--no-create-tag", dest="create_tag", action="store_false")
    parser_app.set_defaults(handler=cmd_app_version_update)

    parser_hasura = subparsers.add_parser("hasura-migration")
    parser_hasura.add_argument("--environment", required=True)
    parser_hasura.add_argument("--service-name", required=False)
    parser_hasura.add_argument("--create-tag", action="store_true", default=False)
    parser_hasura.add_argument("--no-create-tag", dest="create_tag", action="store_false")
    parser_hasura.set_defaults(handler=cmd_hasura_migration)

    return parser


def main() -> None:
    """CLI program entrypoint."""

    parser = build_parser()
    args = parser.parse_args()

    if shutil.which("docker") is None and args.command in {"build-and-push-docker", "build-and-push-docker-php"}:
        raise RuntimeError("docker binary not found in PATH")

    args.handler(args)


if __name__ == "__main__":
    main()
