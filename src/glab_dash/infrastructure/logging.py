"""structlog routed through stdlib logging into Textual's dev console."""

import logging

import structlog
from textual.logging import TextualHandler


def configure_logging() -> None:
    logging.basicConfig(level=logging.INFO, handlers=[TextualHandler()], force=True)
    structlog.configure(
        logger_factory=structlog.stdlib.LoggerFactory(),
        processors=[
            structlog.stdlib.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.ConsoleRenderer(),
        ],
    )


if __name__ == "__main__":
    configure_logging()
    log = structlog.get_logger("glab_dash.demo")
    log.info("structlog routed through stdlib logging", layer="infrastructure")
