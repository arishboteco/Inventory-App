from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa

DEBUG = False

if not SECRET_KEY:  # noqa: F405
    raise ImproperlyConfigured("DJANGO_SECRET_KEY must be set in production")
