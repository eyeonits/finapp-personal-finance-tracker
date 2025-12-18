"""
Transaction service for business logic.
"""
from typing import Optional, List
from datetime import date
from decimal import Decimal
from api.repositories.transaction_repository import TransactionRepository
from api.models.domain import Transaction
from api.utils.exceptions import NotFoundError, ForbiddenError


class TransactionService:
    """Service for transaction business logic."""
    
    def __init__(self, transaction_repo: TransactionRepository):
        """Initialize service with repository."""
        self.transaction_repo = transaction_repo
    
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
        return await self.transaction_repo.get_transactions(
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
            description=description,
            category=category,
            account_id=account_id,
            amount_min=amount_min,
            amount_max=amount_max,
            limit=limit,
            offset=offset
        )
    
    async def get_transaction(
        self,
        transaction_id: str,
        user_id: str
    ) -> Transaction:
        """
        Get a single transaction by ID with authorization check.
        
        Args:
            transaction_id: Transaction ID
            user_id: User ID to verify ownership
            
        Returns:
            Transaction if found and belongs to user
            
        Raises:
            NotFoundError: If transaction not found
            ForbiddenError: If transaction doesn't belong to user
        """
        transaction = await self.transaction_repo.get_transaction_by_id(
            transaction_id=transaction_id,
            user_id=user_id
        )
        
        if not transaction:
            raise NotFoundError(f"Transaction {transaction_id} not found")
        
        return transaction
    
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
        Create a new transaction with validation.
        
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
            
        Raises:
            ValueError: If validation fails
        """
        # Validate source
        if source not in ["credit_card", "bank"]:
            raise ValueError(f"Invalid source: {source}. Must be 'credit_card' or 'bank'")
        
        # Validate description is not empty
        if not description or not description.strip():
            raise ValueError("Description cannot be empty")
        
        return await self.transaction_repo.create_transaction(
            user_id=user_id,
            transaction_date=transaction_date,
            post_date=post_date,
            description=description,
            amount=amount,
            account_id=account_id,
            source=source,
            category=category,
            type=type,
            memo=memo
        )
    
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
    ) -> Transaction:
        """
        Update a transaction with authorization check.
        
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
            Updated transaction
            
        Raises:
            NotFoundError: If transaction not found
            ForbiddenError: If transaction doesn't belong to user
            ValueError: If validation fails
        """
        # Validate description if provided
        if description is not None and (not description or not description.strip()):
            raise ValueError("Description cannot be empty")
        
        transaction = await self.transaction_repo.update_transaction(
            transaction_id=transaction_id,
            user_id=user_id,
            transaction_date=transaction_date,
            post_date=post_date,
            description=description,
            category=category,
            type=type,
            amount=amount,
            memo=memo
        )
        
        if not transaction:
            raise NotFoundError(f"Transaction {transaction_id} not found")
        
        return transaction
    
    async def delete_transaction(
        self,
        transaction_id: str,
        user_id: str
    ) -> None:
        """
        Delete a transaction with authorization check.
        
        Args:
            transaction_id: Transaction ID to delete
            user_id: User ID to verify ownership
            
        Raises:
            NotFoundError: If transaction not found
            ForbiddenError: If transaction doesn't belong to user
        """
        deleted = await self.transaction_repo.delete_transaction(
            transaction_id=transaction_id,
            user_id=user_id
        )
        
        if not deleted:
            raise NotFoundError(f"Transaction {transaction_id} not found")
