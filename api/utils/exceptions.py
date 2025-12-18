"""
Custom exceptions for the API.
"""


class AuthenticationError(Exception):
    """Raised when authentication fails."""
    pass


class AuthorizationError(Exception):
    """Raised when user lacks permission."""
    pass


class ValidationError(Exception):
    """Raised when validation fails."""
    pass


class ResourceNotFoundError(Exception):
    """Raised when resource is not found."""
    pass


class NotFoundError(ResourceNotFoundError):
    """Alias for ResourceNotFoundError for backward compatibility."""
    pass


class ForbiddenError(AuthorizationError):
    """Alias for AuthorizationError for consistency with HTTP status codes."""
    pass


class DuplicateResourceError(Exception):
    """Raised when resource already exists."""
    pass


class DatabaseError(Exception):
    """Raised when database operation fails."""
    pass
