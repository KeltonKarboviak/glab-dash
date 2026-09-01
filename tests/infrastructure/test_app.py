from typing import cast

import pytest
from rich.text import Text
from textual.timer import Timer, TimerCallback
from textual.widgets import DataTable, Static, Tab, TabbedContent

from glab_dash.domain.config import Config, MergeRequestState, Scope, Section
from glab_dash.domain.merge_request import (
    Discussion,
    DiscussionNote,
    MergeRequest,
    MergeRequestDetail,
    SectionNotFoundError,
)
from glab_dash.infrastructure.tui.app import GlabDashApp


class FakeGateway:
    def __init__(
        self,
        merge_requests: list[MergeRequest],
        detail: MergeRequestDetail | None = None,
    ) -> None:
        self._merge_requests = merge_requests
        self._detail = detail or MergeRequestDetail(description="", discussions=[], diff="")
        self.project_list_calls = 0

    def list_project_merge_requests(self, project: str) -> list[MergeRequest]:
        self.project_list_calls += 1
        return self._merge_requests

    def list_group_merge_requests(self, group: str) -> list[MergeRequest]:
        return self._merge_requests

    def list_global_merge_requests(self) -> list[MergeRequest]:
        return self._merge_requests

    def get_merge_request_detail(self, project: str, iid: int) -> MergeRequestDetail:
        return self._detail


class FailingGateway:
    def list_project_merge_requests(self, project: str) -> list[MergeRequest]:
        raise SectionNotFoundError(f"project '{project}' not found")

    def list_group_merge_requests(self, group: str) -> list[MergeRequest]:
        raise SectionNotFoundError(f"group '{group}' not found")

    def list_global_merge_requests(self) -> list[MergeRequest]:
        return []

    def get_merge_request_detail(self, project: str, iid: int) -> MergeRequestDetail:
        raise AssertionError("not used in these tests")


def _make_mr(iid: int = 1) -> MergeRequest:
    return MergeRequest(
        iid=iid,
        project="group/project",
        title="Add feature",
        author="kelton",
        source_branch="feature",
        target_branch="main",
        state=MergeRequestState.OPENED,
        web_url="https://gitlab.com/group/project/-/merge_requests/1",
        updated_at="2026-08-25T00:00:00Z",
        labels=["backend"],
    )


async def test_project_section_renders_a_tab_with_its_title() -> None:
    config = Config(
        sections=[Section(title="My Project", scope=Scope.PROJECT, project="group/project")]
    )
    app = GlabDashApp(config, FakeGateway([_make_mr()]))

    async with app.run_test():
        tab = next(iter(app.query(Tab)))
        assert tab.label_text == "My Project"


async def test_group_not_found_renders_an_error_row_instead_of_crashing() -> None:
    config = Config(sections=[Section(title="Bad Group", scope=Scope.GROUP, group="data-platform")])
    app = GlabDashApp(config, FailingGateway())

    async with app.run_test() as pilot:
        await app.workers.wait_for_complete()
        await pilot.pause()
        table = app.query_one("#table-0", DataTable)
        assert table.row_count == 1
        row = table.get_row_at(0)
        assert "data-platform" in str(row[1])
        assert "not found" in str(row[1])


async def test_project_section_table_lists_its_merge_requests() -> None:
    config = Config(
        sections=[Section(title="My Project", scope=Scope.PROJECT, project="group/project")]
    )
    app = GlabDashApp(config, FakeGateway([_make_mr(), _make_mr(iid=2)]))

    async with app.run_test() as pilot:
        await app.workers.wait_for_complete()
        await pilot.pause()
        table = app.query_one("#table-0", DataTable)
        assert table.row_count == 2


async def test_group_and_global_sections_also_fetch_and_list_merge_requests() -> None:
    config = Config(
        sections=[
            Section(title="Group", scope=Scope.GROUP, group="ramsey-solutions/data-platform"),
            Section(title="Global", scope=Scope.GLOBAL),
        ]
    )
    app = GlabDashApp(config, FakeGateway([_make_mr(), _make_mr(iid=2)]))

    async with app.run_test() as pilot:
        await app.workers.wait_for_complete()
        await pilot.pause()
        assert app.query_one("#table-0", DataTable).row_count == 2
        assert app.query_one("#table-1", DataTable).row_count == 2


async def test_sections_render_as_tabs_in_yaml_order() -> None:
    config = Config(
        sections=[
            Section(title="First", scope=Scope.PROJECT, project="group/a"),
            Section(title="Second", scope=Scope.PROJECT, project="group/b"),
        ]
    )
    app = GlabDashApp(config, FakeGateway([]))

    async with app.run_test():
        tab_titles = [tab.label_text for tab in app.query(Tab)]
        assert tab_titles == ["First", "Second"]


async def test_j_and_k_move_the_row_cursor_within_the_active_section() -> None:
    config = Config(
        sections=[Section(title="My Project", scope=Scope.PROJECT, project="group/project")]
    )
    app = GlabDashApp(config, FakeGateway([_make_mr(), _make_mr(iid=2), _make_mr(iid=3)]))

    async with app.run_test() as pilot:
        await app.workers.wait_for_complete()
        await pilot.pause()
        table = app.query_one("#table-0", DataTable)

        await pilot.press("j", "j")
        assert table.cursor_row == 2

        await pilot.press("k")
        assert table.cursor_row == 1


async def test_g_and_shift_g_jump_to_first_and_last_row() -> None:
    config = Config(
        sections=[Section(title="My Project", scope=Scope.PROJECT, project="group/project")]
    )
    app = GlabDashApp(config, FakeGateway([_make_mr(), _make_mr(iid=2), _make_mr(iid=3)]))

    async with app.run_test() as pilot:
        await app.workers.wait_for_complete()
        await pilot.pause()
        table = app.query_one("#table-0", DataTable)

        await pilot.press("G")
        assert table.cursor_row == 2

        await pilot.press("g")
        assert table.cursor_row == 0


async def test_brackets_switch_the_active_section_tab_and_clamp_at_the_ends() -> None:
    config = Config(
        sections=[
            Section(title="First", scope=Scope.PROJECT, project="group/a"),
            Section(title="Second", scope=Scope.PROJECT, project="group/b"),
        ]
    )
    app = GlabDashApp(config, FakeGateway([]))

    async with app.run_test() as pilot:
        await app.workers.wait_for_complete()
        await pilot.pause()

        await pilot.press("[")
        assert app.query_one(TabbedContent).active == "section-0"

        await pilot.press("]", "]")
        assert app.query_one(TabbedContent).active == "section-1"


async def test_tab_toggles_the_preview_pane_and_loads_the_selected_mrs_detail() -> None:
    config = Config(
        sections=[Section(title="My Project", scope=Scope.PROJECT, project="group/project")]
    )
    detail = MergeRequestDetail(
        description="Fixes the thing",
        discussions=[Discussion(notes=[DiscussionNote(author="octocat", body="Looks good")])],
        diff="+new line\n",
    )
    app = GlabDashApp(config, FakeGateway([_make_mr()], detail=detail))

    async with app.run_test() as pilot:
        await app.workers.wait_for_complete()
        await pilot.pause()

        assert app.query_one("#preview-pane").display is False

        await pilot.press("tab")
        await app.workers.wait_for_complete()
        await pilot.pause()

        assert app.query_one("#preview-pane").display is True
        rendered = cast(Text, app.query_one("#preview-content", Static).content).plain
        assert "Fixes the thing" in rendered
        assert "octocat" in rendered
        assert "Looks good" in rendered
        assert "+new line" in rendered

        await pilot.press("tab")
        assert app.query_one("#preview-pane").display is False


async def test_enter_focuses_the_preview_pane_so_j_k_scroll_it_not_the_list() -> None:
    config = Config(
        sections=[Section(title="My Project", scope=Scope.PROJECT, project="group/project")]
    )
    app = GlabDashApp(config, FakeGateway([_make_mr(), _make_mr(iid=2)]))

    async with app.run_test() as pilot:
        await app.workers.wait_for_complete()
        await pilot.pause()

        await pilot.press("tab")
        await app.workers.wait_for_complete()
        await pilot.pause()
        await pilot.press("enter")

        table = app.query_one("#table-0", DataTable)
        await pilot.press("j")
        assert table.cursor_row == 0


async def test_escape_returns_focus_to_the_list_so_j_k_move_the_cursor_again() -> None:
    config = Config(
        sections=[Section(title="My Project", scope=Scope.PROJECT, project="group/project")]
    )
    app = GlabDashApp(config, FakeGateway([_make_mr(), _make_mr(iid=2)]))

    async with app.run_test() as pilot:
        await app.workers.wait_for_complete()
        await pilot.pause()

        await pilot.press("tab")
        await app.workers.wait_for_complete()
        await pilot.pause()
        await pilot.press("enter")
        await pilot.press("escape")

        table = app.query_one("#table-0", DataTable)
        await pilot.press("j")
        assert table.cursor_row == 1


async def test_r_triggers_an_immediate_refresh_through_the_fetch_path() -> None:
    config = Config(
        sections=[Section(title="My Project", scope=Scope.PROJECT, project="group/project")]
    )
    gateway = FakeGateway([_make_mr()])
    app = GlabDashApp(config, gateway)

    async with app.run_test() as pilot:
        await app.workers.wait_for_complete()
        await pilot.pause()
        assert gateway.project_list_calls == 1

        await pilot.press("r")
        await app.workers.wait_for_complete()
        await pilot.pause()

        assert gateway.project_list_calls == 2


async def test_refresh_preserves_the_active_tab_and_cursor_position() -> None:
    config = Config(
        sections=[
            Section(title="First", scope=Scope.PROJECT, project="group/a"),
            Section(title="Second", scope=Scope.PROJECT, project="group/b"),
        ]
    )
    gateway = FakeGateway([_make_mr(), _make_mr(iid=2), _make_mr(iid=3)])
    app = GlabDashApp(config, gateway)

    async with app.run_test() as pilot:
        await app.workers.wait_for_complete()
        await pilot.pause()

        await pilot.press("]")
        table = app.query_one("#table-1", DataTable)
        await pilot.press("j")
        assert table.cursor_row == 1

        await pilot.press("r")
        await app.workers.wait_for_complete()
        await pilot.pause()

        assert app.query_one(TabbedContent).active == "section-1"
        assert table.cursor_row == 1
        assert table.row_count == 3


async def test_refresh_runs_through_run_worker_without_blocking(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = Config(
        sections=[Section(title="My Project", scope=Scope.PROJECT, project="group/project")]
    )
    app = GlabDashApp(config, FakeGateway([_make_mr()]))

    async with app.run_test() as pilot:
        await app.workers.wait_for_complete()
        await pilot.pause()

        calls = []
        original_run_worker = app.run_worker

        def tracking_run_worker(*args, **kwargs):
            calls.append(kwargs.get("thread"))
            return original_run_worker(*args, **kwargs)

        monkeypatch.setattr(app, "run_worker", tracking_run_worker)

        await pilot.press("r")
        await app.workers.wait_for_complete()
        await pilot.pause()

        assert calls == [True]


async def test_automatic_refresh_is_scheduled_at_the_configured_interval(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = Config(
        sections=[Section(title="My Project", scope=Scope.PROJECT, project="group/project")],
        refresh_interval=42,
    )
    app = GlabDashApp(config, FakeGateway([]))

    intervals = []
    original_set_interval = app.set_interval

    def tracking_set_interval(seconds: float, callback: TimerCallback | None = None) -> Timer:
        intervals.append(seconds)
        return original_set_interval(seconds, callback)

    monkeypatch.setattr(app, "set_interval", tracking_set_interval)

    async with app.run_test():
        assert 42 in intervals


async def test_q_quits_the_app() -> None:
    config = Config(
        sections=[Section(title="My Project", scope=Scope.PROJECT, project="group/project")]
    )
    app = GlabDashApp(config, FakeGateway([]))

    async with app.run_test() as pilot:
        await pilot.press("q")
        assert app.is_running is False


async def test_question_mark_toggles_the_help_panel() -> None:
    config = Config(
        sections=[Section(title="My Project", scope=Scope.PROJECT, project="group/project")]
    )
    app = GlabDashApp(config, FakeGateway([]))

    async with app.run_test() as pilot:
        await pilot.press("?")
        await pilot.pause()
        assert app.screen.query("HelpPanel")

        await pilot.press("?")
        await pilot.pause()
        assert not app.screen.query("HelpPanel")
