import pytest

from glab_dash.domain.config import MergeRequestState
from glab_dash.domain.merge_request import (
    Approvals,
    Failed,
    LineStats,
    MergeRequest,
    Pending,
    filter_by_assignee,
    filter_by_author,
    filter_by_labels,
    filter_by_state,
)


def make_mr(
    state: MergeRequestState = MergeRequestState.OPENED,
    author: str = "octocat",
    assignee: str | None = None,
    labels: list[str] | None = None,
) -> MergeRequest:
    return MergeRequest(
        iid=1,
        project="group/project",
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


def test_filter_by_state_keeps_only_matching_state() -> None:
    opened = make_mr(MergeRequestState.OPENED)
    merged = make_mr(MergeRequestState.MERGED)

    result = filter_by_state([opened, merged], MergeRequestState.OPENED)

    assert result == [opened]


def test_filter_by_state_all_returns_every_mr() -> None:
    opened = make_mr(MergeRequestState.OPENED)
    merged = make_mr(MergeRequestState.MERGED)

    result = filter_by_state([opened, merged], MergeRequestState.ALL)

    assert result == [opened, merged]


def test_filter_by_author_matches_exact_username() -> None:
    mine = make_mr(author="octocat")
    theirs = make_mr(author="hubot")

    result = filter_by_author([mine, theirs], "octocat", current_username="hubot")

    assert result == [mine]


def test_filter_by_author_at_me_matches_the_authenticated_user() -> None:
    mine = make_mr(author="hubot")
    theirs = make_mr(author="octocat")

    result = filter_by_author([mine, theirs], "@me", current_username="hubot")

    assert result == [mine]


def test_filter_by_author_none_returns_every_mr() -> None:
    mine = make_mr(author="hubot")
    theirs = make_mr(author="octocat")

    result = filter_by_author([mine, theirs], None, current_username="hubot")

    assert result == [mine, theirs]


def test_filter_by_author_at_me_without_current_username_raises() -> None:
    with pytest.raises(ValueError, match="@me"):
        filter_by_author([make_mr()], "@me", current_username=None)


def test_filter_by_assignee_matches_exact_username() -> None:
    mine = make_mr(assignee="octocat")
    theirs = make_mr(assignee="hubot")

    result = filter_by_assignee([mine, theirs], "octocat", current_username="hubot")

    assert result == [mine]


def test_filter_by_assignee_at_me_matches_the_authenticated_user() -> None:
    mine = make_mr(assignee="hubot")
    theirs = make_mr(assignee="octocat")

    result = filter_by_assignee([mine, theirs], "@me", current_username="hubot")

    assert result == [mine]


def test_filter_by_assignee_none_returns_every_mr() -> None:
    mine = make_mr(assignee="hubot")
    theirs = make_mr(assignee="octocat")

    result = filter_by_assignee([mine, theirs], None, current_username="hubot")

    assert result == [mine, theirs]


def test_filter_by_labels_requires_every_listed_label() -> None:
    both = make_mr(labels=["bug", "urgent"])
    one = make_mr(labels=["bug"])

    result = filter_by_labels([both, one], ["bug", "urgent"])

    assert result == [both]


def test_filter_by_labels_empty_returns_every_mr() -> None:
    both = make_mr(labels=["bug", "urgent"])
    one = make_mr(labels=["bug"])

    result = filter_by_labels([both, one], [])

    assert result == [both, one]


def test_merge_request_defaults_approvals_and_line_stats_to_pending() -> None:
    mr = make_mr()

    assert mr.approvals == Pending()
    assert mr.line_stats == Pending()


def test_pending_instances_are_equal() -> None:
    assert Pending() == Pending()


def test_approvals_equality_and_construction() -> None:
    assert Approvals(given=1, required=2) == Approvals(given=1, required=2)
    assert Approvals(given=1, required=2) != Approvals(given=2, required=2)


def test_line_stats_equality_and_construction() -> None:
    assert LineStats(added=3, removed=4) == LineStats(added=3, removed=4)
    assert LineStats(added=3, removed=4) != LineStats(added=4, removed=4)


def test_failed_instances_are_equal() -> None:
    assert Failed() == Failed()
