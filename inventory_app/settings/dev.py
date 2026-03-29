from .base import *  # noqa
from .base import MIDDLEWARE as _BASE_MIDDLEWARE

DEBUG = True

MIDDLEWARE = [
    *_BASE_MIDDLEWARE,
    "core.middleware.PerfDebugMiddleware",
]
