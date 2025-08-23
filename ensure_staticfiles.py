#!/usr/bin/env python
"""
Emergency staticfiles creator for Railway deployment
Copies static files if collectstatic fails
"""
import os
import shutil
from pathlib import Path

def copy_static_files():
    """Copy static files manually if collectstatic fails"""
    try:
        # Paths
        source_static = Path("/app/static")
        dest_staticfiles = Path("/app/staticfiles")
        
        print(f"🔍 Checking static files...")
        print(f"Source: {source_static} (exists: {source_static.exists()})")
        print(f"Destination: {dest_staticfiles} (exists: {dest_staticfiles.exists()})")
        
        # Create destination if it doesn't exist
        dest_staticfiles.mkdir(parents=True, exist_ok=True)
        
        # Copy files if source exists
        if source_static.exists():
            print(f"📁 Copying files from {source_static} to {dest_staticfiles}")
            
            for item in source_static.rglob("*"):
                if item.is_file():
                    # Calculate relative path
                    relative_path = item.relative_to(source_static)
                    dest_file = dest_staticfiles / relative_path
                    
                    # Create parent directories
                    dest_file.parent.mkdir(parents=True, exist_ok=True)
                    
                    # Copy file
                    shutil.copy2(item, dest_file)
                    print(f"  ✅ Copied: {relative_path}")
            
            print(f"✅ Static files copied successfully!")
            return True
        else:
            print(f"❌ Source directory {source_static} not found")
            return False
            
    except Exception as e:
        print(f"❌ Error copying static files: {e}")
        return False

if __name__ == "__main__":
    copy_static_files()