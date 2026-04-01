"""Lazy stock snapshot middleware.

On free-tier environments where Django Q workers don't run, this middleware
fires a stock snapshot once per calendar day the first time any authenticated
user loads the main dashboard. The snapshot runs in a background thread so it
never blocks the user's page load.
"""

import logging
import threading

logger = logging.getLogger(__name__)

_DASHBOARD_PATHS = frozenset(["/"])

_snapshot_lock = threading.Lock()
_snapshot_pending = False


def _run_snapshot():
    """Execute the snapshot in a background thread."""
    global _snapshot_pending
    import django

    django.setup()
    try:
        from inventory.services.snapshot_service import take_daily_stock_snapshot

        take_daily_stock_snapshot()
        logger.info("LazyStockSnapshotMiddleware: background snapshot completed")
    except Exception:
        logger.exception("LazyStockSnapshotMiddleware: background snapshot failed")
    finally:
        with _snapshot_lock:
            _snapshot_pending = False


class LazyStockSnapshotMiddleware:
    """Take a daily stock snapshot on the first dashboard load each day."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        global _snapshot_pending

        if (
            request.method == "GET"
            and request.path in _DASHBOARD_PATHS
            and request.user.is_authenticated
        ):
            try:
                from inventory.services.snapshot_service import (
                    should_take_snapshot_today,
                )

                if should_take_snapshot_today():
                    with _snapshot_lock:
                        if not _snapshot_pending:
                            _snapshot_pending = True
                            t = threading.Thread(target=_run_snapshot, daemon=True)
                            t.start()
            except Exception:
                logger.exception("LazyStockSnapshotMiddleware: snapshot check failed")

        return self.get_response(request)
