# 13 — Stale enrichment state and dimmed rendering

**What to build:** a new `Stale(value)` enrichment state, distinct from
`Pending`/`Failed`/resolved, and its visual treatment: the resolved value
text rendered dimmed, per the resolved staleness-display prototype
(commit `49fd9fe`, branch `prototype/warm-start-staleness-display`).

**Blocked by:** None — can start immediately.

**Status:** ready-for-agent

- [ ] `Stale` added to the `approvals` union (alongside `Pending`, `Approvals`, `Failed`) and the `line_stats` union (alongside `Pending`, `LineStats`, `Failed`), each wrapping the underlying resolved value
- [ ] `render_approvals`/`render_line_stats` render a `Stale` value as the same formatted string as its resolved counterpart, wrapped in `rich.text.Text(value, style="dim")`
- [ ] No glyph or italic styling added — dimmed text only, per the prototype decision
- [ ] Unit tests cover `Stale` rendering distinct from `Pending` (spinner frame), `Failed` (`⚠` glyph), and normal-weight resolved text
