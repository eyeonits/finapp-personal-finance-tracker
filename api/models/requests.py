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


# ==================== Recurring Payment Request Models ====================

class CreateRecurringPaymentRequest(BaseModel):
    """Request model for creating a recurring payment."""
    name: str = Field(min_length=1, max_length=255)
    amount: Decimal = Field(gt=0)
    frequency: str = Field(pattern="^(weekly|monthly|quarterly|yearly)$")
    start_date: date
    due_day: Optional[int] = Field(default=None, ge=1, le=31)
    description: Optional[str] = Field(default=None, max_length=500)
    category: Optional[str] = Field(default=None, max_length=100)
    payee: Optional[str] = Field(default=None, max_length=255)
    account_id: Optional[str] = Field(default=None, max_length=100)
    end_date: Optional[date] = None
    reminder_days: Optional[int] = Field(default=3, ge=0)
    auto_pay: bool = False
    notes: Optional[str] = None


class UpdateRecurringPaymentRequest(BaseModel):
    """Request model for updating a recurring payment."""
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = Field(default=None, max_length=500)
    amount: Optional[Decimal] = Field(default=None, gt=0)
    frequency: Optional[str] = Field(default=None, pattern="^(weekly|monthly|quarterly|yearly)$")
    due_day: Optional[int] = Field(default=None, ge=1, le=31)
    category: Optional[str] = Field(default=None, max_length=100)
    payee: Optional[str] = Field(default=None, max_length=255)
    account_id: Optional[str] = Field(default=None, max_length=100)
    is_active: Optional[bool] = None
    end_date: Optional[date] = None
    reminder_days: Optional[int] = Field(default=None, ge=0)
    auto_pay: Optional[bool] = None
    notes: Optional[str] = None


class MarkPaymentPaidRequest(BaseModel):
    """Request model for marking a payment as paid."""
    paid_date: date
    amount_paid: Decimal = Field(gt=0)
    transaction_id: Optional[str] = None


class SkipPaymentRequest(BaseModel):
    """Request model for skipping a payment."""
    notes: Optional[str] = None


class GeneratePaymentRecordsRequest(BaseModel):
    """Request model for generating payment records."""
    months_ahead: int = Field(default=3, ge=1, le=12)
