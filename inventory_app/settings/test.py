from .. import settings as base_settings

for attr in dir(base_settings):
    if attr.isupper():
        globals()[attr] = getattr(base_settings, attr)

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
