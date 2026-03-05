"""Unit tests for deploy workflow CLI helpers."""

from __future__ import annotations

from collections.abc import Callable
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys
from typing import cast
from unittest.mock import Mock, patch

DEPLOY_FILE_PATH = Path(__file__).resolve().parents[1] / "deploy.py"
DEPLOY_SPEC = spec_from_file_location("deploy_module", DEPLOY_FILE_PATH)
if DEPLOY_SPEC is None or DEPLOY_SPEC.loader is None:
    raise RuntimeError(f"Could not load deploy module from: {DEPLOY_FILE_PATH}")

deploy_module = module_from_spec(DEPLOY_SPEC)
sys.modules["deploy_module"] = deploy_module
DEPLOY_SPEC.loader.exec_module(deploy_module)

apply_image_tag = cast(Callable[[Path, str], bool], getattr(deploy_module, "apply_image_tag"))
docker_tag_exists = cast(Callable[[str, str], bool], getattr(deploy_module, "docker_tag_exists"))
get_commit_tag = cast(Callable[[str], str], getattr(deploy_module, "get_commit_tag"))
redact_args = cast(Callable[[list[str]], list[str]], getattr(deploy_module, "redact_args"))
validate_environment = cast(Callable[[str], None], getattr(deploy_module, "validate_environment"))


def assert_raises(expected_exception: type[Exception], action: Callable[[], None]) -> None:
    try:
        action()
    except expected_exception:
        return

    raise AssertionError(f"Expected exception {expected_exception.__name__} to be raised")


def test_get_commit_tag_uses_short_sha() -> None:
    assert get_commit_tag("abcdef123456") == "abcdef1"


def test_validate_environment_accepts_known_values() -> None:
    validate_environment("dev")
    validate_environment("all")


def test_validate_environment_rejects_unknown_value() -> None:
    assert_raises(ValueError, lambda: validate_environment("qa"))


def test_apply_image_tag_replaces_first_tag_occurrence(tmp_path: Path) -> None:
    yaml_file = tmp_path / "dev.yaml"
    yaml_file.write_text("image:\n  tag: '1234567'\n", encoding="utf-8")

    changed = apply_image_tag(yaml_file, "abcdef1")

    assert changed is True
    assert "tag: 'abcdef1'" in yaml_file.read_text(encoding="utf-8")


@patch("deploy.requests.get")
@patch("deploy.requests.post")
def test_docker_tag_exists_true(post_mock: Mock, get_mock: Mock) -> None:
    post_mock.return_value = Mock(status_code=200)
    post_mock.return_value.json.return_value = {"token": "token"}

    get_response = Mock(status_code=200)
    get_response.raise_for_status = Mock()
    get_mock.return_value = get_response

    with patch.dict(
        "os.environ",
        {"DOCKER_HUB_USERNAME": "u", "DOCKER_HUB_PASSWORD": "p"},
    ):
        assert docker_tag_exists("asma-srv-auth", "abcdef1") is True


def test_redact_args_hides_admin_secret() -> None:
    args = ["hasura", "migrate", "apply", "--admin-secret", "super-secret", "--endpoint", "https://example.com"]
    redacted = redact_args(args)

    assert redacted == ["hasura", "migrate", "apply", "--admin-secret", "***", "--endpoint", "https://example.com"]


def test_redact_args_no_secret_unchanged() -> None:
    args = ["hasura", "metadata", "reload", "--endpoint", "https://example.com"]
    redacted = redact_args(args)

    assert redacted == args
