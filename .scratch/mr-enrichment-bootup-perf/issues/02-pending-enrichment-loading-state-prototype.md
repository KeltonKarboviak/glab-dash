Type: prototype
Status: resolved

## Question

What does a not-yet-enriched cell look like in the `DataTable` before its
enrichment chunk lands — a spinner glyph, a placeholder string (`"…"`,
`"-"`), or left blank until filled? Build a cheap, rough prototype of the
table with some rows enriched and some pending to react to; this is a "how
should it look" question, not one to settle by discussion.

Context: rendering lives in `src/glab_dash/infrastructure/tui/rows.py`
(cell formatting) and `src/glab_dash/infrastructure/tui/app.py` (`add_row`
at app.py:225). Resolve with `mattpocock-skills:prototype`.

## Answer

Animated spinner (Variant A) — a braille frame (`⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏`) cycled every
100ms via `set_interval` + `DataTable.update_cell_at`, ticking only cells
whose value is still `Pending`. Beat the static placeholder (`"…"`) and
blank variants on liveness — it visibly communicates "still fetching"
rather than looking like a fixed empty state.

Implementation note for whoever wires this into the real table: only the
per-section enrichment worker's target rows need a ticking interval: once a
row's `approvals`/`line_stats` resolves out of `Pending`, stop animating
that cell (no interval to cancel per-cell — the tick handler in the
prototype already no-ops once the value isn't `Pending`, so the same guard
carries over).

Prototype (3 variants, throwaway): `prototype/pending-enrichment-loading-state`
branch, commit `8628cfe` —
`src/glab_dash/infrastructure/tui/prototype_pending_cell.py`.
