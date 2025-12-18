"""
Authentication service for AWS Cognito integration.
"""
from typing import Dict, Any
import boto3
import hmac
import hashlib
import base64
from botocore.exceptions import ClientError

from api.config import settings
from api.utils.exceptions import (
    AuthenticationError,
    ValidationError,
    DuplicateResourceError,
)


class AuthService:
    """Service for handling authentication operations with AWS Cognito."""
    
    def __init__(self):
        """Initialize authentication service with Cognito client."""
        self.client = boto3.client(
            'cognito-idp',
            region_name=settings.COGNITO_REGION
        )
        self.user_pool_id = settings.COGNITO_USER_POOL_ID
        self.client_id = settings.COGNITO_APP_CLIENT_ID
        self.client_secret = settings.COGNITO_APP_CLIENT_SECRET
    
    def _calculate_secret_hash(self, username: str) -> str:
        """
        Calculate SECRET_HASH for Cognito API calls when client has a secret.
        
        SECRET_HASH = HMAC-SHA256(Message, Secret) where Message = USERNAME + CLIENT_ID
        
        Args:
            username: Username (email) for the user
            
        Returns:
            Base64-encoded SECRET_HASH string
        """
        if not self.client_secret:
            return None
        
        message = username + self.client_id
        dig = hmac.new(
            self.client_secret.encode('utf-8'),
            msg=message.encode('utf-8'),
            digestmod=hashlib.sha256
        ).digest()
        return base64.b64encode(dig).decode('utf-8')
    
    async def register_user(self, email: str, password: str) -> Dict[str, Any]:
        """
        Register a new user in Cognito.
        
        Args:
            email: User email address
            password: User password
            
        Returns:
            Dictionary with user_sub and confirmation status
            
        Raises:
            ValidationError: If password doesn't meet requirements
            DuplicateResourceError: If email already exists
            AuthenticationError: For other Cognito errors
        """
        try:
            sign_up_params = {
                'ClientId': self.client_id,
                'Username': email,
                'Password': password,
                'UserAttributes': [
                    {'Name': 'email', 'Value': email}
                ]
            }
            
            # Add SECRET_HASH if client has a secret
            secret_hash = self._calculate_secret_hash(email)
            if secret_hash:
                sign_up_params['SecretHash'] = secret_hash
            
            response = self.client.sign_up(**sign_up_params)
            
            return {
                'user_sub': response['UserSub'],
                'user_confirmed': response.get('UserConfirmed', False),
                'code_delivery_details': response.get('CodeDeliveryDetails')
            }
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            
            if error_code == 'UsernameExistsException':
                raise DuplicateResourceError("Email already registered")
            elif error_code == 'InvalidPasswordException':
                raise ValidationError(f"Password does not meet requirements: {error_message}")
            elif error_code == 'InvalidParameterException':
                raise ValidationError(error_message)
            else:
                raise AuthenticationError(f"Registration failed: {error_message}")
    
    async def login(self, email: str, password: str) -> Dict[str, Any]:
        """
        Authenticate user and return tokens.
        
        Args:
            email: User email address
            password: User password
            
        Returns:
            Dictionary with access_token, refresh_token, id_token, and expires_in
            
        Raises:
            AuthenticationError: If credentials are invalid or other errors occur
        """
        try:
            auth_parameters = {
                'USERNAME': email,
                'PASSWORD': password
            }
            
            # Add SECRET_HASH if client has a secret
            secret_hash = self._calculate_secret_hash(email)
            if secret_hash:
                auth_parameters['SECRET_HASH'] = secret_hash
            
            response = self.client.initiate_auth(
                ClientId=self.client_id,
                AuthFlow='USER_PASSWORD_AUTH',
                AuthParameters=auth_parameters
            )
            
            auth_result = response['AuthenticationResult']
            
            return {
                'access_token': auth_result['AccessToken'],
                'refresh_token': auth_result.get('RefreshToken'),
                'id_token': auth_result['IdToken'],
                'expires_in': auth_result['ExpiresIn'],
                'token_type': 'Bearer'
            }
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            
            if error_code in ['NotAuthorizedException', 'UserNotFoundException']:
                raise AuthenticationError("Invalid email or password")
            elif error_code == 'UserNotConfirmedException':
                raise AuthenticationError("Email not verified. Please check your email for verification code.")
            else:
                raise AuthenticationError(f"Login failed: {error_message}")
    
    async def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        """
        Refresh access token using refresh token.
        
        Args:
            refresh_token: Refresh token from previous login
            
        Returns:
            Dictionary with new access_token, id_token, and expires_in
            
        Raises:
            AuthenticationError: If refresh token is invalid
        """
        try:
            # For refresh token, we need to get the username from the token
            # Since we don't have it here, we'll need to decode the token or pass username
            # For now, we'll skip SECRET_HASH for refresh token as it's less common to require it
            # But if needed, we can add username parameter to this method
            auth_parameters = {
                'REFRESH_TOKEN': refresh_token
            }
            
            # Note: SECRET_HASH for refresh token requires username, which we'd need to extract
            # from the refresh token or pass as parameter. For now, omitting it.
            
            response = self.client.initiate_auth(
                ClientId=self.client_id,
                AuthFlow='REFRESH_TOKEN_AUTH',
                AuthParameters=auth_parameters
            )
            
            auth_result = response['AuthenticationResult']
            
            return {
                'access_token': auth_result['AccessToken'],
                'id_token': auth_result['IdToken'],
                'expires_in': auth_result['ExpiresIn'],
                'token_type': 'Bearer'
            }
            
        except ClientError as e:
            error_message = e.response['Error']['Message']
            raise AuthenticationError(f"Token refresh failed: {error_message}")
    
    async def forgot_password(self, email: str) -> Dict[str, Any]:
        """
        Initiate password reset flow.
        
        Args:
            email: User email address
            
        Returns:
            Dictionary with code delivery details
            
        Raises:
            AuthenticationError: If user not found or other errors
        """
        try:
            forgot_password_params = {
                'ClientId': self.client_id,
                'Username': email
            }
            
            # Add SECRET_HASH if client has a secret
            secret_hash = self._calculate_secret_hash(email)
            if secret_hash:
                forgot_password_params['SecretHash'] = secret_hash
            
            response = self.client.forgot_password(**forgot_password_params)
            
            return {
                'code_delivery_details': response.get('CodeDeliveryDetails'),
                'success': True
            }
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            
            if error_code == 'UserNotFoundException':
                # Don't reveal if user exists or not for security
                return {
                    'success': True,
                    'message': 'If the email exists, a reset code has been sent'
                }
            else:
                raise AuthenticationError(f"Password reset request failed: {error_message}")
    
    async def reset_password(self, email: str, code: str, new_password: str) -> Dict[str, Any]:
        """
        Complete password reset with verification code.
        
        Args:
            email: User email address
            code: Verification code from email
            new_password: New password
            
        Returns:
            Dictionary with success status
            
        Raises:
            ValidationError: If code is invalid or password doesn't meet requirements
            AuthenticationError: For other errors
        """
        try:
            confirm_params = {
                'ClientId': self.client_id,
                'Username': email,
                'ConfirmationCode': code,
                'Password': new_password
            }
            
            # Add SECRET_HASH if client has a secret
            secret_hash = self._calculate_secret_hash(email)
            if secret_hash:
                confirm_params['SecretHash'] = secret_hash
            
            self.client.confirm_forgot_password(**confirm_params)
            
            return {'success': True}
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            
            if error_code == 'CodeMismatchException':
                raise ValidationError("Invalid verification code")
            elif error_code == 'ExpiredCodeException':
                raise ValidationError("Verification code has expired")
            elif error_code == 'InvalidPasswordException':
                raise ValidationError(f"Password does not meet requirements: {error_message}")
            elif error_code == 'LimitExceededException':
                raise ValidationError("Too many failed attempts. Please request a new code.")
            else:
                raise AuthenticationError(f"Password reset failed: {error_message}")
