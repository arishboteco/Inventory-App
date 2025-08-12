"""Logging utilities for the Inventory App.

This module provides a custom logging configuration using a rotating file
handler and helper functions to obtain loggers and manage log files.
"""

import logging
import os
from logging.handlers import RotatingFileHandler

LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
LOG_FILE = os.getenv("LOG_FILE", "app.log")

_configured = False


def configure_logging() -> None:
    """Configure application-wide logging.

    Uses a :class:`~logging.handlers.RotatingFileHandler` that keeps the log
    file to roughly 1MB with up to three backups. The log level can be
    controlled via the ``LOG_LEVEL`` environment variable.
    """

    global _configured
    if _configured:
        return

    level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)

    root = logging.getLogger()
    root.setLevel(level)

    formatter = logging.Formatter(LOG_FORMAT)

    file_handler = RotatingFileHandler(
        LOG_FILE, maxBytes=1_000_000, backupCount=3
    )
    file_handler.setFormatter(formatter)
    root.addHandler(file_handler)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    root.addHandler(stream_handler)

    _configured = True


def get_logger(name: str) -> logging.Logger:
    """Return a logger with the configured settings."""
    return logging.getLogger(name)


def flush_logs() -> None:
    """Truncate the current log file and flush any buffered records."""

    for handler in logging.getLogger().handlers:
        handler.flush()
    open(LOG_FILE, "w").close()
