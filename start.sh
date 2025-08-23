#!/bin/bash
echo "🚀 Railway Start Script Beginning..."

# Show environment
echo "Environment variables:"
echo "DEBUG = $DEBUG"
echo "DJANGO_SETTINGS_MODULE = $DJANGO_SETTINGS_MODULE"
echo "Current directory: $(pwd)"

# List what we have
echo "📂 Directory contents:"
ls -la

# Check for static files
echo "📁 Checking static directories:"
ls -la static/ 2>/dev/null || echo "No static/ directory"
ls -la staticfiles/ 2>/dev/null || echo "No staticfiles/ directory"

# Force create staticfiles if missing
if [ ! -d "staticfiles" ]; then
    echo "🚨 EMERGENCY: Creating staticfiles directory"
    mkdir -p staticfiles
    
    if [ -d "static" ]; then
        echo "📋 EMERGENCY: Copying static files"
        cp -r static/* staticfiles/ 2>/dev/null || echo "Copy failed"
    fi
fi

# Final check
echo "📊 Final staticfiles check:"
ls -la staticfiles/ 2>/dev/null || echo "Still no staticfiles!"
ls -la staticfiles/css/ 2>/dev/null || echo "No CSS found!"

# Start gunicorn
echo "🚀 Starting gunicorn..."
exec gunicorn dulceria_pos.wsgi --config gunicorn.conf.py