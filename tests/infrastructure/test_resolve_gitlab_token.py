from pathlib import Path

import pytest

from glab_dash.infrastructure.credentials import resolve_gitlab_token


def test_glab_cli_token_wins_when_present(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _write_glab_cli_config(tmp_path, token="glab-cli-token")
    monkeypatch.setenv("GLAB_CONFIG_DIR", str(tmp_path))
    monkeypatch.setenv("GITLAB_TOKEN", "env-token")

    assert resolve_gitlab_token(own_config={"token": "own-config-token"}) == "glab-cli-token"


def test_env_token_wins_when_glab_cli_absent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("GLAB_CONFIG_DIR", str(tmp_path))
    monkeypatch.setenv("GITLAB_TOKEN", "env-token")

    assert resolve_gitlab_token(own_config={"token": "own-config-token"}) == "env-token"


def test_own_config_token_wins_when_others_absent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("GLAB_CONFIG_DIR", str(tmp_path))
    monkeypatch.delenv("GITLAB_TOKEN", raising=False)

    assert resolve_gitlab_token(own_config={"token": "own-config-token"}) == "own-config-token"


def test_returns_none_when_no_source_has_a_token(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("GLAB_CONFIG_DIR", str(tmp_path))
    monkeypatch.delenv("GITLAB_TOKEN", raising=False)

    assert resolve_gitlab_token(own_config=None) is None


def _write_glab_cli_config(config_dir: Path, token: str) -> None:
    import yaml

    (config_dir / "config.yml").write_text(yaml.dump({"token": token}))
