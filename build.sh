#!/bin/bash
echo "🚀 Railway Build Script Starting..."

# Install dependencies
echo "📦 Installing dependencies..."
pip install -r requirements.txt

# Setup environment
export DJANGO_SETTINGS_MODULE=dulceria_pos.settings

# Create staticfiles directory
echo "📁 Creating staticfiles directory..."
mkdir -p /app/staticfiles
ls -la /app/

# Run migrations
echo "🗄️ Running migrations..."
python manage.py migrate --noinput

# Collect static files (try multiple approaches)
echo "🎨 Collecting static files..."
python manage.py collectstatic --noinput --clear --verbosity=2 || echo "⚠️ collectstatic failed, will handle in runtime"

# Copy static files manually as backup
echo "📋 Manual static files backup..."
if [ -d "/app/static" ]; then
    echo "Copying from /app/static to /app/staticfiles"
    cp -r /app/static/* /app/staticfiles/ 2>/dev/null || echo "Manual copy failed"
fi

# Run init script
echo "🎯 Running initialization script..."
python init_railway.py || echo "⚠️ init_railway.py failed, continuing..."

# List staticfiles
echo "📂 Final staticfiles directory contents:"
ls -la /app/staticfiles/ || echo "No staticfiles directory found"
ls -la /app/staticfiles/css/ 2>/dev/null || echo "No CSS directory found"

echo "✅ Build script completed!"