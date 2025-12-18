"""
Configuration management using Pydantic settings.
"""
from typing import List
from pydantic import field_validator, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict
import os
from pathlib import Path


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Environment
    ENVIRONMENT: str = "development"
    
    # API Settings
    API_TITLE: str = "FinApp API"
    API_VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # Database Settings
    DATABASE_URL: str
    DATABASE_POOL_SIZE: int = 5
    DATABASE_MAX_OVERFLOW: int = 10
    
    # AWS Cognito Settings
    COGNITO_REGION: str
    COGNITO_USER_POOL_ID: str
    COGNITO_APP_CLIENT_ID: str
    COGNITO_APP_CLIENT_SECRET: str = ""
    
    # JWT Settings
    JWT_ALGORITHM: str = "RS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    
    # CORS Settings
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:5000"
    
    # Security Settings
    RATE_LIMIT_PER_MINUTE: int = 100
    
    # Logging Settings
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"
    
    @field_validator("DATABASE_URL")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        """Validate database URL is not empty."""
        if not v:
            raise ValueError("DATABASE_URL must be set")
        return v
    
    @field_validator("COGNITO_USER_POOL_ID", "COGNITO_APP_CLIENT_ID")
    @classmethod
    def validate_cognito_settings(cls, v: str) -> str:
        """Validate Cognito settings are not empty."""
        if not v:
            raise ValueError("Cognito settings must be configured")
        return v
    
    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS origins from string to list."""
        if not self.CORS_ORIGINS or self.CORS_ORIGINS.strip() == "":
            return []
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]
    
    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.ENVIRONMENT.lower() in ["development", "dev"]
    
    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.ENVIRONMENT.lower() in ["production", "prod"]
    
    model_config = SettingsConfigDict(
        # Look for .env file in the api directory (where this config file is located)
        # This allows running uvicorn from either the project root or api directory
        env_file=str(Path(__file__).parent / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )


def get_settings() -> Settings:
    """Get settings instance with validation."""
    try:
        return Settings()
    except ValidationError as e:
        print(f"Configuration error: {e}")
        raise


# Global settings instance
settings = get_settings()
