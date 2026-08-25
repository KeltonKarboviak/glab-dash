"""Loads and validates glab-dash's YAML config into Domain entities."""

import os
from collections.abc import Mapping
from pathlib import Path

import yaml
from pydantic import BaseModel, Field, ValidationError, model_validator

from glab_dash.domain.config import (
    Config,
    ConfigError,
    MergeRequestState,
    Scope,
    Section,
)

REPO_LOCAL_CONFIG_NAME = ".glab-dash.yml"


class SectionModel(BaseModel):
    title: str
    scope: Scope
    project: str | None = None
    group: str | None = None
    state: MergeRequestState = MergeRequestState.OPENED
    author: str | None = None
    assignee: str | None = None
    labels: list[str] = []

    @model_validator(mode="after")
    def check_scope_target(self) -> SectionModel:
        if self.scope is Scope.PROJECT and not self.project:
            raise ValueError('scope: project requires a "project" key')
        if self.scope is Scope.GROUP and not self.group:
            raise ValueError('scope: group requires a "group" key')
        return self

    def to_domain(self) -> Section:
        return Section(
            title=self.title,
            scope=self.scope,
            project=self.project,
            group=self.group,
            state=self.state,
            author=self.author,
            assignee=self.assignee,
            labels=self.labels,
        )


class ConfigModel(BaseModel):
    sections: list[SectionModel] = Field(min_length=1)
    refresh_interval: int = 60
    token: str | None = None

    def to_domain(self) -> Config:
        return Config(
            sections=[section.to_domain() for section in self.sections],
            refresh_interval=self.refresh_interval,
            token=self.token,
        )


def resolve_config_path(env: Mapping[str, str] = os.environ) -> Path:
    """Resolve the config path: repo-local `.glab-dash.yml`, else the XDG path."""
    repo_local = Path.cwd() / REPO_LOCAL_CONFIG_NAME
    if repo_local.is_file():
        return repo_local

    xdg_config_home = env.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(xdg_config_home) / "glab-dash" / "config.yml"


def load_config(path: Path) -> Config:
    """Load and validate the YAML config at `path` into a Domain `Config`."""
    if not path.is_file():
        raise ConfigError(f"No config file found at {path}")

    raw = yaml.safe_load(path.read_text()) or {}
    try:
        return ConfigModel.model_validate(raw).to_domain()
    except ValidationError as error:
        raise ConfigError(f"Invalid config at {path}: {error}") from error
