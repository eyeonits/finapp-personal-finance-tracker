"""
Authentication endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, status

from api.models.requests import (
    RegisterRequest,
    LoginRequest,
    RefreshTokenRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
)
from api.models.responses import TokenResponse, UserResponse
from api.services.auth_service import AuthService
from api.services.user_service import UserService
from api.dependencies import get_auth_service, get_user_service, get_current_user_id
from api.utils.exceptions import (
    AuthenticationError,
    ValidationError,
    DuplicateResourceError,
)
from api.utils.jwt_utils import decode_jwt_token

router = APIRouter()


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(
    request: RegisterRequest,
    auth_service: AuthService = Depends(get_auth_service),
):
    """
    Register a new user.
    
    Creates a new user account in AWS Cognito and sends a verification email.
    
    Args:
        request: Registration request with email and password
        auth_service: Authentication service instance
        
    Returns:
        Success message with user_sub
        
    Raises:
        409: Email already registered
        400: Password doesn't meet requirements
    """
    try:
        result = await auth_service.register_user(request.email, request.password)
        return {
            "message": "Registration successful. Please check your email to verify your account.",
            "user_sub": result["user_sub"],
            "email_sent": result.get("code_delivery_details") is not None,
        }
    except DuplicateResourceError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": {"code": "AUTH_EMAIL_EXISTS", "message": str(e)}},
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": {"code": "VALIDATION_ERROR", "message": str(e)}},
        )
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": {"code": "AUTH_ERROR", "message": str(e)}},
        )


@router.post("/login", response_model=TokenResponse)
async def login(
    request: LoginRequest,
    auth_service: AuthService = Depends(get_auth_service),
    user_service: UserService = Depends(get_user_service),
):
    """
    Login and get authentication tokens.
    
    Authenticates user against AWS Cognito and returns JWT tokens.
    Creates user record in local database on first login.
    
    Args:
        request: Login request with email and password
        auth_service: Authentication service instance
        user_service: User service instance
        
    Returns:
        TokenResponse with access_token, refresh_token, and expires_in
        
    Raises:
        401: Invalid credentials or email not verified
    """
    try:
        # Authenticate with Cognito
        tokens = await auth_service.login(request.email, request.password)
        
        # Decode token to get user info
        payload = decode_jwt_token(tokens["access_token"])
        cognito_sub = payload.get("sub")
        email = payload.get("email", request.email)
        
        # Create or get user in local database
        await user_service.get_or_create_user(cognito_sub, email)
        
        return TokenResponse(
            access_token=tokens["access_token"],
            refresh_token=tokens["refresh_token"],
            token_type=tokens["token_type"],
            expires_in=tokens["expires_in"],
        )
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": {"code": "AUTH_INVALID_CREDENTIALS", "message": str(e)}},
        )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    request: RefreshTokenRequest,
    auth_service: AuthService = Depends(get_auth_service),
):
    """
    Refresh access token using refresh token.
    
    Args:
        request: Refresh token request
        auth_service: Authentication service instance
        
    Returns:
        TokenResponse with new access_token and expires_in
        
    Raises:
        401: Invalid or expired refresh token
    """
    try:
        tokens = await auth_service.refresh_token(request.refresh_token)
        
        # Note: refresh_token is not returned in refresh response
        return TokenResponse(
            access_token=tokens["access_token"],
            refresh_token=request.refresh_token,  # Return original refresh token
            token_type=tokens["token_type"],
            expires_in=tokens["expires_in"],
        )
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": {"code": "AUTH_TOKEN_INVALID", "message": str(e)}},
        )


@router.post("/logout")
async def logout(
    user_id: str = Depends(get_current_user_id),
):
    """
    Logout and invalidate tokens.
    
    Note: JWT tokens are stateless, so logout is handled client-side by discarding tokens.
    This endpoint validates the token and confirms logout.
    
    Args:
        user_id: Current user ID from JWT token
        
    Returns:
        Success message
    """
    return {"message": "Logout successful", "user_id": user_id}


@router.post("/forgot-password")
async def forgot_password(
    request: ForgotPasswordRequest,
    auth_service: AuthService = Depends(get_auth_service),
):
    """
    Request password reset.
    
    Sends a verification code to the user's email for password reset.
    
    Args:
        request: Forgot password request with email
        auth_service: Authentication service instance
        
    Returns:
        Success message
    """
    try:
        result = await auth_service.forgot_password(request.email)
        return {
            "message": "If the email exists, a verification code has been sent.",
            "success": result["success"],
        }
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": {"code": "AUTH_ERROR", "message": str(e)}},
        )


@router.post("/reset-password")
async def reset_password(
    request: ResetPasswordRequest,
    auth_service: AuthService = Depends(get_auth_service),
):
    """
    Reset password with verification code.
    
    Completes password reset using the verification code sent via email.
    
    Args:
        request: Reset password request with email, code, and new password
        auth_service: Authentication service instance
        
    Returns:
        Success message
        
    Raises:
        400: Invalid code, expired code, or password doesn't meet requirements
    """
    try:
        result = await auth_service.reset_password(
            request.email, request.code, request.new_password
        )
        return {
            "message": "Password reset successful. Please login with your new password.",
            "success": result["success"],
        }
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": {"code": "VALIDATION_ERROR", "message": str(e)}},
        )
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": {"code": "AUTH_ERROR", "message": str(e)}},
        )


@router.get("/me", response_model=UserResponse)
async def get_current_user(
    user_id: str = Depends(get_current_user_id),
    user_service: UserService = Depends(get_user_service),
):
    """
    Get current user information.
    
    Returns information about the currently authenticated user.
    
    Args:
        user_id: Current user ID from JWT token
        user_service: User service instance
        
    Returns:
        UserResponse with user information
        
    Raises:
        401: Invalid or expired token
        404: User not found
    """
    try:
        user = await user_service.get_user_by_id(user_id)
        return UserResponse(
            user_id=user["user_id"],
            email=user["email"],
            created_at=user["created_at"],
            is_active=user["is_active"],
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "RESOURCE_NOT_FOUND", "message": str(e)}},
        )
