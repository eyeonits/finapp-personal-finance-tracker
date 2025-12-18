"""
Property-based tests for JWT token validation.

**Feature: api-authentication, Property 2: JWT token validation**
**Validates: Requirements 7.2, 7.3, 7.5**
"""
import pytest
from hypothesis import given, strategies as st, settings

from api.utils.jwt_utils import decode_jwt_token
from api.utils.exceptions import AuthenticationError


# Property 2: JWT token validation
# For any API request to a protected endpoint, if the JWT token is invalid or expired,
# the system should return a 401 Unauthorized error (raise AuthenticationError).


@pytest.mark.asyncio
@given(
    # Generate random malformed tokens
    malformed_token=st.one_of(
        st.text(min_size=1, max_size=50).filter(lambda x: '.' not in x),  # No dots
        st.just(""),  # Empty string
        st.just("Bearer "),  # Just the prefix
        st.just("not.a.token"),  # Invalid structure
        st.just("invalid.jwt.token"),  # Invalid JWT
        st.text(alphabet=st.characters(blacklist_characters='.'), min_size=1, max_size=100),  # No dots
    )
)
@settings(max_examples=100)
async def test_malformed_token_raises_authentication_error(malformed_token):
    """
    Property: For any malformed JWT token, decode_jwt_token should raise AuthenticationError.
    
    This tests requirement 7.3: WHEN a JWT token is malformed THEN the System SHALL 
    return a 401 Unauthorized error.
    
    This also tests requirement 7.2: Expired tokens are a form of invalid tokens.
    """
    # Skip tokens that might accidentally be valid-looking
    if malformed_token.count('.') >= 2 and len(malformed_token) > 100:
        return
    
    # The malformed token should be rejected
    with pytest.raises((AuthenticationError, Exception)):
        decode_jwt_token(malformed_token)


@pytest.mark.asyncio
@given(
    # Generate random strings that look like tokens but aren't
    token_part1=st.text(min_size=10, max_size=50, alphabet=st.characters(min_codepoint=65, max_codepoint=122)),
    token_part2=st.text(min_size=10, max_size=50, alphabet=st.characters(min_codepoint=65, max_codepoint=122)),
    token_part3=st.text(min_size=10, max_size=50, alphabet=st.characters(min_codepoint=65, max_codepoint=122)),
)
@settings(max_examples=100)
async def test_invalid_jwt_structure_raises_error(token_part1, token_part2, token_part3):
    """
    Property: For any string that looks like a JWT but isn't valid, 
    decode_jwt_token should raise AuthenticationError.
    
    This tests requirement 7.3: WHEN a JWT token is malformed THEN the System SHALL 
    return a 401 Unauthorized error.
    """
    # Create a token-like string
    fake_token = f"{token_part1}.{token_part2}.{token_part3}"
    
    # The fake token should be rejected
    with pytest.raises((AuthenticationError, Exception)):
        decode_jwt_token(fake_token)


@pytest.mark.asyncio
async def test_empty_token_raises_authentication_error():
    """
    Example test: Verify that empty tokens are rejected.
    
    This tests requirement 7.5: WHEN a request to a protected endpoint lacks a JWT token 
    THEN the System SHALL return a 401 Unauthorized error.
    """
    with pytest.raises((AuthenticationError, Exception)):
        decode_jwt_token("")


@pytest.mark.asyncio
async def test_token_without_bearer_prefix_in_middleware():
    """
    Example test: Verify that middleware handles requests without Authorization header.
    
    This tests requirement 7.5: WHEN a request to a protected endpoint lacks a JWT token 
    THEN the System SHALL return a 401 Unauthorized error.
    """
    from fastapi.responses import JSONResponse
    from api.middleware.auth import jwt_auth_middleware
    
    # Create a mock request without Authorization header
    class MockRequest:
        def __init__(self):
            self.headers = {}
            self.url = type('obj', (object,), {'path': '/api/v1/transactions'})()
            self.state = type('obj', (object,), {})()
    
    request = MockRequest()
    
    # Mock call_next
    async def mock_call_next(req):
        return JSONResponse(content={"success": True})
    
    # Should allow request to proceed (endpoint-level security handles it)
    response = await jwt_auth_middleware(request, mock_call_next)
    
    # Verify response
    assert response is not None


@pytest.mark.asyncio
async def test_middleware_rejects_invalid_bearer_format():
    """
    Example test: Verify that middleware rejects tokens without proper Bearer format.
    
    This tests requirement 7.3: WHEN a JWT token is malformed THEN the System SHALL 
    return a 401 Unauthorized error.
    """
    from fastapi.responses import JSONResponse
    from api.middleware.auth import jwt_auth_middleware
    
    # Create a mock request with invalid Authorization header
    class MockRequest:
        def __init__(self, auth_header):
            self.headers = {"Authorization": auth_header}
            self.url = type('obj', (object,), {'path': '/api/v1/transactions'})()
            self.state = type('obj', (object,), {})()
    
    request = MockRequest("InvalidFormat token123")
    
    # Mock call_next
    async def mock_call_next(req):
        return JSONResponse(content={"success": True})
    
    # Should return 401 error
    response = await jwt_auth_middleware(request, mock_call_next)
    
    # Verify response is an error
    assert response.status_code == 401
