"""
WSGI config for dulceria_pos project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/wsgi/
"""

import os
import django
from pathlib import Path

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dulceria_pos.settings')

# Force staticfiles setup for Railway
def setup_staticfiles():
    """Ensure static files are available in Railway"""
    try:
        import shutil
        from django.conf import settings
        
        # Setup Django first
        django.setup()
        
        # Create staticfiles directory
        staticfiles_dir = Path("/app/staticfiles")
        staticfiles_dir.mkdir(parents=True, exist_ok=True)
        print(f"✅ Created staticfiles directory: {staticfiles_dir}")
        
        # Copy static files manually
        source_dir = Path("/app/static")
        if source_dir.exists():
            print(f"📁 Copying static files from {source_dir}")
            for item in source_dir.rglob("*"):
                if item.is_file():
                    relative_path = item.relative_to(source_dir)
                    dest_file = staticfiles_dir / relative_path
                    dest_file.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(item, dest_file)
            print("Static files copied successfully")
        else:
            print(f"WARNING: Source directory {source_dir} not found")
            
        # Also try collectstatic
        from django.core.management import execute_from_command_line
        print("Running collectstatic...")
        execute_from_command_line(['manage.py', 'collectstatic', '--noinput', '--clear'])
        print("collectstatic completed")
        
    except Exception as e:
        print(f"WARNING: Static files setup error (continuing): {e}")

# ALWAYS run staticfiles setup (force debug logging)
print("WSGI.PY LOADING - About to run staticfiles setup")
print(f"DEBUG = {os.getenv('DEBUG', 'Not Set')}")
print(f"Current working directory: {os.getcwd()}")

# Force run regardless of DEBUG
setup_staticfiles()
print("WSGI.PY - staticfiles setup completed")

application = get_wsgi_application()
