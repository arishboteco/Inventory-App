"""
Production settings for Inventory App

This module contains production-ready settings with security hardening,
performance optimization, and monitoring configuration.
"""

import os
import logging
import dj_database_url
from .settings import *

# Override middleware to add error logging for production debugging
MIDDLEWARE = [
    'core.error_logging_middleware.DetailedErrorLoggingMiddleware',  # Add error logging first
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "core.middleware.LoginRequiredMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

# SECURITY WARNING: DEBUG must be False in production!
# Temporarily enabling for debugging login issues
DEBUG = True  # TEMPORARILY ENABLED FOR DEBUGGING

# Enable debug toolbar for debugging
if DEBUG:
    INTERNAL_IPS = [
        '127.0.0.1',
        'localhost',
    ]

# Production allowed hosts - MUST be configured properly
ALLOWED_HOSTS = [
    # Add your production domain(s) here
    # 'inventory.yourdomain.com',
    # 'www.yourdomain.com',
]

# Allow hosts from environment variable (for deployment flexibility)
if 'DJANGO_ALLOWED_HOSTS' in os.environ:
    ALLOWED_HOSTS.extend(os.environ.get('DJANGO_ALLOWED_HOSTS', '').split(','))

# Ensure allowed hosts are configured
if not ALLOWED_HOSTS or ALLOWED_HOSTS == ['']:
    raise ValueError("ALLOWED_HOSTS must be configured for production deployment")

# Database configuration with connection pooling and thread safety
DATABASES = {
    'default': dj_database_url.parse(env('DATABASE_URL'), conn_max_age=env.int('DATABASE_CONN_MAX_AGE', 600))
}

# Ensure thread-safe database connections
DATABASES['default']['OPTIONS'] = {
    'sslmode': 'require',
}

# Connection health checks for production
DATABASES['default']['CONN_HEALTH_CHECKS'] = True

# Cache configuration - Redis required for production
REDIS_URL = os.environ.get('REDIS_URL')
if REDIS_URL:
    CACHES = {
        'default': {
            'BACKEND': 'django_redis.cache.RedisCache',
            'LOCATION': REDIS_URL,
            'OPTIONS': {
                'CLIENT_CLASS': 'django_redis.client.DefaultClient',
                'CONNECTION_POOL_KWARGS': {
                    'max_connections': 50,
                    'retry_on_timeout': True,
                },
            },
            'KEY_PREFIX': 'inventory_prod',
            'TIMEOUT': 300,
        }
    }
else:
    # Fallback to database cache
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.db.DatabaseCache',
            'LOCATION': 'cache_table',
        }
    }

# Email configuration for production
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', '587'))
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD')
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'noreply@yourdomain.com')

# Static files configuration for production
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Media files configuration
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
MEDIA_URL = '/media/'

# Security settings for production - CRITICAL
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'
SECURE_CROSS_ORIGIN_OPENER_POLICY = 'same-origin'
X_FRAME_OPTIONS = 'DENY'

# Session and CSRF security
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = 'Lax'

# Additional security headers
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Logging Configuration - Enhanced for Debugging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'detailed': {
            'format': '{asctime} [{levelname}] {name}: {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'detailed',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'DEBUG',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'django.contrib.auth': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'django.request': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'django.db': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'inventory': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}

# Django REST Framework settings for production
REST_FRAMEWORK.update({
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle'
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/hour',
        'user': '1000/hour'
    },
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 25,
})

# Performance settings for production
DATA_UPLOAD_MAX_MEMORY_SIZE = 5242880  # 5MB
FILE_UPLOAD_MAX_MEMORY_SIZE = 5242880  # 5MB
DATA_UPLOAD_MAX_NUMBER_FIELDS = 1000

# Admin URL obfuscation for security
ADMIN_URL = os.environ.get('ADMIN_URL', 'admin/')

# Application-specific settings for production
INVENTORY_SETTINGS = {
    'DEFAULT_ITEMS_PER_PAGE': 50,
    'MAX_UPLOAD_SIZE': 1024 * 1024 * 10,  # 10MB
    'ALLOWED_UPLOAD_EXTENSIONS': ['.csv', '.xlsx', '.xls'],
    'ENABLE_API_THROTTLING': True,
    'API_THROTTLE_RATE': '500/hour',
    'ENABLE_AUDIT_LOGGING': True,
    'REQUIRE_SSL': True,
}

# Monitoring and error reporting - Sentry
if 'SENTRY_DSN' in os.environ:
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration
    from sentry_sdk.integrations.logging import LoggingIntegration
    from sentry_sdk.integrations.redis import RedisIntegration
    
    sentry_logging = LoggingIntegration(
        level=logging.INFO,
        event_level=logging.ERROR
    )
    
    sentry_sdk.init(
        dsn=os.environ.get('SENTRY_DSN'),
        integrations=[
            DjangoIntegration(),
            sentry_logging,
            RedisIntegration(),
        ],
        traces_sample_rate=0.01,  # Low sample rate for production
        profiles_sample_rate=0.01,
        send_default_pii=False,
        environment='production',
        release=os.environ.get('APP_VERSION', 'latest'),
    )

# Health check configuration
HEALTH_CHECK_SETTINGS = {
    'DISK_USAGE_MAX': 90,  # Percentage
    'MEMORY_MIN': 100,     # MB
}

# Backup configuration
BACKUP_SETTINGS = {
    'ENABLE_AUTO_BACKUP': True,
    'BACKUP_SCHEDULE': '0 2 * * *',  # Daily at 2 AM
    'BACKUP_RETENTION_DAYS': 30,
    'BACKUP_LOCATION': os.environ.get('BACKUP_LOCATION', '/backups/'),
}

# Rate limiting
RATELIMIT_ENABLE = True
RATELIMIT_USE_CACHE = 'default'

# Content Security Policy
CSP_DEFAULT_SRC = ["'self'"]
CSP_SCRIPT_SRC = ["'self'", "'unsafe-inline'"]
CSP_STYLE_SRC = ["'self'", "'unsafe-inline'"]
CSP_IMG_SRC = ["'self'", "data:", "https:"]
CSP_FONT_SRC = ["'self'"]

# WhiteNoise settings for static files
WHITENOISE_USE_FINDERS = True
WHITENOISE_AUTOREFRESH = False
WHITENOISE_MAX_AGE = 31536000  # 1 year

# Session configuration
SESSION_ENGINE = 'django.contrib.sessions.backends.cached_db'
SESSION_CACHE_ALIAS = 'default'
SESSION_COOKIE_AGE = 3600  # 1 hour

# Password validation - extra strict for production
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
        'OPTIONS': {
            'max_similarity': 0.7,
        }
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 12,
        }
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Ensure critical environment variables are set
required_env_vars = [
    'DJANGO_SECRET_KEY',
    'DATABASE_URL',
    'DJANGO_ALLOWED_HOSTS',
]

missing_vars = [var for var in required_env_vars if not os.environ.get(var)]
if missing_vars:
    raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")

print("🚀 Production settings loaded successfully!")
print(f"🔒 Security: SSL enabled, HSTS configured")
print(f"📊 Monitoring: {'Sentry enabled' if 'SENTRY_DSN' in os.environ else 'Sentry not configured'}")
print(f"💾 Cache: {'Redis enabled' if REDIS_URL else 'Database cache fallback'}")
print(f"📧 Email: {'SMTP configured' if EMAIL_HOST_USER else 'Email not configured'}")
