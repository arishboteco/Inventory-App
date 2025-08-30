# 🚀 Staging Deployment Guide

> **Note:** Placeholder values only. Replace with real credentials in your deployment environment—never commit live secrets.

## Environment Setup

### 1. Staging Environment Variables

Create a `.env.staging` file with:

```bash
# Django Configuration
DJANGO_DEBUG=False
DJANGO_SECRET_KEY=<STAGING_SECRET_KEY>
DJANGO_ALLOWED_HOSTS=<STAGING_DOMAIN>,localhost,127.0.0.1

# Database Configuration (Use staging database)
DATABASE_URL=postgresql://<STAGING_DB_USER>:<STAGING_DB_PASSWORD>@<STAGING_DB_HOST>:5432/<STAGING_DB_NAME>
DATABASE_SSL_REQUIRE=True

# Application Settings
DJANGO_SETTINGS_MODULE=inventory_app.settings

# Optional: Monitoring and Logging
SENTRY_DSN=<SENTRY_DSN>
LOG_LEVEL=INFO

# Email Settings (for testing)
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend

# Cache Configuration
REDIS_URL=redis://staging-redis:6379/0
```

### 2. Staging Settings Override

Create `inventory_app/settings_staging.py`:

```python
from .settings import *

# Staging-specific overrides
DEBUG = False
ALLOWED_HOSTS = os.environ.get('DJANGO_ALLOWED_HOSTS', '').split(',')

# Use staging database
DATABASES = {
    'default': dj_database_url.parse(
        os.environ.get('DATABASE_URL', 'sqlite:///staging.db')
    )
}

# Email backend for testing
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Logging configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': '/tmp/django-staging.log',
            'formatter': 'verbose',
        },
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': True,
        },
        'inventory': {
            'handlers': ['file', 'console'],
            'level': 'DEBUG',
            'propagate': True,
        },
    },
}
```

## Deployment Commands

### 1. Database Migration Check

```bash
# Check migration status
python manage.py showmigrations --settings=inventory_app.settings_staging

# Apply migrations (should be no-op)
python manage.py migrate --settings=inventory_app.settings_staging
```

### 2. Static Files Collection

```bash
# Collect static files
python manage.py collectstatic --noinput --settings=inventory_app.settings_staging
```

### 3. Application Server

```bash
# Start with Gunicorn
gunicorn inventory_app.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers 3 \
    --timeout 30 \
    --keep-alive 2 \
    --max-requests 1000 \
    --max-requests-jitter 100 \
    --env DJANGO_SETTINGS_MODULE=inventory_app.settings_staging
```

## Validation Tests

### 1. Health Check

```bash
curl -f http://staging-domain/healthz || echo "Health check failed"
```

### 2. Database Connectivity

```bash
python manage.py shell --settings=inventory_app.settings_staging -c "
from django.db import connection
cursor = connection.cursor()
cursor.execute('SELECT 1')
print('Database connection: OK')
"
```

### 3. Core Functionality

```bash
# Run critical path tests
python manage.py test tests.test_item_service tests.test_recipe_service tests.test_dashboard_service --settings=inventory_app.settings_staging
```

## Docker Option (Alternative)

### Dockerfile.staging

```dockerfile
FROM python:3.13-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy application code
COPY . .

# Set environment variables
ENV DJANGO_SETTINGS_MODULE=inventory_app.settings_staging
ENV PYTHONPATH=/app

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/healthz || exit 1

# Start command
CMD ["gunicorn", "inventory_app.wsgi:application", "--bind", "0.0.0.0:8000"]
```

### docker-compose.staging.yml

```yaml
version: "3.8"

services:
  web:
    build:
      context: .
      dockerfile: Dockerfile.staging
    ports:
      - "8000:8000"
    environment:
      - DJANGO_SETTINGS_MODULE=inventory_app.settings_staging
    env_file:
      - .env.staging
    depends_on:
      - db
      - redis

  db:
    image: postgres:15
    env_file:
      - .env.staging
    environment:
      POSTGRES_DB: ${POSTGRES_DB}
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - staging_postgres_data:/var/lib/postgresql/data/

  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes
    volumes:
      - staging_redis_data:/data

volumes:
  staging_postgres_data:
  staging_redis_data:
```

## Monitoring Setup

### 1. Application Monitoring

```bash
# Install monitoring packages
pip install sentry-sdk django-health-check

# Add to requirements.txt if not present
echo "sentry-sdk[django]==1.32.0" >> requirements.txt
echo "django-health-check==3.17.0" >> requirements.txt
```

### 2. Log Monitoring

```bash
# Set up log rotation
sudo tee /etc/logrotate.d/django-staging > /dev/null <<EOF
/tmp/django-staging.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    create 644 www-data www-data
}
EOF
```

## Rollback Plan

### 1. Application Rollback

```bash
# Keep previous version available
cp -r /app/current /app/backup-$(date +%Y%m%d-%H%M%S)

# Rollback command
mv /app/backup-YYYYMMDD-HHMMSS /app/current
sudo systemctl restart gunicorn-staging
```

### 2. Database Rollback

```bash
# Database backup before deployment
pg_dump staging_inventory > backup-$(date +%Y%m%d-%H%M%S).sql

# Rollback database if needed
psql staging_inventory < backup-YYYYMMDD-HHMMSS.sql
```

## Success Criteria

### Performance Targets

- Page load time: < 2 seconds
- API response time: < 500ms
- Database query time: < 100ms average
- Zero 5xx errors during testing

### Functionality Validation

- [ ] User authentication works
- [ ] CRUD operations on all major entities
- [ ] Department management features
- [ ] Recipe creation and management
- [ ] Dashboard displays correctly
- [ ] Data import/export functions
- [ ] API endpoints respond correctly

### Load Testing

```bash
# Install Apache Bench for basic load testing
sudo apt-get install apache2-utils

# Basic load test
ab -n 1000 -c 10 http://staging-domain/dashboard/

# Test API endpoints
ab -n 500 -c 5 http://staging-domain/api/items/
```

## Next Steps After Staging Success

1. ✅ Staging validation complete
2. 🔄 Production deployment planning
3. 🔄 User acceptance testing
4. 🔄 Performance optimization if needed
5. 🔄 Production deployment execution
