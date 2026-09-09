# glab-dash Glossary

## Merge request (MR)

A GitLab merge request. The unit glab-dash's v1 dashboard is built around — no
issues, notifications, or branches in scope for v1.

## Section

A user-configured, named list of merge requests shown as one tab in the
dashboard. Defined in YAML by structured filter keys (`state`, `author`,
`assignee`, `labels`, `scope`) — not a query-string DSL. Term kept from
gh-dash's precedent; no conflicting GitLab concept.

## Scope (of a section)

Which merge requests a section's filters are evaluated against. One of:

- **Project scope** — merge requests within one named GitLab project.
- **Group scope** — merge requests within one named GitLab group (a
  collection of projects).
- **Global scope** — all merge requests visible to the authenticated user,
  across every project/group they can see.

Named to match python-gitlab's own manager split
(`ProjectMergeRequestManager` / `GroupMergeRequestManager` /
`MergeRequestManager`), not invented terms.

## Note

A single comment on a merge request.

## Discussion

A thread of one or more notes on a merge request. May be resolvable. The
preview pane's discussion area shows all of an MR's discussions (threads),
not just top-level notes — matches `mergerequest.discussions.list()`, not
`mergerequest.notes.list()`.

## Unresolved discussion count

The number of a merge request's Discussions whose `resolved` field is
false. Shown per-row in an MR list section; distinct from a raw note tally
(which would count every Note across every Discussion, resolved or not).

## Credential source

One place glab-dash may find a GitLab access token: the `glab` CLI's stored
config, the `GITLAB_TOKEN` environment variable, or glab-dash's own config
file field.

## Credential resolution

The fixed-priority process of trying each credential source in order (glab
CLI config → `GITLAB_TOKEN` → own config file) until one yields a token.

## Enrichment

The set of merge request fields not present on GitLab's MR-list response
and requiring additional API calls to obtain: approvals (given/required),
diff stats (additions/deletions), pipeline status, unresolved discussion
count. Distinct from list fields (title, state, author, assignee, labels),
which arrive on the initial list fetch.

## Boot

The app's startup sequence, from process start to a section's merge
requests being visible on screen. Ends at first paint, not at full
enrichment.

## First paint

The moment a section's merge request list is rendered with list fields
populated. Enrichment fields may still be loading; first paint does not
wait for them.

## Progressive enrichment

Rendering first paint immediately with list fields only, then filling in
each merge request's enrichment fields asynchronously as they arrive,
without blocking or re-rendering the whole list.

## Pending

A merge request's enrichment field (approvals or diff stats) not yet
fetched. Distinct from a fetched zero — a merge request with `Pending`
approvals has no known approval count yet, not zero approvals.

## Approvals

A merge request's approval enrichment: how many approvals it has (given)
and how many it needs (required). Given/required always arrive and update
together as one unit.

## Line stats

A merge request's diff-size enrichment: lines added and lines removed.
Added/removed always arrive and update together as one unit, independently
of Approvals — the two enrichment fields resolve on separate timelines.

## Failed

A merge request's enrichment field (approvals or line stats) that was
attempted but could not be fetched. Distinct from `Pending` — a `Failed`
field will not be retried automatically, whereas `Pending` means the fetch
just hasn't completed yet.

## Warm-start cache

A persisted copy of a previous boot's enriched merge request data, used to
render a subsequent boot's first paint already enriched (possibly stale),
while a fresh fetch refreshes it in the background. Distinct from
progressive enrichment, which has no prior data to show and always starts
from list fields only. Stored as one JSON file per section, keyed by
`project#iid`, holding only enrichment fields (list fields are always
re-fetched fresh). Pruned on every write to drop entries for merge
requests no longer present in the section's latest fetch.

## Stale

A merge request's enrichment field (approvals or line stats) shown from
the warm-start cache at first paint, before the background fetch has
confirmed or replaced it. Distinct from `Pending` (no value known yet) and
`Failed` (fetch attempted and gave up) — `Stale` has a value, just an
unconfirmed one. Resolves to a fresh value through the same per-MR
streaming update path used for `Pending → resolved`, no separate
mechanism.
