"""Lists a project's merge requests from GitLab via python-gitlab."""

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


def _unresolved_discussion_count(raw_mr: Any) -> int:
    # ponytail: group/global-scoped MRs are GitLab's bare GroupMergeRequest/
    # MergeRequest types, which have no `discussions` manager -- only
    # ProjectMergeRequest does. Skip enrichment rather than crash.
    if not hasattr(raw_mr, "discussions"):
        return 0
    return sum(1 for discussion in raw_mr.discussions.list(get_all=True) if not discussion.resolved)


def _approvals(raw_mr: Any) -> tuple[int, int]:
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
        unresolved_discussion_count=_unresolved_discussion_count(raw_mr),
        approvals_given=approvals_given,
        approvals_required=approvals_required,
        pipeline_status=_pipeline_status(raw_mr),
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


def _map_all(raw_mrs: Any, project_of: Any = _project_from_references) -> list[MergeRequest]:
    """Map raw MRs to domain entities, stopping early if the fetch is cancelled.

    `project_of` derives each MR's project; defaults to reading it off the MR
    itself for scopes (group/global) that don't already know it.
    """
    merge_requests = []
    for raw_mr in raw_mrs:
        if _quit_requested():
            break
        merge_requests.append(_to_domain(raw_mr, project_of(raw_mr)))
    return merge_requests


def _reraise_not_found(kind: str, name: str, error: gitlab.exceptions.GitlabGetError) -> NoReturn:
    if error.response_code == 404:
        raise SectionNotFoundError(f"{kind} '{name}' not found") from error
    raise error


class GitlabMergeRequestGateway:
    def __init__(self, client: gitlab.Gitlab) -> None:
        self._client = client

    def list_project_merge_requests(self, project: str) -> list[MergeRequest]:
        try:
            raw_project = self._client.projects.get(project)
        except gitlab.exceptions.GitlabGetError as e:
            _reraise_not_found("project", project, e)
        raw_mrs = raw_project.mergerequests.list(get_all=True)
        return _map_all(raw_mrs, project_of=lambda _raw_mr: project)

    def list_group_merge_requests(self, group: str) -> list[MergeRequest]:
        try:
            raw_group = self._client.groups.get(group)
        except gitlab.exceptions.GitlabGetError as e:
            _reraise_not_found("group", group, e)
        raw_mrs = raw_group.mergerequests.list(get_all=True)
        return _map_all(raw_mrs)

    def list_global_merge_requests(self) -> list[MergeRequest]:
        raw_mrs = self._client.mergerequests.list(get_all=True, scope="all")
        return _map_all(raw_mrs)

    def get_merge_request_detail(self, project: str, iid: int) -> MergeRequestDetail:
        raw_mr = self._client.projects.get(project).mergerequests.get(iid)
        return MergeRequestDetail(
            description=raw_mr.description or "",
            discussions=_discussions(raw_mr),
            diff=_diff_text(raw_mr),
        )
