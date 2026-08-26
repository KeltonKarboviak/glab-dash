Type: research
Status: resolved

## Question

How does the `glab` CLI actually store its GitLab access token on disk (file
path, format, config key), and does `glab`/GitLab itself have any existing
convention around a `GITLAB_TOKEN` environment variable that glab-dash's own
`GITLAB_TOKEN` credential source might collide or need to align with?

Resolve by reading `glab`'s own config-loading source/docs (not python-gitlab
— python-gitlab's `~/.python-gitlab.cfg` is a separate, already-researched
mechanism). Report: config file path + format, the config key holding the
token, and any environment variable `glab` itself already reads.

## Answer

**Config file**: YAML at `~/.config/glab-cli/config.yml` (XDG-compliant:
`$XDG_CONFIG_HOME/glab-cli/config.yml`, or system-wide
`/etc/xdg/glab-cli/config.yml`). Location can be overridden with the
`GLAB_CONFIG_DIR` env var (glab's `internal/config/config_file.go`,
`ConfigDir()`).

**Config key**: `token` — e.g. `glab config set token <value>` writes a
top-level (or per-host, under `hosts:`) `token:` key in `config.yml`. Per
GitLab's own docs (docs.gitlab.com/cli/config/): "Your GitLab access token.
Defaults to environment variables."

**Environment variable**: glab reads `GITLAB_TOKEN` directly, and it takes
precedence over both the config file and the `--token` flag (see
gitlab-org/cli issue #6285, "Environment variable GITLAB_TOKEN takes
precedence over the --token parameter"). This is the same env var name
glab-dash's own `GITLAB_TOKEN` credential source uses, so no rename is
needed for alignment, but note glab_dash and glab CLI would both honor a
`GITLAB_TOKEN` set in the shell, so exporting it for one tool implicitly
authenticates the other too.

Sources:
- https://docs.gitlab.com/cli/config/
- https://gitlab.com/gitlab-org/cli/-/blob/main/internal/config/config_file.go
- https://gitlab.com/gitlab-org/cli/-/issues/6285
