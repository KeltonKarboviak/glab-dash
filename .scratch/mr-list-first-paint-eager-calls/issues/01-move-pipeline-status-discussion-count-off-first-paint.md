# 01 — Move `pipeline_status`/`unresolved_discussion_count` off first-paint, onto on-demand detail fetch

**What to build:** `list_project_merge_requests`/`list_group_merge_requests`/`list_global_merge_requests`
make zero per-MR API calls — only the single list request. `pipeline_status` and
`unresolved_discussion_count` are removed from the list-fetch path entirely: dropped from
`MergeRequest` and added to `MergeRequestDetail`, computed inside `get_merge_request_detail`
against the MR it already fetches. The `discussion.resolved` `AttributeError` (raised because
`discussions.list()`-fetched discussions don't populate `resolved`) is fixed against the actual
shape of discussion objects available inside `get_merge_request_detail`. Progressive enrichment
(`approvals`/`line_stats`, the `Pending`/`Failed` states, `enrich_merge_request`, the per-section
enrich worker) is untouched — this fix does not widen that path.

**Blocked by:** None — can start immediately.

**Status:** ready-for-agent

- [ ] `_to_domain` no longer calls `_pipeline_status`/`_unresolved_discussion_count`; `MergeRequest`
      no longer has `pipeline_status`/`unresolved_discussion_count` fields.
- [ ] `MergeRequestDetail` gains `pipeline_status: str | None` and `unresolved_discussion_count: int`
      fields, populated by `get_merge_request_detail`.
- [ ] `_unresolved_discussion_count`'s attribute access is fixed to work against the discussion
      shape actually available inside `get_merge_request_detail` (confirmed against python-gitlab's
      actual behavior, not guessed).
- [ ] `test_unresolved_discussion_count_excludes_resolved_discussions`,
      `test_pipeline_status_is_the_latest_pipelines_status`, and
      `test_pipeline_status_is_none_when_there_are_no_pipelines` are inverted (not duplicated) to
      assert the new on-demand behavior.
- [ ] New regression test: `list_project_merge_requests` (and group/global equivalents) make exactly
      one raw list call and zero per-MR calls (`discussions.list`/`pipelines.list` never touched).
- [ ] New test: the `discussion.resolved` fix works against a discussion shaped the way
      `get_merge_request_detail`'s actual code path fetches it.
- [ ] Approvals/line-stats progressive-enrichment behavior shipped by `mr-enrichment-bootup-perf`
      shows no regression.
- [ ] Tests written first (red), confirmed failing against current code, then implementation makes
      them pass (green), per this repo's TDD practice.
