"""
User service for user management business logic.
"""
from typing import Dict, Any, Optional

from api.repositories.user_repository import UserRepository
from api.utils.exceptions import ResourceNotFoundError


class UserService:
    """Service for handling user management operations."""
    
    def __init__(self, user_repository: UserRepository):
        """
        Initialize user service.
        
        Args:
            user_repository: User repository instance
        """
        self.user_repository = user_repository
    
    async def get_or_create_user(self, cognito_sub: str, email: str) -> Dict[str, Any]:
        """
        Get user by Cognito sub, or create if doesn't exist.
        
        This is called on first login to sync Cognito users with local database.
        
        Args:
            cognito_sub: Cognito user identifier
            email: User email address
            
        Returns:
            User dictionary
        """
        # Try to get existing user
        user = await self.user_repository.get_user_by_cognito_sub(cognito_sub)
        
        if user:
            return user
        
        # Create new user if doesn't exist
        return await self.user_repository.create_user(cognito_sub, email)
    
    async def get_user_by_id(self, user_id: str) -> Dict[str, Any]:
        """
        Get user by user ID.
        
        Args:
            user_id: User ID
            
        Returns:
            User dictionary
            
        Raises:
            ResourceNotFoundError: If user not found
        """
        user = await self.user_repository.get_user_by_cognito_sub(user_id)
        
        if not user:
            raise ResourceNotFoundError("User not found")
        
        return user
    
    async def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """
        Get user by email.
        
        Args:
            email: User email address
            
        Returns:
            User dictionary if found, None otherwise
        """
        return await self.user_repository.get_user_by_email(email)
