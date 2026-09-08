Type: grilling
Status: (open)

## Question

Progressive enrichment means a `MergeRequest` (`src/glab_dash/domain/merge_request.py:33`)
can be on-screen before its enrichment fields (`approvals_given`,
`approvals_required`, diff stats — `lines_added`/`lines_removed`) are known.
Today those fields default to `0`, indistinguishable from "fetched, actually
zero."

Does the domain model need an explicit "pending" representation (e.g. a
sentinel, a union/`Enriched | Pending` split, or `int | None` with `None`
meaning "not yet fetched") so the renderer and the enrichment-merge code can
tell "no data yet" apart from "zero approvals/zero lines changed"? Resolve
with `mattpocock-skills:domain-modeling` — this is a real domain decision
about `MergeRequest`'s shape, not a rendering detail.

Scope: only `approvals_given`, `approvals_required`, `lines_added`,
`lines_removed` — per the map's Decisions-so-far, progressive enrichment
covers `{approvals, diff_stats}` only; `pipeline_status` and
`unresolved_discussion_count` stay on the existing on-demand detail-fetch
path and are out of scope here.
