#!/usr/bin/env bash
# Render.com build script for Django Inventory App

set -o errexit  # exit on error

echo "🚀 Starting Render deployment build..."

# Install Python dependencies
echo "📦 Installing Python dependencies..."
pip install -r requirements.txt

# Install Node.js dependencies and build CSS
echo "📦 Installing Node.js dependencies..."
npm install

echo "🎨 Building Tailwind CSS..."
npm run build-css

# Collect static files
echo "📂 Collecting static files..."
python manage.py collectstatic --noinput

# Run database migrations
echo "🗄️ Running database migrations..."
python manage.py migrate

# Ensure superuser exists for admin access
echo "👤 Ensuring superuser exists..."
python manage.py ensure_superuser

echo "✅ Build completed successfully!"
