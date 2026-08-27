from glab_dash.infrastructure.tui.diff import colorize_diff


def test_added_and_removed_lines_get_distinct_styles():
    diff = "@@ -1,1 +1,1 @@\n-old line\n+new line\n"

    text = colorize_diff(diff)

    spans_by_style = {span.style: text.plain[span.start : span.end] for span in text.spans}
    assert spans_by_style["green"] == "+new line\n"
    assert spans_by_style["red"] == "-old line\n"
    assert spans_by_style["cyan"] == "@@ -1,1 +1,1 @@\n"


def test_unrecognized_lines_are_left_unstyled():
    text = colorize_diff("plain context line\n")

    assert text.spans == []
