"""
Performance monitoring middleware for tracking query performance and response times
"""

import logging
import time

from django.conf import settings
from django.db import connection

logger = logging.getLogger("performance")


class PerformanceMonitoringMiddleware:
    """
    Middleware to monitor database queries and response times in production
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Skip monitoring for static files and admin media
        if (
            request.path.startswith("/static/")
            or request.path.startswith("/media/")
            or request.path.startswith("/admin/jsi18n/")
        ):
            return self.get_response(request)

        # Start timing
        start_time = time.time()
        initial_queries = len(connection.queries)

        # Process request
        response = self.get_response(request)

        # Calculate metrics
        end_time = time.time()
        response_time = (end_time - start_time) * 1000  # Convert to milliseconds
        query_count = len(connection.queries) - initial_queries

        # Log performance metrics
        if settings.DEBUG or query_count > 10 or response_time > 500:
            logger.info(
                "Performance: %s %s - %dms, %d queries",
                request.method,
                request.path,
                int(response_time),
                query_count,
            )

            # Log slow queries in debug mode
            if settings.DEBUG and query_count > 5:
                slow_queries = [
                    q
                    for q in connection.queries[-query_count:]
                    if float(q["time"]) > 0.1
                ]
                if slow_queries:
                    logger.warning(
                        "Slow queries detected (%d queries > 100ms) for %s",
                        len(slow_queries),
                        request.path,
                    )
                    for query in slow_queries[:3]:  # Log first 3 slow queries
                        logger.warning(
                            "Slow query (%.2fms): %s",
                            float(query["time"]) * 1000,
                            (
                                query["sql"][:200] + "..."
                                if len(query["sql"]) > 200
                                else query["sql"]
                            ),
                        )

        # Add performance headers for monitoring
        response["X-Response-Time"] = f"{int(response_time)}ms"
        response["X-Query-Count"] = str(query_count)

        return response
