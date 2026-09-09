Status: ready-for-agent

# Progressive MR enrichment

## Problem Statement

Opening glab-dash against a section with real MR volume makes first paint
wait on GitLab computing approvals and diff stats for every MR before any
row appears — 3.9-4.9x over the ≤1s first-paint bar, even with the fastest
query shape tested (Prototype E, single group-level GraphQL query). The
floor is GitLab's server-side per-MR computation, not round-trip count or
client concurrency, so no query restructuring closes the gap. The user is
left staring at a blank tab for several seconds on every boot and every
manual/automatic refresh.

## Solution

Split first paint from enrichment. The MR list (state, title, author,
branches, labels, updated-at) renders within ≤1s of a section's fetch
completing, with each row's Approvals and Lines columns showing an animated
"pending" spinner. A second, per-section background worker then fetches
approvals and diff stats one MR at a time and streams each result into its
row's Approvals/Lines cell as soon as that MR's data arrives — the user
watches the two columns fill in live rather than waiting for the whole
section to enrich. A chunk that fails to fetch after retries flips its rows
to a visible error state the user can retry with a keybind, without
disturbing already-enriched rows or forcing a full section refresh.

## User Stories

1. As a user opening glab-dash against a section with many MRs, I want the
   MR list to appear within ~1s, so that I'm not staring at a blank tab
   while GitLab computes per-MR stats.
2. As a user watching a freshly-painted section, I want each row's
   Approvals and Lines cells to show a visibly animated "still loading"
   indicator, so that I know enrichment is in progress rather than assuming
   the app is stuck or those columns are simply empty.
3. As a user watching enrichment progress, I want the Approvals cell to
   fill in independently of the Lines cell (and vice versa), so that I see
   data as soon as it's available rather than waiting for the slower of the
   two to resolve.
4. As a user watching enrichment progress, I want rows to enrich in the
   same order they're listed, updating live one at a time, so that
   progress is visible and predictable rather than appearing to jump
   around or land in one big batch at the end.
5. As a user, I want the pending-state spinner to stop animating a cell
   the instant that cell's real value lands, so that the table doesn't
   keep animating stale placeholders.
6. As a user, I want a transient GitLab API failure during enrichment to
   retry automatically (a couple of times, with brief backoff) before
   giving up, so that a single flaky request doesn't leave rows stuck
   showing an error the user has to notice and act on.
7. As a user whose enrichment retries have exhausted, I want the affected
   rows' Approvals/Lines cells to show a visible error state instead of an
   infinite spinner, so that I know those specific rows didn't enrich and
   nothing is silently broken.
8. As a user looking at rows with a visible enrichment error, I want a
   keybind that retries only the errored rows in the active section (not
   already-enriched rows, not other sections), so that I can recover
   without paying for a full section refetch.
9. As a user who presses refresh (`r`) or waits for the automatic refresh
   interval while enrichment is still in progress, I want the previous
   enrichment pass for that section to stop and a fresh one to start
   against the newly-fetched rows, so that I never see enrichment results
   from a stale MR list overwrite or race with the new one.
10. As a user quitting the app while enrichment is in progress, I want the
    enrichment worker to stop promptly (same as the first-paint fetch
    already does), so that quitting doesn't hang or delay on outstanding
    API calls.
11. As a user browsing a section whose MRs are still enriching, I want the
    existing navigation (`j`/`k`/`g`/`G`, tab switching, preview pane) to
    keep working unaffected by the in-progress enrichment worker, so that
    enrichment is a background nicety, not something that blocks or
    interferes with using the app.
12. As a developer reading `MergeRequest`, I want approvals and diff stats
    represented as two independent `Pending | Value | Failed` unions
    (matching how they're actually fetched and rendered), so that "not yet
    fetched," "fetched," and "failed to fetch" are distinguishable states
    the type system enforces, instead of overloaded `0` defaults.

## Implementation Decisions

- **Domain model** (`glab_dash/domain/merge_request.py`): remove the four
  scalar fields `approvals_given`, `approvals_required`, `lines_added`,
  `lines_removed`. Add three new frozen dataclasses — `Pending` (no
  fields), `Approvals(given: int, required: int)`, `LineStats(added: int,
  removed: int)` — plus a fourth marker, `Failed` (no fields, distinct type
  from `Pending`). `MergeRequest` gains two fields:
  `approvals: Pending | Approvals | Failed = Pending()` and
  `line_stats: Pending | LineStats | Failed = Pending()`. These two fields
  update independently of each other and of the rest of `MergeRequest`'s
  fields. `pipeline_status` and `unresolved_discussion_count` are
  unchanged and stay on the existing on-demand detail-fetch path.
- **Gateway** (`glab_dash/infrastructure/gitlab_gateway.py`):
  - `_to_domain` no longer calls `_approvals`/`_line_stats` inline; MRs
    from `list_project_merge_requests`/`list_group_merge_requests`/
    `list_global_merge_requests` come back with `approvals=Pending()` and
    `line_stats=Pending()`.
  - Add `enrich_merge_request(project: str, iid: int) -> tuple[Approvals,
    LineStats]` on `GitlabMergeRequestGateway`, reusing the existing
    `_approvals`/`_line_stats` helper logic against a freshly-fetched raw
    MR (`self._client.projects.get(project).mergerequests.get(iid)`, same
    pattern as `get_merge_request_detail`). This method fetches one MR's
    enrichment data per call; batching/looping over a section's MR list is
    the enrichment worker's responsibility, not the gateway's.
  - `MergeRequestGateway` (the `Protocol`/interface consumed by
    `application/list_merge_requests.py` and implemented by `FakeGateway`
    in tests) gains this same `enrich_merge_request` method.
- **App** (`glab_dash/infrastructure/tui/app.py`):
  - `table.add_row` (currently unkeyed) gains `key=f"{mr.project}#{mr.iid}"`.
  - `_merge_requests_by_table_id: dict[str, list[MergeRequest]]` becomes
    `dict[str, dict[str, MergeRequest]]` (table id → row key → MergeRequest).
    Update `_selected_merge_request` and any other reader accordingly
    (cursor-row-to-MR lookup now needs the table's row order preserved
    separately, or resolved via `table.get_row_at`/row key — pick whichever
    keeps `_selected_merge_request`'s existing behavior unchanged from the
    user's perspective).
  - `table.add_columns` gains `"Approvals"` and `"Lines"`.
  - On a first-paint worker's `SUCCESS` (`on_worker_state_changed`, after
    rows are added), start a per-section enrichment worker:
    `self.run_worker(partial(_enrich_section, ...), name=f"section-{index}-enrich", thread=True)`.
    Reusing this exact name on every refresh is sufficient for Textual to
    auto-cancel the prior cycle's enrichment worker.
  - The enrichment worker loops over its section's MR list one MR at a
    time, checking `_quit_requested()` each iteration (same cancellation
    pattern `_fetch_section_merge_requests` uses), calling
    `gateway.enrich_merge_request(mr.project, mr.iid)` per MR. On success,
    it calls `self.call_from_thread(self._update_enriched_row, ...)` for
    that MR immediately — not batched until the loop ends.
  - `_update_enriched_row` makes two independent
    `table.update_cell(row_key, "Approvals", ...)` /
    `table.update_cell(row_key, "Lines", ...)` calls, one per resolved
    value, so Approvals and Lines update the instant each is available.
  - A single global `set_interval` (started once in `on_mount`, alongside
    the refresh interval) sweeps every mounted table's rows each tick
    (~100ms), calling `update_cell_at` to advance the spinner frame only on
    cells whose current value is still `Pending`. No per-section or
    per-cell interval lifecycle — the tick handler no-ops once a cell
    isn't `Pending`.
  - Chunk-failure handling: if `enrich_merge_request` raises for a given
    MR, the enrichment worker retries that MR's fetch up to 2 more times
    with 1s then 3s backoff before giving up; on final failure it writes
    `Failed()` to both `approvals` and `line_stats` for that MR (unless one
    already resolved successfully on this pass — only the fields still
    unresolved flip to `Failed`) and streams that update the same way as a
    success. Log the exception at the point of failure; nothing downstream
    needs it.
  - Add a section-wide retry keybind (e.g. bound to a new action,
    `action_retry_failed_enrichment` or similar — name to match existing
    `action_*` conventions) that, for the active section only, re-runs
    enrichment for exactly the rows whose `approvals` or `line_stats` is
    currently `Failed`, via a worker named
    `f"section-{index}-enrich-retry"`. This does not touch rows that are
    already enriched or still `Pending`.
- **Rendering** (`glab_dash/infrastructure/tui/rows.py`):
  - Add `render_approvals(value: Pending | Approvals | Failed, frame: str) -> str`
    and `render_line_stats(value: Pending | LineStats | Failed, frame: str) -> str`,
    adapted from the loading-state prototype's variant-A functions
    (`src/glab_dash/infrastructure/tui/prototype_pending_cell.py` on branch
    `prototype/pending-enrichment-loading-state`, commit `8628cfe`):
    `Pending` renders the current spinner frame (braille cycle
    `⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏`, one frame per ~100ms tick); a resolved `Approvals`/
    `LineStats` renders its formatted value (e.g. `"given/required"`,
    `"+added/-removed"`); `Failed` renders a fixed error glyph/string (e.g.
    `"⚠"`) — never animated, since it's a terminal state until manual
    retry.
  - `render_mr_row` is unaffected — it never touched these two fields.
- **Domain-modeling / glossary** (`CONTEXT.md`): `Pending`, `Approvals`,
  and `Line stats` are already recorded as domain value types per the
  Streamed-enrichment merge mechanics ticket's answer; `Failed` needs the
  same glossary treatment (new value type, same status as `Pending`/
  `Approvals`/`LineStats`).

## Testing Decisions

- Only test observable behavior (rendered cell contents, row counts, table
  state, worker names/kwargs actually invoked) — not internal call
  sequencing beyond what's already asserted in the existing suite (e.g.
  `test_refresh_runs_through_run_worker_without_blocking` asserts on
  `run_worker`'s `thread=True` kwarg, not its internal control flow).
- **`tests/domain/test_merge_request.py`** (pure domain seam, prior art:
  existing file): add tests for `Pending`/`Approvals`/`LineStats`/`Failed`
  equality/construction and that `MergeRequest`'s new fields default to
  `Pending()`. No GitLab or Textual dependency — matches this file's
  existing "no I/O" scope.
- **`tests/infrastructure/test_gitlab_gateway.py`** (prior art: existing
  `FakeMergeRequestManager`/`make_raw_mr` fixtures): add tests for
  `enrich_merge_request` returning `(Approvals, LineStats)` from a raw MR's
  `approvals`/`changes` data, reusing the existing `make_raw_mr` fixture
  rather than inventing new fixture machinery.
- **`tests/infrastructure/test_rows.py`** (prior art: existing
  `render_mr_row` tests): add tests for `render_approvals`/
  `render_line_stats` covering all three states (`Pending` shows the given
  spinner frame, resolved shows formatted values, `Failed` shows the fixed
  error glyph).
- **`tests/infrastructure/test_app.py`** (prior art: existing `FakeGateway`
  + `app.run_test()`/`pilot` seam — the highest-leverage seam here since it
  exercises real worker scheduling, `Worker.StateChanged`, and table
  state): extend `FakeGateway` with `enrich_merge_request`, and add a
  `SlowFakeGateway`/`FailingEnrichGateway`-style fake (following the
  existing `FailingGateway` pattern) for retry/failure scenarios. Cover:
  - a first-paint SUCCESS triggers an enrichment worker
    (`f"section-{index}-enrich"`) and, once complete, rows show resolved
    Approvals/Lines instead of the pending spinner glyph;
  - enrichment updates a row's Approvals cell independent of its Lines
    cell (assert intermediate state where one resolved cell shows real
    data while the other still shows the spinner);
  - a refresh (`r`) while enrichment is in-flight results in exactly one
    enrichment pass completing per section afterward (no leftover stale
    update landing on the new table state) — mirrors the existing
    `test_refresh_preserves_the_active_tab_and_cursor_position` pattern;
  - a gateway that raises for `enrich_merge_request` on every call ends,
    after retries, with the affected row(s) showing the `Failed` glyph, not
    stuck on the spinner;
  - the retry keybind re-enriches only `Failed` rows in the active section,
    leaving already-`Approvals`/`LineStats`-resolved rows untouched
    (assert via a gateway call counter, following the existing
    `gateway.project_list_calls` counter pattern).
  - quitting (`q`) while an enrichment worker is running exits promptly
    (mirrors how quit already behaves for the first-paint fetch worker).

## Out of Scope

- Warm-start cache (invalidation, staleness display, storage location) —
  explicitly deferred on the map until this progressive-enrichment
  architecture is built; a later, separate effort.
- Widening progressive enrichment to `pipeline_status` or
  `unresolved_discussion_count` — both stay on the existing on-demand
  detail-fetch path (`get_merge_request_detail`), unchanged.
- Per-MR partial GraphQL error handling within an otherwise-successful
  enrichment response — only whole-chunk (whole-call) failure is handled;
  this codebase's gateway is REST-based per-MR calls today, not a batched
  GraphQL query, so "chunk" here means one MR's `enrich_merge_request`
  call.
- Any query-shape/GraphQL restructuring to hit the ≤1s bar for full
  enrichment in one shot — ruled out already (Prototype E measured
  3.88-4.93s live; see map's Out of scope section).
- Per-row or cursor-targeted manual retry — the retry keybind is
  section-wide only, per the Enrichment failure retry policy ticket.
- Persisting `Failed` state across a section refresh — a refresh always
  re-fetches the MR list fresh and restarts enrichment from `Pending` for
  every row; `Failed` only exists within one enrichment pass until refresh
  or manual retry.

## Further Notes

- Source tickets (all resolved) on the wayfinder map at
  `.scratch/mr-enrichment-bootup-perf/map.md`:
  [Pending-enrichment domain model](issues/01-pending-enrichment-domain-model.md),
  [Pending-enrichment loading-state prototype](issues/02-pending-enrichment-loading-state-prototype.md),
  [Enrichment failure retry policy](issues/03-enrichment-failure-retry-policy.md),
  [Streamed-enrichment merge mechanics](issues/04-streamed-enrichment-merge-mechanics.md).
- Suggested build order, following the existing dependency chain: domain
  model → gateway `enrich_merge_request` → rendering functions → app
  wiring (row keys, columns, enrichment worker, spinner interval) → retry
  keybind and failure path.
- `tests/test_architecture.py`'s layer rules apply unchanged: the new
  `Pending`/`Approvals`/`LineStats`/`Failed` types live in `domain/` and
  must stay stdlib-only; `enrich_merge_request` lives in
  `infrastructure/gitlab_gateway.py`, not `domain/` or `application/`.
