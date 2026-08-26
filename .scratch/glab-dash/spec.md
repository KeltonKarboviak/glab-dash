Status: ready-for-agent

## Problem Statement

Tracking merge requests across multiple GitLab projects and groups today means
either living in the GitLab web UI (slow, tab-heavy, not keyboard-driven) or
running `glab mr list` repeatedly by hand. There is no fast, terminal-native
way to see "what MRs need my attention right now" across several projects and
groups at once, drill into an MR's discussions and diff, and refresh that view
on an interval without leaving the terminal.

## Solution

`glab-dash`: a Textual-based TUI, modeled on gh-dash's UX, that renders
user-defined **sections** (project-, group-, or global-scoped MR lists) as
tabs, each populated from python-gitlab against gitlab.com. Selecting an MR
opens a toggleable preview pane showing its description, discussions, and
diff. Sections refresh on a configurable interval or on manual keypress. All
GitLab-facing calls run through python-gitlab off Textual's event loop.

## User Stories

1. As a GitLab user, I want to define one or more sections in a YAML config
   file, so that I can group MRs the way I think about my work (by project,
   by team's group, or "everything assigned to me").
2. As a GitLab user, I want a section scoped to a single project, so that I
   can watch one repo's open MRs.
3. As a GitLab user, I want a section scoped to a group, so that I can watch
   every project under a team without listing each one.
4. As a GitLab user, I want a global-scoped section, so that I can see every
   MR visible to me regardless of project or group.
5. As a GitLab user, I want to filter a section by state (`opened`/`closed`/
   `merged`/`all`), so that I can separate "needs review" from "already
   merged" work.
6. As a GitLab user, I want to filter a section by author, so that I can see
   only my own open MRs.
7. As a GitLab user, I want to filter a section by author using the literal
   `"@me"`, so that I don't have to hardcode my own username in config.
8. As a GitLab user, I want to filter a section by assignee, so that I can see
   MRs assigned to me for review.
9. As a GitLab user, I want to filter a section by a list of labels
   (AND-matched), so that I can narrow to MRs tagged with all of a specific
   set of labels.
10. As a GitLab user, I want each section to have a required, freeform title,
    so that I can label tabs meaningfully regardless of their filters.
11. As a GitLab user, I want section tabs to appear in the order I listed them
    in YAML, so that I control the tab layout without a separate ordering key.
12. As a GitLab user, I want to switch between section tabs with `[` and `]`,
    so that I can move through my sections without a mouse.
13. As a GitLab user, I want to move the row cursor within a section's MR list
    with `j`/`k` or the arrow keys, so that I can navigate the way I already
    do in similar TUIs.
14. As a GitLab user, I want `g`/`G` to jump to the first/last row, so that I
    can reach the ends of a long list quickly.
15. As a GitLab user, I want each MR row to show a state icon, an
    extended-title block, labels, the unresolved discussion count, approvals
    as `"approved/required"`, a pipeline status icon, `+`/`-` line stats, and
    the updated-at time, so that I can triage an MR without opening it.
16. As a GitLab user, I want the unresolved discussion count to count
    Discussions (threads) whose `resolved` field is false, not a raw note
    tally, so that the number reflects "things still needing action," not
    total chatter.
17. As a GitLab user, I want to toggle a preview pane with `Tab`, so that I
    can see MR detail without leaving the list view permanently.
18. As a GitLab user, I want `Enter` to focus the preview pane and `Esc` to
    return focus to the list, so that scrolling the diff doesn't fight with
    list navigation.
19. As a GitLab user, I want the focused preview pane to scroll with the same
    `j`/`k`/arrow keys as the list, so that I don't have to learn a second
    navigation scheme.
20. As a GitLab user, I want the preview pane to show the MR description, all
    discussions (every thread of notes, not just top-level notes), and a diff,
    in one pane, so that I get full context without extra navigation.
21. As a GitLab user, I want the diff rendered as plain colorized unified-diff
    text in-process, so that I don't need an external pager or syntax
    highlighter installed to read a diff.
22. As a GitLab user, I want sections to refresh automatically on a
    configurable interval, so that the dashboard stays current without my
    intervention.
23. As a GitLab user, I want a manual refresh keybinding (`r`), so that I can
    force an update without waiting for the interval.
24. As a GitLab user, I want to quit with `q` or `Ctrl+C`, so that exiting
    follows conventions I already know.
25. As a GitLab user, I want glab-dash to find my GitLab token automatically
    from the `glab` CLI's stored config first, so that I don't have to
    configure credentials separately if I already use `glab`.
26. As a GitLab user, I want glab-dash to fall back to the `GITLAB_TOKEN`
    environment variable if no `glab` CLI token is found, so that CI-style or
    environment-based credential setups still work.
27. As a GitLab user, I want glab-dash to fall back to a `token` field in its
    own config file as a last resort, so that I have an explicit override
    available when the other two sources don't apply.
28. As a GitLab user, I want my config file to live at the standard XDG
    location (`$XDG_CONFIG_HOME/glab-dash/config.yml`, or
    `~/.config/glab-dash/config.yml`), so that it follows the convention other
    CLI tools I use already follow.
29. As a GitLab user, I want an optional repo-local `.glab-dash.yml` to
    override the XDG config when present, so that I can have per-repo section
    definitions.
30. As a GitLab user, I want a `refresh_interval` config key (seconds,
    default `60`), so that I can tune polling frequency without touching
    code.
31. As a developer maintaining glab-dash, I want the GitLab base URL
    (`gitlab.com`) defined as a single named constant in the Infrastructure
    layer and injected wherever a GitLab client/gateway is constructed —
    never a literal string at the call site — so that adding self-hosted
    support later is a one-place change instead of a grep-and-replace, even
    though v1 exposes no config key for it.
32. As a developer maintaining glab-dash, I want Domain to stay stdlib-only
    (no python-gitlab/PyYAML/Pydantic imports), so that filter-matching and
    credential-priority logic stays trivially unit-testable and free of I/O.
33. As a developer maintaining glab-dash, I want Application to depend only
    on Domain plus gateway interfaces (never concrete Infrastructure), so
    that use cases can be tested against fake gateways without a network or a
    running TUI.
34. As a developer maintaining glab-dash, I want Infrastructure to own all
    python-gitlab calls, Textual widgets/screens/App, YAML loading, and
    Pydantic models, so that external-data validation and I/O are isolated
    from business logic.
35. As a developer maintaining glab-dash, I want the three-layer dependency
    rule enforced by an ArchUnitPython check running as a normal `pytest`
    test, so that layering violations fail CI the same way any other test
    failure would, with no separate tooling to remember to run.
36. As a developer maintaining glab-dash, I want GitLab API calls to run via
    Textual's `run_worker`, so that python-gitlab's synchronous calls never
    block the event loop and freeze the UI.
37. As a developer maintaining glab-dash, I want structlog output forwarded
    through stdlib `logging` via Textual's `TextualHandler`, so that logs are
    visible in Textual's dev console without a second logging pipeline.

## Implementation Decisions

- **Architecture**: three layers under `src/glab_dash/{domain,application,infrastructure}/`,
  enforced by an ArchUnitPython rule set (folder-to-folder `should_not().depend_on_files()`
  plus a declarative `project_layers(...).may_only_depend_on_layers()`) running as a
  plain `pytest` test (`tests/test_architecture.py`).
  - Domain: stdlib-only. Plain dataclasses for entities (MR, Section, Discussion,
    etc.) plus pure functions: filter matching (state/author/assignee/labels
    against an MR) and credential-priority resolution (given available sources,
    pick the first present in priority order).
  - Application: use cases (e.g. "list MRs for a section", "resolve credential
    token", "load config") depending only on Domain plus gateway interfaces
    (protocols) it defines. Never imports concrete Infrastructure.
  - Infrastructure: python-gitlab-backed gateway implementations, Textual
    App/Screens/Widgets, YAML config loading, Pydantic models for
    parsing/validating YAML config and GitLab API payloads at the boundary,
    then mapping into Domain entities before handing them to Application.
- **GitLab base URL**: a single named constant (e.g. `GITLAB_COM_URL`) defined
  in the Infrastructure module that constructs the python-gitlab client/gateway.
  No config key exposes it in v1; it is passed as a parameter into gateway
  construction rather than referenced as a literal at each call site, so a
  future `host`/`gitlab_url` config key only has to change this one
  construction point.
- **Credential resolution order**: glab CLI stored config (`~/.config/glab-cli/config.yml`,
  `token` key, `GLAB_CONFIG_DIR`-overridable) → `GITLAB_TOKEN` env var →
  glab-dash's own config file `token` key. Implemented as a pure Domain
  function taking already-fetched candidate values (Infrastructure is
  responsible for fetching each candidate; Domain only picks the first
  present one) so the resolution logic itself needs no I/O to test.
- **Config schema (top-level)**:
  - `sections`: required list, order = tab order. Each section: `title`
    (required string), `scope` (`project`/`group`/`global`), a `project` or
    `group` path key matching `scope` (required for `project`/`group`, absent
    for `global`), `state` (`opened`/`closed`/`merged`/`all`, default
    `opened`), `author` (username string or `"@me"`, optional), `assignee`
    (username string or `"@me"`, optional), `labels` (list of strings,
    AND-matched, optional).
  - `refresh_interval`: optional int, seconds, default `60`.
  - `token`: optional string, lowest-priority credential source.
  - No `theme`/`colors`, no `keybindings`, no `host`/`gitlab_url` key in v1.
- **Config file resolution**: XDG path (`$XDG_CONFIG_HOME/glab-dash/config.yml`
  falling back to `~/.config/glab-dash/config.yml`) as the base, overridden
  entirely by a repo-local `.glab-dash.yml` when present (not merged).
- **Layout**: tabs (one per section, in YAML order) + toggleable preview pane
  (Textual widgets), mirroring gh-dash's layout.
- **MR row columns** (fixed order, not user-configurable in v1): state icon,
  extended-title block, labels, unresolved discussion count, approvals as
  `"approved/required"`, pipeline status icon, `+`/`-` line stats, updated-at.
- **Unresolved discussion count**: derived from `mergerequest.discussions.list()`,
  counting discussions with `resolved is False` — not from `mergerequest.notes.list()`.
- **Preview pane content**: MR description + all discussions (every note in
  every thread) + diff, combined in one scrollable pane.
- **Diff rendering**: plain colorized unified-diff text rendered by a Textual
  widget in-process. No external pager, no syntax-highlighting library.
- **Keybindings** (hardcoded, no override mechanism in v1): `j`/`k`/arrows
  list nav; `g`/`G` first/last; `[`/`]` section tabs; `Tab` toggle preview
  pane; `Enter` focus preview / `Esc` return focus to list (focused pane
  reuses `j`/`k`/arrows to scroll); `r` manual refresh; `q`/`Ctrl+C` quit.
- **Refresh**: background interval polling via Textual's timer/worker
  mechanism at `refresh_interval` seconds, plus the `r` manual-refresh
  keybinding triggering the same code path.
- **GitLab I/O**: all python-gitlab calls run via Textual's `run_worker`
  (thread workers, since python-gitlab is sync-only) — never called directly
  from a Textual event handler.
- **Logging**: `structlog` configured to render through stdlib `logging`,
  forwarded to Textual's `TextualHandler` so log output lands in Textual's
  built-in dev console.
- **Dev tooling** (locked): `uv` for dependency/venv management, `ruff` for
  lint/format, `mise` for tool version pinning, `prek` for pre-commit hooks,
  `pytest` as the test runner. Python 3.14+.

## Testing Decisions

- Tests assert observable behavior (returned MR lists, rendered row content,
  resolved credential value, parsed config shape) — never internal call
  counts or private state.
- **Domain**: direct unit tests on pure functions — filter matching (state/
  author/assignee/labels against a Domain MR entity) and credential-priority
  resolution (given a set of candidate token values, which one wins). No
  mocking needed; these are the property-testing candidates noted in
  `map.md` where a clear invariant exists (e.g. "resolution always returns
  the first non-empty candidate in priority order").
- **Application**: use-case tests run against fake/in-memory implementations
  of the gateway interfaces (e.g. a fake MR-listing gateway seeded with
  canned Domain entities) — no real python-gitlab client, no Textual app.
  Verifies use cases correctly apply Domain filter logic and shape results,
  independent of how data was fetched.
- **Infrastructure**:
  - python-gitlab gateway adapters: tested with recorded HTTP fixtures
    (VCR-style cassette) or minimal contract tests confirming the adapter
    maps GitLab API payloads into Domain entities correctly.
  - Textual widgets/screens/App: tested with Textual's `Pilot` and
    `pytest-textual-snapshot`, per the tooling already locked in `map.md`.
  - YAML config loading and Pydantic models: example-based tests (valid
    config parses into expected structure; invalid config raises with a
    clear error) — not property-tested, per the PBT guidance in `map.md`
    (testing Pydantic validation would just test Pydantic).
- **Architecture test**: `tests/test_architecture.py` runs the ArchUnitPython
  layer rules as a normal `pytest` test — no separate CI step.
- Prior art: none yet in this repo (pre-implementation); gh-dash
  (`/Users/kelton.karboviak/Code/open-source/gh-dash`) is UX prior art only,
  not a testing-pattern source (different language/stack).

## Out of Scope

- Issues dashboard, notifications view, branches/repo view, and local git
  integration (checking out branches, shelling into a repo) — no scope
  discussed for v1.
- Custom keybinding shell-out to external commands (gh-dash's `command`
  templates for e.g. `lazygit`, `tmux`).
- Top-level or inline MR comment submission — deferred stretch goal;
  inline diff comment mechanics (position dict against base/head/start
  SHAs) are not sharp enough to spec until top-level commenting exists.
- Self-hosted GitLab instance support — v1 is gitlab.com-only; the base-URL
  constant decision exists solely to make this a one-place change later, not
  to implement it now.
- Theme/color customization and keybinding override support.
- Packaging/distribution (PyPI, `pipx`, Homebrew).

## Further Notes

- This spec covers the full v1 destination locked in `.scratch/glab-dash/map.md`;
  all prerequisite architectural questions (auth, YAML schema, keybindings,
  row layout, ArchUnitPython idioms, config schema extras) are already
  resolved — see the linked issues under `.scratch/glab-dash/issues/` for the
  reasoning behind each locked decision.
- No triage-label remapping exists for this repo (`triage-labels.md` was
  never generated via `/setup-matt-pocock-skills`), so this spec's `ready-for-agent`
  status line uses the canonical mattpocock-skills label string as-is, per
  this repo's own `Status:` convention documented in
  `docs/agents/issue-tracker.md`.
