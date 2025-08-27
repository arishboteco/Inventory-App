# inventory_app/settings_test.py
from .settings import *  # import your existing base settings

# --- Test-only overrides ---
DEBUG = False

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

# Fast hashing
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

# Avoid DB-backed sessions in tests
SESSION_ENGINE = "django.contrib.sessions.backends.cache"

ALLOWED_HOSTS = ["*", "localhost", "127.0.0.1", "testserver"]

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "ERROR"},
}
