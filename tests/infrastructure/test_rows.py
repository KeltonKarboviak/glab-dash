from glab_dash.domain.config import MergeRequestState
from glab_dash.domain.merge_request import MergeRequest
from glab_dash.infrastructure.tui.rows import render_mr_row


def _make_mr(**overrides) -> MergeRequest:
    defaults = dict(
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
    defaults.update(overrides)
    return MergeRequest(**defaults)


def test_render_mr_row_builds_extended_title_block():
    state_icon, extended_title, _labels, _updated_at = render_mr_row(_make_mr())

    assert state_icon == "●"
    assert extended_title == "group/project!42 by kelton\nfeature → main\nAdd feature"


def test_render_mr_row_joins_labels():
    _icon, _title, labels, _updated_at = render_mr_row(_make_mr(labels=["bug", "urgent"]))

    assert labels == "bug, urgent"


def test_render_mr_row_shows_dash_for_no_labels():
    _icon, _title, labels, _updated_at = render_mr_row(_make_mr(labels=[]))

    assert labels == "-"


def test_render_mr_row_passes_through_updated_at():
    _icon, _title, _labels, updated_at = render_mr_row(_make_mr(updated_at="2026-01-02T03:04:05Z"))

    assert updated_at == "2026-01-02T03:04:05Z"


def test_render_mr_row_maps_merged_and_closed_state_icons():
    merged_icon, *_ = render_mr_row(_make_mr(state=MergeRequestState.MERGED))
    closed_icon, *_ = render_mr_row(_make_mr(state=MergeRequestState.CLOSED))

    assert merged_icon == "✓"
    assert closed_icon == "✗"
