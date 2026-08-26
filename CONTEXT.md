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
