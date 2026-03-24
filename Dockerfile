# Multi-environment Dockerfile for Django application
# Stage 1: Build Tailwind CSS using Node
FROM node:20-slim AS css-builder

WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm install
COPY static/ ./static/
COPY tailwind.config.js postcss.config.js ./
RUN npm run build

# Stage 2: Python app
FROM python:3.13-slim

# Build-time environment selection
ARG BUILD_ENV=dev

# Runtime environment configuration
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=inventory_app.settings.${BUILD_ENV} \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y postgresql-client curl && \
    if [ "$BUILD_ENV" = "prod" ]; then \
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
    if [ "$BUILD_ENV" = "prod" ] && [ -f requirements-prod.txt ]; then \
        pip install -r requirements-prod.txt; \
    fi

# Copy project
COPY --chown=appuser:appuser . .

# Copy compiled CSS from Node stage
COPY --from=css-builder --chown=appuser:appuser /app/static/css/app.css ./static/css/app.css

# Collect static files for prod/staging
RUN if [ "$BUILD_ENV" = "prod" ] || [ "$BUILD_ENV" = "staging" ]; then \
        python manage.py collectstatic --noinput; \
    fi

# Expose the port Gunicorn will listen on
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/ || exit 1

# Default command (migrations handled by fly.toml release_command in prod)
CMD ["sh", "-c", "exec gunicorn inventory_app.wsgi:application --bind 0.0.0.0:8000 --workers 2 --timeout 120"]
