"""Domain entity for a GitLab merge request: no I/O, no validation library."""

from dataclasses import dataclass, field

from glab_dash.domain.config import MergeRequestState

AT_ME = "@me"


@dataclass(frozen=True)
class MergeRequest:
    iid: int
    project: str
    title: str
    author: str
    source_branch: str
    target_branch: str
    state: MergeRequestState
    web_url: str
    updated_at: str
    assignee: str | None = None
    labels: list[str] = field(default_factory=list)


def filter_by_state(
    merge_requests: list[MergeRequest], state: MergeRequestState
) -> list[MergeRequest]:
    """Return only merge requests matching `state`, or all of them for ALL."""
    if state is MergeRequestState.ALL:
        return list(merge_requests)
    return [mr for mr in merge_requests if mr.state is state]


def _resolve_username(username: str | None, current_username: str | None) -> str | None:
    if username != AT_ME:
        return username
    if current_username is None:
        raise ValueError('"@me" filter requires a current_username')
    return current_username


def filter_by_author(
    merge_requests: list[MergeRequest],
    author: str | None,
    current_username: str | None = None,
) -> list[MergeRequest]:
    """Return only merge requests authored by `author` (`"@me"` resolves)."""
    target = _resolve_username(author, current_username)
    if target is None:
        return list(merge_requests)
    return [mr for mr in merge_requests if mr.author == target]


def filter_by_assignee(
    merge_requests: list[MergeRequest],
    assignee: str | None,
    current_username: str | None = None,
) -> list[MergeRequest]:
    """Return only merge requests assigned to `assignee` (`"@me"` resolves)."""
    target = _resolve_username(assignee, current_username)
    if target is None:
        return list(merge_requests)
    return [mr for mr in merge_requests if mr.assignee == target]


def filter_by_labels(
    merge_requests: list[MergeRequest], labels: list[str]
) -> list[MergeRequest]:
    """Return only merge requests carrying every listed label (AND-matched)."""
    if not labels:
        return list(merge_requests)
    required = set(labels)
    return [mr for mr in merge_requests if required.issubset(mr.labels)]
