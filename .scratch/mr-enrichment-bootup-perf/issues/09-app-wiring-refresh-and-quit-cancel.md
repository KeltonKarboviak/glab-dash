# 09 — App wiring: refresh-cancel & quit-cancel for enrichment

**What to build:** Pressing refresh (`r`) or hitting the auto-refresh
interval while a section's enrichment is in progress stops that stale pass
cleanly and starts a fresh one against the newly-fetched rows — no stale
results landing on new table state. Quitting (`q`) during enrichment exits
promptly, same as it already does for the first-paint fetch worker.

**Blocked by:** 08 — App wiring: columns, row keys, first enrichment pass

**Status:** ready-for-agent

- [ ] Reusing the enrichment worker name `f"section-{index}-enrich"` on every
      refresh is confirmed sufficient for Textual to auto-cancel the prior
      cycle's worker before the new one starts
- [ ] `tests/infrastructure/test_app.py` covers: a refresh (`r`) while
      enrichment is in-flight results in exactly one enrichment pass
      completing per section afterward, with no leftover stale update
      landing on the new table state (mirrors
      `test_refresh_preserves_the_active_tab_and_cursor_position`)
- [ ] `tests/infrastructure/test_app.py` covers: quitting (`q`) while an
      enrichment worker is running exits promptly, mirroring existing quit
      behavior for the first-paint fetch worker
- [ ] Existing navigation (`j`/`k`/`g`/`G`, tab switching, preview pane)
      verified unaffected by an in-progress enrichment worker
