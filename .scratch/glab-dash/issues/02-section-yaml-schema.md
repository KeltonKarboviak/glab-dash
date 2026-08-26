Type: grilling
Status: resolved

## Question

What is the exact YAML schema for a section? Decisions so far settle that
sections use structured keys (`state`, `author`, `assignee`, `labels`,
`scope`) and can target project scope, group scope, or global scope — but
not the precise shape. Needs answers on:

- How is the scope target expressed? E.g. `scope: project` + `project:
  "group/project-path"`, vs `scope: group` + `group: "group-path"`, vs a
  single `target:` key whose form implies the scope.
- Which filter keys are required vs optional per scope (e.g. is `project`
  required only when `scope: project`)?
- What are the accepted values/types for `state` (`opened`/`merged`/`closed`/
  `all`?), `author`/`assignee` (username string, `"@me"` literal, or numeric
  id?), and `labels` (list of strings, AND or OR matching?).
- Section-level metadata: `title`, ordering, per-section refresh override?

## Answer

The section YAML schema:

```yaml
sections:
  - title: "My Reviews"
    scope: project          # project | group | global
    project: "group/project-path"   # required when scope: project
    # group: "group-path"           # required when scope: group
    state: opened            # opened | closed | merged | all (default: opened)
    author: "@me"             # username string or literal "@me"
    assignee: "someone"
    labels: ["bug", "priority::high"]   # AND-matched
```

- **Scope target**: a `scope:` key (`project`/`group`/`global`) plus a
  matching key holding the path — `project: "group/project-path"` when
  `scope: project`, `group: "group-path"` when `scope: group`, neither when
  `scope: global`. Mirrors python-gitlab's manager split
  (`ProjectMergeRequestManager` / `GroupMergeRequestManager` /
  `MergeRequestManager`).
- **Required vs optional**: `project`/`group` is hard-required for its scope
  — a config-load error if missing. No implicit "current directory"
  fallback in v1.
- **`state` values**: `opened` / `closed` / `merged` / `all`, exactly
  GitLab API's own accepted values (confirmed in python-gitlab's
  `_list_filters`). Default when omitted: `opened`.
- **`author`/`assignee` type**: username string or literal `"@me"`,
  resolved to the authenticated user's username at query time (GitLab's
  API itself has no `@me` — glab-dash resolves it before calling
  python-gitlab's `author_username`/`assignee_username`). No numeric id
  support in v1.
- **`labels` matching**: AND — matches GitLab API's own `labels` filter
  (comma-separated = must have all).
- **Section-level metadata**: `title` (required, display string); ordering
  is implicit from list position in YAML (no explicit `order:` key); no
  per-section refresh override in v1 (a single global interval + manual
  refresh keybinding is already locked).
