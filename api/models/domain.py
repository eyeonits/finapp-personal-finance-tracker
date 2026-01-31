"""
Domain models for database entities.
"""
from sqlalchemy import Column, String, DateTime, Boolean, Date, Numeric, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
import uuid

Base = declarative_base()


class User(Base):
    """User model."""
    __tablename__ = "users"
    
    user_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    cognito_sub = Column(String(255), unique=True, nullable=True, index=True)  # Nullable for local auth
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=True)  # For local authentication
    email_verified = Column(Boolean, nullable=False, default=False)  # For local auth email verification
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    is_active = Column(Boolean, nullable=False, default=True)


class Transaction(Base):
    """Transaction model."""
    __tablename__ = "transactions"
    
    transaction_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.user_id"), nullable=False, index=True)
    transaction_date = Column(Date, nullable=False)
    post_date = Column(Date, nullable=False)
    description = Column(String, nullable=False)
    category = Column(String)
    type = Column(String)
    amount = Column(Numeric(10, 2), nullable=False)
    memo = Column(String)
    account_id = Column(String, nullable=False)
    source = Column(String, nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())


class ImportHistory(Base):
    """Import history model."""
    __tablename__ = "import_history"
    
    import_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.user_id"), nullable=False, index=True)
    import_type = Column(String(50), nullable=False)
    account_id = Column(String(100), nullable=False)
    filename = Column(String(255))
    rows_total = Column(Numeric, nullable=False)
    rows_inserted = Column(Numeric, nullable=False)
    rows_skipped = Column(Numeric, nullable=False)
    status = Column(String(50), nullable=False)
    error_message = Column(Text)
    created_at = Column(DateTime, nullable=False, server_default=func.now(), index=True)


class RecurringPayment(Base):
    """Recurring payment/bill model for tracking subscriptions and regular bills."""
    __tablename__ = "recurring_payments"
    
    payment_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.user_id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(String(500), nullable=True)
    amount = Column(Numeric(10, 2), nullable=False)
    frequency = Column(String(50), nullable=False)  # 'weekly', 'monthly', 'quarterly', 'yearly'
    due_day = Column(Numeric, nullable=True)  # Day of month (1-31) or day of week (1-7)
    category = Column(String(100), nullable=True)
    payee = Column(String(255), nullable=True)
    account_id = Column(String(100), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=True)
    reminder_days = Column(Numeric, nullable=True, default=3)
    auto_pay = Column(Boolean, nullable=False, default=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())


class PaymentRecord(Base):
    """Payment record model for tracking actual payments made for recurring bills."""
    __tablename__ = "payment_records"
    
    record_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    payment_id = Column(String, ForeignKey("recurring_payments.payment_id"), nullable=False, index=True)
    user_id = Column(String, ForeignKey("users.user_id"), nullable=False, index=True)
    due_date = Column(Date, nullable=False)
    paid_date = Column(Date, nullable=True)
    amount_due = Column(Numeric(10, 2), nullable=False)
    amount_paid = Column(Numeric(10, 2), nullable=True)
    status = Column(String(50), nullable=False, default='pending')  # 'pending', 'paid', 'overdue', 'skipped'
    transaction_id = Column(String, ForeignKey("transactions.transaction_id"), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
