"""
Pydantic response models for API endpoints.
"""
from pydantic import BaseModel
from typing import Optional, List
from datetime import date, datetime
from decimal import Decimal


class TokenResponse(BaseModel):
    """Response model for authentication tokens."""
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int


class UserResponse(BaseModel):
    """Response model for user information."""
    user_id: str
    email: str
    created_at: datetime
    is_active: bool


class TransactionResponse(BaseModel):
    """Response model for a single transaction."""
    transaction_id: str
    transaction_date: date
    post_date: date
    description: str
    category: Optional[str]
    type: Optional[str]
    amount: Decimal
    memo: Optional[str]
    account_id: str
    source: str
    created_at: datetime


class TransactionListResponse(BaseModel):
    """Response model for list of transactions."""
    transactions: List[TransactionResponse]
    total: int
    limit: int
    offset: int


class ImportResponse(BaseModel):
    """Response model for CSV import."""
    import_id: str
    rows_total: int
    rows_inserted: int
    rows_skipped: int
    status: str


class ImportHistoryResponse(BaseModel):
    """Response model for import history."""
    import_id: str
    import_type: str
    account_id: str
    filename: Optional[str]
    rows_total: int
    rows_inserted: int
    rows_skipped: int
    status: str
    error_message: Optional[str]
    created_at: datetime


class DailySpending(BaseModel):
    """Model for daily spending data."""
    date: date
    amount: Decimal


class CategorySpending(BaseModel):
    """Model for category spending data."""
    category: str
    amount: Decimal


class DashboardMetricsResponse(BaseModel):
    """Response model for dashboard metrics."""
    num_transactions: int
    total_spent: Decimal
    total_received: Decimal
    net_flow: Decimal
    avg_daily_spend: Decimal
    daily_spending: List[DailySpending]
    category_breakdown: List[CategorySpending]


class ErrorResponse(BaseModel):
    """Response model for errors."""
    error: dict
