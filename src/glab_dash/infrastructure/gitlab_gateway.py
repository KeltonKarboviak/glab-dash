"""Lists a project's merge requests from GitLab via python-gitlab."""

from typing import Any

import gitlab

from glab_dash.domain.config import MergeRequestState
from glab_dash.domain.merge_request import MergeRequest

GITLAB_COM_URL = "https://gitlab.com"


def build_gitlab_client(token: str, url: str) -> gitlab.Gitlab:
    return gitlab.Gitlab(url, private_token=token)


def _unresolved_discussion_count(raw_mr: Any) -> int:
    return sum(1 for discussion in raw_mr.discussions.list(get_all=True) if not discussion.resolved)


def _approvals(raw_mr: Any) -> tuple[int, int]:
    approval = raw_mr.approvals.get()
    return len(approval.approved_by), approval.approvals_required


def _pipeline_status(raw_mr: Any) -> str | None:
    pipelines = raw_mr.pipelines.list(get_all=True)
    return pipelines[0].status if pipelines else None


def _line_stats(raw_mr: Any) -> tuple[int, int]:
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


def _project_from_references(raw_mr: Any) -> str:
    return raw_mr.references["full"].rsplit("!", 1)[0]


def _map_all(raw_mrs: Any) -> list[MergeRequest]:
    """Map raw MRs whose project isn't already known, deriving it per-MR."""
    return [_to_domain(raw_mr, _project_from_references(raw_mr)) for raw_mr in raw_mrs]


class GitlabMergeRequestGateway:
    def __init__(self, client: gitlab.Gitlab) -> None:
        self._client = client

    def list_project_merge_requests(self, project: str) -> list[MergeRequest]:
        raw_mrs = self._client.projects.get(project).mergerequests.list(get_all=True)
        return [_to_domain(raw_mr, project) for raw_mr in raw_mrs]

    def list_group_merge_requests(self, group: str) -> list[MergeRequest]:
        raw_mrs = self._client.groups.get(group).mergerequests.list(get_all=True)
        return _map_all(raw_mrs)

    def list_global_merge_requests(self) -> list[MergeRequest]:
        raw_mrs = self._client.mergerequests.list(get_all=True, scope="all")
        return _map_all(raw_mrs)
