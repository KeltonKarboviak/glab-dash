from glab_dash.domain.config import Config, MergeRequestState, Scope, Section
from glab_dash.domain.merge_request import MergeRequest
from glab_dash.infrastructure.tui.app import GlabDashApp


class FakeGateway:
    def __init__(self, merge_requests: list[MergeRequest]) -> None:
        self._merge_requests = merge_requests

    def list_project_merge_requests(self, project: str) -> list[MergeRequest]:
        return self._merge_requests


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


async def test_project_section_renders_a_tab_with_its_title():
    config = Config(
        sections=[Section(title="My Project", scope=Scope.PROJECT, project="group/project")]
    )
    app = GlabDashApp(config, FakeGateway([_make_mr()]))

    async with app.run_test():
        tab = next(iter(app.query("Tab")))
        assert tab.label_text == "My Project"


async def test_project_section_table_lists_its_merge_requests():
    config = Config(
        sections=[Section(title="My Project", scope=Scope.PROJECT, project="group/project")]
    )
    app = GlabDashApp(config, FakeGateway([_make_mr(), _make_mr(iid=2)]))

    async with app.run_test() as pilot:
        await app.workers.wait_for_complete()
        await pilot.pause()
        table = app.query_one("#table-0")
        assert table.row_count == 2


async def test_sections_render_as_tabs_in_yaml_order():
    config = Config(
        sections=[
            Section(title="First", scope=Scope.PROJECT, project="group/a"),
            Section(title="Second", scope=Scope.PROJECT, project="group/b"),
        ]
    )
    app = GlabDashApp(config, FakeGateway([]))

    async with app.run_test():
        tab_titles = [tab.label_text for tab in app.query("Tab")]
        assert tab_titles == ["First", "Second"]
