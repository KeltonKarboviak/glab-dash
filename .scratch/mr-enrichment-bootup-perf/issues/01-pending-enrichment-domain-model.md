Type: grilling
Status: resolved

## Question

Progressive enrichment means a `MergeRequest` (`src/glab_dash/domain/merge_request.py:33`)
can be on-screen before its enrichment fields (`approvals_given`,
`approvals_required`, diff stats — `lines_added`/`lines_removed`) are known.
Today those fields default to `0`, indistinguishable from "fetched, actually
zero."

Does the domain model need an explicit "pending" representation (e.g. a
sentinel, a union/`Enriched | Pending` split, or `int | None` with `None`
meaning "not yet fetched") so the renderer and the enrichment-merge code can
tell "no data yet" apart from "zero approvals/zero lines changed"? Resolve
with `mattpocock-skills:domain-modeling` — this is a real domain decision
about `MergeRequest`'s shape, not a rendering detail.

Scope: only `approvals_given`, `approvals_required`, `lines_added`,
`lines_removed` — per the map's Decisions-so-far, progressive enrichment
covers `{approvals, diff_stats}` only; `pipeline_status` and
`unresolved_discussion_count` stay on the existing on-demand detail-fetch
path and are out of scope here.

## Answer

Replace the four scalar fields with two independent `Pending | <Value>`
union fields on `MergeRequest`, not one bundled union and not `int | None`:

```python
@dataclass(frozen=True)
class Pending:
    pass

@dataclass(frozen=True)
class Approvals:
    given: int
    required: int

@dataclass(frozen=True)
class LineStats:
    added: int
    removed: int

# on MergeRequest:
approvals: Pending | Approvals = Pending()
line_stats: Pending | LineStats = Pending()
```

Rejected shapes and why:
- **`int | None` per field**: simplest, but loses the "given/required arrive
  together" and "added/removed arrive together" pairing — a stray `None` on
  just one of a pair is a state the domain shouldn't allow.
- **One bundled `enrichment: Pending | Enrichment` covering all four
  fields**: assumes approvals and diff stats always resolve together.
  Checked against `gitlab_gateway.py:41-65` — `_approvals()` and
  `_line_stats()` are already separate REST calls today, and the prototype
  doc (`docs/prototypes/2026-09-04-mr-enrichment-perf-prototypes.md:48-49`)
  shows they have different latency profiles even inside one GraphQL query
  (approvals alone 2.2-7.5s; diff stats alone 3.0-4.1s). Bundling would force
  the renderer to wait for the slower of the two before showing either,
  defeating the point of streamed progressive updates.
- **Full `MergeRequest` variant split** (`PendingMergeRequest` vs
  `EnrichedMergeRequest`): rejected early — forces every consumer to branch
  on type for fields (`title`, `author`, etc.) that exist identically in
  both states.

Net: two pairs, matching the two real fetch calls / two real metrics, each
independently `Pending` until its own fetch resolves.
