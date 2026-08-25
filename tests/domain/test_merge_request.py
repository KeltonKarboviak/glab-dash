from glab_dash.domain.config import MergeRequestState
from glab_dash.domain.merge_request import MergeRequest, filter_by_state


def make_mr(state: MergeRequestState) -> MergeRequest:
    return MergeRequest(
        iid=1,
        project="group/project",
        title="Add feature",
        author="octocat",
        source_branch="feature",
        target_branch="main",
        state=state,
        labels=[],
        web_url="https://gitlab.com/group/project/-/merge_requests/1",
        updated_at="2026-08-25T00:00:00Z",
    )


def test_filter_by_state_keeps_only_matching_state():
    opened = make_mr(MergeRequestState.OPENED)
    merged = make_mr(MergeRequestState.MERGED)

    result = filter_by_state([opened, merged], MergeRequestState.OPENED)

    assert result == [opened]


def test_filter_by_state_all_returns_every_mr():
    opened = make_mr(MergeRequestState.OPENED)
    merged = make_mr(MergeRequestState.MERGED)

    result = filter_by_state([opened, merged], MergeRequestState.ALL)

    assert result == [opened, merged]
