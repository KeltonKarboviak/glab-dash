# MR enrichment bootup performance

Label: wayfinder:map

## Destination

Either (a) a single group-level GraphQL query that hits full ≤1s boot
including enrichment — adopted if Prototype E clears that bar within its
timebox — or (b) a progressive-enrichment architecture: first paint of the
unenriched MR list within ≤1s, with approvals/diff-stats/pipeline-status
filling in asynchronously after. (b) is the fallback destination if
Prototype E doesn't clear (a)'s bar.

## Notes

- Domain: see `CONTEXT.md` for Boot, First paint, Enrichment, Progressive
  enrichment, Warm-start cache.
- Prior prototyping: `docs/prototypes/2026-09-04-mr-enrichment-perf-prototypes.md`
  (prototypes A-D, all 5.3-14.6x over the ≤1s bar because the floor is
  GitLab API round-trip latency, not concurrency model).
- GitLab's GraphQL query-complexity ceiling (250 default, ~27/project) is
  why A-D's per-project-aliased enrichment queries were chunked to 8
  projects/request — confirmed real, documented in
  `src/glab_dash/infrastructure/gitlab_gateway.py:124-130`.
- Consult `mattpocock-skills:grilling` and `mattpocock-skills:domain-modeling`
  when resolving tickets on this map.

## Decisions so far

- (charting session, no ticket) "Bootup ≤1s" means first paint (list fields only); progressive enrichment after first paint is accepted UX; warm-start cache is in scope as a later lever, layered on after cold-boot-to-first-paint is solved.
- (grilling session, no ticket) Prototype E (single group-level GraphQL query) measured 3.88-4.93s live — still 3.9-4.9x over the ≤1s bar. Confirmed: the floor is GitLab computing `diffStatsSummary`/approvals per MR server-side, not round-trip count or client concurrency (see `docs/prototypes/2026-09-04-mr-enrichment-perf-prototypes.md`). Destination (b), progressive enrichment, is now locked in; option (a) is closed out.
- (grilling session, no ticket) Progressive enrichment scope is exactly `{approvals, diff_stats}` — `pipeline_status`/`unresolved_discussion_count` stay on the existing on-demand detail-fetch path, unwidened.
- (grilling session, no ticket) Mechanism: a second per-section Textual worker (e.g. `f"section-{index}-enrich"`), started after the first-paint worker completes, reusing the existing `Worker.StateChanged`/`_tables_by_worker_name` pattern in `app.py` rather than a new concurrency primitive.
- (grilling session, no ticket) Enrichment updates rows as each chunk/batch lands (streamed), not in one batch at the end — that's the reason progressive enrichment is the destination.
- (grilling session, no ticket) Fact: `DataTable.add_row` at `app.py:225` never passes a `key=`, so no stable row identity exists today for routing an enrichment result back to its row under sort/filter. Needs adding (e.g. `key=f"{mr.project}#{mr.iid}"`) as part of whichever ticket implements the merge-in-place update.
- (grilling session, no ticket) Warm-start cache stays out of scope for this batch of tickets — confirmed separate, later fog patch; not to be reached for as a stopgap during progressive-enrichment work.
- [Pending-enrichment domain model](issues/01-pending-enrichment-domain-model.md) — `MergeRequest` gets two independent `Pending | <Value>` union fields (`approvals: Pending | Approvals`, `line_stats: Pending | LineStats`) replacing the four scalar fields, not one bundled union and not `int | None` — approvals and diff stats resolve on different timelines even within one GraphQL query, so each must update independently.
- [Pending-enrichment loading-state prototype](issues/02-pending-enrichment-loading-state-prototype.md) — animated spinner (braille frames, ticking every 100ms via `set_interval`/`update_cell_at`, only on cells still `Pending`) beats a static placeholder or blank cell.
- [Streamed-enrichment merge mechanics](issues/04-streamed-enrichment-merge-mechanics.md) — row key `f"{project}#{iid}"` on `add_row`/`_merge_requests_by_table_id`; new `enrich_merge_request` gateway method, worker-driven per-MR loop streaming via `call_from_thread` + two independent `update_cell` calls; new Approvals/Lines columns; one global spinner interval; enrich worker chained off first-paint SUCCESS, reusing its name each refresh for auto-cancellation.
- [Enrichment failure retry policy](issues/03-enrichment-failure-retry-policy.md) — whole-chunk failures auto-retry 2x (1s/3s backoff) then flip to a bare `Failed` variant (added to both `approvals`/`line_stats` unions); a section-wide keybind manually retries only rows still `Failed`.

## Not yet specified

- Warm-start cache design: invalidation, staleness display, storage
  location — deferred until the boot-to-first-paint destination above is
  chosen and built.

## Out of scope

- Single group-level GraphQL query as the ≤1s solution (destination (a)) —
  Prototype E measured 3.88-4.93s live, still 3.9-4.9x over the ≤1s bar;
  the floor is GitLab's server-side per-MR computation of diff
  stats/approvals, not round-trip count or client concurrency. See
  `docs/prototypes/2026-09-04-mr-enrichment-perf-prototypes.md`.
