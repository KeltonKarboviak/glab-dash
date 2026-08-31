# glab-dash

A terminal dashboard for GitLab merge requests, built with Textual.

## Configuration

glab-dash reads its config from a YAML file. It resolves the path in this order:

1. `.glab-dash.yml` in the current directory (repo-local)
2. `$XDG_CONFIG_HOME/glab-dash/config.yml`, falling back to `~/.config/glab-dash/config.yml`

### Top-level keys

| Key                | Type   | Default | Description                                    |
| ------------------ | ------ | ------- | ----------------------------------------------- |
| `sections`         | list   | —       | Required. At least one section (see below).     |
| `refresh_interval` | int    | `60`    | Seconds between automatic dashboard refreshes.  |
| `token`            | string | —       | GitLab personal access token. See Token below.  |

### Section keys

Each entry under `sections` renders as one panel in the dashboard.

| Key        | Type   | Default    | Description                                                          |
| ---------- | ------ | ---------- | ---------------------------------------------------------------------|
| `title`    | string | —          | Required. Panel heading.                                             |
| `scope`    | string | —          | Required. One of `project`, `group`, `global`.                       |
| `project`  | string | —          | Required when `scope: project`. `namespace/project` path.            |
| `group`    | string | —          | Required when `scope: group`. Group path.                            |
| `state`    | string | `opened`   | MR state filter: `opened`, `closed`, `merged`, `all`.                 |
| `author`   | string | —          | Filter by author username.                                            |
| `assignee` | string | —          | Filter by assignee username.                                          |
| `labels`   | list   | `[]`       | Filter by label names.                                                 |

### Token

If `token` is omitted, glab-dash resolves a GitLab token from, in order:

1. The `glab` CLI's stored config (`~/.config/glab-cli/config.yml`, or `$GLAB_CONFIG_DIR/config.yml`)
2. The `GITLAB_TOKEN` environment variable
3. The `token` key in this config file

See [`examples/`](examples/) for sample configs.
