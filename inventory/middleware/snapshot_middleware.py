"""Lazy stock snapshot middleware.

On free-tier environments where Django Q workers don't run, this middleware
fires a synchronous stock snapshot once per calendar day the first time any
authenticated user loads the main dashboard (/ or /interactive-dashboard/).

The snapshot is taken in a try/except so that any DB errors never break the
page render.
"""

import logging
import threading

logger = logging.getLogger(__name__)

_DASHBOARD_PATHS = frozenset(["/"])

# Thread-local flag to avoid recursive calls within the same request
_taking_snapshot = threading.local()


class LazyStockSnapshotMiddleware:
    """Take a daily stock snapshot on the first dashboard load each day."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if (
            request.method == "GET"
            and request.path in _DASHBOARD_PATHS
            and request.user.is_authenticated
            and not getattr(_taking_snapshot, "active", False)
        ):
            try:
                from inventory.services.snapshot_service import (
                    should_take_snapshot_today,
                    take_daily_stock_snapshot,
                )

                if should_take_snapshot_today():
                    _taking_snapshot.active = True
                    try:
                        take_daily_stock_snapshot()
                    finally:
                        _taking_snapshot.active = False
            except Exception:
                logger.exception(
                    "LazyStockSnapshotMiddleware: snapshot failed silently"
                )

        return self.get_response(request)
