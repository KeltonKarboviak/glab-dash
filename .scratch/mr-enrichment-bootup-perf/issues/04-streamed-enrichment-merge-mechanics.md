Type: grilling
Status: (open)

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
