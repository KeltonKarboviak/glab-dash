"""py-spy wrapper: records a flamegraph of glab-dash's boot, safe to Ctrl+C."""

import os
import shutil
import sys


def record() -> None:
    py_spy = shutil.which("py-spy")
    if py_spy is None:
        sys.exit("py-spy not found; run `uv sync` to install dev dependencies")
    os.execvp(
        py_spy,
        [py_spy, "record", "-o", "profile.svg", "--", sys.executable, "-m", "glab_dash.infrastructure.tui.app"],
    )


def run_dev() -> None:
    """Run glab-dash in Textual dev mode; pair with `uv run textual console`."""
    textual = shutil.which("textual")
    if textual is None:
        sys.exit("textual CLI not found; run `uv sync` to install dev dependencies")
    os.execvp(textual, [textual, "run", "--dev", "-c", "glab-dash"])
