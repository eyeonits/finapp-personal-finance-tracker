"""
Transaction endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import Optional
from datetime import date
from decimal import Decimal

from api.models.requests import CreateTransactionRequest, UpdateTransactionRequest
from api.models.responses import TransactionResponse, TransactionListResponse
from api.services.transaction_service import TransactionService
from api.dependencies import get_transaction_service, get_current_user_id, get_current_db_user_id
from api.utils.exceptions import NotFoundError, ForbiddenError

router = APIRouter()


@router.get("", response_model=TransactionListResponse)
async def list_transactions(
    start_date: Optional[date] = Query(None, description="Filter transactions on or after this date"),
    end_date: Optional[date] = Query(None, description="Filter transactions on or before this date"),
    description: Optional[str] = Query(None, description="Filter by description (case-insensitive partial match)"),
    category: Optional[str] = Query(None, description="Filter by category (exact match)"),
    account_id: Optional[str] = Query(None, description="Filter by account ID (exact match)"),
    amount_min: Optional[Decimal] = Query(None, description="Filter transactions with amount >= this value"),
    amount_max: Optional[Decimal] = Query(None, description="Filter transactions with amount <= this value"),
    limit: int = Query(100, le=1000, description="Maximum number of results to return"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    user_id: str = Depends(get_current_db_user_id),
    transaction_service: TransactionService = Depends(get_transaction_service),
):
    """
    List transactions with filters.
    
    Returns a paginated list of transactions for the authenticated user.
    Supports filtering by date range, description, category, account, and amount range.
    
    Args:
        start_date: Filter transactions on or after this date
        end_date: Filter transactions on or before this date
        description: Filter by description (case-insensitive partial match)
        category: Filter by category (exact match)
        account_id: Filter by account ID (exact match)
        amount_min: Filter transactions with amount >= this value
        amount_max: Filter transactions with amount <= this value
        limit: Maximum number of results to return (max 1000)
        offset: Number of results to skip for pagination
        user_id: Current user ID from JWT token
        transaction_service: Transaction service instance
        
    Returns:
        TransactionListResponse with transactions, total count, limit, and offset
        
    Raises:
        401: Invalid or expired token
    """
    transactions, total = await transaction_service.get_transactions(
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
    
    # Convert domain models to response models
    transaction_responses = [
        TransactionResponse(
            transaction_id=txn.transaction_id,
            transaction_date=txn.transaction_date,
            post_date=txn.post_date,
            description=txn.description,
            category=txn.category,
            type=txn.type,
            amount=txn.amount,
            memo=txn.memo,
            account_id=txn.account_id,
            source=txn.source,
            created_at=txn.created_at
        )
        for txn in transactions
    ]
    
    return TransactionListResponse(
        transactions=transaction_responses,
        total=total,
        limit=limit,
        offset=offset
    )


@router.get("/{transaction_id}", response_model=TransactionResponse)
async def get_transaction(
    transaction_id: str,
    user_id: str = Depends(get_current_db_user_id),
    transaction_service: TransactionService = Depends(get_transaction_service),
):
    """
    Get single transaction by ID.
    
    Returns a single transaction if it exists and belongs to the authenticated user.
    
    Args:
        transaction_id: Transaction ID
        user_id: Current user ID from JWT token
        transaction_service: Transaction service instance
        
    Returns:
        TransactionResponse with transaction details
        
    Raises:
        401: Invalid or expired token
        404: Transaction not found or doesn't belong to user
    """
    try:
        transaction = await transaction_service.get_transaction(
            transaction_id=transaction_id,
            user_id=user_id
        )
        
        return TransactionResponse(
            transaction_id=transaction.transaction_id,
            transaction_date=transaction.transaction_date,
            post_date=transaction.post_date,
            description=transaction.description,
            category=transaction.category,
            type=transaction.type,
            amount=transaction.amount,
            memo=transaction.memo,
            account_id=transaction.account_id,
            source=transaction.source,
            created_at=transaction.created_at
        )
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "RESOURCE_NOT_FOUND", "message": str(e)}}
        )


@router.post("", response_model=TransactionResponse, status_code=status.HTTP_201_CREATED)
async def create_transaction(
    request: CreateTransactionRequest,
    user_id: str = Depends(get_current_db_user_id),
    transaction_service: TransactionService = Depends(get_transaction_service),
):
    """
    Create a new transaction.
    
    Creates a new transaction for the authenticated user.
    
    Args:
        request: Transaction creation request
        user_id: Current user ID from JWT token
        transaction_service: Transaction service instance
        
    Returns:
        TransactionResponse with created transaction details
        
    Raises:
        401: Invalid or expired token
        400: Validation error
    """
    try:
        transaction = await transaction_service.create_transaction(
            user_id=user_id,
            transaction_date=request.transaction_date,
            post_date=request.post_date,
            description=request.description,
            amount=request.amount,
            account_id=request.account_id,
            source=request.source,
            category=request.category,
            type=request.type,
            memo=request.memo
        )
        
        return TransactionResponse(
            transaction_id=transaction.transaction_id,
            transaction_date=transaction.transaction_date,
            post_date=transaction.post_date,
            description=transaction.description,
            category=transaction.category,
            type=transaction.type,
            amount=transaction.amount,
            memo=transaction.memo,
            account_id=transaction.account_id,
            source=transaction.source,
            created_at=transaction.created_at
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": {"code": "VALIDATION_ERROR", "message": str(e)}}
        )


@router.put("/{transaction_id}", response_model=TransactionResponse)
async def update_transaction(
    transaction_id: str,
    request: UpdateTransactionRequest,
    user_id: str = Depends(get_current_db_user_id),
    transaction_service: TransactionService = Depends(get_transaction_service),
):
    """
    Update a transaction.
    
    Updates an existing transaction if it belongs to the authenticated user.
    
    Args:
        transaction_id: Transaction ID to update
        request: Transaction update request
        user_id: Current user ID from JWT token
        transaction_service: Transaction service instance
        
    Returns:
        TransactionResponse with updated transaction details
        
    Raises:
        401: Invalid or expired token
        404: Transaction not found or doesn't belong to user
        400: Validation error
    """
    try:
        transaction = await transaction_service.update_transaction(
            transaction_id=transaction_id,
            user_id=user_id,
            transaction_date=request.transaction_date,
            post_date=request.post_date,
            description=request.description,
            category=request.category,
            type=request.type,
            amount=request.amount,
            memo=request.memo
        )
        
        return TransactionResponse(
            transaction_id=transaction.transaction_id,
            transaction_date=transaction.transaction_date,
            post_date=transaction.post_date,
            description=transaction.description,
            category=transaction.category,
            type=transaction.type,
            amount=transaction.amount,
            memo=transaction.memo,
            account_id=transaction.account_id,
            source=transaction.source,
            created_at=transaction.created_at
        )
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "RESOURCE_NOT_FOUND", "message": str(e)}}
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": {"code": "VALIDATION_ERROR", "message": str(e)}}
        )


@router.delete("/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_transaction(
    transaction_id: str,
    user_id: str = Depends(get_current_db_user_id),
    transaction_service: TransactionService = Depends(get_transaction_service),
):
    """
    Delete a transaction.
    
    Deletes a transaction if it belongs to the authenticated user.
    
    Args:
        transaction_id: Transaction ID to delete
        user_id: Current user ID from JWT token
        transaction_service: Transaction service instance
        
    Returns:
        204 No Content on success
        
    Raises:
        401: Invalid or expired token
        404: Transaction not found or doesn't belong to user
    """
    try:
        await transaction_service.delete_transaction(
            transaction_id=transaction_id,
            user_id=user_id
        )
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "RESOURCE_NOT_FOUND", "message": str(e)}}
        )
