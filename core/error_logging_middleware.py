import logging
import traceback

logger = logging.getLogger(__name__)


def _sanitize_post_data(post_data):
    """Return a copy of POST data with sensitive values redacted."""
    sanitized = {}
    for key, value in post_data.items():
        key_lower = key.lower()
        if any(s in key_lower for s in ("password", "token", "secret")):
            sanitized[key] = "[REDACTED]"
        else:
            sanitized[key] = value
    return sanitized


class DetailedErrorLoggingMiddleware:
    """
    Middleware to log detailed error information for debugging
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        return response

    def process_exception(self, request, exception):
        """
        Log detailed exception information
        """
        logger.error("🚨 DETAILED ERROR REPORT 🚨")
        logger.error(f"Exception Type: {type(exception).__name__}")
        logger.error(f"Exception Message: {str(exception)}")
        sanitized_meta = {
            "path": request.path,
            "method": request.method,
            "user": str(getattr(request, "user", "Anonymous")),
        }
        logger.error(f"Request Info: {sanitized_meta}")

        if request.method == "POST":
            logger.error(f"POST Data: {_sanitize_post_data(request.POST)}")

        logger.error("🔍 FULL TRACEBACK:")
        logger.error(traceback.format_exc())
        logger.error("🚨 END ERROR REPORT 🚨")

        # Don't return a response - let Django handle it normally
        return None
