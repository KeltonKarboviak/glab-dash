Type: grilling
Status: resolved
Blocked by: 01 (resolved)

## Question

Once enrichment is async and streamed in chunks after first paint (per the
map's Decisions-so-far), what happens when one chunk's fetch fails after
the user is already looking at the rendered list? Options include: leave
those rows permanently in "pending" state with no retry, retry the failed
chunk N times with backoff, or surface a visible per-row error state (and
if so, does the user get a manual retry action, e.g. a keybind).

This is a UX + reliability trade-off with no obvious default — grill it
rather than assuming an answer. Depends on Q1 (domain model for "pending")
being settled first, since a retryable failure needs to be distinguishable
from both "pending" and "enriched."

## Answer

Whole-chunk failure granularity: a transport-level failure (exception raised
before any per-MR data is parsed) marks every row in that chunk as errored.
Per-MR partial GraphQL errors inside an otherwise-successful response are a
separate, rarer case — out of scope for v1.

Retry policy: auto-retry the failed chunk 2 times with 1s then 3s backoff
(enrichment is a background nicety, not the critical path — keep added
latency small rather than fighting rate limits). If retries exhaust, flip
those rows to a visible error state.

Domain model: add a third bare-marker variant to both unions established in
[Pending-enrichment domain model](01-pending-enrichment-domain-model.md):

```python
@dataclass(frozen=True)
class Failed:
    pass

# on MergeRequest:
approvals: Pending | Approvals | Failed = Pending()
line_stats: Pending | LineStats | Failed = Pending()
```

`Failed` carries no payload (same shape as `Pending`) — nothing downstream
needs the underlying exception; log it at the point of failure instead.

Manual retry: a section-wide keybind that re-enriches only rows still
`Failed` for that section (not a full re-fetch of already-enriched rows),
via a new worker named `f"section-{index}-enrich-retry"`, reusing the
existing `Worker.StateChanged` / `_tables_by_worker_name` pattern in
`app.py`. No per-row/cursor-targeted retry — section-wide only.
