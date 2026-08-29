# ty type checker research

Sources: https://github.com/astral-sh/ty, https://docs.astral.sh/ty/,
https://docs.astral.sh/ty/installation/, https://docs.astral.sh/ty/configuration/,
https://docs.astral.sh/ty/reference/rules/, https://github.com/astral-sh/ty-pre-commit.

## 1. Maturity/stability

- `ty` is Astral's Rust-based type checker + language server (same org as
  `uv`/`ruff`). Repo description: "An extremely fast Python type checker
  and language server, written in Rust." ~19.5k GitHub stars as of this
  research (repo pushed within the last day, actively developed).
- Versioning is explicitly `0.0.x`. Docs state directly: "ty does not yet
  have a stable API; breaking changes, including changes to diagnostics,
  may occur between any two versions." No 1.0 date committed; docs
  reference a "Stable" GitHub milestone for tracking, not a firm roadmap.
- Conclusion: pre-1.0, beta-quality by Astral's own admission. Comparable
  to where `ruff` was in its early seed-round days — usable, but expect
  diagnostic/config churn across versions.

## 2. Install method via `uv`

Docs (installation page) give a clear recommendation split:

- `uv add --dev ty` — adds it as a project dev dependency. Docs: "Adding
  ty as a dependency ensures that all developers on the project are using
  the same version of ty." This is the team-consistency path and matches
  how glab-dash already pins `ruff`/`pytest` as dev dependencies via `uv`.
- `uv tool install ty` — global/individual install, for personal use
  across many projects, not pinned per-repo.
- Also documented: `pip install ty`, `pipx install ty`, a standalone
  installer, and Docker images. `uvx ty check` works for one-off/no-install
  runs.
- For glab-dash's locked `uv`-based stack, `uv add --dev ty` is the
  consistent choice (mirrors `ruff`/`pytest`), not `uv tool install`.

## 3. Config surface and ruff overlap

- `ty` reads a `[tool.ty]` table in `pyproject.toml` (confirmed directly:
  "If a `pyproject.toml` file is found, ty will read configuration from
  the `[tool.ty]` table"). A standalone `ty.toml` at the same directory
  level takes precedence over `pyproject.toml` if both exist. Project
  config overrides user-level `~/.config/ty/ty.toml`; CLI flags override
  everything.
- Rule configuration exists per-rule (e.g. docs show ignoring
  `index-out-of-bounds`), with per-file overrides and inline suppression
  comments, but no single "strictness level" preset was found on the
  fetched pages (unlike mypy's `--strict`); rules appear to default to
  sensible severities that can be individually adjusted.
- Ruff overlap: none of substance. Ruff is a linter/formatter — its
  type-adjacent rules (`flake8-annotations`, `ANN*`) only check that type
  annotations *exist* and are stylistically consistent; ruff does not
  evaluate whether the types are *correct*. `ty` performs actual type
  inference/checking (assignment compatibility, argument types, return
  types, etc. — see `invalid-assignment`, `invalid-argument-type`,
  `invalid-return-type` rules). The two tools are complementary, not
  competing: ruff enforces annotation presence/style, `ty` verifies
  annotation correctness. No conflicting rule surface identified.

## 4. `prek`/pre-commit and CI

- Astral maintains an official pre-commit hook repo:
  **https://github.com/astral-sh/ty-pre-commit** (Apache-2.0, 142 stars,
  actively pushed as of this research, `.pre-commit-hooks.yaml`-style
  repo analogous to `astral-sh/ruff-pre-commit`). This slots directly into
  glab-dash's existing `prek` config the same way `ruff-pre-commit` does.
- No separate CI-specific guidance was found beyond "install it like any
  other dev dependency and run it" — because it's a normal CLI (`ty
  check`), it runs in CI exactly like `ruff check`/`pytest` do today: `uv
  run ty check`.
- Performance: docs claim "10x-100x faster than mypy and Pyright,"
  benchmarked against the home-assistant project (Rust implementation,
  same speed positioning as `ruff` vs. flake8/pylint). No reason to expect
  it to be a CI bottleneck for a project glab-dash's size.

## 5. Clean Architecture layering / Pydantic interaction

- `ty` has no awareness of Clean Architecture-style folder/layer rules —
  that's squarely ArchUnitPython's job (see issue 05 research); `ty` only
  checks type correctness within and across files, not import-direction
  policy. No overlap, no conflict — both would coexist in
  `tests/test_architecture.py`/CI as answering different questions.
- Pydantic: `ty` has at least one dedicated Pydantic-aware rule,
  `pydantic-discarded-extra-argument`, confirming it understands Pydantic
  model construction semantics natively (not via a required plugin, unlike
  mypy's separate `pydantic-mypy` plugin requirement). This directly
  matters for glab-dash's Infrastructure-layer Pydantic models (YAML
  config, GitLab API payload parsing) — `ty` should type-check those
  without extra plugin wiring, though the fetched rule-reference page did
  not show an exhaustive Pydantic rule list, so some dynamic-field edge
  cases may still slip through given the pre-1.0 status.

## Recommendation

**Overridden 2026-08-28: adopt now, not adopt-later.** The analysis below
originally concluded adopt-later on stability grounds; the user's call,
after grilling, is to adopt immediately. Rationale: `ty` is a dev-only
dependency, never shipped or run at runtime, so its `0.0.x`/no-stable-API
status is a re-pinning inconvenience on a breaking release, not a
production risk — the stability concern doesn't carry the weight the
original analysis gave it. Installation (`uv add --dev ty`), config
(`[tool.ty]`), and pre-commit integration (`astral-sh/ty-pre-commit`) are
all clean fits for glab-dash's existing `uv`/`ruff`/`prek` stack with no
rule conflicts and native (non-plugin) Pydantic awareness. See
[ticket 20](../issues/20-adopt-ty-type-checker.md) for the implementation.

<details>
<summary>Original recommendation (superseded)</summary>

Adopt-later, not adopt-now. `ty` is officially pre-1.0/beta with an
explicit no-stable-API disclaimer; installation (`uv add --dev ty`),
config (`[tool.ty]`), and pre-commit integration (`astral-sh/ty-pre-commit`)
are all clean fits for glab-dash's existing `uv`/`ruff`/`prek` stack with
no rule conflicts and native (non-plugin) Pydantic awareness — so there's
no technical blocker. The blocker is purely stability risk: pinning a
`0.0.x` tool with "breaking changes... may occur between any two versions"
into a project whose other tooling is deliberately locked/stable adds
version-churn risk for a nice-to-have (extra AI guardrail on top of
ArchUnitPython + ruff), not a functional gap. Revisit once `ty` nears or
reaches a stable/1.0 milestone, or if a concrete correctness bug ArchUnitPython
and ruff can't catch actually surfaces during implementation.

</details>
