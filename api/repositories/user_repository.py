"""
User repository for database operations.
"""
from typing import Optional, Dict, Any
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from api.repositories.base_repository import BaseRepository
from api.models.domain import User
from api.utils.exceptions import DuplicateResourceError, DatabaseError


class UserRepository(BaseRepository):
    """Repository for user database operations."""
    
    async def get_user_by_cognito_sub(self, cognito_sub: str) -> Optional[Dict[str, Any]]:
        """
        Get user by Cognito sub.
        
        Args:
            cognito_sub: Cognito user identifier
            
        Returns:
            User dictionary if found, None otherwise
        """
        try:
            stmt = select(User).where(User.cognito_sub == cognito_sub)
            result = await self.db.execute(stmt)
            user = result.scalar_one_or_none()
            
            if user:
                return {
                    'user_id': user.user_id,
                    'cognito_sub': user.cognito_sub,
                    'email': user.email,
                    'created_at': user.created_at,
                    'updated_at': user.updated_at,
                    'is_active': user.is_active
                }
            return None
            
        except Exception as e:
            raise DatabaseError(f"Failed to get user by cognito_sub: {str(e)}")
    
    async def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """
        Get user by email.
        
        Args:
            email: User email address
            
        Returns:
            User dictionary if found, None otherwise
        """
        try:
            stmt = select(User).where(User.email == email)
            result = await self.db.execute(stmt)
            user = result.scalar_one_or_none()
            
            if user:
                return {
                    'user_id': user.user_id,
                    'cognito_sub': user.cognito_sub,
                    'email': user.email,
                    'created_at': user.created_at,
                    'updated_at': user.updated_at,
                    'is_active': user.is_active
                }
            return None
            
        except Exception as e:
            raise DatabaseError(f"Failed to get user by email: {str(e)}")
    
    async def create_user(self, cognito_sub: str, email: str) -> Dict[str, Any]:
        """
        Create a new user.
        
        Args:
            cognito_sub: Cognito user identifier
            email: User email address
            
        Returns:
            Created user dictionary
            
        Raises:
            DuplicateResourceError: If user with email or cognito_sub already exists
            DatabaseError: If database operation fails
        """
        try:
            user = User(
                cognito_sub=cognito_sub,
                email=email,
                is_active=True
            )
            
            self.db.add(user)
            await self.db.flush()
            await self.db.refresh(user)
            
            return {
                'user_id': user.user_id,
                'cognito_sub': user.cognito_sub,
                'email': user.email,
                'created_at': user.created_at,
                'updated_at': user.updated_at,
                'is_active': user.is_active
            }
            
        except IntegrityError as e:
            await self.db.rollback()
            if 'cognito_sub' in str(e):
                raise DuplicateResourceError("User with this Cognito ID already exists")
            elif 'email' in str(e):
                raise DuplicateResourceError("User with this email already exists")
            else:
                raise DuplicateResourceError("User already exists")
        except Exception as e:
            await self.db.rollback()
            raise DatabaseError(f"Failed to create user: {str(e)}")
