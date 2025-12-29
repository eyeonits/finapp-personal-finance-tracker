"""
Local authentication service using database and JWT tokens.
Used when USE_COGNITO=False (default).
"""
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import uuid
import re
import hashlib
import secrets
import hmac

from jose import jwt

from api.config import settings
from api.utils.exceptions import (
    AuthenticationError,
    ValidationError,
    DuplicateResourceError,
    ResourceNotFoundError,
)


class LocalAuthService:
    """
    Service for handling local authentication without AWS Cognito.
    Uses bcrypt for password hashing and JWT for tokens.
    """
    
    def __init__(self, user_repository):
        """Initialize local authentication service."""
        self.user_repository = user_repository
        self.secret_key = settings.JWT_SECRET_KEY
        self.algorithm = settings.JWT_ALGORITHM
        self.access_token_expire_minutes = settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
        self.refresh_token_expire_days = settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS
    
    def _hash_password(self, password: str) -> str:
        """
        Hash password using PBKDF2-SHA256.
        
        Args:
            password: Plain text password
            
        Returns:
            Hashed password string (salt$hash format)
        """
        salt = secrets.token_hex(16)
        hash_obj = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt.encode('utf-8'),
            100000  # iterations
        )
        return f"{salt}${hash_obj.hex()}"
    
    def _verify_password(self, password: str, password_hash: str) -> bool:
        """
        Verify password against hash.
        
        Args:
            password: Plain text password to verify
            password_hash: Stored hash (salt$hash format)
            
        Returns:
            True if password matches, False otherwise
        """
        try:
            salt, stored_hash = password_hash.split('$')
            hash_obj = hashlib.pbkdf2_hmac(
                'sha256',
                password.encode('utf-8'),
                salt.encode('utf-8'),
                100000
            )
            return hmac.compare_digest(hash_obj.hex(), stored_hash)
        except (ValueError, AttributeError):
            return False
    
    def _validate_password(self, password: str) -> None:
        """
        Validate password meets requirements.
        
        Requirements:
        - Minimum 8 characters
        - At least one uppercase letter
        - At least one lowercase letter
        - At least one digit
        
        Args:
            password: Password to validate
            
        Raises:
            ValidationError: If password doesn't meet requirements
        """
        errors = []
        
        if len(password) < 8:
            errors.append("Password must be at least 8 characters long")
        if not re.search(r'[A-Z]', password):
            errors.append("Password must contain at least one uppercase letter")
        if not re.search(r'[a-z]', password):
            errors.append("Password must contain at least one lowercase letter")
        if not re.search(r'\d', password):
            errors.append("Password must contain at least one digit")
        
        if errors:
            raise ValidationError("; ".join(errors))
    
    def _create_access_token(self, user_id: str, email: str) -> str:
        """
        Create JWT access token.
        
        Args:
            user_id: User's database ID
            email: User's email
            
        Returns:
            JWT access token string
        """
        expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)
        
        payload = {
            "sub": user_id,
            "email": email,
            "exp": expire,
            "iat": datetime.utcnow(),
            "token_type": "access",
        }
        
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
    
    def _create_refresh_token(self, user_id: str) -> str:
        """
        Create JWT refresh token.
        
        Args:
            user_id: User's database ID
            
        Returns:
            JWT refresh token string
        """
        expire = datetime.utcnow() + timedelta(days=self.refresh_token_expire_days)
        
        payload = {
            "sub": user_id,
            "exp": expire,
            "iat": datetime.utcnow(),
            "token_type": "refresh",
            "jti": str(uuid.uuid4()),  # Unique token ID for potential revocation
        }
        
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
    
    async def register_user(self, email: str, password: str) -> Dict[str, Any]:
        """
        Register a new user with local authentication.
        
        Args:
            email: User email address
            password: User password
            
        Returns:
            Dictionary with user_id and confirmation status
            
        Raises:
            ValidationError: If password doesn't meet requirements
            DuplicateResourceError: If email already exists
        """
        # Validate password requirements
        self._validate_password(password)
        
        # Check if email already exists
        existing_user = await self.user_repository.get_user_by_email(email)
        if existing_user:
            raise DuplicateResourceError("Email already registered")
        
        # Hash password
        password_hash = self._hash_password(password)
        
        # Create user
        user_id = str(uuid.uuid4())
        user = await self.user_repository.create_user(
            user_id=user_id,
            cognito_sub=user_id,  # Use user_id as cognito_sub for local auth
            email=email,
            password_hash=password_hash,
            email_verified=True,  # Auto-verify for local dev (can add email verification later)
        )
        
        return {
            "user_sub": user_id,
            "user_confirmed": True,  # Auto-confirmed for local auth
            "code_delivery_details": None,
        }
    
    async def login(self, email: str, password: str) -> Dict[str, Any]:
        """
        Authenticate user and return tokens.
        
        Args:
            email: User email address
            password: User password
            
        Returns:
            Dictionary with access_token, refresh_token, and expires_in
            
        Raises:
            AuthenticationError: If credentials are invalid
        """
        # Get user by email
        user = await self.user_repository.get_user_by_email(email)
        
        if not user:
            raise AuthenticationError("Invalid email or password")
        
        # Verify password
        if not user.get("password_hash"):
            raise AuthenticationError("Invalid email or password")
        
        if not self._verify_password(password, user["password_hash"]):
            raise AuthenticationError("Invalid email or password")
        
        # Check if user is active
        if not user.get("is_active", True):
            raise AuthenticationError("Account is disabled")
        
        # Generate tokens
        user_id = user["user_id"]
        access_token = self._create_access_token(user_id, email)
        refresh_token = self._create_refresh_token(user_id)
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "id_token": access_token,  # For compatibility with Cognito response
            "expires_in": self.access_token_expire_minutes * 60,
            "token_type": "Bearer",
        }
    
    async def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        """
        Refresh access token using refresh token.
        
        Args:
            refresh_token: Refresh token from previous login
            
        Returns:
            Dictionary with new access_token and expires_in
            
        Raises:
            AuthenticationError: If refresh token is invalid
        """
        try:
            payload = jwt.decode(
                refresh_token,
                self.secret_key,
                algorithms=[self.algorithm]
            )
            
            # Verify it's a refresh token
            if payload.get("token_type") != "refresh":
                raise AuthenticationError("Invalid token type")
            
            user_id = payload.get("sub")
            if not user_id:
                raise AuthenticationError("Invalid token: missing user ID")
            
            # Get user to verify they still exist and are active
            user = await self.user_repository.get_user_by_id(user_id)
            if not user:
                raise AuthenticationError("User not found")
            
            if not user.get("is_active", True):
                raise AuthenticationError("Account is disabled")
            
            # Generate new access token
            access_token = self._create_access_token(user_id, user["email"])
            
            return {
                "access_token": access_token,
                "id_token": access_token,
                "expires_in": self.access_token_expire_minutes * 60,
                "token_type": "Bearer",
            }
            
        except jwt.ExpiredSignatureError:
            raise AuthenticationError("Refresh token has expired")
        except jwt.JWTError as e:
            raise AuthenticationError(f"Invalid refresh token: {str(e)}")
    
    async def forgot_password(self, email: str) -> Dict[str, Any]:
        """
        Initiate password reset flow (placeholder for local auth).
        
        In a full implementation, this would:
        1. Generate a reset token
        2. Send email with reset link
        
        For now, just returns success without sending email.
        
        Args:
            email: User email address
            
        Returns:
            Dictionary with success status
        """
        # Check if user exists (but don't reveal if they do or not)
        user = await self.user_repository.get_user_by_email(email)
        
        # Always return success to prevent email enumeration
        return {
            "success": True,
            "message": "If the email exists, a reset code has been sent",
            "code_delivery_details": None,
        }
    
    async def reset_password(self, email: str, code: str, new_password: str) -> Dict[str, Any]:
        """
        Reset password with verification code (placeholder for local auth).
        
        In a full implementation, this would:
        1. Verify the reset code
        2. Update the password
        
        For local dev, this is a simplified implementation.
        
        Args:
            email: User email address
            code: Verification code (not used in simple implementation)
            new_password: New password
            
        Returns:
            Dictionary with success status
        """
        # Validate new password
        self._validate_password(new_password)
        
        # Get user
        user = await self.user_repository.get_user_by_email(email)
        if not user:
            raise ValidationError("Invalid email or verification code")
        
        # Hash new password
        password_hash = self._hash_password(new_password)
        
        # Update password in database
        await self.user_repository.update_password(user["user_id"], password_hash)
        
        return {"success": True}
    
    async def change_password(
        self, user_id: str, current_password: str, new_password: str
    ) -> Dict[str, Any]:
        """
        Change password for authenticated user.
        
        Args:
            user_id: Current user's database ID
            current_password: User's current password
            new_password: New password to set
            
        Returns:
            Dictionary with success status
            
        Raises:
            AuthenticationError: If current password is incorrect
            ValidationError: If new password doesn't meet requirements
        """
        # Get user
        user = await self.user_repository.get_user_by_id(user_id)
        if not user:
            raise AuthenticationError("User not found")
        
        # Verify current password
        if not user.get("password_hash"):
            raise AuthenticationError("Cannot change password for this account")
        
        if not self._verify_password(current_password, user["password_hash"]):
            raise AuthenticationError("Current password is incorrect")
        
        # Validate new password
        self._validate_password(new_password)
        
        # Ensure new password is different
        if self._verify_password(new_password, user["password_hash"]):
            raise ValidationError("New password must be different from current password")
        
        # Hash and update password
        password_hash = self._hash_password(new_password)
        await self.user_repository.update_password(user_id, password_hash)
        
        return {"success": True}

