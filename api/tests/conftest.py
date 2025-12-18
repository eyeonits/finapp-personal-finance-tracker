"""
Pytest configuration and fixtures for tests.
"""
import os
import pytest

# Set up test environment variables before importing any application code
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost:5432/test_db")
os.environ.setdefault("COGNITO_REGION", "us-east-1")
os.environ.setdefault("COGNITO_USER_POOL_ID", "us-east-1_TEST123456")
os.environ.setdefault("COGNITO_APP_CLIENT_ID", "test_client_id_123456")
os.environ.setdefault("COGNITO_APP_CLIENT_SECRET", "test_secret")
os.environ.setdefault("ENVIRONMENT", "test")


@pytest.fixture(scope="session")
def test_settings():
    """Provide test settings."""
    from api.config import settings
    return settings
