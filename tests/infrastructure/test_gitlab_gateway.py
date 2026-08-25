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
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


class FakeMergeRequestManager:
    def __init__(self, raw_mrs):
        self._raw_mrs = raw_mrs

    def list(self, get_all=True):
        return self._raw_mrs


class FakeProject:
    def __init__(self, raw_mrs):
        self.mergerequests = FakeMergeRequestManager(raw_mrs)


class FakeProjectManager:
    def __init__(self, projects_by_path):
        self._projects_by_path = projects_by_path

    def get(self, project_path):
        return self._projects_by_path[project_path]


class FakeGitlabClient:
    def __init__(self, projects_by_path):
        self.projects = FakeProjectManager(projects_by_path)


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


def test_use_case_returns_correctly_filtered_mrs_via_the_real_gateway():
    opened = make_raw_mr(iid=1, state="opened")
    merged = make_raw_mr(iid=2, state="merged")
    client = FakeGitlabClient({"group/project": FakeProject([opened, merged])})
    gateway = GitlabMergeRequestGateway(client)
    section = Section(title="My MRs", scope=Scope.PROJECT, project="group/project")

    result = list_merge_requests_for_section(gateway, section)

    assert [mr.iid for mr in result] == [1]
