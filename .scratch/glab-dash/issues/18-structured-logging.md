# 18 — Structured logging to Textual dev console

**What to build:** `structlog` configured to render through stdlib
`logging`, forwarded to Textual's `TextualHandler` so log output is visible
in Textual's built-in dev console, with no second logging pipeline to
maintain.

**Blocked by:** 07 — Project scaffolding & layer enforcement.

Status: done

- [x] `structlog` is configured to route through stdlib `logging`
- [x] Log records reach Textual's `TextualHandler` and appear in the dev console (`textual console` / `textual run --dev`)
- [x] A sample log call from each layer (Domain excluded, since it stays stdlib-only and I/O-free) demonstrates the pipeline works end-to-end
