"""Application logging helpers configured for debug output."""

import logging


def configure_logging() -> None:
    """Configure console logging at DEBUG level."""
    if logging.getLogger().handlers:
        return
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )


def get_logger(name: str) -> logging.Logger:
    """Return a logger instance."""
    return logging.getLogger(name)


def flush_logs() -> None:
    """Flush all log handlers."""
    for handler in logging.getLogger().handlers:
        try:
            handler.flush()
        except Exception:
            pass


__all__ = ["configure_logging", "get_logger", "flush_logs"]
