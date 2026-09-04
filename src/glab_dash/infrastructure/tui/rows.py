"""Formats a Domain MergeRequest into DataTable cell values."""

from glab_dash.domain.config import MergeRequestState
from glab_dash.domain.merge_request import MergeRequest

MR_ROW_HEIGHT = 4

_STATE_ICONS: dict[MergeRequestState, str] = {
    MergeRequestState.OPENED: "●",
    MergeRequestState.MERGED: "✓",
    MergeRequestState.CLOSED: "✗",
    MergeRequestState.ALL: "?",
}


def render_mr_row(mr: MergeRequest) -> tuple[str, str, str, str]:
    """Return (state icon, extended-title block, labels, updated-at) cells."""
    diff_size = f"+{mr.lines_added}/-{mr.lines_removed}"
    approvals = f"{mr.approvals_given}/{mr.approvals_required} approved"
    extended_title = (
        f"{mr.project}!{mr.iid} by {mr.author}\n"
        f"{mr.source_branch} → {mr.target_branch}\n"
        f"{mr.title}\n"
        f"{diff_size} · {approvals}"
    )
    labels = ", ".join(mr.labels) if mr.labels else "-"
    return _STATE_ICONS[mr.state], extended_title, labels, mr.updated_at
