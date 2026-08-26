# 14 — Row enrichment: unresolved discussion count, approvals, pipeline status, +/- line stats

**What to build:** extend the MR gateway to attach per-MR fields not
present on the base MR payload: unresolved discussion count (from
`mergerequest.discussions.list()`, counting discussions whose `resolved`
field is `false` — not a raw note tally), approvals as
`"approved/required"`, a pipeline status icon (from the MR's latest
pipeline), and `+`/`-` line diff stats.

`+`/`-` line stats were descoped from ticket 11 because GitLab's
list-merge-requests endpoint (used by ticket 10's gateway) has no
line-diff data — only a `changes_count` file count on the single-MR
endpoint. Getting real added/removed line counts needs a per-MR call
(e.g. `mergerequest.changes()` or the `/diffs` endpoint with
`unidiff=true`) summed across files, same enrichment shape as the other
three fields here.

**Blocked by:** 10 — Gateway + use case: list MRs for a project section.

Status: ready-for-agent

- [ ] Unresolved discussion count reflects discussions with `resolved is False`, verified against a fixture with both resolved and unresolved discussions
- [ ] Approvals render as `"approved/required"` sourced from the MR's approval state
- [ ] Pipeline status icon reflects the MR's latest pipeline status
- [ ] `+`/`-` line stats are sourced from a per-MR diff/changes call and reflect total lines added/removed across the MR's files
- [ ] Domain MR entity carries these four fields; Application/Infrastructure tests cover the mapping from GitLab payloads
