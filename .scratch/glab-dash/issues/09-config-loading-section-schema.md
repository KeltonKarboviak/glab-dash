# 09 — Config loading & section schema

**What to build:** glab-dash loads and validates its YAML config into
Domain `Section` entities (plus top-level `refresh_interval` and `token`).
Config resolution checks the XDG path
(`$XDG_CONFIG_HOME/glab-dash/config.yml`, falling back to
`~/.config/glab-dash/config.yml`) and, when a repo-local `.glab-dash.yml`
is present, uses it entirely in place of the XDG config (no merge).
Sections preserve YAML list order (tab order). Pydantic models validate the
raw YAML shape at the Infrastructure boundary, then map into Domain
entities.

**Blocked by:** 07 — Project scaffolding & layer enforcement.

Status: complete

- [x] Valid YAML with one or more `sections` (each with required `title`, `scope`, matching `project`/`group` key, optional `state`/`author`/`assignee`/`labels`) parses into Domain `Section` entities in YAML order
- [x] `refresh_interval` defaults to `60` when absent
- [x] `token` field parses when present
- [x] Invalid config (missing required field, bad `scope`/`state` value) raises with a clear error
- [x] Repo-local `.glab-dash.yml`, when present, is used entirely instead of the XDG config (not merged)
- [x] XDG path resolution honors `$XDG_CONFIG_HOME`, falling back to `~/.config/glab-dash/config.yml`

## Comments

Implemented as `domain/config.py` (`Section`, `Config`, `Scope`,
`MergeRequestState`, `ConfigError` — stdlib-only, no I/O) +
`infrastructure/config.py` (`SectionModel`/`ConfigModel` pydantic models,
`load_config`, `resolve_config_path`). A `model_validator` on `SectionModel`
enforces the `project`/`group` key matching `scope`; `pydantic.ValidationError`
is caught at the boundary and re-raised as `ConfigError` so nothing downstream
depends on pydantic. `resolve_config_path` checks `Path.cwd() / ".glab-dash.yml"`
first, then falls back to `$XDG_CONFIG_HOME` (or `~/.config`) `/glab-dash/config.yml`.
Added `pydantic` to `pyproject.toml` dependencies.
