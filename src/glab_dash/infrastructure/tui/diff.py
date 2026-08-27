"""Colorizes unified-diff text for the preview pane, no syntax-highlighter dependency."""

from rich.text import Text

_LINE_STYLES = (
    ("+++", "bold"),
    ("---", "bold"),
    ("diff --git", "bold yellow"),
    ("index ", "bold yellow"),
    ("@@", "cyan"),
    ("+", "green"),
    ("-", "red"),
)


def _style_for(line: str) -> str | None:
    for prefix, style in _LINE_STYLES:
        if line.startswith(prefix):
            return style
    return None


def colorize_diff(diff: str) -> Text:
    text = Text()
    for line in diff.splitlines():
        text.append(line + "\n", style=_style_for(line))
    return text
