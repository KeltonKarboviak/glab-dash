# ArchUnitPython rule idioms

Source repo (local clone): `/Users/kelton.karboviak/Code/open-source/ArchUnitPython`

## Install / import surface

`pip install archunitpython`. Top-level public API imported from the `archunitpython`
package: `project_files`, `project_layers`, `project_slices`, `project_graph`,
`assert_passes`, `CheckOptions`, `rules_from_config`.

Source: README.md lines 37, 124, 148, 202, 293, 486, 521 (all `from archunitpython import ...`).

## Wiring a rule into a pytest test

Pattern is: build a `rule` via the fluent API, then either
`assert_passes(rule)` (pytest-friendly, gives a formatted violation message) or
call `rule.check()` yourself and assert `len(violations) == 0`. No fixture or
scan step is required — `project_files("src/")` / `project_layers("src/")` do the
scanning internally when `.check()` runs.

Source: README.md lines 119-141:
```python
from archunitpython import project_files, assert_passes

def test_my_architecture():
    rule = project_files("src/").should().have_no_cycles()
    assert_passes(rule)
```
and the "Any Other Framework" variant (README.md lines 135-141) using `.check()` directly.

## Rule 1: file/folder dependency direction ("X must not import Y")

Built via `project_files(root).in_folder(pattern).should_not().depend_on_files().in_folder(pattern)`.

Source: README.md lines 46-55 (`test_presentation_should_not_depend_on_database`) and
confirmed in the actual fluent-API source, `src/archunitpython/files/fluentapi/files.py`:
- `in_folder` defined at line 67 (on the initial builder) and line 98 (on `FilesShouldCondition`)
- `should_not()` defined at line 81 and line 112, returning `NegatedMatchPatternFileConditionBuilder`
- `depend_on_files()` on that negated builder at line 183, returning `DependOnFileConditionBuilder`
- `DependOnFileConditionBuilder.in_folder` at line 250 (the target-side folder filter)

Confirmed against `tests/files/test_files_fluentapi.py`, which exercises this exact
`.should_not().depend_on_files().in_folder(...)` chain against fixtures.

## Rule 2: named layers with an explicit allow-list ("layer X may only depend on layer Y")

Alternative, more declarative way to express layered rules using `project_layers`,
`.layer(name).defined_by_folder(pattern)`, then `.where_layer(name).may_only_depend_on_layers(*names)`.

Source: README.md lines 292-309:
```python
from archunitpython import project_layers

def test_clean_architecture_layers():
    rule = (
        project_layers("src/")
        .layer("presentation").defined_by_folder("**/presentation/**")
        .layer("business").defined_by_folder("**/business/**")
        .layer("database").defined_by_folder("**/database/**")
        .where_layer("presentation")
        .may_only_depend_on_layers("business")
        .where_layer("business")
        .may_only_depend_on_layers()
        .where_layer("database")
        .may_only_depend_on_layers()
    )
    assert_passes(rule)
```

Confirmed in source `src/archunitpython/layers/fluentapi/layers.py`:
- `project_layers(project_path)` function at line 18, returns `LayeredArchitecture`
- `LayeredArchitecture` class at line 26
- `.layer(name)` method at line 35, returns `LayerDefinitionBuilder` (class at line 71)
- `.where_layer(name)` method at line 40, returns `LayerDependencyRuleBuilder` (class at line 95)
- `.may_only_depend_on_layers(...)` method at line 102

Confirmed against real usage in `tests/layers/test_layers.py` lines 1-49, e.g.:
```python
_sample_layers()
    .where_layer("controllers")
    .may_only_depend_on_layers("services")
    ...
    .check()
```
An empty `may_only_depend_on_layers()` call (no args) means "this layer may depend on
nothing" — used for the innermost layer (`database`/`models` in both examples).
`may_only_depend_on_layers` is an allow-list API: it does not need a separate
"must-not" rule per forbidden pair — everything not listed is implicitly forbidden.

## Rule 3: forbidding third-party/external module imports ("domain must not import pydantic")

Yes, ArchUnitPython supports this explicitly via `depend_on_external_modules().matching(name)`,
chained off `.should_not()` the same way as file-to-file rules.

Source: README.md lines 313-322 ("External Dependencies" section):
```python
def test_domain_does_not_import_requests():
    rule = (
        project_files("src/")
        .in_folder("**/domain/**")
        .should_not()
        .depend_on_external_modules()
        .matching("requests")
    )
    assert_passes(rule)
```

Confirmed in source `src/archunitpython/files/fluentapi/files.py`:
- `depend_on_external_modules()` defined on the positive builder at line 132, and on
  `NegatedMatchPatternFileConditionBuilder` at line 187 (this is the one reached after
  `.should_not()`), returning `DependOnExternalModuleConditionBuilder`
- `.matching(module_name)` defined at line 280 (and again at line 395 on a related
  condition class), returns `DependOnExternalModuleCondition`

Confirmed against `tests/files/test_files_fluentapi.py` lines 14-17 and 84-143, which
import `ViolatingExternalModuleDependency` from
`archunitpython.files.assertion.depend_on_external_modules` and exercise
`.depend_on_external_modules().matching("json")` / `.matching("requests")`, including a
multi-`.matching()` chain (lines 109-112) to check several module names in one rule.

`.matching()` accepts glob-style strings or `re.compile(...)` patterns (same pattern
system as `in_folder`/`with_name`/`in_path`, documented README.md lines 680-710), so
`matching("pydantic")`, `matching("yaml")`, `matching("gitlab")` are each valid, and can
be combined into one rule via repeated `.matching(...)` calls (confirmed pattern from
the multi-matching test above).

## Worked example: `tests/test_architecture.py` for glab-dash

```python
from archunitpython import project_files, project_layers, assert_passes

SRC = "src/glab_dash"


def test_domain_does_not_depend_on_infrastructure():
    rule = (
        project_files(SRC)
        .in_folder("**/domain/**")
        .should_not()
        .depend_on_files()
        .in_folder("**/infrastructure/**")
    )
    assert_passes(rule)


def test_domain_does_not_depend_on_application():
    rule = (
        project_files(SRC)
        .in_folder("**/domain/**")
        .should_not()
        .depend_on_files()
        .in_folder("**/application/**")
    )
    assert_passes(rule)


def test_application_does_not_depend_on_infrastructure():
    rule = (
        project_files(SRC)
        .in_folder("**/application/**")
        .should_not()
        .depend_on_files()
        .in_folder("**/infrastructure/**")
    )
    assert_passes(rule)


def test_domain_does_not_import_third_party_packages():
    rule = (
        project_files(SRC)
        .in_folder("**/domain/**")
        .should_not()
        .depend_on_external_modules()
        .matching("pydantic")
        .matching("yaml")
        .matching("gitlab")
    )
    assert_passes(rule)


# Equivalent layered form for the first three rules, as a single allow-list rule:
def test_layered_architecture():
    rule = (
        project_layers(SRC)
        .layer("domain").defined_by_folder("**/domain/**")
        .layer("application").defined_by_folder("**/application/**")
        .layer("infrastructure").defined_by_folder("**/infrastructure/**")
        .where_layer("domain")
        .may_only_depend_on_layers()
        .where_layer("application")
        .may_only_depend_on_layers("domain")
        .where_layer("infrastructure")
        .may_only_depend_on_layers("domain", "application")
    )
    assert_passes(rule)
```

Note: `project_files(SRC)` / `project_layers(SRC)` take the project root to scan
(here `src/glab_dash`) — no separate fixture or explicit scan call is needed; scanning
happens inside `.check()` (invoked by `assert_passes`).

## Things NOT invented / caveats

- All three requested rules ARE expressible with the real, documented API — no gaps.
- `may_only_depend_on_layers()` with no arguments (used for `domain` above) means
  "this layer must not depend on any other declared layer," per
  `tests/layers/test_layers.py` usage (e.g. the innermost `models` layer in that file).
- `depend_on_external_modules().matching(...)` matches on the imported module name
  itself (e.g. `"pydantic"`, `"yaml"`, `"gitlab"`), not on file paths — confirmed by the
  test file importing `ViolatingExternalModuleDependency` and asserting on module names
  like `"json"`/`"requests"`/`"typing"` in `tests/files/test_files_fluentapi.py`.
