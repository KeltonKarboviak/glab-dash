# 13 — Author/assignee/labels filters

**What to build:** extend Domain filter matching and the use case to
support a section's `author` filter (username or the literal `"@me"`
resolving to the authenticated user), `assignee` filter (same rules), and
`labels` filter (list of strings, AND-matched — an MR must carry every
listed label).

**Blocked by:** 10 — Gateway + use case: list MRs for a project section.

Status: closed

- [x] `author` filter matches MRs by exact username
- [x] `author: "@me"` matches MRs authored by the authenticated user
- [x] `assignee` filter matches by exact username and by `"@me"`
- [x] `labels` filter requires all listed labels to be present (AND, not OR)
- [x] Filters compose (e.g. `state` + `author` + `labels` together narrow correctly)
- [x] Domain filter-matching tests cover each filter independently and in combination
