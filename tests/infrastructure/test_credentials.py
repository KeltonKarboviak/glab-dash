from pathlib import Path

import pytest
import yaml

from glab_dash.infrastructure.credentials import (
    fetch_env_token,
    fetch_glab_cli_token,
    fetch_own_config_token,
)


def test_fetch_glab_cli_token_reads_top_level_token_key(tmp_path: Path) -> None:
    config_dir = tmp_path / "glab-cli"
    config_dir.mkdir()
    (config_dir / "config.yml").write_text(yaml.dump({"token": "glab-cli-token"}))

    assert fetch_glab_cli_token(env={"GLAB_CONFIG_DIR": str(config_dir)}) == "glab-cli-token"


def test_fetch_glab_cli_token_honors_default_location(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    default_dir = tmp_path / ".config" / "glab-cli"
    default_dir.mkdir(parents=True)
    (default_dir / "config.yml").write_text(yaml.dump({"token": "default-location-token"}))
    monkeypatch.setenv("HOME", str(tmp_path))

    assert fetch_glab_cli_token(env={}) == "default-location-token"


def test_fetch_glab_cli_token_returns_none_when_config_file_missing(tmp_path: Path) -> None:
    assert fetch_glab_cli_token(env={"GLAB_CONFIG_DIR": str(tmp_path)}) is None


def test_fetch_glab_cli_token_returns_none_when_token_key_absent(tmp_path: Path) -> None:
    (tmp_path / "config.yml").write_text(yaml.dump({"host": "gitlab.com"}))

    assert fetch_glab_cli_token(env={"GLAB_CONFIG_DIR": str(tmp_path)}) is None


def test_fetch_env_token_reads_gitlab_token() -> None:
    assert fetch_env_token(env={"GITLAB_TOKEN": "env-token"}) == "env-token"


def test_fetch_env_token_returns_none_when_absent() -> None:
    assert fetch_env_token(env={}) is None


def test_fetch_own_config_token_reads_token_field() -> None:
    assert fetch_own_config_token({"token": "own-config-token"}) == "own-config-token"


def test_fetch_own_config_token_returns_none_when_absent() -> None:
    assert fetch_own_config_token({}) is None
    assert fetch_own_config_token(None) is None
