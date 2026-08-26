Label: wayfinder:map

## Destination

A locked set of architectural decisions for glab-dash v1: a GitLab merge-request
dashboard TUI (Python + Textual + python-gitlab, gitlab.com only) — enough
settled that implementation can begin without re-litigating the big calls.
This is not a spec-to-hand-off; the user is both planner and implementer.
The codebase is structured per Clean Architecture (3 layers: domain,
application, infrastructure), enforced by ArchUnitPython tests.

## Notes

- Domain vocabulary lives in `CONTEXT.md` — read it before naming concepts
  (section, scope, note, discussion, credential source/resolution).
- Reference repos for exploration: gh-dash at
  `/Users/kelton.karboviak/Code/open-source/gh-dash` (Go/Bubble Tea prior art),
  python-gitlab at `/Users/kelton.karboviak/Code/open-source/python-gitlab`
  (the GitLab SDK, sync-only — REST calls must run off Textual's event loop
  via `run_worker`).
- Dev tooling is locked, not open: `uv`, `ruff`, `mise`, `prek`, `pytest` +
  Textual's `Pilot`/`pytest-textual-snapshot`, `structlog` forwarded through
  stdlib `logging` via Textual's `TextualHandler`. Python 3.14+.
- ArchUnitPython reference repo for exploration:
  `/Users/kelton.karboviak/Code/open-source/ArchUnitPython`.
- Hypothesis reference repo for exploration:
  `/Users/kelton.karboviak/Code/open-source/hypothesis`.
- PBT guidance: property-test pure Domain-layer logic (filter matching,
  credential-priority resolution, YAML-schema validation rules) where a
  clear invariant exists. Skip PBT for Textual widgets/screens, network
  I/O, and Pydantic-validated models (that would test Pydantic, not our
  logic) — Infrastructure stays example/unit-tested. No dedicated ticket;
  judged per-function during implementation.

## Decisions so far

- **Destination and v1 scope** — locked architectural decisions (not a spec);
  v1 = merge requests only, read-focused, top-level comment submission
  deferred as a stretch goal (inline diff comments preferred when it lands).
- **Target** — gitlab.com only, no self-hosted support in v1.
- **Section scoping** — sections may target project scope, group scope, or
  global scope (all MRs visible to the user); filters are structured YAML
  keys (`state`, `author`, `assignee`, `labels`, `scope`), not a query-string
  DSL.
- **Credential resolution** — glab CLI config → `GITLAB_TOKEN` env var →
  glab-dash's own config file token, in that priority order.
- **glab CLI token storage** — glab stores its token under the `token` key
  in `~/.config/glab-cli/config.yml` (XDG, overridable via `GLAB_CONFIG_DIR`)
  and itself already reads the `GITLAB_TOKEN` env var, taking precedence
  over its `--token` flag — confirming glab-dash's own `GITLAB_TOKEN` source
  aligns with, rather than collides with, glab's convention (see
  [glab CLI token storage & env var research](issues/01-glab-cli-auth-research.md)).
- **Packaging/distribution** — deferred; not a blocker for architecture.
- **Layout** — tabs (one per section) + toggleable preview pane, mirroring
  gh-dash.
- **Refresh** — background interval polling (configurable) plus a manual
  refresh keybinding.
- **Config file location** — XDG (`$XDG_CONFIG_HOME/glab-dash/config.yml`,
  falling back to `~/.config/glab-dash/config.yml`), with an optional
  repo-local `.glab-dash.yml` override — mirrors gh-dash.
- **Preview pane content** — MR description + all discussions (threads of
  notes) + diff view, all in one pane.
- **Diff rendering** — plain colorized unified-diff text, rendered in-process
  in a Textual widget. No external pager, no syntax highlighting in v1.
- **Dev tooling** — `uv`, `ruff`, `mise`, `prek`, `pytest` + Textual
  `Pilot`/`pytest-textual-snapshot`, `structlog` via `TextualHandler`.
- **Python version** — target 3.14+.
- **Section YAML schema** — `scope` key (`project`/`group`/`global`) paired
  with a matching `project`/`group` path key (required for its scope);
  `state` accepts GitLab's own `opened`/`closed`/`merged`/`all` (default
  `opened`); `author`/`assignee` are a username string or literal `"@me"`;
  `labels` is a list, AND-matched; `title` required, ordering is YAML list
  position, no per-section refresh override (see
  [Section YAML schema](issues/02-section-yaml-schema.md)).
- **Clean Architecture layers** — destination-level, not deferred: 3
  layers, `src/glab_dash/{domain,application,infrastructure}/`. Domain is
  stdlib-only (plain dataclasses, no python-gitlab/PyYAML/Pydantic
  imports) and holds entities plus pure logic (filter matching,
  credential-priority resolution). Application holds use cases, depending
  only on Domain plus gateway interfaces (never concrete Infrastructure).
  Infrastructure holds python-gitlab calls, Textual widgets/screens/App,
  YAML loading, and Pydantic models — Pydantic validates/parses external
  data (YAML config, GitLab API payloads) at the boundary, then maps into
  plain Domain entities; Infrastructure never decides, only displays/
  dispatches. Enforced by ArchUnitPython as a normal `pytest` test
  (`tests/test_architecture.py`), so it runs locally, in `prek`, and in CI
  with no separate tooling.
- **ArchUnitPython rule idioms** — its real fluent API covers all needed
  rules with no gaps: folder-to-folder `should_not().depend_on_files()`,
  a declarative layered form (`project_layers(...).may_only_depend_on_layers()`),
  and `should_not().depend_on_external_modules().matching("pydantic")` for
  third-party bans; no fixture/scan step needed, just `assert_passes(rule)`
  in a plain pytest function (see
  [ArchUnitPython rule idioms research](issues/05-archunitpython-rule-idioms.md)).

- **V1 keybindings** — hardcoded (not user-overridable) for v1: `j/k`+
  arrows list nav, `g/G` first/last, `[`/`]` section tabs, `Tab` toggle
  preview pane, `Enter`/`Esc` to focus/unfocus the preview (focused pane
  reuses `j/k`+arrows to scroll the diff — no separate page keys), `r`
  manual refresh, `q`/`ctrl+c` quit — gh-dash-derived scheme (see
  [V1 keybindings](issues/03-v1-keybindings.md)).
- **MR row layout** — fixed (not user-configurable) column set mirroring
  gh-dash's PR row shape: state icon, extended-title block, labels,
  unresolved discussion count, approvals as `"approved/required"`,
  pipeline status icon, +/- line stats, updated-at; width/visibility
  configurability deferred to a config-schema follow-up (see
  [MR row layout](issues/04-mr-row-layout.md)).
- **Config schema extras** — top-level `refresh_interval` (int, seconds,
  default `60`) and `token` (optional string); no `theme`/`colors` key
  (deferred), no `keybindings` key (omitted, not reserved), no `host`/
  `gitlab_url` config key — the GitLab base URL is a single named constant
  in the Infrastructure layer, never inlined at call sites, so self-hosted
  support later is a one-place change (see
  [Config schema extras](issues/06-config-schema-extras.md)).

## Not yet specified

- Inline diff comment mechanics (position dict construction against
  base/head/start SHAs) — deferred stretch goal from the comment-submission
  decision; not sharp enough to ticket until top-level comments exist.
- Packaging/distribution mechanics (PyPI, `pipx`, Homebrew) — deferred per
  Decisions so far; revisit once the core app works.

## Out of scope

- Issues dashboard — v1 is merge requests only.
- Notifications view — not requested for v1.
- Branches/repo view and local git integration (e.g. checking out a branch,
  shelling into a local repo) — no git-operations scope discussed for v1.
- Custom keybinding shell-out (gh-dash's `command` templates to run e.g.
  `lazygit`, `tmux`) — no actions beyond viewing/commenting are in scope yet.
