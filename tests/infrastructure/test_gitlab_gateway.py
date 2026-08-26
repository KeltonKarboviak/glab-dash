from types import SimpleNamespace

from glab_dash.application.list_merge_requests import list_merge_requests_for_section
from glab_dash.domain.config import MergeRequestState, Scope, Section
from glab_dash.infrastructure.gitlab_gateway import (
    GITLAB_COM_URL,
    GitlabMergeRequestGateway,
    build_gitlab_client,
)


def make_raw_mr(**overrides):
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
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


class FakeMergeRequestManager:
    def __init__(self, raw_mrs):
        self._raw_mrs = raw_mrs
        self.list_kwargs = None

    def list(self, get_all=True, **kwargs):
        self.list_kwargs = kwargs
        return self._raw_mrs


class FakeProject:
    def __init__(self, raw_mrs):
        self.mergerequests = FakeMergeRequestManager(raw_mrs)


class FakeProjectManager:
    def __init__(self, projects_by_path):
        self._projects_by_path = projects_by_path

    def get(self, project_path):
        return self._projects_by_path[project_path]


class FakeGroup:
    def __init__(self, raw_mrs):
        self.mergerequests = FakeMergeRequestManager(raw_mrs)


class FakeGroupManager:
    def __init__(self, groups_by_path):
        self._groups_by_path = groups_by_path

    def get(self, group_path):
        return self._groups_by_path[group_path]


class FakeGitlabClient:
    def __init__(self, projects_by_path=None, groups_by_path=None, global_raw_mrs=None):
        self.projects = FakeProjectManager(projects_by_path or {})
        self.groups = FakeGroupManager(groups_by_path or {})
        self.mergerequests = FakeMergeRequestManager(global_raw_mrs or [])


def test_lists_and_maps_a_projects_merge_requests_into_domain_entities():
    raw_mr = make_raw_mr()
    client = FakeGitlabClient({"group/project": FakeProject([raw_mr])})
    gateway = GitlabMergeRequestGateway(client)

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


def test_gitlab_com_url_is_the_single_named_constant():
    assert GITLAB_COM_URL == "https://gitlab.com"


def test_build_gitlab_client_uses_the_url_passed_in_not_a_hardcoded_literal():
    client = build_gitlab_client(token="secret", url=GITLAB_COM_URL)

    assert client.url == GITLAB_COM_URL


def test_lists_and_maps_a_groups_merge_requests_deriving_project_from_references():
    raw_mr = make_raw_mr(references={"full": "team/project!42"})
    client = FakeGitlabClient(groups_by_path={"team": FakeGroup([raw_mr])})
    gateway = GitlabMergeRequestGateway(client)

    result = gateway.list_group_merge_requests("team")

    assert len(result) == 1
    assert result[0].project == "team/project"


def test_lists_and_maps_every_visible_merge_request_deriving_project_from_references():
    raw_mr = make_raw_mr(references={"full": "team/project!42"})
    client = FakeGitlabClient(global_raw_mrs=[raw_mr])
    gateway = GitlabMergeRequestGateway(client)

    result = gateway.list_global_merge_requests()

    assert len(result) == 1
    assert result[0].project == "team/project"


def test_global_scope_requests_all_visible_mrs_not_just_the_authenticated_users():
    client = FakeGitlabClient(global_raw_mrs=[make_raw_mr()])
    gateway = GitlabMergeRequestGateway(client)

    gateway.list_global_merge_requests()

    assert client.mergerequests.list_kwargs == {"scope": "all"}


def test_use_case_returns_correctly_filtered_mrs_via_the_real_gateway():
    opened = make_raw_mr(iid=1, state="opened")
    merged = make_raw_mr(iid=2, state="merged")
    client = FakeGitlabClient({"group/project": FakeProject([opened, merged])})
    gateway = GitlabMergeRequestGateway(client)
    section = Section(title="My MRs", scope=Scope.PROJECT, project="group/project")

    result = list_merge_requests_for_section(gateway, section)

    assert [mr.iid for mr in result] == [1]
