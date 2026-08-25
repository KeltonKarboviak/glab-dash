from glab_dash.domain.credentials import resolve_token


def test_returns_first_present_candidate():
    assert resolve_token(["glab-cli-token", "env-token"]) == "glab-cli-token"


def test_skips_none_candidates_in_priority_order():
    assert resolve_token([None, "env-token", "config-token"]) == "env-token"


def test_returns_none_when_no_candidates_present():
    assert resolve_token([None, None]) is None


def test_skips_empty_string_candidates():
    assert resolve_token(["", "env-token"]) == "env-token"
