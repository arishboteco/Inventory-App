from ..settings import *  # noqa

# Ensure tests NEVER hit Supabase/Postgres
DEBUG = False

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

# Speed up hashing in tests (optional)
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

# Use cache-based sessions so we don't need the django_session DB table
SESSION_ENGINE = "django.contrib.sessions.backends.cache"

# Make sure allowed hosts are permissive for Django test client
ALLOWED_HOSTS = ["*", "localhost", "127.0.0.1", "testserver"]

# Quiet logging
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "ERROR"},
}
