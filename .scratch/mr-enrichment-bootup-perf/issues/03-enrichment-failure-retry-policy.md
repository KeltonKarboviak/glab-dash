Type: grilling
Status: (open)
Blocked by: 01

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
