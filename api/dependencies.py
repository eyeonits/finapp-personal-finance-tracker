"""
Dependency injection for FastAPI endpoints.
"""
from typing import AsyncGenerator
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from api.utils.db import get_db_session
from api.utils.jwt_utils import decode_jwt_token
from api.services.auth_service import AuthService
from api.services.user_service import UserService
from api.services.transaction_service import TransactionService
from api.services.import_service import ImportService
from api.services.analytics_service import AnalyticsService
from api.repositories.user_repository import UserRepository
from api.repositories.transaction_repository import TransactionRepository
from api.repositories.import_repository import ImportRepository


# Security scheme for JWT Bearer tokens
security = HTTPBearer()


async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> str:
    """
    Extract and validate user ID from JWT token.
    
    Args:
        credentials: HTTP Authorization credentials with Bearer token
        
    Returns:
        User ID (Cognito sub) from token claims
        
    Raises:
        HTTPException: If token is invalid or expired
    """
    token = credentials.credentials
    
    try:
        payload = decode_jwt_token(token)
        user_id = payload.get("sub")
        
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing user ID",
            )
        
        return user_id
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}",
        )


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Get database session."""
    async for session in get_db_session():
        yield session


def get_auth_service() -> AuthService:
    """Get authentication service instance."""
    return AuthService()


def get_user_repository(db: AsyncSession = Depends(get_db)) -> UserRepository:
    """Get user repository instance."""
    return UserRepository(db)


async def get_current_db_user_id(
    cognito_sub: str = Depends(get_current_user_id),
    user_repository: UserRepository = Depends(get_user_repository),
) -> str:
    """
    Get database user_id from Cognito sub.
    
    This dependency converts the Cognito sub (from JWT token) to the database user_id.
    The database user_id is required for foreign key relationships.
    
    Args:
        cognito_sub: Cognito sub from JWT token (via get_current_user_id)
        user_repository: User repository instance
        
    Returns:
        Database user_id
        
    Raises:
        HTTPException: If user not found in database
    """
    try:
        user = await user_repository.get_user_by_cognito_sub(cognito_sub)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found in database. Please log in again.",
            )
        
        return user['user_id']
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get user: {str(e)}",
        )


def get_user_service(
    user_repository: UserRepository = Depends(get_user_repository),
) -> UserService:
    """Get user service instance."""
    return UserService(user_repository)


def get_transaction_repository(db: AsyncSession = Depends(get_db)) -> TransactionRepository:
    """Get transaction repository instance."""
    return TransactionRepository(db)


def get_transaction_service(
    repository: TransactionRepository = Depends(get_transaction_repository),
) -> TransactionService:
    """Get transaction service instance."""
    return TransactionService(repository)


def get_import_repository(db: AsyncSession = Depends(get_db)) -> ImportRepository:
    """Get import repository instance."""
    return ImportRepository(db)


def get_import_service(
    transaction_repository: TransactionRepository = Depends(get_transaction_repository),
    import_repository: ImportRepository = Depends(get_import_repository),
) -> ImportService:
    """Get import service instance."""
    return ImportService(transaction_repository, import_repository)


def get_analytics_service(
    transaction_repository: TransactionRepository = Depends(get_transaction_repository),
) -> AnalyticsService:
    """Get analytics service instance."""
    return AnalyticsService(transaction_repository)
