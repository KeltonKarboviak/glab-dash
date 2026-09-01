from collections.abc import Sequence
from types import SimpleNamespace
from typing import cast

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
    approved_by: Sequence[dict[str, str]] = (),
    approvals_required: int = 0,
    pipeline_statuses: Sequence[str] = (),
    diffs: Sequence[str] = (),
    **overrides: object,
) -> SimpleNamespace:
    defaults = {
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
        "approvals": SimpleNamespace(
            get=lambda: SimpleNamespace(
                approved_by=list(approved_by), approvals_required=approvals_required
            )
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


def test_stops_starting_new_enrichment_batches_once_the_worker_is_cancelled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Regression: the TUI hung on quit because fetches kept enriching every MR.

    Enrichment now runs `_ENRICHMENT_BATCH_SIZE` MRs at a time on a thread
    pool, so cancellation is only checked *between* batches -- an in-flight
    batch always finishes (its threads are already running), but no new
    batch is started once cancelled.
    """
    monkeypatch.setattr(gitlab_gateway, "_ENRICHMENT_BATCH_SIZE", 2)

    class FakeCancellableWorker:
        is_cancelled = False

    worker = FakeCancellableWorker()
    token = active_worker.set(worker)

    def cancel_after_first_batchs_discussions_call(get_all: bool = True) -> list[SimpleNamespace]:
        worker.is_cancelled = True
        return []

    cancelling_raw_mr = make_raw_mr(iid=1)
    cancelling_raw_mr.discussions.list = cancel_after_first_batchs_discussions_call
    same_batch_raw_mr = make_raw_mr(iid=2)
    next_batch_raw_mr = make_raw_mr(iid=3)
    client = FakeGitlabClient(
        {"group/project": FakeProject([cancelling_raw_mr, same_batch_raw_mr, next_batch_raw_mr])}
    )
    gateway = GitlabMergeRequestGateway(cast("gitlab.Gitlab", client))

    try:
        result = gateway.list_project_merge_requests("group/project")
    finally:
        active_worker.reset(token)

    assert {mr.iid for mr in result} == {1, 2}


def test_unresolved_discussion_count_excludes_resolved_discussions() -> None:
    raw_mr = make_raw_mr(discussions=[True, False, False])
    client = FakeGitlabClient({"group/project": FakeProject([raw_mr])})
    gateway = GitlabMergeRequestGateway(cast("gitlab.Gitlab", client))

    result = gateway.list_project_merge_requests("group/project")

    assert result[0].unresolved_discussion_count == 2


def test_approvals_reflect_approved_by_and_required_count() -> None:
    raw_mr = make_raw_mr(approved_by=[{"username": "octocat"}], approvals_required=2)
    client = FakeGitlabClient({"group/project": FakeProject([raw_mr])})
    gateway = GitlabMergeRequestGateway(cast("gitlab.Gitlab", client))

    result = gateway.list_project_merge_requests("group/project")

    assert result[0].approvals_given == 1
    assert result[0].approvals_required == 2


def test_pipeline_status_is_the_latest_pipelines_status() -> None:
    raw_mr = make_raw_mr(pipeline_statuses=["success", "failed"])
    client = FakeGitlabClient({"group/project": FakeProject([raw_mr])})
    gateway = GitlabMergeRequestGateway(cast("gitlab.Gitlab", client))

    result = gateway.list_project_merge_requests("group/project")

    assert result[0].pipeline_status == "success"


def test_pipeline_status_is_none_when_there_are_no_pipelines() -> None:
    raw_mr = make_raw_mr(pipeline_statuses=[])
    client = FakeGitlabClient({"group/project": FakeProject([raw_mr])})
    gateway = GitlabMergeRequestGateway(cast("gitlab.Gitlab", client))

    result = gateway.list_project_merge_requests("group/project")

    assert result[0].pipeline_status is None


def test_line_stats_sum_added_and_removed_lines_across_files_diffs() -> None:
    diffs = [
        "@@ -1,2 +1,3 @@\n-old line\n+++ b/file\n+new line 1\n+new line 2\n",
        "@@ -1,1 +1,1 @@\n--- a/other\n-removed line\n",
    ]
    raw_mr = make_raw_mr(diffs=diffs)
    client = FakeGitlabClient({"group/project": FakeProject([raw_mr])})
    gateway = GitlabMergeRequestGateway(cast("gitlab.Gitlab", client))

    result = gateway.list_project_merge_requests("group/project")

    assert result[0].lines_added == 2
    assert result[0].lines_removed == 2


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


def _make_bare_raw_mr(**overrides: object) -> SimpleNamespace:
    """A group/global-scoped merge request as GitLab actually returns it.

    Real `GroupMergeRequest`/`MergeRequest` objects have no `approvals`,
    `pipelines`, `discussions`, or `changes` manager -- only `ProjectMergeRequest`
    does. `make_raw_mr()` stubs those managers on every fixture, which hid this
    shape from tests.
    """
    raw_mr = make_raw_mr(**overrides)
    for missing_attr in ("approvals", "pipelines", "discussions", "changes"):
        delattr(raw_mr, missing_attr)
    return raw_mr


def test_lists_a_groups_merge_requests_without_project_only_managers() -> None:
    raw_mr = _make_bare_raw_mr(references={"full": "team/project!42"})
    client = FakeGitlabClient(groups_by_path={"team": FakeGroup([raw_mr])})
    gateway = GitlabMergeRequestGateway(cast("gitlab.Gitlab", client))

    result = gateway.list_group_merge_requests("team")

    assert len(result) == 1
    mr = result[0]
    assert mr.approvals_given == 0
    assert mr.approvals_required == 0
    assert mr.pipeline_status is None
    assert mr.unresolved_discussion_count == 0
    assert mr.lines_added == 0
    assert mr.lines_removed == 0


def test_lists_global_merge_requests_without_project_only_managers() -> None:
    raw_mr = _make_bare_raw_mr(references={"full": "team/project!42"})
    client = FakeGitlabClient(global_raw_mrs=[raw_mr])
    gateway = GitlabMergeRequestGateway(cast("gitlab.Gitlab", client))

    result = gateway.list_global_merge_requests()

    assert len(result) == 1
    mr = result[0]
    assert mr.approvals_given == 0
    assert mr.approvals_required == 0
    assert mr.pipeline_status is None
    assert mr.unresolved_discussion_count == 0
    assert mr.lines_added == 0
    assert mr.lines_removed == 0


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
