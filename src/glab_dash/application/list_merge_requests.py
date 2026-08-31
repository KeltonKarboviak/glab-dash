"""Use case: list a section's merge requests via a gateway protocol."""

from typing import Protocol

import structlog

from glab_dash.domain.config import Scope, Section
from glab_dash.domain.merge_request import (
    MergeRequest,
    MergeRequestDetail,
    filter_by_assignee,
    filter_by_author,
    filter_by_labels,
    filter_by_state,
)


class MergeRequestGateway(Protocol):
    def list_project_merge_requests(self, project: str) -> list[MergeRequest]: ...
    def list_group_merge_requests(self, group: str) -> list[MergeRequest]: ...
    def list_global_merge_requests(self) -> list[MergeRequest]: ...
    def get_merge_request_detail(self, project: str, iid: int) -> MergeRequestDetail: ...


log = structlog.get_logger(__name__)


def _list_by_scope(gateway: MergeRequestGateway, section: Section) -> list[MergeRequest]:
    match section.scope:
        case Scope.PROJECT:
            return gateway.list_project_merge_requests(section.project)
        case Scope.GROUP:
            return gateway.list_group_merge_requests(section.group)
        case Scope.GLOBAL:
            return gateway.list_global_merge_requests()


def list_merge_requests_for_section(
    gateway: MergeRequestGateway, section: Section, current_username: str | None = None
) -> list[MergeRequest]:
    """Return `section`'s merge requests, filtered by its configured criteria."""
    log.info("listing merge requests", section=section.title, scope=section.scope)
    # ponytail: fetches every MR in scope before filtering; push filters into
    # the gateway list calls if global-scope pagination gets slow.
    merge_requests = _list_by_scope(gateway, section)
    merge_requests = filter_by_state(merge_requests, section.state)
    merge_requests = filter_by_author(merge_requests, section.author, current_username)
    merge_requests = filter_by_assignee(merge_requests, section.assignee, current_username)
    return filter_by_labels(merge_requests, section.labels)
