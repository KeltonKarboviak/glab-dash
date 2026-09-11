"""Formats a Domain MergeRequest into DataTable cell values."""

from glab_dash.domain.config import MergeRequestState
from glab_dash.domain.merge_request import Approvals, Failed, LineStats, MergeRequest, Pending

MR_ROW_HEIGHT = 3

FAILED_GLYPH = "⚠"

_STATE_ICONS: dict[MergeRequestState, str] = {
    MergeRequestState.OPENED: "●",
    MergeRequestState.MERGED: "✓",
    MergeRequestState.CLOSED: "✗",
    MergeRequestState.ALL: "?",
}


def render_mr_row(mr: MergeRequest) -> tuple[str, str, str, str]:
    """Return (state icon, extended-title block, labels, updated-at) cells."""
    extended_title = (
        f"{mr.project}!{mr.iid} by {mr.author}\n{mr.source_branch} → {mr.target_branch}\n{mr.title}"
    )
    labels = ", ".join(mr.labels) if mr.labels else "-"
    return _STATE_ICONS[mr.state], extended_title, labels, mr.updated_at


def render_approvals(value: Pending | Approvals | Failed, frame: str) -> str:
    """Render a spinner frame while pending, "given/required" once resolved, or an error glyph."""
    if isinstance(value, Approvals):
        return f"{value.given}/{value.required}"
    if isinstance(value, Failed):
        return FAILED_GLYPH
    return frame


def format_line_stats(value: LineStats) -> str:
    """Render a detail view's line stats as "+added/-removed"."""
    return f"+{value.added}/-{value.removed}"
