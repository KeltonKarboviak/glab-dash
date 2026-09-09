Label: wayfinder:prototype

## Question

How should a `Stale` enrichment cell (warm-cached value, not yet confirmed
by the background fetch) look distinct from a resolved cell and from a
`Pending`/`Failed` cell? Build a cheap, rough prototype of the visual
treatment (dimming, marker glyph, color) to react to — reuses the existing
per-cell state machine from
[Warm-start cache mechanics](11-warm-start-cache-mechanics.md); only the
rendering is undecided.
