"""Django project logging helpers.

This module exposes the logging utilities originally implemented for the
Streamlit application.  They are re-exported here so test code can import them
via the ``inventory_app`` namespace, reflecting the Django project's structure.
"""

import importlib

_legacy = importlib.reload(
    importlib.import_module("legacy_streamlit.app.core.logging")
)

LOG_FILE = _legacy.LOG_FILE  # noqa: F401
LOG_RETENTION_DAYS = _legacy.LOG_RETENTION_DAYS  # noqa: F401
configure_logging = _legacy.configure_logging  # noqa: F401
flush_logs = _legacy.flush_logs  # noqa: F401
get_logger = _legacy.get_logger  # noqa: F401

__all__ = [
    "LOG_FILE",
    "LOG_RETENTION_DAYS",
    "configure_logging",
    "flush_logs",
    "get_logger",
]

