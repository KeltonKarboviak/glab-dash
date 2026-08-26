Type: grilling
Status: closed

## Question

What is the v1 keybinding scheme? Needs at minimum: navigation within an
MR list (up/down, page), switching between section tabs, toggling the
preview pane, triggering manual refresh, quitting, and (given the preview
pane now includes a diff view) scrolling/navigating the diff. Decide
whether these are hardcoded or user-overridable in the config file for v1
(full config schema is fog — Not yet specified — but the keybinding
defaults themselves need to be pinned to build the app).

## Answer

Hardcoded for v1 — no `keybindings:` config section; overriding is
deferred to whenever the full config schema (fog) gets ticketed.

Scheme (gh-dash-derived, vim-style + arrows):

- **List nav**: `j`/`down` and `k`/`up` move selection; `g`/`home` jump to
  first, `G`/`end` jump to last.
- **Section tabs**: `[` previous section, `]` next section.
- **Toggle preview pane**: `Tab`.
- **Focus preview pane / diff**: `Enter` moves focus into the preview pane;
  `Esc` returns focus to the list. While focused, the same `j`/`k` and
  arrow keys scroll the diff/preview content (pane-scoped reuse, not a
  separate keyset) — no page keys added in v1 (`ctrl+u`/`ctrl+d`) since
  Textual's scrollable widgets already support `PageUp`/`PageDown`
  natively.
- **Manual refresh**: `r`.
- **Quit**: `q` / `ctrl+c`.

Rationale for reuse over new bindings: keeps the keymap small and
consistent with gh-dash's prior art (confirmed via
`/Users/kelton.karboviak/Code/open-source/gh-dash` —
`internal/tui/keys/keys.go`), where list nav, tabs, preview toggle, and
refresh use exactly these keys and diff scrolling reuses the list's
up/down bindings once focus shifts to the preview pane.
