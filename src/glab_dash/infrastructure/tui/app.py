"""Textual App shell: one tab per configured section, project tabs list MRs."""

from functools import partial

import structlog
from rich.text import Text
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import VerticalScroll
from textual.widgets import DataTable, Footer, Header, Static, TabbedContent, TabPane
from textual.worker import Worker, WorkerState

from glab_dash.application.list_merge_requests import (
    MergeRequestGateway,
    list_merge_requests_for_section,
)
from glab_dash.domain.config import Config, ConfigError, Section
from glab_dash.domain.merge_request import MergeRequest, MergeRequestDetail
from glab_dash.infrastructure.config import load_config, resolve_config_path
from glab_dash.infrastructure.credentials import resolve_gitlab_token
from glab_dash.infrastructure.gitlab_gateway import (
    GITLAB_COM_URL,
    GitlabMergeRequestGateway,
    build_gitlab_client,
)
from glab_dash.infrastructure.logging import configure_logging
from glab_dash.infrastructure.tui.diff import colorize_diff
from glab_dash.infrastructure.tui.rows import MR_ROW_HEIGHT, render_mr_row

PREVIEW_WORKER_NAME = "preview-detail"

log = structlog.get_logger(__name__)


def _fetch_section_merge_requests(
    gateway: MergeRequestGateway, section: Section
) -> list[MergeRequest]:
    return list_merge_requests_for_section(gateway, section)


class GlabDashApp(App):
    BINDINGS = [
        Binding("j", "cursor_down", "Down", show=False),
        Binding("k", "cursor_up", "Up", show=False),
        Binding("g", "cursor_top", "Top", show=False),
        Binding("G", "cursor_bottom", "Bottom", show=False),
        Binding("[", "previous_tab", "Prev tab", show=False),
        Binding("]", "next_tab", "Next tab", show=False),
        Binding("tab", "toggle_preview", "Preview", show=False, priority=True),
        Binding("enter", "focus_preview", "Focus preview", show=False, priority=True),
        Binding("escape", "unfocus_preview", "Back to list", show=False, priority=True),
        Binding("r", "refresh", "Refresh", show=False),
        Binding("?", "toggle_help_panel", "Help", show=False),
        Binding("q", "quit", "Quit", show=False),
        Binding("ctrl+c", "quit", "Quit", show=False, priority=True),
    ]

    def __init__(self, config: Config, gateway: MergeRequestGateway) -> None:
        super().__init__()
        self._config = config
        self._gateway = gateway
        self._tables_by_worker_name: dict[str, DataTable] = {}
        self._sections_by_worker_name: dict[str, Section] = {}
        self._merge_requests_by_table_id: dict[str, list[MergeRequest]] = {}
        self._preview_visible = False
        self._preview_focused = False

    def compose(self) -> ComposeResult:
        yield Header()
        with TabbedContent():
            for index, section in enumerate(self._config.sections):
                with TabPane(section.title, id=f"section-{index}"):
                    yield DataTable(id=f"table-{index}")
        with VerticalScroll(id="preview-pane"):
            yield Static(id="preview-content")
        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#preview-pane").display = False
        for index, section in enumerate(self._config.sections):
            table = self.query_one(f"#table-{index}", DataTable)
            table.add_columns("", "Merge Request", "Labels", "Updated")
            worker_name = f"section-{index}"
            self._tables_by_worker_name[worker_name] = table
            self._sections_by_worker_name[worker_name] = section
            self._fetch_section(worker_name, section)
        self.set_interval(self._config.refresh_interval, self._refresh_all_sections)
        log.info("tui mounted", section_count=len(self._config.sections))

    def _fetch_section(self, worker_name: str, section: Section) -> None:
        self.run_worker(
            partial(_fetch_section_merge_requests, self._gateway, section),
            name=worker_name,
            thread=True,
        )

    def _refresh_all_sections(self) -> None:
        for worker_name, section in self._sections_by_worker_name.items():
            self._fetch_section(worker_name, section)

    def action_refresh(self) -> None:
        self._refresh_all_sections()

    def _active_table(self) -> DataTable | None:
        tabbed_content = self.query_one(TabbedContent)
        pane = tabbed_content.active_pane
        if pane is None:
            return None
        return pane.query_one(DataTable)

    def action_cursor_down(self) -> None:
        if self._preview_focused:
            self.query_one("#preview-pane").scroll_down()
        elif (table := self._active_table()) is not None:
            table.action_cursor_down()

    def action_cursor_up(self) -> None:
        if self._preview_focused:
            self.query_one("#preview-pane").scroll_up()
        elif (table := self._active_table()) is not None:
            table.action_cursor_up()

    def action_cursor_top(self) -> None:
        if self._preview_focused:
            self.query_one("#preview-pane").scroll_home()
        elif (table := self._active_table()) is not None:
            table.action_scroll_top()

    def action_cursor_bottom(self) -> None:
        if self._preview_focused:
            self.query_one("#preview-pane").scroll_end()
        elif (table := self._active_table()) is not None:
            table.action_scroll_bottom()

    def action_previous_tab(self) -> None:
        self._switch_tab(-1)

    def action_next_tab(self) -> None:
        self._switch_tab(1)

    def action_toggle_preview(self) -> None:
        self._preview_visible = not self._preview_visible
        self.query_one("#preview-pane").display = self._preview_visible
        if self._preview_visible:
            self._load_preview()
        else:
            self._preview_focused = False

    def action_focus_preview(self) -> None:
        if self._preview_visible:
            self._preview_focused = True

    def action_unfocus_preview(self) -> None:
        self._preview_focused = False

    def action_toggle_help_panel(self) -> None:
        if self.screen.query("HelpPanel"):
            self.action_hide_help_panel()
        else:
            self.action_show_help_panel()

    def _selected_merge_request(self) -> MergeRequest | None:
        table = self._active_table()
        if table is None or table.row_count == 0 or table.id is None:
            return None
        merge_requests = self._merge_requests_by_table_id.get(table.id, [])
        if table.cursor_row >= len(merge_requests):
            return None
        return merge_requests[table.cursor_row]

    def _load_preview(self) -> None:
        merge_request = self._selected_merge_request()
        if merge_request is None:
            return
        self.run_worker(
            partial(
                self._gateway.get_merge_request_detail,
                merge_request.project,
                merge_request.iid,
            ),
            name=PREVIEW_WORKER_NAME,
            thread=True,
        )

    def _render_preview(self, detail: MergeRequestDetail) -> None:
        text = Text(detail.description or "(no description)")
        text.append("\n\n")
        for discussion in detail.discussions:
            for note in discussion.notes:
                text.append(f"{note.author}: ", style="bold")
                text.append(f"{note.body}\n")
            text.append("\n")
        text.append(colorize_diff(detail.diff))
        self.query_one("#preview-content", Static).update(text)

    def _switch_tab(self, offset: int) -> None:
        section_count = len(self._config.sections)
        tabbed_content = self.query_one(TabbedContent)
        current_index = int(tabbed_content.active.removeprefix("section-"))
        new_index = max(0, min(section_count - 1, current_index + offset))
        tabbed_content.active = f"section-{new_index}"

    def on_worker_state_changed(self, event: Worker.StateChanged) -> None:
        if event.state is not WorkerState.SUCCESS:
            return
        if event.worker.name == PREVIEW_WORKER_NAME:
            detail = event.worker.result
            assert detail is not None, "SUCCESS worker must have a result"
            self._render_preview(detail)
            return
        table = self._tables_by_worker_name.get(event.worker.name)
        if table is None:
            return
        previous_cursor_row = table.cursor_row
        merge_requests = event.worker.result
        assert merge_requests is not None, "SUCCESS worker must have a result"
        self._merge_requests_by_table_id[table.id] = merge_requests
        table.clear()
        for mr in merge_requests:
            state_icon, extended_title, labels, updated_at = render_mr_row(mr)
            table.add_row(state_icon, extended_title, labels, updated_at, height=MR_ROW_HEIGHT)
        if table.row_count:
            table.move_cursor(row=min(previous_cursor_row, table.row_count - 1))


def run() -> None:
    configure_logging()
    config = load_config(resolve_config_path())
    token = resolve_gitlab_token({"token": config.token})
    if token is None:
        raise ConfigError("no GitLab token found: set it in config, GITLAB_TOKEN, or glab CLI")
    client = build_gitlab_client(token, GITLAB_COM_URL)
    GlabDashApp(config, GitlabMergeRequestGateway(client)).run()


if __name__ == "__main__":
    run()
