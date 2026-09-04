# MR list + enrichment bootup performance prototypes

**Question:** can bootup fetch of a group's MR list + enrichment (approvals,
diff stats) get from the ~10s REST baseline down to the ≤1s target?

**Dataset:** `ramsey-solutions/data-platform` group on gitlab.com, live API.
Prototypes A-C measured 58 open MRs spread across 34 distinct projects;
prototype D measured 59 open MRs (dataset grew by one MR between sessions,
same group/shape).

> This page lives on `master`. The prototype implementations and benchmark
> scripts it describes were never merged here on purpose -- they're
> throwaway spikes, not code the app runs. Each is on its own branch (listed
> per prototype below); check that branch out to read or re-run one.

## Summary

| # | Branch | Approach | Measured | vs. target (≤1s) |
|---|--------|----------|----------|-------------------|
| — | (baseline) | Sync REST, 4 calls/MR, no concurrency | 9.98s | 10x over |
| A | `perf/enrichment-thread-pool` | Sync REST, 4 calls/MR, thread-pool batches of 8 | not separately measured (superseded by B) | — |
| B | `perf/enrichment-trimmed-thread-pool` | Sync REST, 2 calls/MR (approvals + diff, pipeline/discussions moved to lazy detail fetch), thread-pool batches of 8 | **7.78s — winner going into this round** | 7.8x over |
| C | `perf/enrichment-graphql` | Sync REST list + batched per-project-aliased GraphQL enrichment, chunked 8 projects/request | 14.62s (5 sequential chunked requests) | 14.6x over, *slower than B* |
| D | `perf/enrichment-asyncio` | Async REST list fetch + async enrichment, two enrichment strategies compared head-to-head (below) | **5.27-5.58s** | 5.3-5.6x over |
| E | `perf/enrichment-asyncio` | Sync, single group-level GraphQL query (list + approvals + diff stats in one connection, cursor-paginated -- no per-project aliasing) | **3.88-4.93s** | 3.9-4.9x over |

Prototype D beats B (5.3s vs 7.8s); E beats D by collapsing to one round
trip, but still lands nowhere near ≤1s. D and E are both on
`perf/enrichment-asyncio` (E built on top of D in the same session).

## Prototype E detail: one group-level query instead of per-project aliasing

A-D all fetch enrichment via a query aliased per distinct project (to stay
under GitLab's GraphQL query-complexity ceiling), which caps at 8
projects/request and needs chunking for larger project counts. E asks a
structurally different question: does GitLab's schema expose a
*group-level* `mergeRequests` connection with list fields *and* enrichment
fields together, avoiding aliasing/chunking entirely
(`benchmark_prototype_e.py` on `perf/enrichment-asyncio`)?

It does -- `Group.mergeRequests` exposes every needed field
(`approvedBy`, `approvalsLeft`, `diffStatsSummary`, etc.), confirmed live
(57 open MRs, one page at `first: 100`, no complexity error). But the fields
are expensive to compute per-node server-side regardless of request shape:

```
bare list only:                    1.5-1.7s
+ approvedBy/approvalsLeft only:   2.2-7.5s
+ diffStatsSummary only:           3.0-4.1s
list + both enrichment fields:     3.88-4.93s (3 runs)
```

**Conclusion:** collapsing list + enrichment into a single round trip does
help (beats D's two-round-trip 5.3-5.6s), but the floor isn't round-trip
count -- it's GitLab computing `diffStatsSummary` (and, less consistently,
approvals) per MR server-side. No request shape tested across A-E gets
within reach of ≤1s.

## Prototype D detail: asyncio, GraphQL vs. pure REST

`python-gitlab` is sync-only, so D hand-rolls an `httpx.AsyncClient` against
GitLab's REST + GraphQL APIs (`src/glab_dash/infrastructure/prototype_d_asyncio_gateway.py`
and `benchmark_prototype_d.py`, both on `perf/enrichment-asyncio`). Two
independent questions were tested:

1. Does concurrent (asyncio) list-page + enrichment fetching beat B's
   thread-pool concurrency?
2. Within that, does GraphQL batching still win over pure REST once both
   are made concurrent via asyncio (unlike prototype C, which was GraphQL
   but *not* concurrent across its 5 chunk requests)?

Both enrichment strategies reuse the same async REST list fetch (GitLab's
paginated pages requested concurrently instead of python-gitlab's
sequential pagination); only the enrichment step differs:

- **`graphql` strategy** — same batched, per-project-aliased GraphQL query as
  prototype C, but every chunk (8 projects/request) is fired concurrently via
  `asyncio.gather` instead of C's sequential for-loop.
- **`rest` strategy** — no GraphQL at all: the same 2 REST calls/MR B made
  (approvals, changes), all issued concurrently via `asyncio.gather` instead
  of thread-pool-batched.

### Results (state=opened, 59 MRs)

```
graphql : 5.58s, 59 MRs, 59 enriched
rest    : 5.27s, 59 MRs, 59 enriched
speedup: 0.94x (graphql vs rest — roughly even, rest slightly faster)
```

### Conclusions

- **Asyncio > thread pool, but not by enough.** Making the whole fetch
  concurrent (list pages + enrichment calls, all in one event loop) beat B's
  thread-pool batching by ~30% (5.3-5.6s vs 7.8s), because thread-pool
  batches of 8 still serialize *between* batches while asyncio's `gather`
  has no such ceiling.
- **GraphQL's batching advantage disappears once REST is also made
  concurrent.** Unlike prototype C (GraphQL lost to REST because C's GraphQL
  chunks ran sequentially), D shows GraphQL and pure REST landing within 6%
  of each other once *both* run fully concurrently. The aliasing/chunking
  overhead that hurt C stops mattering once nothing is serialized to begin
  with — but it also stops helping enough to justify the extra
  query-complexity bookkeeping.
- **Concurrency model was never the real bottleneck.** At ~59 MRs, the floor
  is the number of sequential *round trips*, not how many things run at
  once within a round trip: one list fetch, then one enrichment step, each
  paying GitLab's per-request latency (roughly 150-300ms, amplified by
  however many distinct projects/chunks are involved). No amount of
  concurrency within a single round trip gets under that latency floor.
- **≤1s is very unlikely to be reachable by fetching more data per boot,
  concurrently or not.** Getting under 1s would need either fewer round
  trips than "list + enrich" (e.g. a single GraphQL query returning list
  fields *and* approvals/diff stats together, cutting D's two round trips to
  one) or deferring enrichment out of the boot path entirely (render the
  list first, enrich in the background/on-demand) rather than further
  optimizing the concurrency model of the fetch itself.

## Recommendation

None of A-E's fetch-shape variants reach ≤1s — E (single group-level
query) is the fastest at 3.88-4.93s, beating D's two-round-trip asyncio
approach, but the floor is GitLab computing diff stats/approvals per MR
server-side, not round-trip count or client concurrency. **Progressive
enrichment is the destination**: render the list first, enrich
(approvals/diff stats) in the background/on-demand, rather than continuing
to optimize the bootup fetch shape itself. Follow-on tickets (UI
loading-state model, merge-in-place rendering, error handling) should
proceed on that basis without re-litigating fetch-shape options.

## Artifacts

Implementations and benchmark scripts are intentionally not on `master` --
each lives only on the branch that produced it:

- `perf/enrichment-thread-pool` (A)
- `perf/enrichment-trimmed-thread-pool` (B, prior winner)
- `perf/enrichment-graphql` (C)
- `perf/enrichment-asyncio` (D and E):
  `src/glab_dash/infrastructure/prototype_d_asyncio_gateway.py`,
  `benchmark_prototype_d.py`, `benchmark_prototype_e.py`
