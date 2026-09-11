"""Visual regression tests via pytest-textual-snapshot.

Catches layout bugs (e.g. a widget rendering off-screen) that behavioral
assertions on `display`/region values can miss.
"""

from textual.pilot import Pilot

from glab_dash.domain.config import Config, MergeRequestState, Scope, Section
from glab_dash.domain.merge_request import Discussion, DiscussionNote, LineStats, MergeRequest, MergeRequestDetail
from glab_dash.infrastructure.tui.app import GlabDashApp

from .test_app import FakeGateway, _make_mr


def _build_app(merge_requests: list[MergeRequest], detail: MergeRequestDetail | None = None) -> GlabDashApp:
    config = Config(
        sections=[Section(title="My Project", scope=Scope.PROJECT, project="group/project")]
    )
    return GlabDashApp(config, FakeGateway(merge_requests, detail=detail))


async def _wait_for_workers(pilot: Pilot) -> None:
    await pilot.app.workers.wait_for_complete()
    await pilot.pause()


def test_mr_list_snapshot(snap_compare) -> None:
    app = _build_app([_make_mr(iid=i) for i in range(1, 4)])
    assert snap_compare(app, run_before=_wait_for_workers)


def test_preview_pane_open_snapshot(snap_compare) -> None:
    detail = MergeRequestDetail(
        description="Fixes the thing",
        discussions=[Discussion(notes=[DiscussionNote(author="octocat", body="Looks good")])],
        diff="+new line\n",
        line_stats=LineStats(added=3, removed=1),
    )
    app = _build_app([_make_mr()], detail=detail)
    assert snap_compare(app, press=["tab"], run_before=_wait_for_workers)


def test_overflowing_mr_list_snapshot(snap_compare) -> None:
    app = _build_app([_make_mr(iid=i) for i in range(1, 31)])
    assert snap_compare(app, press=["tab"], run_before=_wait_for_workers, terminal_size=(80, 24))
