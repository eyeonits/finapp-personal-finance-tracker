"""
Pydantic request models for API endpoints.
"""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import date
from decimal import Decimal


class RegisterRequest(BaseModel):
    """Request model for user registration."""
    email: EmailStr
    password: str = Field(min_length=8)


class LoginRequest(BaseModel):
    """Request model for user login."""
    email: EmailStr
    password: str


class RefreshTokenRequest(BaseModel):
    """Request model for token refresh."""
    refresh_token: str


class ForgotPasswordRequest(BaseModel):
    """Request model for password reset initiation."""
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    """Request model for password reset completion."""
    email: EmailStr
    code: str
    new_password: str = Field(min_length=8)


class ChangePasswordRequest(BaseModel):
    """Request model for changing password (authenticated user)."""
    current_password: str
    new_password: str = Field(min_length=8)


class CreateTransactionRequest(BaseModel):
    """Request model for creating a transaction."""
    transaction_date: date
    post_date: date
    description: str
    category: Optional[str] = None
    type: Optional[str] = None
    amount: Decimal
    memo: Optional[str] = None
    account_id: str
    source: str


class UpdateTransactionRequest(BaseModel):
    """Request model for updating a transaction."""
    transaction_date: Optional[date] = None
    post_date: Optional[date] = None
    description: Optional[str] = None
    category: Optional[str] = None
    type: Optional[str] = None
    amount: Optional[Decimal] = None
    memo: Optional[str] = None


class TransactionFilters(BaseModel):
    """Query parameters for filtering transactions."""
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    description: Optional[str] = None
    category: Optional[str] = None
    amount_min: Optional[Decimal] = None
    amount_max: Optional[Decimal] = None
    limit: int = Field(default=100, le=1000)
    offset: int = Field(default=0, ge=0)
