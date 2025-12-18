"""
Property-based test for date range filtering.

Feature: api-authentication, Property 11: Date range filtering
Validates: Requirements 4.2
"""
import pytest
from hypothesis import given, strategies as st, settings
from datetime import date, timedelta
from decimal import Decimal
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from api.models.domain import Base, User, Transaction
from api.repositories.transaction_repository import TransactionRepository
import uuid


# Strategy for generating dates
def date_strategy():
    """Generate dates between 2020 and 2025."""
    return st.dates(
        min_value=date(2020, 1, 1),
        max_value=date(2025, 12, 31)
    )


# Strategy for generating transactions
@st.composite
def transaction_strategy(draw):
    """Generate a transaction with random data."""
    return {
        "transaction_date": draw(date_strategy()),
        "post_date": draw(date_strategy()),
        "description": draw(st.text(min_size=1, max_size=100)),
        "category": draw(st.one_of(st.none(), st.text(min_size=1, max_size=50))),
        "type": draw(st.one_of(st.none(), st.text(min_size=1, max_size=20))),
        "amount": Decimal(str(draw(st.floats(min_value=-10000, max_value=10000, allow_nan=False, allow_infinity=False)))),
        "memo": draw(st.one_of(st.none(), st.text(min_size=0, max_size=100))),
        "account_id": draw(st.text(min_size=1, max_size=50)),
        "source": draw(st.sampled_from(["credit_card", "bank"]))
    }





@pytest.mark.asyncio
@given(
    transactions=st.lists(transaction_strategy(), min_size=5, max_size=20),
    start_date=date_strategy(),
    end_date=date_strategy()
)
@settings(max_examples=100, deadline=None)
async def test_date_range_filtering_property(transactions, start_date, end_date):
    """
    Property 11: Date range filtering
    
    For any transaction query with start and end date filters,
    all returned transactions should have transaction dates within
    the specified range (inclusive).
    
    Validates: Requirements 4.2
    """
    # Ensure start_date <= end_date
    if start_date > end_date:
        start_date, end_date = end_date, start_date
    
    # Create test database
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False
    )
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        # Create test user
        user = User(
            user_id=str(uuid.uuid4()),
            cognito_sub=f"test-sub-{uuid.uuid4()}",
            email=f"test-{uuid.uuid4()}@example.com",
            is_active=True
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        
        # Create transactions
        created_transactions = []
        for txn_data in transactions:
            txn = Transaction(
                user_id=user.user_id,
                **txn_data
            )
            session.add(txn)
            created_transactions.append(txn)
        
        await session.commit()
        
        # Query with date range filter
        repo = TransactionRepository(session)
        results, total = await repo.get_transactions(
            user_id=user.user_id,
            start_date=start_date,
            end_date=end_date
        )
        
        # Property: All returned transactions should have dates within range
        for txn in results:
            assert start_date <= txn.transaction_date <= end_date, (
                f"Transaction date {txn.transaction_date} is outside range "
                f"[{start_date}, {end_date}]"
            )
        
        # Verify we didn't miss any transactions that should be in range
        expected_in_range = [
            txn for txn in created_transactions
            if start_date <= txn.transaction_date <= end_date
        ]
        assert len(results) == len(expected_in_range), (
            f"Expected {len(expected_in_range)} transactions in range, "
            f"but got {len(results)}"
        )
    
    await engine.dispose()


@pytest.mark.asyncio
async def test_date_range_filtering_example():
    """
    Example test: Verify date range filtering with specific dates.
    """
    # Create test database
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False
    )
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        # Create test user
        user = User(
            user_id=str(uuid.uuid4()),
            cognito_sub="test-sub-example",
            email="example@test.com",
            is_active=True
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        
        repo = TransactionRepository(session)
        
        # Create transactions with specific dates
        txn1 = await repo.create_transaction(
            user_id=user.user_id,
            transaction_date=date(2024, 1, 15),
            post_date=date(2024, 1, 16),
            description="Transaction 1",
            amount=Decimal("100.00"),
            account_id="account1",
            source="credit_card"
        )
        
        txn2 = await repo.create_transaction(
            user_id=user.user_id,
            transaction_date=date(2024, 2, 15),
            post_date=date(2024, 2, 16),
            description="Transaction 2",
            amount=Decimal("200.00"),
            account_id="account1",
            source="credit_card"
        )
        
        txn3 = await repo.create_transaction(
            user_id=user.user_id,
            transaction_date=date(2024, 3, 15),
            post_date=date(2024, 3, 16),
            description="Transaction 3",
            amount=Decimal("300.00"),
            account_id="account1",
            source="bank"
        )
        
        # Query with date range
        results, total = await repo.get_transactions(
            user_id=user.user_id,
            start_date=date(2024, 2, 1),
            end_date=date(2024, 2, 28)
        )
        
        # Should only return txn2
        assert len(results) == 1
        assert results[0].transaction_id == txn2.transaction_id
        assert results[0].transaction_date == date(2024, 2, 15)
    
    await engine.dispose()
