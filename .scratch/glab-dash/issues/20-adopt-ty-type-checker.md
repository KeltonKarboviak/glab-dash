Type: task
Status: ready-for-agent

## Task

Wire `ty` into the dev-tooling stack per the decision in
[ty type checker research](../research/ty-type-checker.md) and
[issue 19](19-ty-type-checker.md).

- `uv add --dev ty` (dev dependency, not shipped at runtime).
- Add a `[tool.ty]` section to `pyproject.toml` (exclude `.scratch`,
  matching `[tool.ruff]`'s `extend-exclude`).
- Add the `astral-sh/ty-pre-commit` hook to the `prek` config, alongside
  the existing `ruff-pre-commit` entry.
- Run `ty check` against the current source tree. Fix small/obvious
  findings inline as part of this ticket; if anything non-trivial or
  contentious surfaces, file it as a separate follow-up ticket rather
  than block adoption on it.
- Enable ruff's `ANN` annotation rules, scoped to public API surface
  only: add `ANN001, ANN201, ANN204, ANN205, ANN206` to
  `[tool.ruff.lint] select`. Deliberately excluded: `ANN002`/`ANN003`
  (`*args`/`**kwargs` — variadics stay unenforced), `ANN202` (return type
  on private/`_`-prefixed functions — internals stay unenforced),
  `ANN401` (bans `Any` outright — separate stylistic discussion, and
  `Any` may be legitimate at the Infrastructure boundary handling
  `python-gitlab` API payloads).
- CI wiring: **out of scope**. No CI pipeline (`.gitlab-ci.yml`,
  `.github/`, etc.) exists in this repo yet — only local `prek` hooks.
  Revisit once a CI pipeline exists.

## Definition of done

- `uv run ty check` passes locally.
- `uv run ruff check` passes locally with the new `ANN` rules enabled.
- `prek run --all-files` passes with the new `ty` hook installed.
