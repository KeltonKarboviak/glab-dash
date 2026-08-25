# 08 — Credential resolution

**What to build:** glab-dash finds a GitLab access token automatically,
trying sources in priority order: the `glab` CLI's stored config
(`~/.config/glab-cli/config.yml` `token` key, `GLAB_CONFIG_DIR`-overridable)
→ `GITLAB_TOKEN` environment variable → glab-dash's own config file's
`token` field. The priority-pick itself is a pure Domain function taking
already-fetched candidate values; Infrastructure owns fetching each
candidate (including reading glab-dash's own config file for its `token`
key).

**Blocked by:** 07 — Project scaffolding & layer enforcement.

**Status:** complete

- [x] Domain function picks the first present candidate given an ordered list of optional token values, with no I/O
- [x] Infrastructure fetcher reads the glab CLI config token, honoring `GLAB_CONFIG_DIR`
- [x] Infrastructure fetcher reads `GITLAB_TOKEN` from the environment
- [x] Infrastructure fetcher reads the `token` field from glab-dash's own parsed config
- [x] End-to-end resolution (a small script or integration test) demonstrates each source winning when it's the highest-priority one present

## Comments

Implemented as `domain/credentials.py` (`resolve_token`) +
`infrastructure/credentials.py` (`fetch_glab_cli_token`, `fetch_env_token`,
`fetch_own_config_token`, `resolve_gitlab_token`). The orchestrating
`resolve_gitlab_token` was first written in `application/`, but that put
application depending directly on infrastructure, so it was moved into
`infrastructure/` (pure wiring of concrete fetchers, no business logic).

While verifying that move, found the layer test hadn't actually caught the
violation — traced it to an ArchUnitPython bug in `in_folder()`'s glob
matching, now documented with a workaround in
[issue 05](05-archunitpython-rule-idioms.md#comments). `tests/test_architecture.py`
now uses the regex workaround for all three layer checks, and the fixed
test does correctly fail against a deliberately reintroduced violation.
