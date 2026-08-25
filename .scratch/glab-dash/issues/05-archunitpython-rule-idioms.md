Type: research
Status: resolved

## Question

How does ArchUnitPython express layer-dependency and import-restriction
rules (e.g. "domain must not import infrastructure", "domain must not
import a specific third-party package")? Survey its API/examples at
`/Users/kelton.karboviak/Code/open-source/ArchUnitPython` so the eventual
`tests/test_architecture.py` for glab-dash's
`domain`/`application`/`infrastructure` layers can be authored correctly
against the real API (not guessed).

## Answer

ArchUnitPython's real fluent API covers all three rules needed
(domain-must-not-import-infrastructure/application,
application-must-not-import-infrastructure, domain-must-not-import
third-party packages) with no gaps:

- Folder-to-folder rule:
  `project_files(root).in_folder("domain").should_not().depend_on_files().in_folder("infrastructure")`
  (`archunitpython/files/fluentapi/files.py`).
- Declarative layered form (allow-list style):
  `project_layers(root).layer("domain").defined_by_folder("domain")` +
  `.where_layer("domain").may_only_depend_on_layers()` (empty args =
  depends on nothing) (`archunitpython/layers/fluentapi/layers.py`).
- Third-party import ban:
  `.should_not().depend_on_external_modules().matching("pydantic")`,
  chainable with repeated `.matching(...)` for `yaml`/`gitlab`
  (`archunitpython/files/fluentapi/files.py`).
- No fixture/scan step needed — build the rule, then `assert_passes(rule)`
  (scanning happens inside `.check()`); a plain pytest function is enough.

Full worked `tests/test_architecture.py` example and file/line citations
recorded in
[ArchUnitPython rule idioms research](../research/archunitpython-rule-idioms.md).

## Comments

**Bug found while implementing issue 08** (2026-08-25): `in_folder("**/glob/**")`
— the exact form used in the ArchUnitPython README's own layer example — never
matches a file living directly inside the target folder, only one nested a
level deeper. `matches_pattern()` tests the glob against the directory path
with the filename stripped (`path-no-filename`); a direct child like
`domain/credentials.py` strips to `.../domain` with no trailing slash, so the
compiled regex's required `/domain/` substring never appears. A file at
`domain/sub/credentials.py` strips to `.../domain/sub`, which does contain
`/domain/`, so only that deeper case is ever caught. This makes every
one-level layer check (subject or object) a silent no-op — `assert_passes`
passes even when a real violation exists.

**Workaround, and the pattern for all future ArchUnitPython folder filters
in this repo:** pass a compiled regex anchored on `(/|$)` instead of a glob
string, e.g. `re.compile(r"/domain(/|$)")` instead of `"**/domain/**"`. The
alternation matches both a nested file (trailing `/`) and a file directly in
the folder (end of string). Applied to all three checks in
`tests/test_architecture.py`. Never write a new `.in_folder("**/name/**")`
glob call in this repo — always use the regex form.
