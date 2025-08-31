# Multi-environment Dockerfile for Django application
FROM python:3.13-slim

# Build-time environment selection
ARG BUILD_ENV=dev

# Runtime environment configuration
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=inventory_app.settings \
    DJANGO_ENV=${BUILD_ENV} \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y postgresql-client curl && \
    if [ "$BUILD_ENV" = "production" ]; then \
        apt-get install -y wget gcc libc6-dev libpq-dev; \
    fi && \
    rm -rf /var/lib/apt/lists/* && \
    apt-get clean

# Create non-root user
RUN adduser --disabled-password --gecos '' appuser && \
    chown -R appuser:appuser /app
USER appuser

# Install Python dependencies
COPY requirements.txt requirements-prod.txt* ./
RUN pip install --upgrade pip && \
    pip install -r requirements.txt && \
    if [ "$BUILD_ENV" = "production" ] && [ -f requirements-prod.txt ]; then \
        pip install -r requirements-prod.txt; \
    fi && \
    if [ "$BUILD_ENV" = "production" ]; then \
        pip install \ \
            gunicorn[gevent]==23.0.0 \ \
            psycopg[binary]==3.2.9 \ \
            redis==5.0.1 \ \
            sentry-sdk[django]==1.32.0 \ \
            django-health-check==3.17.0; \
    fi

# Copy project
COPY --chown=appuser:appuser . .

# Expose the port Gunicorn will listen on
EXPOSE 8000

# Health check varies by environment
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD if [ "$BUILD_ENV" = "production" ]; then curl -f http://localhost:8000/healthz || exit 1; \
    elif [ "$BUILD_ENV" = "staging" ]; then curl -f http://localhost:8000/admin/ || exit 1; \
    else exit 0; fi

# Default command
CMD ["sh", "-c", "python manage.py migrate && if [ '$BUILD_ENV' != 'dev' ]; then python manage.py collectstatic --noinput; fi && if [ '$BUILD_ENV' = 'production' ]; then exec gunicorn inventory_app.wsgi:application --bind 0.0.0.0:8000 --workers 4 --worker-class gevent --worker-connections 1000 --max-requests 1000 --max-requests-jitter 100 --timeout 30 --keep-alive 2; else exec gunicorn inventory_app.wsgi:application --bind 0.0.0.0:8000 --workers 3 --timeout 30; fi"]
