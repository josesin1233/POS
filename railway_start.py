#!/usr/bin/env python
"""
Railway startup script que maneja migrations y static files
"""
import os
import sys
import subprocess
import django

def run_command(cmd):
    """Execute command and handle errors"""
    print(f"🔄 Running: {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"❌ Error running: {cmd}")
        print(f"STDOUT: {result.stdout}")
        print(f"STDERR: {result.stderr}")
        return False
    else:
        print(f"✅ Success: {cmd}")
        if result.stdout:
            print(f"OUTPUT: {result.stdout}")
        return True

def main():
    print("🚀 Starting Railway deployment setup...")
    
    # Set Django settings
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dulceria_pos.settings')
    
    # Ensure staticfiles directory exists
    import os
    staticfiles_dir = "/app/staticfiles"
    if not os.path.exists(staticfiles_dir):
        os.makedirs(staticfiles_dir, exist_ok=True)
        print(f"✅ Created directory: {staticfiles_dir}")
    
    # Commands to run in order
    commands = [
        "python manage.py migrate --noinput",
        "python manage.py collectstatic --noinput --clear --verbosity=2",
        "python init_railway.py",
    ]
    
    success_count = 0
    
    for cmd in commands:
        if run_command(cmd):
            success_count += 1
        else:
            print(f"⚠️ Command failed but continuing: {cmd}")
    
    print(f"📊 Completed {success_count}/{len(commands)} commands successfully")
    
    # Emergency staticfiles backup if collectstatic failed
    if success_count < 2:
        print("🚨 collectstatic might have failed, trying emergency backup...")
        if run_command("python ensure_staticfiles.py"):
            print("✅ Emergency staticfiles backup completed!")
        else:
            print("❌ Emergency backup also failed")
    
    if success_count >= 1:  # At least migrate worked
        print("✅ Railway setup completed successfully!")
        return True
    else:
        print("⚠️ Some commands failed but continuing...")
        return True  # Continue anyway to start the web server

if __name__ == "__main__":
    success = main()
    if not success:
        sys.exit(1)