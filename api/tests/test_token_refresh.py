"""
Property-based tests for token refresh validity.

Feature: api-authentication, Property 8: Token refresh validity
Validates: Requirements 2.4
"""
import pytest
from hypothesis import given, strategies as st, settings, HealthCheck
from unittest.mock import patch
from botocore.exceptions import ClientError

from api.services.auth_service import AuthService
from api.utils.exceptions import AuthenticationError


@pytest.mark.asyncio
@given(
    refresh_token=st.text(min_size=10, max_size=100),
    user_sub=st.text(min_size=10, max_size=50)
)
@settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
async def test_token_refresh_validity(refresh_token, user_sub):
    """
    Property 8: Token refresh validity
    
    For any valid refresh token, the system should issue a new access token
    with the same user identity.
    
    Validates: Requirements 2.4
    """
    auth_service = AuthService()
    
    # Mock Cognito client to simulate successful token refresh
    with patch.object(auth_service, 'client') as mock_client:
        mock_client.initiate_auth.return_value = {
            'AuthenticationResult': {
                'AccessToken': 'new-access-token-' + user_sub,
                'IdToken': 'new-id-token-' + user_sub,
                'ExpiresIn': 3600,
                'TokenType': 'Bearer'
            }
        }
        
        # Call refresh_token
        result = await auth_service.refresh_token(refresh_token)
        
        # Verify all required fields are present
        assert 'access_token' in result
        assert 'id_token' in result
        assert 'expires_in' in result
        assert 'token_type' in result
        
        # Verify new access token is returned
        assert isinstance(result['access_token'], str)
        assert len(result['access_token']) > 0
        
        # Verify id_token is returned
        assert isinstance(result['id_token'], str)
        assert len(result['id_token']) > 0
        
        # Verify expires_in is a positive integer
        assert isinstance(result['expires_in'], int)
        assert result['expires_in'] > 0
        
        # Verify token_type is Bearer
        assert result['token_type'] == 'Bearer'
        
        # Verify the refresh token was used in the call
        mock_client.initiate_auth.assert_called_once()
        call_args = mock_client.initiate_auth.call_args
        assert call_args[1]['AuthFlow'] == 'REFRESH_TOKEN_AUTH'
        assert call_args[1]['AuthParameters']['REFRESH_TOKEN'] == refresh_token


@pytest.mark.asyncio
@given(refresh_token=st.text(min_size=1, max_size=100))
@settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
async def test_invalid_refresh_token_rejection(refresh_token):
    """
    Property 8: Token refresh validity (negative case)
    
    For any invalid refresh token, the system should reject the refresh request
    and raise an authentication error.
    
    Validates: Requirements 2.4
    """
    auth_service = AuthService()
    
    # Mock Cognito client to simulate invalid refresh token
    with patch.object(auth_service, 'client') as mock_client:
        mock_client.initiate_auth.side_effect = ClientError(
            {
                'Error': {
                    'Code': 'NotAuthorizedException',
                    'Message': 'Invalid Refresh Token'
                }
            },
            'InitiateAuth'
        )
        
        # Call refresh_token and expect an exception
        with pytest.raises(AuthenticationError) as exc_info:
            await auth_service.refresh_token(refresh_token)
        
        # Verify error message contains information about token refresh failure
        assert "Token refresh failed" in str(exc_info.value)


@pytest.mark.asyncio
@given(
    original_user_sub=st.text(min_size=10, max_size=50),
    refresh_token=st.text(min_size=10, max_size=100)
)
@settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
async def test_token_refresh_preserves_user_identity(original_user_sub, refresh_token):
    """
    Property 8: Token refresh validity (user identity preservation)
    
    For any valid refresh token, the new access token should contain the same
    user identity (sub claim) as the original token.
    
    This test verifies that token refresh doesn't change the user identity.
    
    Validates: Requirements 2.4
    """
    auth_service = AuthService()
    
    # Mock Cognito to return tokens with consistent user identity
    with patch.object(auth_service, 'client') as mock_client:
        # The new access token should be for the same user
        mock_client.initiate_auth.return_value = {
            'AuthenticationResult': {
                'AccessToken': f'new-access-token-{original_user_sub}',
                'IdToken': f'new-id-token-{original_user_sub}',
                'ExpiresIn': 3600,
                'TokenType': 'Bearer'
            }
        }
        
        # Call refresh_token
        result = await auth_service.refresh_token(refresh_token)
        
        # Verify the new access token is returned
        assert 'access_token' in result
        assert original_user_sub in result['access_token']
        
        # In a real scenario, we would decode the JWT and verify the 'sub' claim
        # matches the original user. Here we verify the mock behavior is correct.
        assert result['access_token'].startswith('new-access-token-')
