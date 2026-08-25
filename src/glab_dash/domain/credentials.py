"""Pure credential-resolution logic: no I/O."""

from collections.abc import Sequence


def resolve_token(candidates: Sequence[str | None]) -> str | None:
    """Return the first present candidate, in priority order."""
    return next((candidate for candidate in candidates if candidate), None)
