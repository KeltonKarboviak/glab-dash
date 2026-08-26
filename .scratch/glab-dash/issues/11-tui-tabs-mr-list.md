# 11 — TUI rendering: tabs + MR list for a project section

**What to build:** the first fully end-to-end demoable slice. A Textual
App shell renders one tab per configured section (in YAML order), and a
project-scoped tab's table lists its MRs using ticket 10's use case,
showing the core row fields available directly off the MR entity: state
icon, extended-title block, labels, `+`/`-` line stats, and updated-at
time. GitLab calls run via Textual's `run_worker`, never called directly
from an event handler.

**Blocked by:** 10 — Gateway + use case: list MRs for a project section.

Status: complete

- [x] Running the app against a configured project section shows a tab with that section's title
- [x] The tab's table lists MRs with state icon, title, labels, and updated-at
- [x] Section tabs appear in YAML-declared order
- [x] The GitLab fetch backing the table runs via `run_worker`, not inline in an event handler

## Comments

`+`/`-` line stats descoped: GitLab's list-merge-requests endpoint (used by
ticket 10's gateway) has no line-diff data — only a `changes_count` file
count on the single-MR endpoint. Real line stats require a per-MR
`/diffs` call, which is ticket 14's (row enrichment) territory. Deferred
there rather than guessed at here.
