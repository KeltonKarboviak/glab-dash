"""Textual App shell: one tab per configured section, project tabs list MRs."""

from functools import partial

from textual.app import App, ComposeResult
from textual.widgets import DataTable, Footer, Header, TabbedContent, TabPane
from textual.worker import Worker, WorkerState

from glab_dash.application.list_merge_requests import (
    MergeRequestGateway,
    list_merge_requests_for_section,
)
from glab_dash.domain.config import Config, Scope, Section
from glab_dash.domain.merge_request import MergeRequest
from glab_dash.infrastructure.config import load_config, resolve_config_path
from glab_dash.infrastructure.credentials import resolve_gitlab_token
from glab_dash.infrastructure.gitlab_gateway import (
    GITLAB_COM_URL,
    GitlabMergeRequestGateway,
    build_gitlab_client,
)
from glab_dash.infrastructure.tui.rows import MR_ROW_HEIGHT, render_mr_row


def _fetch_section_merge_requests(
    gateway: MergeRequestGateway, section: Section
) -> list[MergeRequest]:
    return list_merge_requests_for_section(gateway, section)


class GlabDashApp(App):
    def __init__(self, config: Config, gateway: MergeRequestGateway) -> None:
        super().__init__()
        self._config = config
        self._gateway = gateway
        self._tables_by_worker_name: dict[str, DataTable] = {}

    def compose(self) -> ComposeResult:
        yield Header()
        with TabbedContent():
            for index, section in enumerate(self._config.sections):
                with TabPane(section.title, id=f"section-{index}"):
                    yield DataTable(id=f"table-{index}")
        yield Footer()

    def on_mount(self) -> None:
        for index, section in enumerate(self._config.sections):
            table = self.query_one(f"#table-{index}", DataTable)
            table.add_columns("", "Merge Request", "Labels", "Updated")
            if section.scope is Scope.PROJECT:
                worker_name = f"section-{index}"
                self._tables_by_worker_name[worker_name] = table
                self.run_worker(
                    partial(_fetch_section_merge_requests, self._gateway, section),
                    name=worker_name,
                    thread=True,
                )

    def on_worker_state_changed(self, event: Worker.StateChanged) -> None:
        if event.state is not WorkerState.SUCCESS:
            return
        table = self._tables_by_worker_name.get(event.worker.name)
        if table is None:
            return
        for mr in event.worker.result:
            state_icon, extended_title, labels, updated_at = render_mr_row(mr)
            table.add_row(state_icon, extended_title, labels, updated_at, height=MR_ROW_HEIGHT)


def run() -> None:
    config = load_config(resolve_config_path())
    token = resolve_gitlab_token({"token": config.token})
    client = build_gitlab_client(token, GITLAB_COM_URL)
    GlabDashApp(config, GitlabMergeRequestGateway(client)).run()


if __name__ == "__main__":
    run()
