"""
Property-based test for user ID association.

Feature: api-authentication, Property 7: User ID association
Validates: Requirements 9.1
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


# Strategy for generating transaction data
@st.composite
def transaction_data_strategy(draw):
    """Generate transaction data without user_id."""
    return {
        "transaction_date": date(2024, 1, 1),
        "post_date": date(2024, 1, 1),
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
    transaction_data=transaction_data_strategy()
)
@settings(max_examples=100, deadline=None)
async def test_user_id_association_property(transaction_data):
    """
    Property 7: User ID association
    
    For any transaction created through the API, the transaction should be
    automatically associated with the authenticated user's ID.
    
    Validates: Requirements 9.1
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
            cognito_sub=f"test-sub-{uuid.uuid4()}",
            email=f"test-{uuid.uuid4()}@example.com",
            is_active=True
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        
        # Create transaction through repository
        repo = TransactionRepository(session)
        transaction = await repo.create_transaction(
            user_id=user.user_id,
            **transaction_data
        )
        
        # Property: Transaction should be associated with the user
        assert transaction.user_id == user.user_id, (
            f"Transaction user_id {transaction.user_id} does not match "
            f"expected user_id {user.user_id}"
        )
        
        # Verify we can retrieve the transaction using the user_id
        retrieved_txn = await repo.get_transaction_by_id(
            transaction_id=transaction.transaction_id,
            user_id=user.user_id
        )
        assert retrieved_txn is not None, (
            "Transaction should be retrievable using the user_id"
        )
        assert retrieved_txn.transaction_id == transaction.transaction_id
        
        # Verify a different user cannot access this transaction
        other_user = User(
            user_id=str(uuid.uuid4()),
            cognito_sub=f"test-sub-other-{uuid.uuid4()}",
            email=f"test-other-{uuid.uuid4()}@example.com",
            is_active=True
        )
        session.add(other_user)
        await session.commit()
        await session.refresh(other_user)
        
        other_user_txn = await repo.get_transaction_by_id(
            transaction_id=transaction.transaction_id,
            user_id=other_user.user_id
        )
        assert other_user_txn is None, (
            "Transaction should not be accessible by a different user"
        )
    
    await engine.dispose()


@pytest.mark.asyncio
async def test_user_id_association_example():
    """
    Example test: Verify user ID association with specific data.
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
        # Create two test users
        user1 = User(
            user_id=str(uuid.uuid4()),
            cognito_sub="test-sub-user1",
            email="user1@test.com",
            is_active=True
        )
        user2 = User(
            user_id=str(uuid.uuid4()),
            cognito_sub="test-sub-user2",
            email="user2@test.com",
            is_active=True
        )
        session.add(user1)
        session.add(user2)
        await session.commit()
        await session.refresh(user1)
        await session.refresh(user2)
        
        repo = TransactionRepository(session)
        
        # Create transaction for user1
        txn1 = await repo.create_transaction(
            user_id=user1.user_id,
            transaction_date=date(2024, 1, 15),
            post_date=date(2024, 1, 16),
            description="User 1 Transaction",
            amount=Decimal("100.00"),
            account_id="account1",
            source="credit_card"
        )
        
        # Create transaction for user2
        txn2 = await repo.create_transaction(
            user_id=user2.user_id,
            transaction_date=date(2024, 1, 15),
            post_date=date(2024, 1, 16),
            description="User 2 Transaction",
            amount=Decimal("200.00"),
            account_id="account2",
            source="bank"
        )
        
        # Verify user1 can only access their transaction
        user1_txns, total1 = await repo.get_transactions(user_id=user1.user_id)
        assert len(user1_txns) == 1
        assert user1_txns[0].transaction_id == txn1.transaction_id
        assert user1_txns[0].user_id == user1.user_id
        
        # Verify user2 can only access their transaction
        user2_txns, total2 = await repo.get_transactions(user_id=user2.user_id)
        assert len(user2_txns) == 1
        assert user2_txns[0].transaction_id == txn2.transaction_id
        assert user2_txns[0].user_id == user2.user_id
        
        # Verify user1 cannot access user2's transaction
        user1_access_txn2 = await repo.get_transaction_by_id(
            transaction_id=txn2.transaction_id,
            user_id=user1.user_id
        )
        assert user1_access_txn2 is None
        
        # Verify user2 cannot access user1's transaction
        user2_access_txn1 = await repo.get_transaction_by_id(
            transaction_id=txn1.transaction_id,
            user_id=user2.user_id
        )
        assert user2_access_txn1 is None
    
    await engine.dispose()
