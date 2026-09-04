from collections.abc import Sequence
from types import SimpleNamespace
from typing import Any, cast

import gitlab
import pytest
from textual.worker import active_worker

from glab_dash.application.list_merge_requests import list_merge_requests_for_section
from glab_dash.domain.config import MergeRequestState, Scope, Section
from glab_dash.domain.merge_request import SectionNotFoundError
from glab_dash.infrastructure import gitlab_gateway
from glab_dash.infrastructure.gitlab_gateway import (
    GITLAB_COM_URL,
    GitlabMergeRequestGateway,
    build_gitlab_client,
)


def make_raw_mr(
    discussions: Sequence[bool] = (),
    pipeline_statuses: Sequence[str] = (),
    diffs: Sequence[str] = (),
    **overrides: object,
) -> SimpleNamespace:
    defaults = {
        "id": 42,
        "iid": 42,
        "title": "Add feature",
        "author": {"username": "octocat"},
        "source_branch": "feature",
        "target_branch": "main",
        "state": "opened",
        "labels": ["backend"],
        "web_url": "https://gitlab.com/group/project/-/merge_requests/42",
        "updated_at": "2026-08-25T00:00:00Z",
        "references": {"full": "group/project!42"},
        "discussions": SimpleNamespace(
            list=lambda get_all=True: [
                SimpleNamespace(resolved=resolved) for resolved in discussions
            ]
        ),
        "pipelines": SimpleNamespace(
            list=lambda get_all=True: [
                SimpleNamespace(status=status) for status in pipeline_statuses
            ]
        ),
        "changes": lambda: {"changes": [{"diff": diff} for diff in diffs]},
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


class FakeGraphQLResponse:
    """Stands in for `requests.post(...)`'s return value.

    `nodes_by_alias` mirrors the real response shape: one key per aliased
    `project(fullPath: ...)` sub-query (e.g. `p0`), each holding that
    project's `mergeRequests.nodes`.
    """

    def __init__(self, nodes_by_alias: dict[str, list[dict[str, object]]]) -> None:
        self._nodes_by_alias = nodes_by_alias

    def raise_for_status(self) -> None:
        pass

    def json(self) -> dict[str, object]:
        return {
            "data": {
                alias: {"mergeRequests": {"nodes": nodes}}
                for alias, nodes in self._nodes_by_alias.items()
            }
        }


def enrichment_node(
    iid: int,
    approved_by: Sequence[str] = (),
    approvals_left: int = 0,
    additions: int = 0,
    deletions: int = 0,
) -> dict[str, object]:
    """A GraphQL `mergeRequests.nodes[]` entry for the MR with `iid`."""
    return {
        "iid": str(iid),
        "approvedBy": {"nodes": [{"username": username} for username in approved_by]},
        "approvalsLeft": approvals_left,
        "diffStatsSummary": {"additions": additions, "deletions": deletions},
    }


@pytest.fixture(autouse=True)
def _no_enrichment_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    """Every gateway list call fetches enrichment via one GraphQL POST.

    Stub it to return nothing unless a test overrides `requests.post` itself
    to assert on the request or return specific enrichment.
    """
    monkeypatch.setattr(gitlab_gateway.requests, "post", lambda *a, **k: FakeGraphQLResponse({}))


class FakeMergeRequestManager:
    def __init__(self, raw_mrs: Sequence[SimpleNamespace]) -> None:
        self._raw_mrs = raw_mrs
        self.list_kwargs: dict[str, object] | None = None

    def list(self, get_all: bool = True, **kwargs: object) -> Sequence[SimpleNamespace]:
        self.list_kwargs = kwargs
        return self._raw_mrs

    def get(self, iid: int) -> SimpleNamespace:
        return next(raw_mr for raw_mr in self._raw_mrs if raw_mr.iid == iid)


class FakeProject:
    def __init__(self, raw_mrs: list[SimpleNamespace]) -> None:
        self.mergerequests = FakeMergeRequestManager(raw_mrs)


class FakeProjectManager:
    def __init__(self, projects_by_path: dict[str, FakeProject]) -> None:
        self._projects_by_path = projects_by_path

    def get(self, project_path: str) -> FakeProject:
        return self._projects_by_path[project_path]


class FakeGroup:
    def __init__(self, raw_mrs: list[SimpleNamespace]) -> None:
        self.mergerequests = FakeMergeRequestManager(raw_mrs)


class FakeGroupManager:
    def __init__(self, groups_by_path: dict[str, FakeGroup]) -> None:
        self._groups_by_path = groups_by_path

    def get(self, group_path: str) -> FakeGroup:
        return self._groups_by_path[group_path]


class FakeGitlabClient:
    def __init__(
        self,
        projects_by_path: dict[str, FakeProject] | None = None,
        groups_by_path: dict[str, FakeGroup] | None = None,
        global_raw_mrs: list[SimpleNamespace] | None = None,
    ) -> None:
        self.projects = FakeProjectManager(projects_by_path or {})
        self.groups = FakeGroupManager(groups_by_path or {})
        self.mergerequests = FakeMergeRequestManager(global_raw_mrs or [])
        self.url = GITLAB_COM_URL
        self.private_token = "secret"


def test_lists_and_maps_a_projects_merge_requests_into_domain_entities() -> None:
    raw_mr = make_raw_mr()
    client = FakeGitlabClient({"group/project": FakeProject([raw_mr])})
    gateway = GitlabMergeRequestGateway(cast("gitlab.Gitlab", client))

    result = gateway.list_project_merge_requests("group/project")

    assert len(result) == 1
    mr = result[0]
    assert mr.iid == 42
    assert mr.project == "group/project"
    assert mr.title == "Add feature"
    assert mr.author == "octocat"
    assert mr.source_branch == "feature"
    assert mr.target_branch == "main"
    assert mr.state is MergeRequestState.OPENED
    assert mr.labels == ["backend"]
    assert mr.web_url == raw_mr.web_url
    assert mr.updated_at == raw_mr.updated_at
    assert mr.assignee is None


def test_skips_the_enrichment_call_entirely_when_already_cancelled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Regression: the TUI hung on quit because fetches kept enriching every MR.

    Enrichment is now one batched GraphQL call for the whole list rather than
    N per-MR REST calls, so there's no "stop partway through enriching" --
    cancellation just skips issuing that call at all.
    """

    class FakeCancellableWorker:
        is_cancelled = True

    token = active_worker.set(FakeCancellableWorker())

    def fail_if_called(*args: object, **kwargs: object) -> None:
        raise AssertionError("GraphQL enrichment should not run once cancelled")

    monkeypatch.setattr(gitlab_gateway.requests, "post", fail_if_called)

    client = FakeGitlabClient({"group/project": FakeProject([make_raw_mr()])})
    gateway = GitlabMergeRequestGateway(cast("gitlab.Gitlab", client))

    try:
        result = gateway.list_project_merge_requests("group/project")
    finally:
        active_worker.reset(token)

    assert result == []


def test_approvals_reflect_approved_by_and_approvals_left(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    raw_mr = make_raw_mr(iid=7)
    monkeypatch.setattr(
        gitlab_gateway.requests,
        "post",
        lambda *a, **k: FakeGraphQLResponse(
            {"p0": [enrichment_node(7, approved_by=["octocat"], approvals_left=1)]}
        ),
    )
    client = FakeGitlabClient({"group/project": FakeProject([raw_mr])})
    gateway = GitlabMergeRequestGateway(cast("gitlab.Gitlab", client))

    result = gateway.list_project_merge_requests("group/project")

    assert result[0].approvals_given == 1
    assert result[0].approvals_required == 2


def test_line_stats_come_from_the_graphql_diff_stats_summary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    raw_mr = make_raw_mr(iid=7)
    monkeypatch.setattr(
        gitlab_gateway.requests,
        "post",
        lambda *a, **k: FakeGraphQLResponse({"p0": [enrichment_node(7, additions=12, deletions=3)]}),
    )
    client = FakeGitlabClient({"group/project": FakeProject([raw_mr])})
    gateway = GitlabMergeRequestGateway(cast("gitlab.Gitlab", client))

    result = gateway.list_project_merge_requests("group/project")

    assert result[0].lines_added == 12
    assert result[0].lines_removed == 3


def test_enrichment_defaults_to_zero_when_graphql_omits_a_merge_request() -> None:
    """The default GraphQL stub returns no nodes; enrichment should degrade

    to zero rather than raising a KeyError.
    """
    raw_mr = make_raw_mr(iid=7)
    client = FakeGitlabClient({"group/project": FakeProject([raw_mr])})
    gateway = GitlabMergeRequestGateway(cast("gitlab.Gitlab", client))

    result = gateway.list_project_merge_requests("group/project")

    assert result[0].approvals_given == 0
    assert result[0].approvals_required == 0
    assert result[0].lines_added == 0
    assert result[0].lines_removed == 0


def test_enrichment_call_batches_every_project_into_one_aliased_graphql_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A group section spans multiple projects; enrichment should still be a

    single HTTP request, with one aliased `project(fullPath: ...)` sub-query
    per distinct project rather than one request per project.
    """
    mr_in_a = make_raw_mr(iid=1, references={"full": "team/a!1"})
    mr_in_b = make_raw_mr(iid=2, references={"full": "team/b!2"})
    captured: dict[str, Any] = {}

    def fake_post(
        url: str, json: dict[str, object], headers: dict[str, str], **_: object
    ) -> FakeGraphQLResponse:
        captured["url"] = url
        captured["json"] = json
        captured["headers"] = headers
        return FakeGraphQLResponse({})

    monkeypatch.setattr(gitlab_gateway.requests, "post", fake_post)
    client = FakeGitlabClient(groups_by_path={"team": FakeGroup([mr_in_a, mr_in_b])})
    gateway = GitlabMergeRequestGateway(cast("gitlab.Gitlab", client))

    gateway.list_group_merge_requests("team")

    assert captured["url"] == f"{GITLAB_COM_URL}/api/graphql"
    assert captured["headers"] == {"Authorization": "Bearer secret"}
    assert captured["json"]["variables"] == {
        "path0": "team/a",
        "iids0": ["1"],
        "path1": "team/b",
        "iids1": ["2"],
    }
    assert captured["json"]["query"].count("project(fullPath:") == 2


def test_maps_assignee_username_when_present() -> None:
    raw_mr = make_raw_mr(assignee={"username": "hubot"})
    client = FakeGitlabClient({"group/project": FakeProject([raw_mr])})
    gateway = GitlabMergeRequestGateway(cast("gitlab.Gitlab", client))

    result = gateway.list_project_merge_requests("group/project")

    assert result[0].assignee == "hubot"


def test_gitlab_com_url_is_the_single_named_constant() -> None:
    assert GITLAB_COM_URL == "https://gitlab.com"


def test_build_gitlab_client_uses_the_url_passed_in_not_a_hardcoded_literal() -> None:
    client = build_gitlab_client(token="secret", url=GITLAB_COM_URL)

    assert client.url == GITLAB_COM_URL


def test_lists_and_maps_a_groups_merge_requests_deriving_project_from_references() -> None:
    raw_mr = make_raw_mr(references={"full": "team/project!42"})
    client = FakeGitlabClient(groups_by_path={"team": FakeGroup([raw_mr])})
    gateway = GitlabMergeRequestGateway(cast("gitlab.Gitlab", client))

    result = gateway.list_group_merge_requests("team")

    assert len(result) == 1
    assert result[0].project == "team/project"


def test_lists_and_maps_every_visible_merge_request_deriving_project_from_references() -> None:
    raw_mr = make_raw_mr(references={"full": "team/project!42"})
    client = FakeGitlabClient(global_raw_mrs=[raw_mr])
    gateway = GitlabMergeRequestGateway(cast("gitlab.Gitlab", client))

    result = gateway.list_global_merge_requests()

    assert len(result) == 1
    assert result[0].project == "team/project"


def test_lists_a_groups_merge_requests_without_project_only_managers() -> None:
    """GraphQL enrichment keys off `.id` alone, so group/global-scoped MRs

    (GitLab's bare `GroupMergeRequest`/`MergeRequest`, which have no
    `approvals`/`pipelines`/`discussions`/`changes` manager) enrich the same
    way a `ProjectMergeRequest` does -- no REST manager to be missing.
    """
    raw_mr = make_raw_mr(id=99, references={"full": "team/project!42"})
    for missing_attr in ("pipelines", "discussions", "changes"):
        delattr(raw_mr, missing_attr)
    client = FakeGitlabClient(groups_by_path={"team": FakeGroup([raw_mr])})
    gateway = GitlabMergeRequestGateway(cast("gitlab.Gitlab", client))

    result = gateway.list_group_merge_requests("team")

    assert len(result) == 1
    assert result[0].project == "team/project"


def test_global_scope_requests_all_visible_mrs_not_just_the_authenticated_users() -> None:
    client = FakeGitlabClient(global_raw_mrs=[make_raw_mr()])
    gateway = GitlabMergeRequestGateway(cast("gitlab.Gitlab", client))

    gateway.list_global_merge_requests()

    assert client.mergerequests.list_kwargs == {"scope": "all"}


def test_list_project_merge_requests_forwards_state_author_assignee_and_labels_server_side() -> (
    None
):
    """Regression: fetching every MR then filtering client-side made a 20k-MR group

    fetch (and enrich!) its entire history for a section that only wanted open MRs.
    """
    fake_project = FakeProject([make_raw_mr()])
    client = FakeGitlabClient({"group/project": fake_project})
    gateway = GitlabMergeRequestGateway(cast("gitlab.Gitlab", client))

    gateway.list_project_merge_requests(
        "group/project",
        state=MergeRequestState.OPENED,
        author="octocat",
        assignee="hubot",
        labels=["urgent", "backend"],
    )

    assert fake_project.mergerequests.list_kwargs == {
        "state": "opened",
        "author_username": "octocat",
        "assignee_username": "hubot",
        "labels": "urgent,backend",
    }


def test_list_project_merge_requests_omits_state_param_when_state_is_all() -> None:
    fake_project = FakeProject([make_raw_mr()])
    client = FakeGitlabClient({"group/project": fake_project})
    gateway = GitlabMergeRequestGateway(cast("gitlab.Gitlab", client))

    gateway.list_project_merge_requests("group/project", state=MergeRequestState.ALL)

    assert fake_project.mergerequests.list_kwargs == {}


def test_list_group_merge_requests_forwards_filters_server_side() -> None:
    fake_group = FakeGroup([make_raw_mr()])
    client = FakeGitlabClient(groups_by_path={"team": fake_group})
    gateway = GitlabMergeRequestGateway(cast("gitlab.Gitlab", client))

    gateway.list_group_merge_requests("team", state=MergeRequestState.OPENED, labels=["urgent"])

    assert fake_group.mergerequests.list_kwargs == {"state": "opened", "labels": "urgent"}


def test_list_global_merge_requests_forwards_filters_alongside_scope_all() -> None:
    client = FakeGitlabClient(global_raw_mrs=[make_raw_mr()])
    gateway = GitlabMergeRequestGateway(cast("gitlab.Gitlab", client))

    gateway.list_global_merge_requests(state=MergeRequestState.OPENED, author="octocat")

    assert client.mergerequests.list_kwargs == {"scope": "all", "state": "opened", "author_username": "octocat"}


def test_get_merge_request_detail_returns_description_discussions_and_diff() -> None:
    raw_mr = SimpleNamespace(
        iid=42,
        description="Fixes the thing",
        discussions=SimpleNamespace(
            list=lambda get_all=True: [
                SimpleNamespace(
                    attributes={
                        "notes": [
                            {"author": {"username": "octocat"}, "body": "Looks good"},
                            {"author": {"username": "hubot"}, "body": "Agreed"},
                        ]
                    }
                )
            ]
        ),
        changes=lambda: {
            "changes": [{"old_path": "a.py", "new_path": "a.py", "diff": "+new line\n"}]
        },
        pipelines=SimpleNamespace(list=lambda get_all=True: [SimpleNamespace(status="success")]),
    )
    client = FakeGitlabClient({"group/project": FakeProject([raw_mr])})
    gateway = GitlabMergeRequestGateway(cast("gitlab.Gitlab", client))

    detail = gateway.get_merge_request_detail("group/project", 42)

    assert detail.description == "Fixes the thing"
    assert len(detail.discussions) == 1
    assert [note.author for note in detail.discussions[0].notes] == ["octocat", "hubot"]
    assert [note.body for note in detail.discussions[0].notes] == ["Looks good", "Agreed"]
    assert "diff --git a/a.py b/a.py" in detail.diff
    assert "+new line" in detail.diff
    assert detail.pipeline_status == "success"


class RaisingManager:
    def __init__(self, response_code: int) -> None:
        self._response_code = response_code

    def get(self, path: str) -> SimpleNamespace:
        raise gitlab.exceptions.GitlabGetError(response_code=self._response_code)


def test_list_group_merge_requests_raises_section_not_found_on_404() -> None:
    client = FakeGitlabClient()
    client.groups = cast("FakeGroupManager", RaisingManager(response_code=404))
    gateway = GitlabMergeRequestGateway(cast("gitlab.Gitlab", client))

    with pytest.raises(SectionNotFoundError):
        gateway.list_group_merge_requests("data-platform")


def test_list_project_merge_requests_raises_section_not_found_on_404() -> None:
    client = FakeGitlabClient()
    client.projects = cast("FakeProjectManager", RaisingManager(response_code=404))
    gateway = GitlabMergeRequestGateway(cast("gitlab.Gitlab", client))

    with pytest.raises(SectionNotFoundError):
        gateway.list_project_merge_requests("group/missing")


def test_list_group_merge_requests_reraises_non_404_gitlab_errors() -> None:
    client = FakeGitlabClient()
    client.groups = cast("FakeGroupManager", RaisingManager(response_code=500))
    gateway = GitlabMergeRequestGateway(cast("gitlab.Gitlab", client))

    with pytest.raises(gitlab.exceptions.GitlabGetError):
        gateway.list_group_merge_requests("data-platform")


def test_use_case_returns_correctly_filtered_mrs_via_the_real_gateway() -> None:
    opened = make_raw_mr(iid=1, state="opened")
    merged = make_raw_mr(iid=2, state="merged")
    client = FakeGitlabClient({"group/project": FakeProject([opened, merged])})
    gateway = GitlabMergeRequestGateway(cast("gitlab.Gitlab", client))
    section = Section(title="My MRs", scope=Scope.PROJECT, project="group/project")

    result = list_merge_requests_for_section(gateway, section)

    assert [mr.iid for mr in result] == [1]
