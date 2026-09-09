Label: wayfinder:prototype
Status: resolved

## Question

How should a `Stale` enrichment cell (warm-cached value, not yet confirmed
by the background fetch) look distinct from a resolved cell and from a
`Pending`/`Failed` cell? Build a cheap, rough prototype of the visual
treatment (dimming, marker glyph, color) to react to — reuses the existing
per-cell state machine from
[Warm-start cache mechanics](11-warm-start-cache-mechanics.md); only the
rendering is undecided.

## Answer

Variant A — dimmed/muted: the resolved value text rendered with `dim` style,
no glyph or prefix change. Chosen over a `~` marker-glyph prefix (Variant B)
and italic styling (Variant C). Reads clearly distinct from a spinner
(`Pending`), the `⚠` glyph (`Failed`), and normal-weight resolved text,
without adding visual noise.

Implementation note: wrap the existing `render_approvals`/`render_line_stats`
formatted string in `rich.text.Text(value, style="dim")` when the cell's
source value is `Stale`, in `src/glab_dash/infrastructure/tui/rows.py`.

Prototype (3 variants, throwaway): `prototype/warm-start-staleness-display`
branch, commit `49fd9fe` —
`src/glab_dash/infrastructure/tui/prototype_stale_cell.py`.
