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

**Status:** ready-for-agent

- [x] Domain function picks the first present candidate given an ordered list of optional token values, with no I/O
- [x] Infrastructure fetcher reads the glab CLI config token, honoring `GLAB_CONFIG_DIR`
- [x] Infrastructure fetcher reads `GITLAB_TOKEN` from the environment
- [x] Infrastructure fetcher reads the `token` field from glab-dash's own parsed config
- [x] End-to-end resolution (a small script or integration test) demonstrates each source winning when it's the highest-priority one present
