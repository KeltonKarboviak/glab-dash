# 07 — Rendering: pending/resolved/failed cell formatting

**What to build:** Formatting functions for the Approvals and Lines table
cells that render a spinner while a value is `Pending`, the resolved value
once fetched, and a fixed error glyph if enrichment failed — so the table
can show live, per-cell loading state.

**Blocked by:** 05 — Domain model: Pending/Approvals/LineStats/Failed unions

**Status:** ready-for-agent

- [ ] `render_approvals(value: Pending | Approvals | Failed, frame: str) -> str`
      in `glab_dash/infrastructure/tui/rows.py`
- [ ] `render_line_stats(value: Pending | LineStats | Failed, frame: str) -> str`
      in the same module
- [ ] Both adapted from the loading-state prototype's variant-A functions
      (`prototype_pending_cell.py`, branch `prototype/pending-enrichment-loading-state`,
      commit `8628cfe`): `Pending` renders the given braille spinner frame
      (`⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏`); resolved renders formatted value (`"given/required"`,
      `"+added/-removed"`); `Failed` renders a fixed, non-animated glyph
      (e.g. `"⚠"`)
- [ ] `render_mr_row` unchanged — it never touched these two fields
- [ ] `tests/infrastructure/test_rows.py` covers all three states for both
      functions
