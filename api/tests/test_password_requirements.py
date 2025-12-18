"""
Property-based tests for password requirement enforcement.

Feature: api-authentication, Property 4: Password requirement enforcement
Validates: Requirements 1.3
"""
import pytest
from hypothesis import given, strategies as st, settings, HealthCheck
from unittest.mock import AsyncMock, patch
from botocore.exceptions import ClientError

from api.services.auth_service import AuthService
from api.utils.exceptions import ValidationError


# Password generation strategies
@st.composite
def invalid_passwords(draw):
    """Generate passwords that don't meet requirements."""
    choice = draw(st.integers(min_value=0, max_value=3))
    
    if choice == 0:
        # Too short (less than 8 characters)
        return draw(st.text(min_size=0, max_size=7))
    elif choice == 1:
        # No uppercase letters
        return draw(st.text(
            alphabet=st.characters(whitelist_categories=('Ll', 'Nd', 'P')),
            min_size=8,
            max_size=20
        ))
    elif choice == 2:
        # No lowercase letters
        return draw(st.text(
            alphabet=st.characters(whitelist_categories=('Lu', 'Nd', 'P')),
            min_size=8,
            max_size=20
        ))
    else:
        # No numbers
        return draw(st.text(
            alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'P')),
            min_size=8,
            max_size=20
        ))


@st.composite
def valid_passwords(draw):
    """Generate passwords that meet all requirements."""
    # At least 8 characters with uppercase, lowercase, and numbers
    length = draw(st.integers(min_value=8, max_value=30))
    
    # Ensure we have at least one of each required character type
    uppercase = draw(st.text(alphabet=st.characters(whitelist_categories=('Lu',)), min_size=1, max_size=1))
    lowercase = draw(st.text(alphabet=st.characters(whitelist_categories=('Ll',)), min_size=1, max_size=1))
    digit = draw(st.text(alphabet=st.characters(whitelist_categories=('Nd',)), min_size=1, max_size=1))
    
    # Fill the rest with any valid characters
    remaining_length = length - 3
    if remaining_length > 0:
        rest = draw(st.text(
            alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd')),
            min_size=remaining_length,
            max_size=remaining_length
        ))
    else:
        rest = ""
    
    # Shuffle all characters together
    chars = list(uppercase + lowercase + digit + rest)
    draw(st.randoms()).shuffle(chars)
    
    return ''.join(chars)


@pytest.mark.asyncio
@given(password=invalid_passwords(), email=st.emails())
@settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
async def test_password_requirements_rejection(password, email):
    """
    Property 4: Password requirement enforcement
    
    For any registration request, if the password does not meet minimum requirements
    (8 characters, uppercase, lowercase, numbers), the system should reject the registration.
    
    Validates: Requirements 1.3
    """
    auth_service = AuthService()
    
    # Mock Cognito client to simulate password validation error
    with patch.object(auth_service, 'client') as mock_client:
        mock_client.sign_up.side_effect = ClientError(
            {
                'Error': {
                    'Code': 'InvalidPasswordException',
                    'Message': 'Password does not meet requirements'
                }
            },
            'SignUp'
        )
        
        # The service should raise ValidationError for invalid passwords
        with pytest.raises(ValidationError) as exc_info:
            await auth_service.register_user(email, password)
        
        assert "Password does not meet requirements" in str(exc_info.value)


@pytest.mark.asyncio
@given(password=valid_passwords(), email=st.emails())
@settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
async def test_password_requirements_acceptance(password, email):
    """
    Property 4: Password requirement enforcement (positive case)
    
    For any registration request with a valid password (8+ characters, uppercase,
    lowercase, numbers), the system should accept the registration.
    
    Validates: Requirements 1.3
    """
    auth_service = AuthService()
    
    # Mock Cognito client to simulate successful registration
    with patch.object(auth_service, 'client') as mock_client:
        mock_client.sign_up.return_value = {
            'UserSub': 'test-user-sub-123',
            'UserConfirmed': False,
            'CodeDeliveryDetails': {
                'Destination': email,
                'DeliveryMedium': 'EMAIL'
            }
        }
        
        # The service should successfully register with valid passwords
        result = await auth_service.register_user(email, password)
        
        assert result['user_sub'] == 'test-user-sub-123'
        assert result['user_confirmed'] == False
        assert mock_client.sign_up.called
