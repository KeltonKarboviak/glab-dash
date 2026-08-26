Type: grilling
Status: resolved

## Question

The config file schema for `sections` is locked (see [Section YAML schema](02-section-yaml-schema.md)).
What does the rest of the v1 config file schema look like — specifically:

- Theme/color customization: is it in scope for v1, or deferred like packaging?
- Keybinding overrides: [V1 keybindings](03-v1-keybindings.md) locked a hardcoded
  scheme with no per-user overrides — does the config file need a placeholder/reserved
  key for future override support, or should keybindings be entirely absent from the
  config schema for now?
- Refresh interval: is the polling interval (see refresh decision in the map) a
  top-level config key, and what's its default value and units?
- Any other top-level keys needed for v1 (e.g. GitLab host override, default token
  source override) beyond `sections`?

Resolve into a concrete top-level YAML schema (keys, types, defaults, required vs
optional) that complements the already-locked `sections` schema.

## Answer

Top-level v1 config schema, alongside the already-locked `sections` key:

- `refresh_interval` — optional int, seconds, default `60`.
- `token` — optional string (glab-dash's own credential source, lowest priority
  in the resolution order).
- No `theme`/`colors` key — deferred, same as packaging.
- No `keybindings` key — omitted entirely rather than reserved unused; add it
  only when per-user override support actually ships.
- No `host`/`gitlab_url` config key — v1 is gitlab.com-only. The GitLab base
  URL is a single named constant in the Infrastructure layer (wherever the
  API client/gateway is constructed), never inlined as a literal at each call
  site, so adding self-hosted support later is a one-place change plus a new
  config key, not a grep-and-replace.
