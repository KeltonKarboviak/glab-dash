# 16 — Preview pane

**What to build:** a toggleable preview pane showing a selected MR's
description, all discussions (every note in every thread, not just
top-level notes), and a diff rendered as plain colorized unified-diff text
in-process — all in one scrollable pane. `Tab` toggles the pane's
visibility; `Enter` focuses it (reusing `j`/`k`/arrow keys to scroll instead
of navigating the list); `Esc` returns focus to the list.

**Blocked by:** 11 — TUI rendering: tabs + MR list for a project section.

Status: ready-for-agent

- [ ] `Tab` shows/hides the preview pane for the currently selected MR
- [ ] The pane shows the MR's description, every discussion thread's notes, and a colorized unified diff
- [ ] `Enter` moves focus into the pane; `j`/`k`/arrows then scroll the pane instead of moving the list cursor
- [ ] `Esc` returns focus to the list, restoring list-scoped `j`/`k`/arrow behavior
- [ ] No external pager or syntax-highlighting dependency is used for the diff
