# Prototype E: group-level GraphQL query for list + enrichment in one round trip

Type: prototype

Status: complete

## Question

Can `group(fullPath: $path) { mergeRequests(...) { nodes { ...list fields,
approvedBy, diffStatsSummary... } } }` — a single group-level GraphQL
query, not the per-project-aliased chunking used in prototypes A-D — fetch
both list fields and enrichment fields (approvals, diff stats) in one (or
few, paginated) round trip(s), and if so, does it hit the ≤1s full-boot
bar (list + enrichment both ready) on the same dataset A-D used
(`ramsey-solutions/data-platform` group, ~59 open MRs)?

This is a structurally different query shape than A-D: it avoids the
per-project aliasing that hit GitLab's GraphQL query-complexity ceiling
(250 default, ~27/project — see `gitlab_gateway.py:124-130`), since it's
one connection with one field set and cursor pagination instead of N
aliased sub-queries. Confirm GitLab's GraphQL schema actually exposes a
group-level `mergeRequests` connection with the needed fields
(`approvedBy`, `diffStatsSummary`, `iid`, `title`, `state`, `author`,
`assignee`, `labels`) before assuming the shape is viable.

Timebox: one focused session. Reuse `benchmark_prototype_d.py`'s harness
and dataset/method for a fair comparison against A-D's numbers.

Resolution criteria (from the map's destination):
- **Full ≤1s** (list + enrichment both ready) → adopt single-query fetch
  as the destination; this ticket's answer should note what a follow-on
  implementation ticket needs (pagination strategy, field list, gateway
  migration shape).
- **Not ≤1s, or the query shape doesn't work at all** (schema doesn't
  expose it, complexity ceiling hit again, etc.) → progressive-enrichment
  becomes the destination; this ticket's answer should note why, so the
  next tickets (UI loading-state model, merge-in-place rendering, error
  handling) aren't re-litigating settled ground.

## Answer

**Not ≤1s. The single group-level query works (schema does expose it), but
one query is not one fast round trip.**

GitLab's schema *does* expose `Group.mergeRequests` with every needed field
(`approvedBy`, `approvalsLeft`, `diffStatsSummary`, `iid`, `title`, `state`,
`author`, `assignees`, `labels`, `project { fullPath }`, etc.) in a single
cursor-paginated connection, confirmed live against
`ramsey-solutions/data-platform` (57 open MRs, one page, `hasNextPage: false`
at `first: 100`) -- no complexity-ceiling error, unlike the per-project
aliasing in A-D.

But GitLab computes `diffStatsSummary` (and to a lesser extent
`approvedBy`/`approvalsLeft`) per-node server-side, and that cost dominates:

- bare list fields only: 1.5-1.7s
- + `approvedBy`/`approvalsLeft` only: 2.2-7.5s
- + `diffStatsSummary` only: 3.0-4.1s
- list + both enrichment fields (the full shape this ticket asked about):
  **3.88-4.93s** across 3 runs (`benchmark_prototype_e.py`)

So even collapsing list + enrichment into one round trip -- the structural
change this prototype set out to test -- doesn't beat prototype D's
5.3-5.6s two-round-trip asyncio approach, and lands nowhere near the ≤1s
bar. The bottleneck isn't round-trip count; it's GitLab computing diff
stats per MR server-side, which no client-side request shape (fewer
requests, more concurrency) can avoid.

**Resolution: progressive-enrichment is the destination.** No fetch-shape
variant tested across A-E gets under ~4s on this dataset. The next tickets
(UI loading-state model, merge-in-place rendering, error handling) should
proceed on that basis -- rendering the list first and enriching
(approvals/diff stats) in the background/on-demand, not blocking boot on any
single request shape.
