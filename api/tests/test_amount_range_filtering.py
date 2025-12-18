"""
Property-based test for amount range filtering.

Feature: api-authentication, Property 12: Amount range filtering
Validates: Requirements 4.4
"""
import pytest
from hypothesis import given, strategies as st, settings
from datetime import date
from decimal import Decimal
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from api.models.domain import Base, User, Transaction
from api.repositories.transaction_repository import TransactionRepository
import uuid


# Strategy for generating amounts
def amount_strategy():
    """Generate amounts between -10000 and 10000."""
    return st.decimals(
        min_value=Decimal("-10000.00"),
        max_value=Decimal("10000.00"),
        allow_nan=False,
        allow_infinity=False,
        places=2
    )


# Strategy for generating transactions
@st.composite
def transaction_strategy(draw):
    """Generate a transaction with random data."""
    return {
        "transaction_date": date(2024, 1, 1),
        "post_date": date(2024, 1, 1),
        "description": draw(st.text(min_size=1, max_size=100)),
        "category": draw(st.one_of(st.none(), st.text(min_size=1, max_size=50))),
        "type": draw(st.one_of(st.none(), st.text(min_size=1, max_size=20))),
        "amount": draw(amount_strategy()),
        "memo": draw(st.one_of(st.none(), st.text(min_size=0, max_size=100))),
        "account_id": draw(st.text(min_size=1, max_size=50)),
        "source": draw(st.sampled_from(["credit_card", "bank"]))
    }


@pytest.mark.asyncio
@given(
    transactions=st.lists(transaction_strategy(), min_size=5, max_size=20),
    amount_min=amount_strategy(),
    amount_max=amount_strategy()
)
@settings(max_examples=100, deadline=None)
async def test_amount_range_filtering_property(transactions, amount_min, amount_max):
    """
    Property 12: Amount range filtering
    
    For any transaction query with minimum and maximum amount filters,
    all returned transactions should have amounts within the specified range.
    
    Validates: Requirements 4.4
    """
    # Ensure amount_min <= amount_max
    if amount_min > amount_max:
        amount_min, amount_max = amount_max, amount_min
    
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
        
        # Query with amount range filter
        repo = TransactionRepository(session)
        results, total = await repo.get_transactions(
            user_id=user.user_id,
            amount_min=amount_min,
            amount_max=amount_max
        )
        
        # Property: All returned transactions should have amounts within range
        for txn in results:
            assert amount_min <= txn.amount <= amount_max, (
                f"Transaction amount {txn.amount} is outside range "
                f"[{amount_min}, {amount_max}]"
            )
        
        # Verify we didn't miss any transactions that should be in range
        expected_in_range = [
            txn for txn in created_transactions
            if amount_min <= txn.amount <= amount_max
        ]
        assert len(results) == len(expected_in_range), (
            f"Expected {len(expected_in_range)} transactions in range, "
            f"but got {len(results)}"
        )
    
    await engine.dispose()


@pytest.mark.asyncio
async def test_amount_range_filtering_example():
    """
    Example test: Verify amount range filtering with specific amounts.
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
        
        # Create transactions with specific amounts
        txn1 = await repo.create_transaction(
            user_id=user.user_id,
            transaction_date=date(2024, 1, 15),
            post_date=date(2024, 1, 16),
            description="Small transaction",
            amount=Decimal("50.00"),
            account_id="account1",
            source="credit_card"
        )
        
        txn2 = await repo.create_transaction(
            user_id=user.user_id,
            transaction_date=date(2024, 2, 15),
            post_date=date(2024, 2, 16),
            description="Medium transaction",
            amount=Decimal("150.00"),
            account_id="account1",
            source="credit_card"
        )
        
        txn3 = await repo.create_transaction(
            user_id=user.user_id,
            transaction_date=date(2024, 3, 15),
            post_date=date(2024, 3, 16),
            description="Large transaction",
            amount=Decimal("500.00"),
            account_id="account1",
            source="bank"
        )
        
        # Query with amount range
        results, total = await repo.get_transactions(
            user_id=user.user_id,
            amount_min=Decimal("100.00"),
            amount_max=Decimal("200.00")
        )
        
        # Should only return txn2
        assert len(results) == 1
        assert results[0].transaction_id == txn2.transaction_id
        assert results[0].amount == Decimal("150.00")
    
    await engine.dispose()
