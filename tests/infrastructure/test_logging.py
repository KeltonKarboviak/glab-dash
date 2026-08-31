import logging

import structlog
from textual.logging import TextualHandler

from glab_dash.infrastructure.logging import configure_logging


def test_configure_logging_routes_stdlib_root_logger_through_textual_handler():
    configure_logging()

    assert any(isinstance(handler, TextualHandler) for handler in logging.root.handlers)
    assert isinstance(structlog.get_logger().bind()._logger, logging.Logger)
