Status: research

# Profiling tools for Ctrl+C-interrupted boot slowness

Requirement: capture a usable profile of glab-dash's boot-to-first-paint path when the
user has to Ctrl+C (SIGINT) out of a hang — not a clean-exit-only tool. Stack:
Python >=3.14, Textual (alt-screen TUI), structlog. From pyproject.toml.

## Comparison

| Tool | Ctrl+C behavior | Code changes needed | Install | Output | Alt-screen/Textual risk |
|---|---|---|---|---|---|
| **`python -m profiling.sampling attach <PID>`** (stdlib, Py 3.15+ "Tachyon") | External attach by PID — SIGINT to glab-dash itself doesn't touch the profiler process at all; run `attach` in a second terminal *before* Ctrl+C-ing glab-dash, or `dump` for one instant snapshot | **None** — stdlib module, zero code changes, zero deps | Already present if Python ≥3.15 | flamegraph HTML, collapsed stacks, gecko JSON, pstats text, binary (replay later) | None — reads process memory externally, never touches glab-dash's terminal/stdout |
| **py-spy `record --pid`** | Same as above: external attach, unaffected by SIGINT to the target | None | `pip install py-spy` (Rust binary via pip wheel) | flamegraph SVG, speedscope JSON, raw | None — same external-memory-read model |
| **py-spy `dump --pid`** | One-shot stack snapshot at the moment of the hang — good for "where is it stuck right now" | None | same as above | plain-text call stack per thread | None |
| **austin (+ austin-tui / flamegraph.pl)** | External attach (`austin -p <PID>` or wrap `austin -- glab-dash`) | None if attaching; none if wrapping | `pip install austin-dist` or brew | collapsed stacks → flamegraph.pl SVG | None; some platforms need extra permissions (same ptrace-style caveat as py-spy) |
| **pyinstrument (context-manager)** | In-process — needs a `try/finally` around app.run() with `profiler.stop()` in `finally` so a `KeyboardInterrupt` from SIGINT still reaches `stop()`/`write_html()` | ~5 lines in `app.py`'s `run()` entrypoint | `pip install pyinstrument` (dev dep) | self-contained HTML (interactive flame chart) or text | Low — pyinstrument doesn't touch the terminal; must call `write_html()` in `finally`, not `atexit`, since Textual's alt-screen teardown also happens in a `finally`/context-manager |

## Ranked pick

1. **`python -m profiling.sampling attach <PID>`** — zero setup (already ships with Python 3.15, which this project already requires), zero code changes, immune to however glab-dash itself exits, and gives a flamegraph HTML the user can hand back directly (`--flamegraph -o profile.html`). This is the top pick: nothing to install, nothing to maintain, no risk of interfering with Textual's alt-screen rendering since it never touches the target's stdio.
2. **py-spy `record --pid`** — same external-attach model, use only if the user is on Python 3.14 (pre-3.15, stdlib module unavailable) or wants speedscope format. One extra dependency (`pip install py-spy`), no code changes.
3. **py-spy `dump --pid`** — fastest, single-command "what's it stuck on right now" snapshot; no timeline, just current stacks. Good first move before reaching for a full recording.
4. **austin** — equivalent capability to py-spy, redundant with it; only worth adding if the user specifically wants the live `austin-tui` view rather than a static flamegraph.
5. **pyinstrument** — only choice needing in-process code changes; use if PID-attach profilers are ever unavailable (locked-down permissions, no root/ptrace) since it doesn't need elevated privileges to profile itself.

## Setup — top pick (Python 3.15 stdlib)

No install, no code changes. When glab-dash hangs at boot:

```bash
# terminal 1
glab-dash

# terminal 2 — find the PID, then attach and let it sample until you Ctrl+C glab-dash
pgrep -f glab-dash
python -m profiling.sampling attach --flamegraph -o /tmp/glab-dash-boot.html <PID>
```

Hand back `/tmp/glab-dash-boot.html` (or use `--gecko -o profile.json` for a JSON I can
read directly without opening a browser).

## Fallback — Python 3.14 or stdlib module unavailable

```bash
pip install py-spy   # one-time, dev-only
py-spy dump --pid <PID>                              # instant "what's it stuck on"
py-spy record -o /tmp/glab-dash-boot.svg --pid <PID>  # Ctrl+C py-spy itself to stop recording and write the SVG
```

`py-spy record` needs `sudo` on macOS; run `sudo py-spy record ...` if it errors with a
permission message.
