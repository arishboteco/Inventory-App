from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa

DEBUG = False

if not SECRET_KEY:  # noqa: F405
    raise ImproperlyConfigured("DJANGO_SECRET_KEY must be set in production")

# Activate error logging middleware in production so 500s produce full
# tracebacks in the server logs (safe — never leaks info to the browser).
MIDDLEWARE.insert(  # noqa: F405
    MIDDLEWARE.index("django.contrib.auth.middleware.AuthenticationMiddleware")
    + 1,  # noqa: F405
    "core.error_logging_middleware.DetailedErrorLoggingMiddleware",
)
