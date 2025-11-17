#!/usr/bin/env python
"""
Railway migration script with retry logic and better error handling.
"""
import os
import time
import sys
import subprocess
from pathlib import Path

# Add the project directory to Python path
BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR))

# Set Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dulceria_pos.settings')

def wait_for_db():
    """Wait for database to become available"""
    import django
    django.setup()

    from django.db import connection
    from django.core.management.color import no_style
    style = no_style()

    max_retries = 10
    retry_delay = 5

    for attempt in range(max_retries):
        try:
            print(f"🔄 Attempt {attempt + 1}/{max_retries}: Testing database connection...")
            connection.ensure_connection()
            print("✅ Database connection successful!")
            return True
        except Exception as e:
            print(f"❌ Database connection failed: {e}")
            if attempt < max_retries - 1:
                print(f"⏳ Waiting {retry_delay} seconds before retry...")
                time.sleep(retry_delay)
            else:
                print("💥 All database connection attempts failed!")
                # Print environment info for debugging
                print("🔍 Environment debugging:")
                print(f"DATABASE_URL present: {'DATABASE_URL' in os.environ}")
                if 'DATABASE_URL' in os.environ:
                    db_url = os.environ['DATABASE_URL']
                    # Mask password for security
                    if '://' in db_url and '@' in db_url:
                        parts = db_url.split('://')
                        if len(parts) == 2 and '@' in parts[1]:
                            user_pass, host_db = parts[1].split('@', 1)
                            if ':' in user_pass:
                                user, _ = user_pass.split(':', 1)
                                masked_url = f"{parts[0]}://{user}:***@{host_db}"
                            else:
                                masked_url = f"{parts[0]}://{user_pass}:***@{host_db}"
                        else:
                            masked_url = db_url
                    else:
                        masked_url = "Invalid URL format"
                    print(f"DATABASE_URL (masked): {masked_url}")

                return False

def run_migrations():
    """Run Django migrations"""
    print("🗄️ Starting database migrations...")

    try:
        result = subprocess.run([
            sys.executable, 'manage.py', 'migrate', '--noinput'
        ], check=True, capture_output=True, text=True)

        print("✅ Migrations completed successfully!")
        if result.stdout:
            print("Migration output:")
            print(result.stdout)
        return True

    except subprocess.CalledProcessError as e:
        print(f"❌ Migrations failed with exit code {e.returncode}")
        if e.stdout:
            print("STDOUT:")
            print(e.stdout)
        if e.stderr:
            print("STDERR:")
            print(e.stderr)
        return False

def main():
    print("🚀 Railway Migration Script Starting...")

    # Wait for database
    if not wait_for_db():
        print("💥 Failed to connect to database. Exiting...")
        sys.exit(1)

    # Run migrations
    if not run_migrations():
        print("💥 Migrations failed. Exiting...")
        sys.exit(1)

    print("✅ Railway migration script completed successfully!")

if __name__ == '__main__':
    main()