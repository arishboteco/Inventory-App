import logging
import re
import time

from django.conf import settings
from django.contrib.auth.views import redirect_to_login
from django.db import connection, reset_queries

_perf_logger = logging.getLogger("inventory.perf")
_PROFILE_PATHS = frozenset({"/", "/recipes/food-cost-report/"})


class LoginRequiredMiddleware:
    """Redirect unauthenticated users to the login page."""

    def __init__(self, get_response):
        self.get_response = get_response
        self.exempt_urls = [
            re.compile(expr) for expr in getattr(settings, "LOGIN_EXEMPT_URLS", [])
        ]

    def __call__(self, request):
        logger = logging.getLogger(__name__)
        logger.debug("Processing URL: %s", request.path_info)
        if not request.user.is_authenticated:
            path = request.path_info.lstrip("/")
            for pattern in self.exempt_urls:
                if pattern.match(path):
                    return self.get_response(request)
            return redirect_to_login(request.get_full_path(), settings.LOGIN_URL)
        return self.get_response(request)


class PerfDebugMiddleware:
    """Log request duration and SQL query count in DEBUG mode (local profiling)."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not settings.DEBUG or request.method != "GET":
            return self.get_response(request)
        path = request.path
        if path not in _PROFILE_PATHS:
            return self.get_response(request)

        reset_queries()
        t0 = time.perf_counter()
        response = self.get_response(request)
        elapsed_ms = (time.perf_counter() - t0) * 1000
        n_queries = len(connection.queries)
        _perf_logger.info(
            "perf path=%s status=%s queries=%d time_ms=%.1f",
            path,
            getattr(response, "status_code", "?"),
            n_queries,
            elapsed_ms,
        )
        return response
