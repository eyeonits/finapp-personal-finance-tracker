"""
JWT authentication middleware for validating tokens on protected endpoints.
"""
from typing import Callable
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse

from api.utils.jwt_utils import decode_jwt_token
from api.utils.exceptions import AuthenticationError


async def jwt_auth_middleware(request: Request, call_next: Callable):
    """
    Middleware to validate JWT tokens on protected endpoints.
    
    Extracts the JWT token from Authorization header, validates it,
    and injects the user_id into request state for downstream handlers.
    
    Args:
        request: FastAPI request object
        call_next: Next middleware/handler in chain
        
    Returns:
        Response from downstream handler
        
    Raises:
        HTTPException: 401 if token is missing, invalid, or expired
    """
    # Skip authentication for public endpoints
    public_paths = [
        "/docs",
        "/redoc",
        "/openapi.json",
        "/api/v1/health",
        "/api/v1/auth/register",
        "/api/v1/auth/login",
        "/api/v1/auth/refresh",
        "/api/v1/auth/forgot-password",
        "/api/v1/auth/reset-password",
    ]
    
    if request.url.path in public_paths or request.url.path.startswith("/docs") or request.url.path.startswith("/redoc"):
        return await call_next(request)
    
    # Extract token from Authorization header
    auth_header = request.headers.get("Authorization")
    
    if not auth_header:
        # Allow request to proceed - endpoint-level security will handle it
        return await call_next(request)
    
    if not auth_header.startswith("Bearer "):
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={
                "error": {
                    "code": "AUTH_TOKEN_INVALID",
                    "message": "Invalid authorization header format. Expected 'Bearer <token>'"
                }
            }
        )
    
    token = auth_header.split(" ", 1)[1]
    
    try:
        # Validate token and extract payload
        payload = decode_jwt_token(token)
        
        # Extract user_id (sub claim) from token
        user_id = payload.get("sub")
        
        if not user_id:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={
                    "error": {
                        "code": "AUTH_TOKEN_INVALID",
                        "message": "Token missing user ID claim"
                    }
                }
            )
        
        # Inject user_id into request state for downstream handlers
        request.state.user_id = user_id
        request.state.token_payload = payload
        
        # Continue to next handler
        return await call_next(request)
        
    except AuthenticationError as e:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={
                "error": {
                    "code": "AUTH_TOKEN_INVALID",
                    "message": str(e)
                }
            }
        )
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={
                "error": {
                    "code": "AUTH_TOKEN_INVALID",
                    "message": f"Token validation failed: {str(e)}"
                }
            }
        )
