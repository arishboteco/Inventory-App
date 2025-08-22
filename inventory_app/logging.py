"""Temporary logging stubs with logging disabled."""

import logging


def configure_logging() -> None:
    """Disable all logging."""
    logging.disable(logging.CRITICAL)


def get_logger(name: str) -> logging.Logger:
    """Return a logger with logging disabled."""
    return logging.getLogger(name)


def flush_logs() -> None:
    """No-op when logging is disabled."""
    pass


__all__ = ["configure_logging", "get_logger", "flush_logs"]

