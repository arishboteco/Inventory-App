"""Logging utilities for the Inventory App.

This module provides a custom logging configuration using a rotating file
handler and helper functions to obtain loggers and manage log files.
"""

import logging
import os
from datetime import datetime, timedelta
from logging.handlers import RotatingFileHandler
from pathlib import Path
from stat import ST_MTIME

LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
LOG_FILE = os.getenv("LOG_FILE", "legacy_streamlit.log")
LOG_RETENTION_DAYS = int(os.getenv("LOG_RETENTION_DAYS", "30"))

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
    _purge_old_logs()


def get_logger(name: str) -> logging.Logger:
    """Return a logger with the configured settings."""
    return logging.getLogger(name)


def flush_logs() -> None:
    """Truncate the current log file and flush any buffered records."""

    for handler in logging.getLogger().handlers:
        handler.flush()
    open(LOG_FILE, "w").close()


def _purge_old_logs() -> None:
    """Delete rotated log files older than ``LOG_RETENTION_DAYS``."""

    if LOG_RETENTION_DAYS <= 0:
        return

    log_path = Path(LOG_FILE).resolve()
    cutoff = datetime.now() - timedelta(days=LOG_RETENTION_DAYS)
    for file in log_path.parent.glob(f"{log_path.name}*"):
        if file == log_path:
            continue
        try:
            mtime = datetime.fromtimestamp(file.stat()[ST_MTIME])
        except FileNotFoundError:
            continue
        if mtime < cutoff:
            try:
                file.unlink()
            except FileNotFoundError:
                pass
