# Dockerfile for Django application using Gunicorn
FROM python:3.13-slim

# Disable Python buffering and writing pyc files
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Set work directory
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Copy project
COPY . .

# Expose the port Gunicorn will listen on
EXPOSE 8000

# Run migrations to initialize the auth_user table and other schema objects required for authentication
CMD ["sh", "-c", "python manage.py migrate && exec gunicorn inventory_app.wsgi:application --bind 0.0.0.0:8000"]
