# 05 — Domain model: Pending/Approvals/LineStats/Failed unions

**What to build:** `MergeRequest.approvals` and `MergeRequest.line_stats` become
typed unions (`Pending | Approvals | Failed` and `Pending | LineStats | Failed`)
instead of four overloaded scalar fields, so callers can distinguish "not yet
fetched," "fetched," and "failed to fetch" instead of guessing from `0`
defaults. `CONTEXT.md` glossary gains the `Failed` value type alongside the
already-recorded `Pending`/`Approvals`/`LineStats` entries.

**Blocked by:** None — can start immediately

**Status:** ready-for-agent

- [ ] `glab_dash/domain/merge_request.py` removes `approvals_given`,
      `approvals_required`, `lines_added`, `lines_removed`
- [ ] Adds frozen dataclasses `Pending()`, `Approvals(given: int, required: int)`,
      `LineStats(added: int, removed: int)`, `Failed()` — stdlib-only, no new deps
- [ ] `MergeRequest.approvals: Pending | Approvals | Failed = Pending()`
- [ ] `MergeRequest.line_stats: Pending | LineStats | Failed = Pending()`
- [ ] `tests/domain/test_merge_request.py` covers equality/construction of all
      four types and that `MergeRequest` defaults both fields to `Pending()`
- [ ] `CONTEXT.md` documents `Failed` in the glossary
- [ ] `tests/test_architecture.py` passes — new types stay in `domain/`,
      stdlib-only
