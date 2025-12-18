"""
Property-based tests for authentication token generation.

Feature: api-authentication, Property 3: Authentication token generation
Validates: Requirements 2.1, 2.3
"""
import pytest
from hypothesis import given, strategies as st, settings, HealthCheck
from unittest.mock import patch
from botocore.exceptions import ClientError

from api.services.auth_service import AuthService


@pytest.mark.asyncio
@given(
    email=st.emails(),
    password=st.text(min_size=8, max_size=30)
)
@settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
async def test_authentication_token_generation(email, password):
    """
    Property 3: Authentication token generation
    
    For any valid login request with correct credentials, the system should return
    an access token, refresh token, and expiration time.
    
    Validates: Requirements 2.1, 2.3
    """
    auth_service = AuthService()
    
    # Mock Cognito client to simulate successful authentication
    with patch.object(auth_service, 'client') as mock_client:
        mock_client.initiate_auth.return_value = {
            'AuthenticationResult': {
                'AccessToken': 'mock-access-token-' + email,
                'RefreshToken': 'mock-refresh-token-' + email,
                'IdToken': 'mock-id-token-' + email,
                'ExpiresIn': 3600,
                'TokenType': 'Bearer'
            }
        }
        
        # Call login
        result = await auth_service.login(email, password)
        
        # Verify all required fields are present
        assert 'access_token' in result
        assert 'refresh_token' in result
        assert 'id_token' in result
        assert 'expires_in' in result
        assert 'token_type' in result
        
        # Verify token values are non-empty strings
        assert isinstance(result['access_token'], str)
        assert len(result['access_token']) > 0
        
        assert isinstance(result['refresh_token'], str)
        assert len(result['refresh_token']) > 0
        
        assert isinstance(result['id_token'], str)
        assert len(result['id_token']) > 0
        
        # Verify expires_in is a positive integer
        assert isinstance(result['expires_in'], int)
        assert result['expires_in'] > 0
        
        # Verify token_type is Bearer
        assert result['token_type'] == 'Bearer'


@pytest.mark.asyncio
@given(
    email=st.emails(),
    password=st.text(min_size=1, max_size=30)
)
@settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
async def test_authentication_failure_no_tokens(email, password):
    """
    Property 3: Authentication token generation (negative case)
    
    For any login request with invalid credentials, the system should NOT return
    tokens and should raise an authentication error.
    
    Validates: Requirements 2.1, 2.3
    """
    auth_service = AuthService()
    
    # Mock Cognito client to simulate authentication failure
    with patch.object(auth_service, 'client') as mock_client:
        mock_client.initiate_auth.side_effect = ClientError(
            {
                'Error': {
                    'Code': 'NotAuthorizedException',
                    'Message': 'Incorrect username or password.'
                }
            },
            'InitiateAuth'
        )
        
        # Call login and expect an exception
        from api.utils.exceptions import AuthenticationError
        with pytest.raises(AuthenticationError) as exc_info:
            await auth_service.login(email, password)
        
        # Verify error message
        assert "Invalid email or password" in str(exc_info.value)
