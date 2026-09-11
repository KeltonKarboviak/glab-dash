# Line stats moves from progressive enrichment to on-demand detail fetch

Profiling found `_line_stats` (REST `.changes()`, fetching every changed
file's full diff text just to count `+`/`-` lines) at 16.29% of sampled
boot time — the most expensive enrichment leaf. Research confirmed no
cheaper GitLab API exists for this at MR scope: REST has no MR-level stats
endpoint (`changes_count` is a bucketed string, not real counts; the only
`diff_stats` endpoint is a ref-to-ref repo comparison, not MR-scoped), and
GraphQL's `diffStatsSummary` field trades a smaller payload for a
per-node server-side compute cost that the enrichment-bootup-perf
prototypes (`docs/prototypes/2026-09-04-mr-enrichment-perf-prototypes.md`)
identified as the actual bottleneck — plus it would require a second,
experimental transport (python-gitlab's GraphQL client) alongside the
REST client already used throughout the gateway.

Decided to drop `line_stats` from progressive enrichment entirely rather
than pay that cost, moving it to `MergeRequestDetail`'s on-demand fetch
instead — the same pattern already used for `pipeline_status` and
`unresolved_discussion_count`. This is a free move: `get_merge_request_detail`
already calls `.changes()` to build the diff preview, so deriving line
stats there adds no additional network call. The MR list loses its Lines
column; line counts now show only when a user opens an MR's detail view.

This supersedes the `{approvals, diff_stats}` progressive-enrichment scope
decision recorded in `.scratch/mr-enrichment-bootup-perf/map.md`.
