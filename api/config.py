"""
Configuration management using Pydantic settings.
"""
from typing import List, Optional
from pydantic import field_validator, model_validator, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict
import os
import secrets
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
    
    # Authentication Mode
    # Set to True to use AWS Cognito, False for local authentication (default)
    USE_COGNITO: bool = False
    
    # AWS Cognito Settings (only required if USE_COGNITO=True)
    COGNITO_REGION: str = ""
    COGNITO_USER_POOL_ID: str = ""
    COGNITO_APP_CLIENT_ID: str = ""
    COGNITO_APP_CLIENT_SECRET: str = ""
    
    # Local Auth Settings (used when USE_COGNITO=False)
    JWT_SECRET_KEY: str = ""  # Required for local auth, auto-generated in dev if not set
    JWT_ALGORITHM: str = "HS256"  # HS256 for local, RS256 for Cognito
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    
    # CORS Settings
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:5173"
    
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
    
    @model_validator(mode="after")
    def validate_auth_settings(self) -> "Settings":
        """Validate authentication settings based on mode."""
        if self.USE_COGNITO:
            # Cognito mode: require Cognito settings
            if not self.COGNITO_USER_POOL_ID or not self.COGNITO_APP_CLIENT_ID:
                raise ValueError(
                    "COGNITO_USER_POOL_ID and COGNITO_APP_CLIENT_ID are required when USE_COGNITO=True"
                )
            if not self.COGNITO_REGION:
                raise ValueError("COGNITO_REGION is required when USE_COGNITO=True")
            # Use RS256 for Cognito
            self.JWT_ALGORITHM = "RS256"
        else:
            # Local mode: require or generate JWT secret
            if not self.JWT_SECRET_KEY:
                if self.ENVIRONMENT in ["development", "dev"]:
                    # Auto-generate for development (not secure for production!)
                    self.JWT_SECRET_KEY = "dev-secret-key-change-in-production-" + secrets.token_hex(16)
                else:
                    raise ValueError(
                        "JWT_SECRET_KEY is required for local authentication in non-development environments"
                    )
            # Use HS256 for local auth
            self.JWT_ALGORITHM = "HS256"
        return self
    
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
