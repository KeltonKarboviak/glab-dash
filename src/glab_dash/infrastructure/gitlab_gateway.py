"""Lists a project's merge requests from GitLab via python-gitlab."""

from typing import Any, NoReturn

import gitlab
import requests
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

# Empty enrichment for an MR the batched GraphQL query didn't return (e.g.
# it errors out, or -- in a fake/test client -- was never registered).
_NO_ENRICHMENT = (0, 0, 0, 0)

# GitLab's top-level `mergeRequests` GraphQL field can't be filtered by iid
# cheaply -- querying it without a project/group scope times out server-side
# (verified against the live API). Fetching by project is fast, so each
# distinct project among the fetched MRs becomes its own aliased sub-query,
# batched into a single GraphQL request regardless of how many projects.
_ENRICHMENT_QUERY_TEMPLATE = """
query({variable_declarations}) {{
{project_queries}
}}
"""

_PROJECT_QUERY_TEMPLATE = """
  {alias}: project(fullPath: ${path_var}) {{
    mergeRequests(iids: ${iids_var}) {{
      nodes {{
        iid
        approvedBy {{ nodes {{ username }} }}
        approvalsLeft
        diffStatsSummary {{ additions deletions }}
      }}
    }}
  }}"""


def _quit_requested() -> bool:
    """Whether the Textual worker running this fetch has been cancelled (e.g. app quit)."""
    try:
        return get_current_worker().is_cancelled
    except NoActiveWorker:
        return False


def build_gitlab_client(token: str, url: str) -> gitlab.Gitlab:
    return gitlab.Gitlab(url, private_token=token)


def _pipeline_status(raw_mr: Any) -> str | None:
    if not hasattr(raw_mr, "pipelines"):
        return None
    pipelines = raw_mr.pipelines.list(get_all=True)
    return pipelines[0].status if pipelines else None


def _group_by_project(raw_mrs: list[Any], project_of: Any) -> dict[str, list[Any]]:
    by_project: dict[str, list[Any]] = {}
    for raw_mr in raw_mrs:
        by_project.setdefault(project_of(raw_mr), []).append(raw_mr)
    return by_project


def _enrich_projects(
    client: gitlab.Gitlab, by_project: dict[str, list[Any]]
) -> dict[tuple[str, int], tuple[int, int, int, int]]:
    """One GraphQL request enriching every MR across the given projects."""
    variable_declarations = []
    project_queries = []
    variables: dict[str, Any] = {}
    aliases_by_project: dict[str, str] = {}
    for index, (project, project_mrs) in enumerate(by_project.items()):
        alias, path_var, iids_var = f"p{index}", f"path{index}", f"iids{index}"
        aliases_by_project[project] = alias
        variable_declarations.append(f"${path_var}: ID!, ${iids_var}: [String!]")
        project_queries.append(
            _PROJECT_QUERY_TEMPLATE.format(alias=alias, path_var=path_var, iids_var=iids_var)
        )
        variables[path_var] = project
        variables[iids_var] = [str(raw_mr.iid) for raw_mr in project_mrs]

    response = requests.post(
        f"{client.url}/api/graphql",
        json={
            "query": _ENRICHMENT_QUERY_TEMPLATE.format(
                variable_declarations=", ".join(variable_declarations),
                project_queries="\n".join(project_queries),
            ),
            "variables": variables,
        },
        headers={"Authorization": f"Bearer {client.private_token}"},
        timeout=30,
    )
    response.raise_for_status()
    data = response.json()["data"]

    enrichment: dict[tuple[str, int], tuple[int, int, int, int]] = {}
    for project, alias in aliases_by_project.items():
        project_data = data.get(alias)
        if project_data is None:
            continue
        for node in project_data["mergeRequests"]["nodes"]:
            approvals_given = len(node["approvedBy"]["nodes"])
            approvals_required = approvals_given + node["approvalsLeft"]
            enrichment[(project, int(node["iid"]))] = (
                approvals_given,
                approvals_required,
                node["diffStatsSummary"]["additions"],
                node["diffStatsSummary"]["deletions"],
            )
    return enrichment


# GitLab's GraphQL query-complexity ceiling (250 by default) means an
# aliased sub-query per project can't scale to an arbitrary project count in
# one request -- verified against the live API, where 34 aliased projects
# hit "complexity of 918, which exceeds max complexity of 250" (~27/project).
# Chunking keeps each request comfortably under that regardless of how many
# distinct projects a group section spans.
_GRAPHQL_PROJECTS_PER_REQUEST = 8


def _graphql_enrich(
    client: gitlab.Gitlab, raw_mrs: list[Any], project_of: Any
) -> dict[tuple[str, int], tuple[int, int, int, int]]:
    """Fetch approvals + diff-stat enrichment for every MR via GraphQL
    (one aliased sub-query per distinct project, chunked to stay under
    GitLab's query-complexity limit) instead of 2 REST calls per MR.

    Maps (project, iid) -> (approvals_given, approvals_required,
    lines_added, lines_removed).
    """
    by_project = _group_by_project(raw_mrs, project_of)
    projects = list(by_project.items())
    enrichment: dict[tuple[str, int], tuple[int, int, int, int]] = {}
    for start in range(0, len(projects), _GRAPHQL_PROJECTS_PER_REQUEST):
        chunk = dict(projects[start : start + _GRAPHQL_PROJECTS_PER_REQUEST])
        enrichment.update(_enrich_projects(client, chunk))
    return enrichment


def _to_domain(
    raw_mr: Any, project: str, enrichment: dict[tuple[str, int], tuple[int, int, int, int]]
) -> MergeRequest:
    assignee = getattr(raw_mr, "assignee", None)
    approvals_given, approvals_required, lines_added, lines_removed = enrichment.get(
        (project, raw_mr.iid), _NO_ENRICHMENT
    )
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


def _map_all(
    client: gitlab.Gitlab, raw_mrs: Any, project_of: Any = _project_from_references
) -> list[MergeRequest]:
    """Map raw MRs to domain entities, stopping early if the fetch is cancelled.

    `project_of` derives each MR's project; defaults to reading it off the MR
    itself for scopes (group/global) that don't already know it. Enrichment
    (approvals, diff stats) is fetched for every MR in one batched GraphQL
    call up front rather than 2 REST calls per MR.
    """
    raw_mrs = list(raw_mrs)
    if _quit_requested():
        return []
    enrichment = _graphql_enrich(client, raw_mrs, project_of)
    merge_requests = []
    for raw_mr in raw_mrs:
        if _quit_requested():
            break
        merge_requests.append(_to_domain(raw_mr, project_of(raw_mr), enrichment))
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
        return _map_all(self._client, raw_mrs, project_of=lambda _raw_mr: project)

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
        return _map_all(self._client, raw_mrs)

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
        return _map_all(self._client, raw_mrs)

    def get_merge_request_detail(self, project: str, iid: int) -> MergeRequestDetail:
        raw_mr = self._client.projects.get(project).mergerequests.get(iid)
        return MergeRequestDetail(
            description=raw_mr.description or "",
            discussions=_discussions(raw_mr),
            diff=_diff_text(raw_mr),
            pipeline_status=_pipeline_status(raw_mr),
        )
