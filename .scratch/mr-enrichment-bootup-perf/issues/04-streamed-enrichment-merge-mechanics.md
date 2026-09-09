Type: grilling
Status: resolved

## Question

With `MergeRequest.approvals: Pending | Approvals` and
`MergeRequest.line_stats: Pending | LineStats` settled
([Pending-enrichment domain model](01-pending-enrichment-domain-model.md)),
what's the exact mechanism for merging a streamed enrichment result into an
already-rendered row?

Needs to answer:
- Row identity: `DataTable.add_row` at `app.py:225` passes no `key=` today.
  What key (e.g. `f"{mr.project}#{mr.iid}"`) gets added, and does the
  in-memory MR list/lookup also need to be keyed the same way so the
  enrichment worker can find the row to update?
- Update granularity: `approvals` and `line_stats` arrive independently
  (per Pending-enrichment domain model's answer) — does each land as its
  own `table.update_cell` call per column, or does a row-level refresh
  re-render both columns whenever either arrives?
- Cell rendering: how does a `Pending` value render in the table (e.g. a
  placeholder string like `"…"`) versus an `Approvals`/`LineStats` value?
- Which worker writes the update: the per-section enrichment worker
  described in the map's Decisions-so-far, using the existing
  `Worker.StateChanged`/`_tables_by_worker_name` pattern in `app.py`.

Scope: mechanics only — the fetch/chunking strategy that produces
`Approvals`/`LineStats` values is a separate concern already decided
(map's Decisions-so-far).

## Answer

**Row identity.** Add `key=f"{mr.project}#{mr.iid}"` to `table.add_row`
(`app.py:225`). Replace `_merge_requests_by_table_id: dict[str,
list[MergeRequest]]` with `dict[str, dict[str, MergeRequest]]` (table id →
row key → `MergeRequest`), so the enrichment worker can look up a row by
key in O(1) instead of a linear scan.

**Enrichment fetch shape.** Add a new gateway method,
`enrich_merge_request(project, iid) -> tuple[Approvals, LineStats]`, that
does what `_approvals`/`_line_stats` (`gitlab_gateway.py:41-65`) already do
per-MR today. The enrichment worker owns the batching: it loops over its
section's MR list one at a time and calls this method per MR — chunking
stays a worker-side concern, not a gateway concern.

**Streaming delivery.** Because `Worker.StateChanged` only fires once, on
completion, the enrichment worker (a `thread=True` worker) calls
`self.call_from_thread(self._update_enriched_row, ...)` after each MR's
fetch completes, not after the whole loop. `on_worker_state_changed` still
fires once at SUCCESS, used only to know the section's enrichment pass
finished (nothing to clean up beyond that — the spinner interval already
no-ops on non-`Pending` cells).

**Update granularity.** `_update_enriched_row` makes two independent
`table.update_cell(row_key, "Approvals", ...)` /
`table.update_cell(row_key, "Lines", ...)` calls — whichever of
Approvals/LineStats resolves first updates immediately, matching the map's
locked decision that the two fields update independently.

**New columns.** `table.add_columns` (`app.py:82`) gains `"Approvals"` and
`"Lines"`. `render_approvals(value: Pending | Approvals, frame: str) -> str`
and `render_line_stats(value: Pending | LineStats, frame: str) -> str`
(adapted from the loading-state prototype's variant-A functions) move into
`rows.py`, alongside `render_mr_row`.

**Spinner ownership.** One global app-level `set_interval` (started once in
`on_mount`, alongside `_refresh_all_sections`'s interval) sweeps every
mounted table's rows each tick, calling `update_cell_at` only on cells
still holding `Pending` — no per-section interval lifecycle to track.

**Triggering.** In `on_worker_state_changed`, right after a section's
first-paint worker (`section-{index}`) reaches SUCCESS and its rows are
added, start `self.run_worker(partial(_enrich_section, ...),
name=f"section-{index}-enrich", thread=True)`.

**Refresh interaction.** The enrichment worker's per-MR loop checks
`_quit_requested()` (the same cancellation pattern
`_fetch_section_merge_requests` already uses) each iteration. Reusing the
exact worker name `f"section-{index}-enrich"` on every refresh is
sufficient for Textual to auto-cancel the prior cycle's enrich worker when
a new one starts — no manual `cancel_group`/`cancel_all` call needed.

Domain-modeling pass: `Pending`, `Approvals`, and `Line stats` (renamed from
"LineStats" for glossary prose) added to `CONTEXT.md` as real domain value
types, locked by the pending-enrichment-domain-model ticket but missing
from the glossary until now. Row keys and worker-naming stay out of the
glossary — pure implementation identity, not domain vocabulary.
