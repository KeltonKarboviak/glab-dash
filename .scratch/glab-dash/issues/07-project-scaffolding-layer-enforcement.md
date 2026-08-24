# 07 — Project scaffolding & layer enforcement

**What to build:** the project skeleton so every later ticket has somewhere
to land. `uv`-managed `pyproject.toml` (Python 3.14+), `ruff` lint/format,
`mise` tool pinning, `prek` pre-commit hooks, `pytest` as test runner, and
empty `src/glab_dash/{domain,application,infrastructure}/` packages. An
ArchUnitPython rule set enforces the three-layer dependency rule (Domain:
stdlib-only; Application: Domain + gateway interfaces only, never concrete
Infrastructure; Infrastructure: may depend on either) as a plain `pytest`
test at `tests/test_architecture.py`, passing trivially against the empty
packages.

**Blocked by:** None — can start immediately.

**Status:** complete

- [x] `uv sync` installs a working dev environment per `mise`-pinned Python 3.14+
- [x] `ruff check` and `ruff format --check` pass on the empty skeleton
- [x] `prek run --all-files` passes
- [x] `src/glab_dash/{domain,application,infrastructure}/` exist with `__init__.py`
- [x] `tests/test_architecture.py` encodes the three-layer rule via ArchUnitPython and passes under `pytest`

## Comments

Implemented in `5810f85` (`feat(scaffolding): project skeleton with layer enforcement`).
Used `archunitpython` (not `pytest-archon`/the `archunit` placeholder package)
for the layer rule — see `docs/agents/domain.md`-adjacent note in `AGENTS.md`
pointing at the local clone `~/Code/open-source/ArchUnitPython` for future
fluent-API reference. `code-review` (Standards + Spec axes) ran clean after
fixing a stray staged `.pyc` and dropping a redundant/incomplete layer test.
