"""
Staging settings for Inventory App

This module extends the base settings for staging environment deployment.
Used for pre-production testing and validation.
"""

import logging
import os

import dj_database_url

from .settings import *  # noqa: F401,F403

# SECURITY WARNING: don't run with debug turned on in staging!
DEBUG = False

# Allowed hosts for staging environment
ALLOWED_HOSTS = [
    'localhost',
    '127.0.0.1',
    '0.0.0.0',
    # Add your staging domain here
    # 'staging.yourdomain.com',
]

# Allow all hosts from environment variable
if 'DJANGO_ALLOWED_HOSTS' in os.environ:
    ALLOWED_HOSTS.extend(os.environ.get('DJANGO_ALLOWED_HOSTS', '').split(','))

# Database configuration for staging
# Uses DATABASE_URL environment variable or falls back to SQLite
DATABASES = {
    'default': dj_database_url.parse(
        os.environ.get('DATABASE_URL', 'sqlite:///staging.db'),
        conn_max_age=600,
        conn_health_checks=True,
    )
}

# Cache configuration - Redis for staging
if 'REDIS_URL' in os.environ:
    CACHES = {
        'default': {
            'BACKEND': 'django_redis.cache.RedisCache',
            'LOCATION': os.environ.get('REDIS_URL', 'redis://127.0.0.1:6379/0'),
            'OPTIONS': {
                'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            }
        }
    }

# Email backend for staging - console for testing
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Static files configuration
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')  # noqa: F405
STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'

# Media files configuration
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')  # noqa: F405

# Security settings for staging
SECURE_SSL_REDIRECT = False  # Set to True if using HTTPS in staging
SECURE_HSTS_SECONDS = 0      # Enable HSTS if using HTTPS
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = 'DENY'

# Session configuration
SESSION_COOKIE_SECURE = False  # Set to True if using HTTPS
CSRF_COOKIE_SECURE = False     # Set to True if using HTTPS
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

# Logging configuration for staging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '/tmp/django-staging.log',
            'maxBytes': 1024*1024*15,  # 15MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
        'inventory': {
            'handlers': ['file', 'console'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'core': {
            'handlers': ['file', 'console'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
}

# Django REST Framework settings for staging
REST_FRAMEWORK.update({  # noqa: F405
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
})

# Performance settings
DATA_UPLOAD_MAX_MEMORY_SIZE = 2621440  # 2.5MB
FILE_UPLOAD_MAX_MEMORY_SIZE = 2621440  # 2.5MB

# Admin settings
ADMIN_URL = 'admin/'  # Keep simple for staging

# Application-specific settings
INVENTORY_SETTINGS = {
    'DEFAULT_ITEMS_PER_PAGE': 25,
    'MAX_UPLOAD_SIZE': 1024 * 1024 * 5,  # 5MB
    'ALLOWED_UPLOAD_EXTENSIONS': ['.csv', '.xlsx', '.xls'],
    'ENABLE_API_THROTTLING': True,
    'API_THROTTLE_RATE': '100/hour',
}

# Disable browsable API in staging for security
if not DEBUG:
    REST_FRAMEWORK['DEFAULT_RENDERER_CLASSES'] = [  # noqa: F405
        'rest_framework.renderers.JSONRenderer',
    ]

# Additional staging-specific configurations
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'
SECURE_CROSS_ORIGIN_OPENER_POLICY = 'same-origin'

# Monitoring and error reporting
if 'SENTRY_DSN' in os.environ:
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration
    from sentry_sdk.integrations.logging import LoggingIntegration

    sentry_logging = LoggingIntegration(
        level=logging.INFO,        # Capture info and above as breadcrumbs
        event_level=logging.ERROR  # Send errors as events
    )

    sentry_sdk.init(
        dsn=os.environ.get('SENTRY_DSN'),
        integrations=[DjangoIntegration(), sentry_logging],
        traces_sample_rate=0.1,
        send_default_pii=False,
        environment='staging',
    )
