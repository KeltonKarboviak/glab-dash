# 08 — App wiring: columns, row keys, first enrichment pass

**What to build:** After a section's MR list paints, its rows show an
animated pending spinner in new Approvals/Lines columns, then each row's
cells fill in independently and live as that MR's enrichment data arrives —
demoable end to end: open a section, watch rows paint fast, watch cells fill
in one at a time.

**Blocked by:** 06 — Gateway: enrich_merge_request, 07 — Rendering:
pending/resolved/failed cell formatting

**Status:** ready-for-agent

- [ ] `table.add_row` calls gain `key=f"{mr.project}#{mr.iid}"`
- [ ] `_merge_requests_by_table_id: dict[str, list[MergeRequest]]` becomes
      `dict[str, dict[str, MergeRequest]]` (table id → row key → MergeRequest);
      `_selected_merge_request` and other readers updated so cursor-row-to-MR
      lookup keeps its existing user-visible behavior
- [ ] `table.add_columns` gains `"Approvals"` and `"Lines"`
- [ ] On a first-paint worker's `SUCCESS` (`on_worker_state_changed`, after
      rows are added), start a per-section enrichment worker via
      `self.run_worker(partial(_enrich_section, ...), name=f"section-{index}-enrich", thread=True)`
- [ ] Enrichment worker loops over its section's MR list one MR at a time,
      checking `_quit_requested()` each iteration (mirrors
      `_fetch_section_merge_requests`'s cancellation pattern), calling
      `gateway.enrich_merge_request(mr.project, mr.iid)` per MR
- [ ] On success, `self.call_from_thread(self._update_enriched_row, ...)`
      fires immediately per MR, not batched until the loop ends
- [ ] `_update_enriched_row` makes two independent
      `table.update_cell(row_key, "Approvals", ...)` /
      `table.update_cell(row_key, "Lines", ...)` calls so Approvals and Lines
      update the instant each is available
- [ ] A single global `set_interval` (started once in `on_mount`, alongside
      the refresh interval) sweeps mounted tables' rows each tick (~100ms),
      advancing the spinner frame via `update_cell_at` only on cells whose
      current value is still `Pending`
- [ ] `tests/infrastructure/test_app.py`: `FakeGateway` gains
      `enrich_merge_request`; covers a first-paint SUCCESS triggering
      `f"section-{index}-enrich"` and rows showing resolved Approvals/Lines
      once complete; covers Approvals resolving independently of Lines
      (intermediate state: one cell resolved, other still spinner)
