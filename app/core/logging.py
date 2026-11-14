"""app.core.logging — Structured logging configuration.

Sets up the Python logger for the entire application.
Log level is controlled by the LOG_LEVEL environment variable.

Usage:
    from app.core.logging import get_logger
    logger = get_logger(__name__)
    logger.info("Something happened")
"""

import logging

from app.core.config import settings


def get_logger(name: str) -> logging.Logger:
    """Return a configured logger for the given module name.

    Args:
        name: Name of the module requesting a logger.

    Returns:
        logging.Logger: Configured logger instance.
    """
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    logger = logging.getLogger(name)
    logger.setLevel(log_level)
    return logger
