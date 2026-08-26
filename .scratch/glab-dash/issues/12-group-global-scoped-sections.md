# 12 — Group- and global-scoped sections

**What to build:** extend the ticket-10 gateway and use case to support
`group`-scoped sections (all MRs under a named GitLab group's projects, via
python-gitlab's `GroupMergeRequestManager`) and `global`-scoped sections
(all MRs visible to the authenticated user, via
`MergeRequestManager`), alongside the existing project scope.

**Blocked by:** 10 — Gateway + use case: list MRs for a project section.

Status: complete

- [x] A group-scoped section lists MRs across every project in that group
- [x] A global-scoped section lists every MR visible to the authenticated user
- [x] `state` filtering applies identically across all three scopes
- [x] Use-case tests cover all three scopes against fake gateways
