# 10 — Failure handling & section-wide retry

**What to build:** A transient GitLab API failure during enrichment retries
automatically before giving up; once retries are exhausted, the affected
row(s) show a visible error state instead of an infinite spinner; a keybind
lets the user re-enrich just the errored rows in the active section without
a full refetch.

**Blocked by:** 09 — App wiring: refresh-cancel & quit-cancel for
enrichment

**Status:** ready-for-agent

- [ ] If `enrich_merge_request` raises for a given MR, the enrichment worker
      retries that MR's fetch up to 2 more times with 1s then 3s backoff
      before giving up
- [ ] On final failure, writes `Failed()` to `approvals` and/or `line_stats`
      for that MR — only fields still unresolved flip to `Failed` (a field
      that already resolved successfully this pass is left alone)
- [ ] That update streams the same way as a success (immediate
      `call_from_thread`/`_update_enriched_row`, independent per field)
- [ ] Exception logged at the point of failure; nothing downstream consumes it
- [ ] New action (e.g. `action_retry_failed_enrichment`, matching existing
      `action_*` naming) bound to a keybind: for the active section only,
      re-runs enrichment for exactly the rows whose `approvals` or
      `line_stats` is currently `Failed`, via a worker named
      `f"section-{index}-enrich-retry"`; does not touch already-enriched or
      still-`Pending` rows
- [ ] `tests/infrastructure/test_app.py`: a `FailingEnrichGateway`-style fake
      (following the existing `FailingGateway` pattern) that raises on every
      `enrich_merge_request` call ends, after retries, with affected rows
      showing the `Failed` glyph, not stuck on the spinner
- [ ] `tests/infrastructure/test_app.py`: the retry keybind re-enriches only
      `Failed` rows in the active section, leaving already-resolved rows
      untouched (assert via a gateway call counter, following the existing
      `project_list_calls` counter pattern)
