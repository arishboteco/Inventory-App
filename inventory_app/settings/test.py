from core import config as app_config

# Ensure deterministic secret key for tests
app_config.settings = app_config.load_settings(
    django_secret_key=app_config.settings.django_secret_key or "test-secret-key",
    django_settings_module="inventory_app.settings.test",
)

from .base import *  # noqa

SECRET_KEY = app_config.settings.django_secret_key

# Ensure tests NEVER hit Supabase/Postgres
DEBUG = False

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

# Speed up hashing in tests
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

# Disable inventory migrations in tests to avoid Postgres-specific SQL on SQLite
MIGRATION_MODULES = {
    "inventory": None,
}

# Make selected routes login-exempt to simplify test flows
LOGIN_EXEMPT_URLS = [
    r"^$",
    r"^login/$",
    r"^accounts/login/$",
    r"^accounts/logout/$",
    r"^healthz$",
    r"^static/.*$",
    r"^api/.*$",
    r"^media/.*$",
    r"^ml-dashboard/$",
]

# Hint app code to skip caching in views under tests
DISABLE_DASHBOARD_CACHE = True
