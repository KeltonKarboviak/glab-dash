"""PROTOTYPE — throwaway, answers issue 12-warm-start-staleness-display-prototype.

Three variants of how a `Stale` (warm-cached, unconfirmed) approvals/line-stats
cell renders next to Pending (spinner), Failed, and confirmed/resolved cells,
so the four states stay visually distinguishable at a glance.

Press `v` to cycle variants.

Run: python -m glab_dash.infrastructure.tui.prototype_stale_cell
"""

from dataclasses import dataclass

from rich.text import Text
from textual.app import App, ComposeResult
from textual.coordinate import Coordinate
from textual.widgets import DataTable, Footer, Header

VARIANTS = ["A — dimmed/muted", "B — marker glyph (~)", "C — italic"]
SPINNER_FRAMES = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
FAILED_GLYPH = "⚠"


@dataclass(frozen=True)
class Pending:
    pass


@dataclass(frozen=True)
class Failed:
    pass


@dataclass(frozen=True)
class Stale:
    text: str


@dataclass(frozen=True)
class Resolved:
    text: str


Cell = Pending | Failed | Stale | Resolved

ROWS: list[tuple[str, Cell, Cell]] = [
    ("proj!101 fix retry bug", Resolved("2/2"), Resolved("+34/-12")),
    ("proj!102 add filter ui", Pending(), Pending()),
    ("proj!103 bump deps", Stale("0/1"), Pending()),
    ("proj!104 refactor gateway", Failed(), Stale("+210/-45")),
    ("proj!105 docs pass", Stale("1/1"), Resolved("+8/-3")),
]


def render_cell(value: Cell, variant: int, frame: str) -> Text | str:
    if isinstance(value, Resolved):
        return value.text
    if isinstance(value, Failed):
        return FAILED_GLYPH
    if isinstance(value, Pending):
        return frame
    if variant == 0:  # dimmed/muted
        return Text(value.text, style="dim")
    if variant == 1:  # marker glyph
        return f"~{value.text}"
    return Text(value.text, style="italic")  # variant 2: italic


class StaleCellPrototype(App):
    BINDINGS = [("v", "cycle_variant", "Cycle variant")]

    def __init__(self) -> None:
        super().__init__()
        self._variant = 0
        self._frame_index = 0

    def compose(self) -> ComposeResult:
        yield Header()
        yield DataTable(id="mrs")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one(DataTable)
        table.add_columns("Title", "Approvals", "Lines")
        self._render_rows(table)
        self.sub_title = VARIANTS[self._variant]
        self.set_interval(0.1, self._tick_spinner)

    def _render_rows(self, table: DataTable) -> None:
        table.clear()
        frame = SPINNER_FRAMES[self._frame_index]
        for title, approvals, line_stats in ROWS:
            table.add_row(
                title,
                render_cell(approvals, self._variant, frame),
                render_cell(line_stats, self._variant, frame),
            )

    def _tick_spinner(self) -> None:
        self._frame_index = (self._frame_index + 1) % len(SPINNER_FRAMES)
        frame = SPINNER_FRAMES[self._frame_index]
        table = self.query_one(DataTable)
        for row, (_, approvals, line_stats) in enumerate(ROWS):
            if isinstance(approvals, Pending):
                table.update_cell_at(Coordinate(row, 1), frame)
            if isinstance(line_stats, Pending):
                table.update_cell_at(Coordinate(row, 2), frame)

    def action_cycle_variant(self) -> None:
        self._variant = (self._variant + 1) % len(VARIANTS)
        self.sub_title = VARIANTS[self._variant]
        self._render_rows(self.query_one(DataTable))


if __name__ == "__main__":
    StaleCellPrototype().run()
