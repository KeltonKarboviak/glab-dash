# 15 — Warm-start read at boot with Stale first paint

**What to build:** first paint shows warm-cached enrichment values (as
`Stale`, dimmed) instead of `Pending`/spinner when a prior cache exists,
which then resolve to fresh values through the existing streamed
enrichment path as the background fetch confirms them.

**Blocked by:** 13 (Stale enrichment state and dimmed rendering), 14 (Warm-start cache write-behind)

**Status:** ready-for-agent

- [ ] Before first paint, each section's cache file is read synchronously on the main thread (local file read, no network)
- [ ] MRs with a matching cache entry render `approvals`/`line_stats` as `Stale(value)` at first paint instead of `Pending`
- [ ] Missing file, corrupt JSON, or schema-version mismatch is treated as a cache miss: falls back to `Pending` for that MR/section, logged but not surfaced to the user
- [ ] No TTL — cached data is shown regardless of age; age is never a gate that falls back to `Pending`
- [ ] The background enrichment worker resolves `Stale → real value` through the existing streamed per-MR `update_cell` path (no new mechanism)
- [ ] End-to-end demo: restart the app after a successful enrichment pass and observe dimmed (`Stale`) values at first paint that un-dim as fresh data lands
