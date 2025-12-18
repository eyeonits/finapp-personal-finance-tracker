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
    cognito_sub = Column(String(255), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
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
