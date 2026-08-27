# 15 — Keyboard navigation & quit

**What to build:** hardcoded keybindings for moving around the dashboard:
`j`/`k`/arrow keys move the row cursor within a section's MR list, `g`/`G`
jump to the first/last row, `[`/`]` switch between section tabs, and `q` or
`Ctrl+C` quit the app.

**Blocked by:** 11 — TUI rendering: tabs + MR list for a project section.

Status: complete

- [x] `j`/`k` and the arrow keys move the row cursor up/down within the active section's list
- [x] `g`/`G` jump the cursor to the first/last row
- [x] `[`/`]` switch the active section tab left/right, wrapping or clamping at the ends
- [x] `q` and `Ctrl+C` both quit the app cleanly
