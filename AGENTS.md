## Agent skills

### Issue tracker

Issues live as local markdown files under `.scratch/`. See `docs/agents/issue-tracker.md`.

### Domain docs

Single-context layout — `CONTEXT.md` + `docs/adr/` at the repo root. See `docs/agents/domain.md`.

### Architecture enforcement (ArchUnitPython)

`tests/test_architecture.py` enforces the three-layer dependency rule using
the `archunitpython` PyPI package (not `pytest-archon` or the `archunit`
placeholder package — those are different projects). Its source is cloned
locally at `~/Code/open-source/ArchUnitPython` for reference when the fluent
API (`project_files`, `project_layers`) needs checking against actual
behavior rather than guessed.
