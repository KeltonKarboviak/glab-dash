"""Lists a project's merge requests from GitLab via python-gitlab."""

from typing import Any

import gitlab

from glab_dash.domain.config import MergeRequestState
from glab_dash.domain.merge_request import MergeRequest

GITLAB_COM_URL = "https://gitlab.com"


def build_gitlab_client(token: str, url: str) -> gitlab.Gitlab:
    return gitlab.Gitlab(url, private_token=token)


def _to_domain(raw_mr: Any, project: str) -> MergeRequest:
    return MergeRequest(
        iid=raw_mr.iid,
        project=project,
        title=raw_mr.title,
        author=raw_mr.author["username"],
        source_branch=raw_mr.source_branch,
        target_branch=raw_mr.target_branch,
        state=MergeRequestState(raw_mr.state),
        labels=list(raw_mr.labels),
        web_url=raw_mr.web_url,
        updated_at=raw_mr.updated_at,
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
