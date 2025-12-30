#!/usr/bin/env python3
"""
Script to set a password for an existing user in the database.
Useful when migrating from Cognito to local auth.

Usage:
    python -m api.scripts.set_password user@example.com NewPassword123
    
Or run directly:
    cd api
    python scripts/set_password.py user@example.com NewPassword123
"""
import sys
import asyncio
import hashlib
import secrets
import hmac


def hash_password(password: str) -> str:
    """Hash password using PBKDF2-SHA256."""
    salt = secrets.token_hex(16)
    hash_obj = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt.encode('utf-8'),
        100000
    )
    return f"{salt}${hash_obj.hex()}"


def validate_password(password: str) -> list:
    """Validate password meets requirements."""
    import re
    errors = []
    
    if len(password) < 8:
        errors.append("Password must be at least 8 characters long")
    if not re.search(r'[A-Z]', password):
        errors.append("Password must contain at least one uppercase letter")
    if not re.search(r'[a-z]', password):
        errors.append("Password must contain at least one lowercase letter")
    if not re.search(r'\d', password):
        errors.append("Password must contain at least one digit")
    
    return errors


async def set_user_password(email: str, password: str):
    """Set password for user in database."""
    # Validate password
    errors = validate_password(password)
    if errors:
        print("❌ Password validation failed:")
        for error in errors:
            print(f"   - {error}")
        sys.exit(1)
    
    # Import here to avoid issues when running standalone
    from api.utils.db import async_engine
    from sqlalchemy import text
    
    password_hash = hash_password(password)
    
    async with async_engine.connect() as conn:
        # Check if user exists
        result = await conn.execute(
            text("SELECT user_id, email FROM users WHERE email = :email"),
            {"email": email}
        )
        user = result.fetchone()
        
        if not user:
            print(f"❌ User not found: {email}")
            sys.exit(1)
        
        # Update password
        await conn.execute(
            text("UPDATE users SET password_hash = :hash WHERE email = :email"),
            {"hash": password_hash, "email": email}
        )
        await conn.commit()
        
        print(f"✅ Password updated for: {email}")
        print(f"   User ID: {user[0]}")
        print("")
        print("You can now login with:")
        print(f"   Email: {email}")
        print(f"   Password: {password}")


def main():
    if len(sys.argv) < 3:
        print("Usage: python -m api.scripts.set_password <email> <new_password>")
        print("")
        print("Example:")
        print("  python -m api.scripts.set_password user@example.com MyNewPassword123")
        sys.exit(1)
    
    email = sys.argv[1]
    password = sys.argv[2]
    
    print(f"Setting password for: {email}")
    print("")
    
    asyncio.run(set_user_password(email, password))


if __name__ == "__main__":
    main()

