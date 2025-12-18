"""
JWT token validation utilities.
"""
from typing import Dict, Any
import requests
from jose import jwt, JWTError
from jose.exceptions import ExpiredSignatureError, JWTClaimsError
from functools import lru_cache

from api.config import settings
from api.utils.exceptions import AuthenticationError


@lru_cache(maxsize=1)
def get_cognito_public_keys() -> Dict[str, Any]:
    """
    Fetch Cognito public keys (JWKS) for token validation.
    Cached to avoid repeated requests.
    
    Returns:
        Dictionary containing JWKS keys
        
    Raises:
        AuthenticationError: If keys cannot be fetched
    """
    jwks_url = (
        f"https://cognito-idp.{settings.COGNITO_REGION}.amazonaws.com/"
        f"{settings.COGNITO_USER_POOL_ID}/.well-known/jwks.json"
    )
    
    try:
        response = requests.get(jwks_url, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        raise AuthenticationError(f"Failed to fetch Cognito public keys: {str(e)}")


def get_signing_key(token: str) -> str:
    """
    Extract the signing key from JWKS based on token's kid header.
    
    Args:
        token: JWT token string
        
    Returns:
        Public key for signature verification
        
    Raises:
        AuthenticationError: If signing key cannot be found
    """
    try:
        # Get the key ID from token header
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get('kid')
        
        if not kid:
            raise AuthenticationError("Token missing key ID (kid)")
        
        # Get JWKS and find matching key
        jwks = get_cognito_public_keys()
        
        for key in jwks.get('keys', []):
            if key.get('kid') == kid:
                # Convert JWK to PEM format for python-jose
                return key
        
        raise AuthenticationError("Signing key not found in JWKS")
        
    except JWTError as e:
        raise AuthenticationError(f"Invalid token header: {str(e)}")


def decode_jwt_token(token: str) -> Dict[str, Any]:
    """
    Decode and validate JWT token from Cognito.
    
    Validates:
    - Token signature using Cognito public keys
    - Token expiration
    - Token issuer (Cognito User Pool)
    - Token audience (App Client ID)
    
    Args:
        token: JWT token string
        
    Returns:
        Token payload containing claims (sub, email, etc.)
        
    Raises:
        AuthenticationError: If token is invalid, expired, or malformed
    """
    try:
        # Get the signing key
        signing_key = get_signing_key(token)
        
        # Expected issuer
        issuer = (
            f"https://cognito-idp.{settings.COGNITO_REGION}.amazonaws.com/"
            f"{settings.COGNITO_USER_POOL_ID}"
        )
        
        # Decode and validate token
        payload = jwt.decode(
            token,
            signing_key,
            algorithms=[settings.JWT_ALGORITHM],
            audience=settings.COGNITO_APP_CLIENT_ID,
            issuer=issuer,
            options={
                'verify_signature': True,
                'verify_exp': True,
                'verify_aud': True,
                'verify_iss': True,
            }
        )
        
        return payload
        
    except ExpiredSignatureError:
        raise AuthenticationError("Token has expired")
    except JWTClaimsError as e:
        raise AuthenticationError(f"Invalid token claims: {str(e)}")
    except JWTError as e:
        raise AuthenticationError(f"Invalid token: {str(e)}")
    except Exception as e:
        raise AuthenticationError(f"Token validation failed: {str(e)}")
