from .base import MIDDLEWARE as _BASE_MIDDLEWARE
from .base import *  # noqa

DEBUG = True

MIDDLEWARE = [
    *_BASE_MIDDLEWARE,
    "core.middleware.PerfDebugMiddleware",
]
