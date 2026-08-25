"""Domain entities for glab-dash's config: no I/O, no validation library."""

from dataclasses import dataclass, field
from enum import StrEnum


class Scope(StrEnum):
    PROJECT = "project"
    GROUP = "group"
    GLOBAL = "global"


class MergeRequestState(StrEnum):
    OPENED = "opened"
    CLOSED = "closed"
    MERGED = "merged"
    ALL = "all"


class ConfigError(Exception):
    """Raised when a glab-dash config file fails to load or validate."""


@dataclass(frozen=True)
class Section:
    title: str
    scope: Scope
    project: str | None = None
    group: str | None = None
    state: MergeRequestState = MergeRequestState.OPENED
    author: str | None = None
    assignee: str | None = None
    labels: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class Config:
    sections: list[Section]
    refresh_interval: int = 60
    token: str | None = None
