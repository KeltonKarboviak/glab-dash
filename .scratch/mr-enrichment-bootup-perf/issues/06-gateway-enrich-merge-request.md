# 06 — Gateway: enrich_merge_request

**What to build:** A gateway method that fetches one MR's approvals and diff
stats on demand, so the app can enrich rows after first paint instead of
blocking list-fetch on per-MR computation. `list_project_merge_requests`/
`list_group_merge_requests`/`list_global_merge_requests` stop doing that
per-MR work inline — every MR they return starts as `Pending()`/`Pending()`.

**Blocked by:** 05 — Domain model: Pending/Approvals/LineStats/Failed unions

**Status:** ready-for-agent

- [ ] `GitlabMergeRequestGateway._to_domain` no longer calls
      `_approvals`/`_line_stats` inline; returned MRs have
      `approvals=Pending()`, `line_stats=Pending()`
- [ ] `GitlabMergeRequestGateway.enrich_merge_request(project: str, iid: int) -> tuple[Approvals, LineStats]`
      added, reusing existing `_approvals`/`_line_stats` helper logic against
      a freshly-fetched raw MR (same fetch pattern as
      `get_merge_request_detail`)
- [ ] `MergeRequestGateway` protocol (consumed by
      `application/list_merge_requests.py`) gains `enrich_merge_request`
- [ ] `FakeGateway` (test fixture) implements `enrich_merge_request`
- [ ] `tests/infrastructure/test_gitlab_gateway.py` covers
      `enrich_merge_request` returning `(Approvals, LineStats)` from a raw
      MR's `approvals`/`changes` data, reusing the existing `make_raw_mr`
      fixture
- [ ] `tests/test_architecture.py` passes — `enrich_merge_request` lives in
      `infrastructure/`, not `domain/` or `application/`
