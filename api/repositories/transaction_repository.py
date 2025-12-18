"""
Transaction repository for database operations.
"""
from typing import Optional, List
from datetime import date
from decimal import Decimal
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from api.models.domain import Transaction
from api.repositories.base_repository import BaseRepository


class TransactionRepository(BaseRepository):
    """Repository for transaction database operations."""
    
    async def get_transactions(
        self,
        user_id: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        description: Optional[str] = None,
        category: Optional[str] = None,
        account_id: Optional[str] = None,
        amount_min: Optional[Decimal] = None,
        amount_max: Optional[Decimal] = None,
        limit: int = 100,
        offset: int = 0
    ) -> tuple[List[Transaction], int]:
        """
        Get transactions for a user with optional filters.
        
        Args:
            user_id: User ID to filter by
            start_date: Filter transactions on or after this date
            end_date: Filter transactions on or before this date
            description: Filter by description (case-insensitive partial match)
            category: Filter by category (exact match)
            account_id: Filter by account ID (exact match)
            amount_min: Filter transactions with amount >= this value
            amount_max: Filter transactions with amount <= this value
            limit: Maximum number of results to return
            offset: Number of results to skip
            
        Returns:
            Tuple of (list of transactions, total count)
        """
        # Build base query with user_id filter
        conditions = [Transaction.user_id == user_id]
        
        # Add date range filters
        if start_date:
            conditions.append(Transaction.transaction_date >= start_date)
        if end_date:
            conditions.append(Transaction.transaction_date <= end_date)
        
        # Add description filter (case-insensitive partial match)
        if description:
            conditions.append(Transaction.description.ilike(f"%{description}%"))
        
        # Add category filter
        if category:
            conditions.append(Transaction.category == category)
        
        # Add account filter
        if account_id:
            conditions.append(Transaction.account_id == account_id)
        
        # Add amount range filters
        if amount_min is not None:
            conditions.append(Transaction.amount >= amount_min)
        if amount_max is not None:
            conditions.append(Transaction.amount <= amount_max)
        
        # Build query for transactions
        query = select(Transaction).where(and_(*conditions)).order_by(
            Transaction.transaction_date.desc(),
            Transaction.created_at.desc()
        )
        
        # Get total count
        count_query = select(Transaction).where(and_(*conditions))
        count_result = await self.db.execute(count_query)
        total = len(count_result.scalars().all())
        
        # Apply pagination
        query = query.limit(limit).offset(offset)
        
        # Execute query
        result = await self.db.execute(query)
        transactions = result.scalars().all()
        
        return list(transactions), total
    
    async def get_transaction_by_id(
        self,
        transaction_id: str,
        user_id: str
    ) -> Optional[Transaction]:
        """
        Get a single transaction by ID, ensuring it belongs to the user.
        
        Args:
            transaction_id: Transaction ID
            user_id: User ID to verify ownership
            
        Returns:
            Transaction if found and belongs to user, None otherwise
        """
        query = select(Transaction).where(
            and_(
                Transaction.transaction_id == transaction_id,
                Transaction.user_id == user_id
            )
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def create_transaction(
        self,
        user_id: str,
        transaction_date: date,
        post_date: date,
        description: str,
        amount: Decimal,
        account_id: str,
        source: str,
        category: Optional[str] = None,
        type: Optional[str] = None,
        memo: Optional[str] = None
    ) -> Transaction:
        """
        Create a new transaction.
        
        Args:
            user_id: User ID who owns the transaction
            transaction_date: Transaction date
            post_date: Post date
            description: Transaction description
            amount: Transaction amount
            account_id: Account identifier
            source: Transaction source ('credit_card' or 'bank')
            category: Optional category
            type: Optional type
            memo: Optional memo
            
        Returns:
            Created transaction
        """
        transaction = Transaction(
            user_id=user_id,
            transaction_date=transaction_date,
            post_date=post_date,
            description=description,
            category=category,
            type=type,
            amount=amount,
            memo=memo,
            account_id=account_id,
            source=source
        )
        
        self.db.add(transaction)
        await self.db.commit()
        await self.db.refresh(transaction)
        
        return transaction
    
    async def create_transactions_bulk(
        self,
        transactions: List[Transaction]
    ) -> List[Transaction]:
        """
        Bulk create transactions (more efficient than creating one by one).
        
        Args:
            transactions: List of Transaction objects to create
            
        Returns:
            List of created transactions
        """
        if not transactions:
            return []
        
        self.db.add_all(transactions)
        await self.db.commit()
        
        # Refresh all transactions
        for transaction in transactions:
            await self.db.refresh(transaction)
        
        return transactions
    
    async def transaction_exists(
        self,
        transaction_id: str,
        user_id: str
    ) -> bool:
        """
        Check if a transaction with the given ID already exists for the user.
        Used to avoid duplicates during imports.
        
        Args:
            transaction_id: Transaction ID to check
            user_id: User ID to verify ownership
            
        Returns:
            True if transaction exists, False otherwise
        """
        query = select(Transaction).where(
            and_(
                Transaction.transaction_id == transaction_id,
                Transaction.user_id == user_id
            )
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none() is not None
    
    async def get_existing_transaction_ids(
        self,
        transaction_ids: List[str],
        user_id: str
    ) -> set[str]:
        """
        Bulk check which transaction IDs already exist for the user.
        Much more efficient than checking one by one.
        
        Args:
            transaction_ids: List of transaction IDs to check
            user_id: User ID to verify ownership
            
        Returns:
            Set of transaction IDs that already exist
        """
        if not transaction_ids:
            return set()
        
        query = select(Transaction.transaction_id).where(
            and_(
                Transaction.transaction_id.in_(transaction_ids),
                Transaction.user_id == user_id
            )
        )
        result = await self.db.execute(query)
        existing_ids = result.scalars().all()
        return set(existing_ids)
    
    async def update_transaction(
        self,
        transaction_id: str,
        user_id: str,
        transaction_date: Optional[date] = None,
        post_date: Optional[date] = None,
        description: Optional[str] = None,
        category: Optional[str] = None,
        type: Optional[str] = None,
        amount: Optional[Decimal] = None,
        memo: Optional[str] = None
    ) -> Optional[Transaction]:
        """
        Update a transaction, ensuring it belongs to the user.
        
        Args:
            transaction_id: Transaction ID to update
            user_id: User ID to verify ownership
            transaction_date: New transaction date (optional)
            post_date: New post date (optional)
            description: New description (optional)
            category: New category (optional)
            type: New type (optional)
            amount: New amount (optional)
            memo: New memo (optional)
            
        Returns:
            Updated transaction if found and belongs to user, None otherwise
        """
        # Get transaction with user_id check
        transaction = await self.get_transaction_by_id(transaction_id, user_id)
        if not transaction:
            return None
        
        # Update fields if provided
        if transaction_date is not None:
            transaction.transaction_date = transaction_date
        if post_date is not None:
            transaction.post_date = post_date
        if description is not None:
            transaction.description = description
        if category is not None:
            transaction.category = category
        if type is not None:
            transaction.type = type
        if amount is not None:
            transaction.amount = amount
        if memo is not None:
            transaction.memo = memo
        
        await self.db.commit()
        await self.db.refresh(transaction)
        
        return transaction
    
    async def delete_transaction(
        self,
        transaction_id: str,
        user_id: str
    ) -> bool:
        """
        Delete a transaction, ensuring it belongs to the user.
        
        Args:
            transaction_id: Transaction ID to delete
            user_id: User ID to verify ownership
            
        Returns:
            True if deleted, False if not found or doesn't belong to user
        """
        # Get transaction with user_id check
        transaction = await self.get_transaction_by_id(transaction_id, user_id)
        if not transaction:
            return False
        
        await self.db.delete(transaction)
        await self.db.commit()
        
        return True
