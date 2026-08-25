"""Domain entity for a GitLab merge request: no I/O, no validation library."""

from dataclasses import dataclass, field

from glab_dash.domain.config import MergeRequestState


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
    labels: list[str] = field(default_factory=list)


def filter_by_state(
    merge_requests: list[MergeRequest], state: MergeRequestState
) -> list[MergeRequest]:
    """Return only merge requests matching `state`, or all of them for ALL."""
    if state is MergeRequestState.ALL:
        return list(merge_requests)
    return [mr for mr in merge_requests if mr.state is state]
