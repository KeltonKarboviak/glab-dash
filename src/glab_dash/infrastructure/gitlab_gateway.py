"""Lists a project's merge requests from GitLab via python-gitlab."""

from concurrent.futures import ThreadPoolExecutor
from typing import Any, NoReturn

import gitlab
from textual.worker import NoActiveWorker, get_current_worker

from glab_dash.domain.config import MergeRequestState
from glab_dash.domain.merge_request import (
    Discussion,
    DiscussionNote,
    MergeRequest,
    MergeRequestDetail,
    SectionNotFoundError,
)

GITLAB_COM_URL = "https://gitlab.com"


def _quit_requested() -> bool:
    """Whether the Textual worker running this fetch has been cancelled (e.g. app quit)."""
    try:
        return get_current_worker().is_cancelled
    except NoActiveWorker:
        return False


def build_gitlab_client(token: str, url: str) -> gitlab.Gitlab:
    return gitlab.Gitlab(url, private_token=token)


def _approvals(raw_mr: Any) -> tuple[int, int]:
    # ponytail: group/global-scoped MRs are GitLab's bare GroupMergeRequest/
    # MergeRequest types, which have no `approvals` manager -- only
    # ProjectMergeRequest does. Skip enrichment rather than crash.
    if not hasattr(raw_mr, "approvals"):
        return 0, 0
    approval = raw_mr.approvals.get()
    return len(approval.approved_by), approval.approvals_required


def _pipeline_status(raw_mr: Any) -> str | None:
    if not hasattr(raw_mr, "pipelines"):
        return None
    pipelines = raw_mr.pipelines.list(get_all=True)
    return pipelines[0].status if pipelines else None


def _line_stats(raw_mr: Any) -> tuple[int, int]:
    if not hasattr(raw_mr, "changes"):
        return 0, 0
    added = removed = 0
    for change in raw_mr.changes().get("changes", []):
        for line in change.get("diff", "").splitlines():
            if line.startswith("+") and not line.startswith("+++"):
                added += 1
            elif line.startswith("-") and not line.startswith("---"):
                removed += 1
    return added, removed


def _to_domain(raw_mr: Any, project: str) -> MergeRequest:
    assignee = getattr(raw_mr, "assignee", None)
    approvals_given, approvals_required = _approvals(raw_mr)
    lines_added, lines_removed = _line_stats(raw_mr)
    return MergeRequest(
        iid=raw_mr.iid,
        project=project,
        title=raw_mr.title,
        author=raw_mr.author["username"],
        assignee=assignee["username"] if assignee else None,
        source_branch=raw_mr.source_branch,
        target_branch=raw_mr.target_branch,
        state=MergeRequestState(raw_mr.state),
        labels=list(raw_mr.labels),
        web_url=raw_mr.web_url,
        updated_at=raw_mr.updated_at,
        approvals_given=approvals_given,
        approvals_required=approvals_required,
        lines_added=lines_added,
        lines_removed=lines_removed,
    )


def _discussions(raw_mr: Any) -> list[Discussion]:
    discussions = []
    for discussion in raw_mr.discussions.list(get_all=True):
        notes = [
            DiscussionNote(author=note["author"]["username"], body=note["body"])
            for note in discussion.attributes["notes"]
        ]
        discussions.append(Discussion(notes=notes))
    return discussions


def _diff_text(raw_mr: Any) -> str:
    sections = []
    for change in raw_mr.changes().get("changes", []):
        sections.append(f"diff --git a/{change['old_path']} b/{change['new_path']}")
        sections.append(change.get("diff", ""))
    return "\n".join(sections)


def _project_from_references(raw_mr: Any) -> str:
    return raw_mr.references["full"].rsplit("!", 1)[0]


_ENRICHMENT_BATCH_SIZE = 8


def _batched(items: list[Any], size: int) -> list[list[Any]]:
    return [items[i : i + size] for i in range(0, len(items), size)]


def _map_all(raw_mrs: Any, project_of: Any = _project_from_references) -> list[MergeRequest]:
    """Map raw MRs to domain entities, enriching `_ENRICHMENT_BATCH_SIZE` at a
    time on a thread pool so the 2 blocking enrichment calls per MR
    (approvals, diff line stats) overlap instead of running one MR fully
    before starting the next.

    Cancellation is only checked *between* batches: threads already started
    for the current batch always finish (there's no cheap way to abort a
    blocking HTTP call mid-flight), but no new batch is started once
    cancelled.
    """
    merge_requests = []
    with ThreadPoolExecutor(max_workers=_ENRICHMENT_BATCH_SIZE) as pool:
        for batch in _batched(list(raw_mrs), _ENRICHMENT_BATCH_SIZE):
            if _quit_requested():
                break
            merge_requests.extend(
                pool.map(lambda raw_mr: _to_domain(raw_mr, project_of(raw_mr)), batch)
            )
    return merge_requests


def _reraise_not_found(kind: str, name: str, error: gitlab.exceptions.GitlabGetError) -> NoReturn:
    if error.response_code == 404:
        raise SectionNotFoundError(f"{kind} '{name}' not found") from error
    raise error


def _server_side_filters(
    state: MergeRequestState,
    author: str | None,
    assignee: str | None,
    labels: list[str],
) -> dict[str, Any]:
    """Query params GitLab's list endpoints accept to filter before enrichment.

    Filtering here instead of after the fetch avoids paying the per-MR
    enrichment cost (approvals/pipelines/discussions/changes) for MRs the
    section doesn't even want -- e.g. a group with 20k total MRs but only 57
    open ones.
    """
    filters: dict[str, Any] = {}
    if state is not MergeRequestState.ALL:
        filters["state"] = state.value
    if author is not None:
        filters["author_username"] = author
    if assignee is not None:
        filters["assignee_username"] = assignee
    if labels:
        filters["labels"] = ",".join(labels)
    return filters


class GitlabMergeRequestGateway:
    def __init__(self, client: gitlab.Gitlab) -> None:
        self._client = client

    def list_project_merge_requests(
        self,
        project: str,
        *,
        state: MergeRequestState = MergeRequestState.ALL,
        author: str | None = None,
        assignee: str | None = None,
        labels: list[str] | None = None,
    ) -> list[MergeRequest]:
        try:
            raw_project = self._client.projects.get(project)
        except gitlab.exceptions.GitlabGetError as e:
            _reraise_not_found("project", project, e)
        filters = _server_side_filters(state, author, assignee, labels or [])
        raw_mrs = raw_project.mergerequests.list(get_all=True, **filters)
        return _map_all(raw_mrs, project_of=lambda _raw_mr: project)

    def list_group_merge_requests(
        self,
        group: str,
        *,
        state: MergeRequestState = MergeRequestState.ALL,
        author: str | None = None,
        assignee: str | None = None,
        labels: list[str] | None = None,
    ) -> list[MergeRequest]:
        try:
            raw_group = self._client.groups.get(group)
        except gitlab.exceptions.GitlabGetError as e:
            _reraise_not_found("group", group, e)
        filters = _server_side_filters(state, author, assignee, labels or [])
        raw_mrs = raw_group.mergerequests.list(get_all=True, **filters)
        return _map_all(raw_mrs)

    def list_global_merge_requests(
        self,
        *,
        state: MergeRequestState = MergeRequestState.ALL,
        author: str | None = None,
        assignee: str | None = None,
        labels: list[str] | None = None,
    ) -> list[MergeRequest]:
        filters = _server_side_filters(state, author, assignee, labels or [])
        raw_mrs = self._client.mergerequests.list(get_all=True, scope="all", **filters)
        return _map_all(raw_mrs)

    def get_merge_request_detail(self, project: str, iid: int) -> MergeRequestDetail:
        raw_mr = self._client.projects.get(project).mergerequests.get(iid)
        return MergeRequestDetail(
            description=raw_mr.description or "",
            discussions=_discussions(raw_mr),
            diff=_diff_text(raw_mr),
            pipeline_status=_pipeline_status(raw_mr),
        )
