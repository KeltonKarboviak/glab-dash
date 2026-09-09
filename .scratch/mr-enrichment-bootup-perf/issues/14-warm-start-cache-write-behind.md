# 14 — Warm-start cache write-behind

**What to build:** the app layer persists each section's enrichment
results to a per-section JSON cache file under the XDG cache dir, so a
later boot has warm data to read (read side is a separate ticket).

**Blocked by:** None — can start immediately.

**Status:** ready-for-agent

- [ ] One flat JSON file per section under `~/.cache/glab-dash/`, filename the section name slugified (lowercase, non-alphanumeric → `-`)
- [ ] File holds only enrichment fields (`approvals`, `line_stats`), keyed by `f"{project}#{iid}"`, plus a schema-version field
- [ ] Write is owned by the app layer, triggered on a rolling/debounced basis after each enrichment chunk resolves (reusing the existing enrich-worker callback path in `app.py`, e.g. `_update_enriched_row`) — not batched to app quit
- [ ] Each write prunes entries for MRs no longer present in the section's current fetch (merged/closed MRs no longer in the section are dropped)
- [ ] Unit/integration tests verify the cache file's contents and pruning behavior after an enrichment run
