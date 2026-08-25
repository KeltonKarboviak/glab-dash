from glab_dash.application.list_merge_requests import list_merge_requests_for_section
from glab_dash.domain.config import MergeRequestState, Scope, Section
from glab_dash.domain.merge_request import MergeRequest


class FakeMergeRequestGateway:
    def __init__(self, merge_requests: list[MergeRequest]) -> None:
        self._merge_requests = merge_requests

    def list_project_merge_requests(self, project: str) -> list[MergeRequest]:
        return [mr for mr in self._merge_requests if mr.project == project]


def make_mr(project: str, state: MergeRequestState) -> MergeRequest:
    return MergeRequest(
        iid=1,
        project=project,
        title="Add feature",
        author="octocat",
        source_branch="feature",
        target_branch="main",
        state=state,
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
