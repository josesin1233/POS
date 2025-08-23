#!/usr/bin/env python
"""
Generate a secure Django SECRET_KEY for production deployment
Run this script and copy the output to your Railway environment variables
"""

from django.core.management.utils import get_random_secret_key

def main():
    print("🔑 Generating Django SECRET_KEY for production...")
    print("=" * 60)
    
    secret_key = get_random_secret_key()
    
    print(f"SECRET_KEY={secret_key}")
    print("=" * 60)
    print("✅ Copy the SECRET_KEY above to your Railway environment variables")
    print("🚨 NEVER commit this key to version control!")
    print("💡 Use this key in Railway dashboard > Variables > SECRET_KEY")

if __name__ == "__main__":
    main()