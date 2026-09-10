Status: ready-for-agent

# First paint must not make per-MR API calls

## Problem Statement

First paint still blocks on a per-MR API call for every MR in a section,
even after the progressive-enrichment work (`mr-enrichment-bootup-perf`)
shipped. `list_project_merge_requests`/`list_group_merge_requests`/
`list_global_merge_requests` map each raw MR through `_to_domain`
(`src/glab_dash/infrastructure/gitlab_gateway.py:72-90`), which calls
`_pipeline_status` (one `pipelines.list()` call) and
`_unresolved_discussion_count` (one `discussions.list()` call) for every
MR before the list can return. Measured against a real 601-MR project:
the list call itself takes 14.7s, and the per-MR `pipeline_status` calls
layered on top add another 161.9s (~0.27s/MR, sequential) — all of it
inside the worker that must complete before `on_worker_state_changed`
fires SUCCESS and any row renders. The user sees a blank tab far longer
than the ≤1s first-paint bar `mr-enrichment-bootup-perf` was built to hit,
with no indication of progress or whether it will ever resolve.

This contradicts a decision already recorded in that effort's map
(`.scratch/mr-enrichment-bootup-perf/map.md`, "grilling session, no
ticket"): *"Progressive enrichment scope is exactly `{approvals,
diff_stats}` — `pipeline_status`/`unresolved_discussion_count` stay on the
existing on-demand detail-fetch path, unwidened."* The implementation
never moved these two fields off the list/first-paint path onto the
on-demand path (`get_merge_request_detail`, triggered when the preview
pane opens) — they're still fetched eagerly for every MR at boot, for
every section, on every refresh.

A second, narrower bug was found while isolating the above:
`_unresolved_discussion_count` (`gitlab_gateway.py:35-41`) reads
`discussion.resolved` off discussion objects obtained via
`discussions.list()`; python-gitlab does not populate `resolved` on
list-fetched discussion objects, so this raises `AttributeError` for any
MR that has discussions, which fails that section's entire fetch outright.

## Solution

Remove `pipeline_status` and `unresolved_discussion_count` computation
from `_to_domain` entirely. First paint renders list fields only (state,
title, author, branches, labels, updated-at, plus the already-progressive
`approvals`/`line_stats`) with no per-MR calls beyond the single list
request. `pipeline_status` and `unresolved_discussion_count` become part
of the on-demand preview-pane fetch (`get_merge_request_detail`) — fetched
only for the single MR the user opens, when they open it, matching the
already-decided architecture instead of widening it.

Separately, fix `_unresolved_discussion_count`'s attribute access so it
no longer depends on a field python-gitlab doesn't populate on
list-fetched discussions.

## User Stories

1. As a user opening glab-dash against a section with many MRs, I want
   first paint to depend only on the single list API call, so that
   sections with hundreds of MRs still paint in about the same time as
   sections with a handful.
2. As a user refreshing a section (manual or automatic), I want the
   refresh to re-run the same cheap list-only fetch, so that refreshing a
   large section doesn't reintroduce the same per-MR stall.
3. As a user opening the preview pane for a specific MR, I want to see
   that MR's pipeline status and unresolved discussion count as part of
   the detail I already wait for, so that this information is still
   available without being paid for by every MR I never open.
4. As a user, I want an MR that has discussions to load without crashing
   its section's fetch, so that a single MR's discussion thread doesn't
   take down the whole list.
5. As a user watching a section paint, I want no visible difference in
   the Approvals/Lines progressive-enrichment behavior already shipped by
   `mr-enrichment-bootup-perf`, so that this fix doesn't regress a
   feature that already works correctly.

## Implementation Decisions

- `_to_domain` stops calling `_pipeline_status`/`_unresolved_discussion_count`. The `MergeRequest` domain entity's `pipeline_status`/`unresolved_discussion_count` fields are removed from the list-fetch path — either dropped from `MergeRequest` entirely if nothing else in the TUI renders them from the list-fetched entity today, or read from `MergeRequestDetail` instead. Confirm current renderers/consumers before choosing (`rg` for `pipeline_status`/`unresolved_discussion_count` usage outside the gateway and its tests) rather than assuming.
- `_pipeline_status`/`_unresolved_discussion_count` move to run against the MR already fetched inside `get_merge_request_detail` (`gitlab_gateway.py:211-217`), and their results become fields on `MergeRequestDetail`.
- `_unresolved_discussion_count` fixes its `discussion.resolved` access: confirm against python-gitlab's actual behavior/docs (not guessed) whether a `.get()`-fetched discussion populates `resolved`, or whether the correct signal is available some other way on the object already at hand inside `get_merge_request_detail`.
- This fix does not touch the progressive-enrichment path (`Pending`/`Approvals`/`LineStats`/`Failed`, `enrich_merge_request`, the per-section enrich worker) — that scope was deliberately closed in `mr-enrichment-bootup-perf` and stays closed here. Do not add `pipeline_status`/`unresolved_discussion_count` to the `Enrichment`-style progressive path; they belong on the on-demand detail path per the standing decision.
- No warm-start cache work here — that remains a separate, later, unimplemented effort (`CONTEXT.md:108-117`, `.scratch/mr-enrichment-bootup-perf/issues/11-warm-start-cache-mechanics.md`).

## Testing Decisions

- Test at the existing gateway seam (`tests/infrastructure/test_gitlab_gateway.py`), using its existing `make_raw_mr` fixture pattern — the same seam already used for this module's other behavior, no new seam needed.
- Invert, don't duplicate, the three existing tests that currently assert the eager (buggy) behavior: `test_unresolved_discussion_count_excludes_resolved_discussions` (line 162), `test_pipeline_status_is_the_latest_pipelines_status` (line 193), `test_pipeline_status_is_none_when_there_are_no_pipelines` (line 203). These should become assertions that `list_project_merge_requests` does *not* call `discussions.list`/`pipelines.list`, and that `get_merge_request_detail` does.
- Add a regression test asserting `list_project_merge_requests` (and the group/global equivalents) make exactly one raw list call and zero per-MR calls, using a `make_raw_mr` whose `discussions`/`pipelines` managers raise or track call counts if touched — this is the test that would have caught the original defect.
- Add a test for the `discussion.resolved` fix confirming it works against a discussion shaped the way `get_merge_request_detail`'s actual code path fetches it (not the `.list()` shape that doesn't populate the field).
- Follow this repo's Red/Green TDD practice: invert/write the failing tests first, watch them fail against current code, then implement.

## Out of Scope

- Progressive-enrichment mechanics for `approvals`/`line_stats` — already shipped, working, not touched.
- Warm-start cache — separate, unimplemented, later effort.
- Any change to `pipeline_status`/`unresolved_discussion_count` semantics beyond *when* they're fetched (still latest pipeline status, still unresolved-discussion count).
- Re-opening the closed GraphQL-single-query destination (option (a) in `mr-enrichment-bootup-perf/map.md`) — already ruled out there on measured grounds.

## Further Notes

- Full empirical measurement and diagnosis trail: `/tmp/glab-dash-handoff-boot-slowness.md` (session-local, not committed).
- That handoff's suggested fix (add a 4-field `Enrichment` dataclass to the progressive path) is superseded by this spec once the map's standing "unwidened" decision was found — the correct fix routes these two fields to the on-demand detail path, not the progressive one.
