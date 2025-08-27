#!/usr/bin/env bash
# Render.com build script for Django Inventory App

set -o errexit  # exit on error

echo "🚀 Starting Render deployment build..."

# Install Python dependencies
echo "📦 Installing Python dependencies..."
pip install -r requirements.txt

# Install Node.js dependencies and build CSS (if you have package.json)
if [ -f "package.json" ]; then
    echo "📦 Installing Node.js dependencies..."
    npm install
    
    echo "🎨 Building Tailwind CSS..."
    npx tailwindcss -i ./static/src/app.css -o ./static/css/app.css --minify
fi

# Collect static files
echo "📂 Collecting static files..."
python manage.py collectstatic --noinput

# Run database migrations
echo "🗄️ Running database migrations..."
python manage.py migrate

echo "✅ Build completed successfully!"
