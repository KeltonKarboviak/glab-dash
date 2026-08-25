"""Use case: list a section's merge requests via a gateway protocol."""

from typing import Protocol

from glab_dash.domain.config import Section
from glab_dash.domain.merge_request import MergeRequest, filter_by_state


class MergeRequestGateway(Protocol):
    def list_project_merge_requests(self, project: str) -> list[MergeRequest]: ...


def list_merge_requests_for_section(
    gateway: MergeRequestGateway, section: Section
) -> list[MergeRequest]:
    """Return `section`'s merge requests, filtered by its configured state."""
    merge_requests = gateway.list_project_merge_requests(section.project)
    return filter_by_state(merge_requests, section.state)
