"""Use case: list a section's merge requests via a gateway protocol."""

from typing import Protocol

from glab_dash.domain.config import Scope, Section
from glab_dash.domain.merge_request import MergeRequest, filter_by_state


class MergeRequestGateway(Protocol):
    def list_project_merge_requests(self, project: str) -> list[MergeRequest]: ...
    def list_group_merge_requests(self, group: str) -> list[MergeRequest]: ...
    def list_global_merge_requests(self) -> list[MergeRequest]: ...


def _list_by_scope(gateway: MergeRequestGateway, section: Section) -> list[MergeRequest]:
    match section.scope:
        case Scope.PROJECT:
            return gateway.list_project_merge_requests(section.project)
        case Scope.GROUP:
            return gateway.list_group_merge_requests(section.group)
        case Scope.GLOBAL:
            return gateway.list_global_merge_requests()


def list_merge_requests_for_section(
    gateway: MergeRequestGateway, section: Section
) -> list[MergeRequest]:
    """Return `section`'s merge requests, filtered by its configured state."""
    # ponytail: fetches every MR in scope before filtering by state; push
    # `state` into the gateway list calls if global-scope pagination gets slow.
    merge_requests = _list_by_scope(gateway, section)
    return filter_by_state(merge_requests, section.state)
