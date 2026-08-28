Type: research
Status: resolved

## Question

Should `ty` (astral-sh/ty) be added to glab-dash's dev tooling as a static
type checker, alongside the already-locked `uv`/`ruff`/`mise`/`prek`/
`pytest` stack, to strengthen AI guardrails via static type checking?

Research `ty`'s repo (https://github.com/astral-sh/ty) and docs
(https://docs.astral.sh/ty/) to determine:

- Current maturity/stability (it's pre-1.0 from Astral) — is it safe to
  adopt now, or should glab-dash wait?
- Installation path via `uv` (dev dependency vs `uv tool`) consistent with
  the project's existing `uv`-based tooling.
- Config surface: `pyproject.toml` `[tool.ty]` section, strictness levels,
  how it overlaps/conflicts with `ruff`'s own type-adjacent lint rules.
- Whether it can run in `prek` (pre-commit) and CI the same way `ruff`/
  `pytest` do, and expected performance.
- How it interacts with the project's Clean Architecture layering (any
  value for catching cross-layer import violations, or is that strictly
  ArchUnitPython's job) and with Pydantic models at the Infrastructure
  boundary.

## Answer

Adopted. `ty` is officially pre-1.0/beta (`0.0.x` versioning, Astral's own
docs warn "breaking changes... may occur between any two versions"), but
that risk is judged acceptable: `ty` is a dev dependency only, never
shipped or run at runtime, so a breaking release just means re-pinning in
CI/`prek` — it can't destabilize the deployed app. No technical blocker to
adoption otherwise: install cleanly fits the existing `uv`-based stack
(`uv add --dev ty`, mirroring `ruff`/`pytest`); it reads `[tool.ty]` in
`pyproject.toml`; there's no rule overlap/conflict with ruff (ruff only
checks annotation presence/style via `ANN*`, `ty` checks annotation
*correctness*); Astral maintains an official `prek`/pre-commit hook repo
(`astral-sh/ty-pre-commit`) that plugs in the same way `ruff-pre-commit`
does; it's Rust-fast like ruff/uv; it has no opinion on Clean Architecture
layering (that stays ArchUnitPython's job, no overlap); and it understands
Pydantic model construction natively (a dedicated
`pydantic-discarded-extra-argument` rule exists, no separate plugin needed
like mypy's `pydantic-mypy`). Full findings, citations, and per-topic
detail in [ty type checker research](../research/ty-type-checker.md).
