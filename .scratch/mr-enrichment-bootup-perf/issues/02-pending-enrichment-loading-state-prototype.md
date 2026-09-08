Type: prototype
Status: (open)

## Question

What does a not-yet-enriched cell look like in the `DataTable` before its
enrichment chunk lands — a spinner glyph, a placeholder string (`"…"`,
`"-"`), or left blank until filled? Build a cheap, rough prototype of the
table with some rows enriched and some pending to react to; this is a "how
should it look" question, not one to settle by discussion.

Context: rendering lives in `src/glab_dash/infrastructure/tui/rows.py`
(cell formatting) and `src/glab_dash/infrastructure/tui/app.py` (`add_row`
at app.py:225). Resolve with `mattpocock-skills:prototype`.
