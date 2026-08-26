from glab_dash.application.list_merge_requests import list_merge_requests_for_section
from glab_dash.domain.config import MergeRequestState, Scope, Section
from glab_dash.domain.merge_request import MergeRequest


class FakeMergeRequestGateway:
    def __init__(self, merge_requests: list[MergeRequest]) -> None:
        self._merge_requests = merge_requests

    def list_project_merge_requests(self, project: str) -> list[MergeRequest]:
        return [mr for mr in self._merge_requests if mr.project == project]

    def list_group_merge_requests(self, group: str) -> list[MergeRequest]:
        return [mr for mr in self._merge_requests if mr.project.startswith(f"{group}/")]

    def list_global_merge_requests(self) -> list[MergeRequest]:
        return list(self._merge_requests)


def make_mr(
    project: str,
    state: MergeRequestState,
    author: str = "octocat",
    assignee: str | None = None,
    labels: list[str] | None = None,
) -> MergeRequest:
    return MergeRequest(
        iid=1,
        project=project,
        title="Add feature",
        author=author,
        assignee=assignee,
        source_branch="feature",
        target_branch="main",
        state=state,
        labels=labels or [],
        web_url="https://gitlab.com/group/project/-/merge_requests/1",
        updated_at="2026-08-25T00:00:00Z",
    )


def test_returns_only_merge_requests_for_the_sections_project_and_state():
    section = Section(title="My MRs", scope=Scope.PROJECT, project="group/project")
    matching = make_mr("group/project", MergeRequestState.OPENED)
    wrong_state = make_mr("group/project", MergeRequestState.MERGED)
    wrong_project = make_mr("group/other", MergeRequestState.OPENED)
    gateway = FakeMergeRequestGateway([matching, wrong_state, wrong_project])

    result = list_merge_requests_for_section(gateway, section)

    assert result == [matching]


def test_group_scope_returns_only_merge_requests_under_the_group_and_state():
    section = Section(title="Team MRs", scope=Scope.GROUP, group="team")
    matching = make_mr("team/project", MergeRequestState.OPENED)
    wrong_state = make_mr("team/project", MergeRequestState.MERGED)
    wrong_group = make_mr("other/project", MergeRequestState.OPENED)
    gateway = FakeMergeRequestGateway([matching, wrong_state, wrong_group])

    result = list_merge_requests_for_section(gateway, section)

    assert result == [matching]


def test_global_scope_returns_every_visible_merge_request_matching_state():
    section = Section(title="All MRs", scope=Scope.GLOBAL)
    matching = make_mr("team/project", MergeRequestState.OPENED)
    other_matching = make_mr("other/project", MergeRequestState.OPENED)
    wrong_state = make_mr("team/project", MergeRequestState.MERGED)
    gateway = FakeMergeRequestGateway([matching, other_matching, wrong_state])

    result = list_merge_requests_for_section(gateway, section)

    assert result == [matching, other_matching]


def test_composes_state_author_and_labels_filters():
    section = Section(
        title="My MRs",
        scope=Scope.PROJECT,
        project="group/project",
        author="@me",
        labels=["urgent"],
    )
    matching = make_mr(
        "group/project", MergeRequestState.OPENED, author="hubot", labels=["urgent"]
    )
    wrong_author = make_mr(
        "group/project", MergeRequestState.OPENED, author="octocat", labels=["urgent"]
    )
    missing_label = make_mr("group/project", MergeRequestState.OPENED, author="hubot")
    gateway = FakeMergeRequestGateway([matching, wrong_author, missing_label])

    result = list_merge_requests_for_section(gateway, section, current_username="hubot")

    assert result == [matching]


def test_assignee_at_me_resolves_to_the_authenticated_user():
    section = Section(
        title="Assigned to me", scope=Scope.PROJECT, project="group/project", assignee="@me"
    )
    mine = make_mr("group/project", MergeRequestState.OPENED, assignee="hubot")
    theirs = make_mr("group/project", MergeRequestState.OPENED, assignee="octocat")
    gateway = FakeMergeRequestGateway([mine, theirs])

    result = list_merge_requests_for_section(gateway, section, current_username="hubot")

    assert result == [mine]
