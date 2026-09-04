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

## Not yet specified

- If Prototype E succeeds: how the single-query fetch replaces the current
  gateway (REST list + GraphQL enrichment) — implementation shape,
  pagination strategy for large groups, migration of existing tests.
- If Prototype E doesn't clear the bar: the progressive-enrichment
  architecture itself — UI loading-state model for rows pending
  enrichment, how/when enrichment results merge into already-rendered
  rows, error handling for partial enrichment failures, retry/backoff.
- Warm-start cache design: invalidation, staleness display, storage
  location — deferred until the boot-to-first-paint destination above is
  chosen and built.

## Out of scope

(none yet)
