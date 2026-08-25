"""Fetches candidate GitLab token values from their various sources."""

import os
from collections.abc import Mapping
from pathlib import Path

import yaml

from glab_dash.domain.credentials import resolve_token


def fetch_glab_cli_token(env: Mapping[str, str] = os.environ) -> str | None:
    """Read the `token` key from the glab CLI's stored config.yml."""
    config_dir = env.get("GLAB_CONFIG_DIR", str(Path.home() / ".config" / "glab-cli"))
    config_path = Path(config_dir) / "config.yml"
    if not config_path.is_file():
        return None

    config = yaml.safe_load(config_path.read_text()) or {}
    return config.get("token")


def fetch_env_token(env: Mapping[str, str] = os.environ) -> str | None:
    """Read the GITLAB_TOKEN environment variable."""
    return env.get("GITLAB_TOKEN")


def fetch_own_config_token(config: Mapping | None) -> str | None:
    """Read the `token` field from glab-dash's own parsed config."""
    if config is None:
        return None
    return config.get("token")


def resolve_gitlab_token(own_config: Mapping | None) -> str | None:
    """Resolve a GitLab token, trying each source in priority order."""
    return resolve_token(
        [
            fetch_glab_cli_token(),
            fetch_env_token(),
            fetch_own_config_token(own_config),
        ]
    )
