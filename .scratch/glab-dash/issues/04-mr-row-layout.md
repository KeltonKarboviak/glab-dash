Type: grilling
Status: resolved

## Question

What metadata columns does each row in an MR list section show (mirroring
gh-dash's per-column, configurable-width/hidden layout)? Candidates from
the GitLab MR model: title, author, source→target branch, state, labels,
approvals count, pipeline status, updated-at. Decide the default column set
and whether column visibility/width is user-configurable in v1 or fixed.

## Answer

Default MR row columns, fixed (not user-configurable) in v1, mirroring
gh-dash's non-compact PR row shape adapted to GitLab's data model:

1. State icon
2. Extended-title block — `project!iid by author` line, source→target
   branch line, title line (gh-dash's `renderExtendedTitle` pattern)
3. Labels
4. Unresolved discussion count (see CONTEXT.md — not a raw note tally)
5. Approvals as `"approved/required"` (e.g. `1/2`) — a count, not a binary
   icon, since GitLab MRs have a configurable required-approvals threshold
   unlike GitHub's APPROVED/CHANGES_REQUESTED review decision
6. Pipeline status icon
7. +/- line diff stats
8. Updated-at

Column width/visibility configurability is deferred — same call as the v1
keybindings ticket: hardcode for v1, revisit as a config-schema follow-up
once the core app works.
