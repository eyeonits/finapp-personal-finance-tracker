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
                    'password_hash': user.password_hash,
                    'email_verified': getattr(user, 'email_verified', True),
                    'created_at': user.created_at,
                    'updated_at': user.updated_at,
                    'is_active': user.is_active
                }
            return None
            
        except Exception as e:
            raise DatabaseError(f"Failed to get user by email: {str(e)}")
    
    async def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get user by user_id.
        
        Args:
            user_id: User database ID
            
        Returns:
            User dictionary if found, None otherwise
        """
        try:
            stmt = select(User).where(User.user_id == user_id)
            result = await self.db.execute(stmt)
            user = result.scalar_one_or_none()
            
            if user:
                return {
                    'user_id': user.user_id,
                    'cognito_sub': user.cognito_sub,
                    'email': user.email,
                    'password_hash': user.password_hash,
                    'email_verified': getattr(user, 'email_verified', True),
                    'created_at': user.created_at,
                    'updated_at': user.updated_at,
                    'is_active': user.is_active
                }
            return None
            
        except Exception as e:
            raise DatabaseError(f"Failed to get user by id: {str(e)}")
    
    async def create_user(
        self,
        cognito_sub: str = None,
        email: str = None,
        user_id: str = None,
        password_hash: str = None,
        email_verified: bool = False,
    ) -> Dict[str, Any]:
        """
        Create a new user.
        
        Args:
            cognito_sub: Cognito user identifier (optional for local auth)
            email: User email address
            user_id: Optional user ID (auto-generated if not provided)
            password_hash: Hashed password for local auth
            email_verified: Whether email is verified
            
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
                password_hash=password_hash,
                email_verified=email_verified,
                is_active=True
            )
            
            # Override auto-generated user_id if provided
            if user_id:
                user.user_id = user_id
            
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
    
    async def update_password(self, user_id: str, password_hash: str) -> None:
        """
        Update user password hash.
        
        Args:
            user_id: User database ID
            password_hash: New hashed password
            
        Raises:
            DatabaseError: If database operation fails
        """
        try:
            stmt = select(User).where(User.user_id == user_id)
            result = await self.db.execute(stmt)
            user = result.scalar_one_or_none()
            
            if user:
                user.password_hash = password_hash
                await self.db.flush()
                
        except Exception as e:
            await self.db.rollback()
            raise DatabaseError(f"Failed to update password: {str(e)}")
