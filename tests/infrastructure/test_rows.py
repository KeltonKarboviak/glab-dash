from dataclasses import replace

from glab_dash.domain.config import MergeRequestState
from glab_dash.domain.merge_request import Approvals, Failed, LineStats, MergeRequest, Pending
from glab_dash.infrastructure.tui.rows import render_approvals, render_line_stats, render_mr_row


def _make_mr(**overrides: object) -> MergeRequest:
    mr = MergeRequest(
        iid=42,
        project="group/project",
        title="Add feature",
        author="kelton",
        source_branch="feature",
        target_branch="main",
        state=MergeRequestState.OPENED,
        web_url="https://gitlab.com/group/project/-/merge_requests/42",
        updated_at="2026-08-25T00:00:00Z",
        labels=["backend"],
    )
    return replace(mr, **overrides)


def test_render_mr_row_builds_extended_title_block() -> None:
    state_icon, extended_title, _labels, _updated_at = render_mr_row(_make_mr())

    assert state_icon == "●"
    assert extended_title == "group/project!42 by kelton\nfeature → main\nAdd feature"


def test_render_mr_row_joins_labels() -> None:
    _icon, _title, labels, _updated_at = render_mr_row(_make_mr(labels=["bug", "urgent"]))

    assert labels == "bug, urgent"


def test_render_mr_row_shows_dash_for_no_labels() -> None:
    _icon, _title, labels, _updated_at = render_mr_row(_make_mr(labels=[]))

    assert labels == "-"


def test_render_mr_row_passes_through_updated_at() -> None:
    _icon, _title, _labels, updated_at = render_mr_row(_make_mr(updated_at="2026-01-02T03:04:05Z"))

    assert updated_at == "2026-01-02T03:04:05Z"


def test_render_mr_row_maps_merged_and_closed_state_icons() -> None:
    merged_icon, *_ = render_mr_row(_make_mr(state=MergeRequestState.MERGED))
    closed_icon, *_ = render_mr_row(_make_mr(state=MergeRequestState.CLOSED))

    assert merged_icon == "✓"
    assert closed_icon == "✗"


def test_render_approvals_shows_spinner_frame_when_pending() -> None:
    assert render_approvals(Pending(), frame="⠹") == "⠹"


def test_render_approvals_shows_given_over_required_when_resolved() -> None:
    assert render_approvals(Approvals(given=2, required=2), frame="⠹") == "2/2"


def test_render_approvals_shows_fixed_glyph_when_failed() -> None:
    assert render_approvals(Failed(), frame="⠹") == "⚠"


def test_render_line_stats_shows_spinner_frame_when_pending() -> None:
    assert render_line_stats(Pending(), frame="⠹") == "⠹"


def test_render_line_stats_shows_added_and_removed_when_resolved() -> None:
    assert render_line_stats(LineStats(added=34, removed=12), frame="⠹") == "+34/-12"


def test_render_line_stats_shows_fixed_glyph_when_failed() -> None:
    assert render_line_stats(Failed(), frame="⠹") == "⚠"
