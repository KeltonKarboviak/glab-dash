Label: wayfinder:grilling
Status: closed

## Question

Now that progressive enrichment has landed, design the warm-start cache
graduated from the map's "Not yet specified" fog: storage format/location,
what's cached, read/write timing, staleness handling, invalidation, and
which layer owns writes.

## Resolution

- **Storage**: one flat JSON file per section, under the XDG cache dir
  (`~/.cache/glab-dash/`). Filename is the section name slugified
  (lowercase, non-alphanumeric → `-`). A section rename orphans the old
  cache file (harmless disk litter); the renamed section cold-starts.
- **Cached content**: enrichment fields only (`Approvals`, `LineStats`),
  keyed by `f"{project}#{iid}"`. List fields (title, state, author, labels)
  are always re-fetched fresh, never cached — cheap to fetch, and stale
  values there would be worse than showing `Pending`.
- **New state**: `Stale(value)` added alongside `Pending`/`Failed`/resolved
  on the enrichment unions — a value with an unconfirmed timestamp, shown
  at first paint when the cache has an entry for that MR. Visual treatment
  is a separate prototype ticket (see
  [Warm-start staleness display prototype](12-warm-start-staleness-display-prototype.md)).
- **Read timing**: synchronous, on the main thread, before first paint —
  local file read, no network, and the point is first paint shows warm
  data immediately.
- **Write timing/owner**: app layer (already owns section row/enrichment
  state), rolling/debounced write-behind after each chunk resolves — not
  batched to app quit, so a Ctrl-C mid-boot doesn't lose an otherwise-
  successful enrichment pass.
- **Pruning**: each write persists only entries for MRs present in the
  current fetch, dropping merged/closed MRs no longer in the section —
  keeps the file bounded, avoids ever showing a warm row for an MR that's
  gone.
- **Corruption/missing/version mismatch**: treated as a cache miss, falls
  back to `Pending` for that MR/section, logged but not surfaced to the
  user. Cache file carries a schema version field so future format changes
  can detect mismatch cheaply.
- **No TTL**: cached data is always shown regardless of age; age is
  informational only, never a gate that falls back to `Pending`.
- **Resolution handoff**: `Stale → resolved` reuses the existing streamed
  per-MR `update_cell` path from
  [Streamed-enrichment merge mechanics](04-streamed-enrichment-merge-mechanics.md)
  — no new mechanism, `Stale` is just another starting cell state that
  gets overwritten when the real value lands.
