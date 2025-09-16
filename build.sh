#!/usr/bin/env bash
# 🚀 Render.com build script for Django Inventory Pro - FIXED THREADING
# 🔧 Updated: 2025-08-27 - Using sync workers to prevent threading errors

set -o errexit  # exit on error

echo "🚀 Starting Render deployment build..."

# Install Python dependencies
echo "📦 Installing Python dependencies..."
pip install -r requirements.txt

# Install Node.js dependencies and build CSS
echo "📦 Installing Node.js dependencies..."
npm install

echo "🎨 Building Tailwind CSS..."
npm run build

# Collect static files
echo "📂 Collecting static files..."
python manage.py collectstatic --noinput

# Run database migrations
echo "🗄️ Running database migrations..."
python manage.py migrate

# Setup cache table for database caching
echo "💾 Setting up cache table..."
python manage.py setup_cache

# Ensure superuser exists for admin access
echo "👤 Creating default superuser..."
python manage.py create_default_superuser

# Reset admin password to known value
echo "🔑 Resetting admin password..."
python manage.py reset_admin_password

echo "✅ Build completed successfully!"
echo "🔧 IMPORTANT: This deployment uses sync workers to fix threading issues"
