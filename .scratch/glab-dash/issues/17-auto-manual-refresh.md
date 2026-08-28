# 17 — Auto-refresh + manual refresh

**What to build:** each section refreshes its MR list automatically every
`refresh_interval` seconds (config-driven, default `60`) via Textual's
timer/worker mechanism, reusing the same fetch path as the initial load.
The `r` key triggers an immediate manual refresh through that same code
path.

**Blocked by:** 11 — TUI rendering: tabs + MR list for a project section.

Status: complete

- [x] Sections refresh automatically at the configured `refresh_interval`
- [x] `r` triggers an immediate refresh without waiting for the interval
- [x] Both automatic and manual refresh run through `run_worker`, never blocking the event loop
- [x] Refreshing preserves the current tab and row cursor position where the underlying data still supports it
