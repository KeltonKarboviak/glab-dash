"""Use case: list a section's merge requests via a gateway protocol."""

from typing import Protocol

import structlog

from glab_dash.domain.config import MergeRequestState, Scope, Section
from glab_dash.domain.merge_request import (
    MergeRequest,
    MergeRequestDetail,
    filter_by_assignee,
    filter_by_author,
    filter_by_labels,
    filter_by_state,
    resolve_username,
)


class MergeRequestGateway(Protocol):
    def list_project_merge_requests(
        self,
        project: str,
        *,
        state: MergeRequestState = MergeRequestState.ALL,
        author: str | None = None,
        assignee: str | None = None,
        labels: list[str] | None = None,
    ) -> list[MergeRequest]: ...
    def list_group_merge_requests(
        self,
        group: str,
        *,
        state: MergeRequestState = MergeRequestState.ALL,
        author: str | None = None,
        assignee: str | None = None,
        labels: list[str] | None = None,
    ) -> list[MergeRequest]: ...
    def list_global_merge_requests(
        self,
        *,
        state: MergeRequestState = MergeRequestState.ALL,
        author: str | None = None,
        assignee: str | None = None,
        labels: list[str] | None = None,
    ) -> list[MergeRequest]: ...
    def get_merge_request_detail(self, project: str, iid: int) -> MergeRequestDetail: ...


log = structlog.get_logger(__name__)


def _list_by_scope(
    gateway: MergeRequestGateway,
    section: Section,
    author: str | None,
    assignee: str | None,
) -> list[MergeRequest]:
    match section.scope:
        case Scope.PROJECT:
            assert section.project is not None, "PROJECT scope requires section.project"
            return gateway.list_project_merge_requests(
                section.project,
                state=section.state,
                author=author,
                assignee=assignee,
                labels=section.labels,
            )
        case Scope.GROUP:
            assert section.group is not None, "GROUP scope requires section.group"
            return gateway.list_group_merge_requests(
                section.group,
                state=section.state,
                author=author,
                assignee=assignee,
                labels=section.labels,
            )
        case Scope.GLOBAL:
            return gateway.list_global_merge_requests(
                state=section.state, author=author, assignee=assignee, labels=section.labels
            )


def list_merge_requests_for_section(
    gateway: MergeRequestGateway, section: Section, current_username: str | None = None
) -> list[MergeRequest]:
    """Return `section`'s merge requests, filtered by its configured criteria.

    Filters are pushed into the gateway list call as GitLab API query params
    (see `_server_side_filters` in the gateway) so a section only pays the
    per-MR enrichment cost for MRs it actually wants -- a group can have tens
    of thousands of historical MRs but only a handful open. The filter
    functions below are re-applied client-side as a safety net (e.g. "@me"
    resolution, and in case a param is ever dropped), which is cheap once the
    server has already narrowed the result set down.
    """
    log.info("listing merge requests", section=section.title, scope=section.scope)
    author = resolve_username(section.author, current_username)
    assignee = resolve_username(section.assignee, current_username)
    merge_requests = _list_by_scope(gateway, section, author, assignee)
    merge_requests = filter_by_state(merge_requests, section.state)
    merge_requests = filter_by_author(merge_requests, section.author, current_username)
    merge_requests = filter_by_assignee(merge_requests, section.assignee, current_username)
    return filter_by_labels(merge_requests, section.labels)
