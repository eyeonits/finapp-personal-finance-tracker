#!/usr/bin/env python3
"""
Verification script to check if the API setup is correct.
"""
import sys
import os

# Add the parent directory to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def verify_imports():
    """Verify all critical imports work."""
    print("Verifying imports...")
    
    try:
        from api.main import app
        print("✓ Main application imports successfully")
    except Exception as e:
        print(f"✗ Failed to import main application: {e}")
        return False
    
    try:
        from api.config import settings
        print("✓ Configuration imports successfully")
    except Exception as e:
        print(f"✗ Failed to import configuration: {e}")
        return False
    
    try:
        from api.dependencies import get_current_user_id
        print("✓ Dependencies import successfully")
    except Exception as e:
        print(f"✗ Failed to import dependencies: {e}")
        return False
    
    try:
        from api.models.domain import User, Transaction, ImportHistory
        print("✓ Domain models import successfully")
    except Exception as e:
        print(f"✗ Failed to import domain models: {e}")
        return False
    
    try:
        from api.models.requests import RegisterRequest, LoginRequest
        print("✓ Request models import successfully")
    except Exception as e:
        print(f"✗ Failed to import request models: {e}")
        return False
    
    try:
        from api.models.responses import TokenResponse, UserResponse
        print("✓ Response models import successfully")
    except Exception as e:
        print(f"✗ Failed to import response models: {e}")
        return False
    
    return True


def verify_structure():
    """Verify directory structure."""
    print("\nVerifying directory structure...")
    
    required_dirs = [
        "api/routers",
        "api/services",
        "api/repositories",
        "api/models",
        "api/middleware",
        "api/utils",
        "api/alembic",
    ]
    
    all_exist = True
    for dir_path in required_dirs:
        if os.path.isdir(dir_path):
            print(f"✓ {dir_path} exists")
        else:
            print(f"✗ {dir_path} missing")
            all_exist = False
    
    return all_exist


def verify_files():
    """Verify critical files exist."""
    print("\nVerifying critical files...")
    
    required_files = [
        "api/main.py",
        "api/config.py",
        "api/dependencies.py",
        "api/requirements.txt",
        "api/docker-compose.yml",
        "api/Dockerfile",
        "api/.env.example",
        "api/alembic.ini",
        "infrastructure/cognito.tf",
    ]
    
    all_exist = True
    for file_path in required_files:
        if os.path.isfile(file_path):
            print(f"✓ {file_path} exists")
        else:
            print(f"✗ {file_path} missing")
            all_exist = False
    
    return all_exist


def main():
    """Run all verification checks."""
    print("=" * 60)
    print("FinApp API Setup Verification")
    print("=" * 60)
    
    results = []
    
    results.append(("Directory Structure", verify_structure()))
    results.append(("Critical Files", verify_files()))
    results.append(("Python Imports", verify_imports()))
    
    print("\n" + "=" * 60)
    print("Verification Summary")
    print("=" * 60)
    
    all_passed = True
    for name, passed in results:
        status = "PASSED" if passed else "FAILED"
        symbol = "✓" if passed else "✗"
        print(f"{symbol} {name}: {status}")
        if not passed:
            all_passed = False
    
    print("=" * 60)
    
    if all_passed:
        print("\n✓ All checks passed! The API setup is complete.")
        print("\nNext steps:")
        print("1. Configure AWS Cognito (see infrastructure/README.md)")
        print("2. Update .env file with your Cognito credentials")
        print("3. Start PostgreSQL: docker-compose up -d postgres")
        print("4. Run migrations: alembic upgrade head")
        print("5. Start the API: uvicorn api.main:app --reload")
        return 0
    else:
        print("\n✗ Some checks failed. Please review the errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
