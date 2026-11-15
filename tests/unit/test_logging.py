"""tests.unit.test_logging — Unit tests for structured logging configuration."""

import logging

from app.core.logging import get_logger


def test_get_logger_returns_configured_logger() -> None:
    """Verify get_logger returns a Logger instance configured with app settings."""
    logger = get_logger("test_module")
    assert isinstance(logger, logging.Logger)
    assert logger.name == "test_module"
    assert logger.level > 0
