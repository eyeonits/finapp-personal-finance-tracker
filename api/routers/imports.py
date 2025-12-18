"""
CSV import endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Query
from typing import Optional

from api.dependencies import get_import_service, get_current_user_id, get_current_db_user_id, get_import_repository
from api.services.import_service import ImportService
from api.repositories.import_repository import ImportRepository
from api.models.responses import ImportResponse, ImportHistoryResponse
from api.utils.exceptions import NotFoundError

router = APIRouter()


@router.post("/credit-card", response_model=ImportResponse)
async def import_credit_card(
    file: UploadFile = File(..., description="Credit card CSV file"),
    account_id: str = Form(..., description="Account identifier (e.g., 'cc_apple', 'cc_chase')"),
    user_id: str = Depends(get_current_db_user_id),
    import_service: ImportService = Depends(get_import_service),
):
    """
    Import credit card CSV file.
    
    Supports multiple CSV formats:
    - Standard format: transaction date, post date, description, category, type, amount, memo
    - Apple Card format: Transaction Date, Clearing Date, Description, Merchant, Category, Type, Amount (USD), Purchased By
    - Simple Date/Amount format (e.g., Amex): Date, Description, Amount, Category
    
    Args:
        file: CSV file to import
        account_id: Account identifier for the transactions
        user_id: Current user ID from JWT token
        import_service: Import service instance
        
    Returns:
        ImportResponse with import results
        
    Raises:
        400: If file is invalid or account_id is missing
        401: Invalid or expired token
    """
    if not file.filename or not file.filename.endswith('.csv'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be a CSV file"
        )
    
    if not account_id or not account_id.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="account_id is required"
        )
    
    try:
        file_content = await file.read()
        result = await import_service.import_credit_card_csv(
            user_id=user_id,
            file_content=file_content,
            account_id=account_id.strip(),
            filename=file.filename
        )
        
        return ImportResponse(
            import_id=result["import_id"],
            rows_total=result["rows_total"],
            rows_inserted=result["rows_inserted"],
            rows_skipped=result["rows_skipped"],
            status=result["status"]
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid CSV format: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Import failed: {str(e)}"
        )


@router.post("/bank", response_model=ImportResponse)
async def import_bank(
    file: UploadFile = File(..., description="Bank CSV file"),
    account_id: str = Form(..., description="Account identifier (e.g., 'chk_main', 'sav_main')"),
    user_id: str = Depends(get_current_db_user_id),
    import_service: ImportService = Depends(get_import_service),
):
    """
    Import bank CSV file.
    
    Expected CSV columns (case-insensitive):
    - Posted Date
    - Effective Date
    - Transaction
    - Amount
    - Balance
    - Description
    - Check#
    - Memo
    
    Args:
        file: CSV file to import
        account_id: Account identifier for the transactions
        user_id: Current user ID from JWT token
        import_service: Import service instance
        
    Returns:
        ImportResponse with import results
        
    Raises:
        400: If file is invalid or account_id is missing
        401: Invalid or expired token
    """
    if not file.filename or not file.filename.endswith('.csv'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be a CSV file"
        )
    
    if not account_id or not account_id.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="account_id is required"
        )
    
    try:
        file_content = await file.read()
        result = await import_service.import_bank_csv(
            user_id=user_id,
            file_content=file_content,
            account_id=account_id.strip(),
            filename=file.filename
        )
        
        return ImportResponse(
            import_id=result["import_id"],
            rows_total=result["rows_total"],
            rows_inserted=result["rows_inserted"],
            rows_skipped=result["rows_skipped"],
            status=result["status"]
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid CSV format: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Import failed: {str(e)}"
        )


@router.get("/history", response_model=list[ImportHistoryResponse])
async def get_import_history(
    limit: int = Query(50, ge=1, le=100, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    user_id: str = Depends(get_current_db_user_id),
    import_repository: ImportRepository = Depends(get_import_repository),
):
    """
    Get import history for the authenticated user.
    
    Args:
        limit: Maximum number of results to return (1-100)
        offset: Number of results to skip
        user_id: Current user ID from JWT token
        import_repository: Import repository instance
        
    Returns:
        List of import history records
        
    Raises:
        401: Invalid or expired token
    """
    imports, total = await import_repository.get_import_history(
        user_id=user_id,
        limit=limit,
        offset=offset
    )
    
    return [
        ImportHistoryResponse(
            import_id=imp.import_id,
            import_type=imp.import_type,
            account_id=imp.account_id,
            filename=imp.filename,
            rows_total=int(imp.rows_total),
            rows_inserted=int(imp.rows_inserted),
            rows_skipped=int(imp.rows_skipped),
            status=imp.status,
            error_message=imp.error_message,
            created_at=imp.created_at
        )
        for imp in imports
    ]


@router.get("/{import_id}", response_model=ImportHistoryResponse)
async def get_import_details(
    import_id: str,
    user_id: str = Depends(get_current_db_user_id),
    import_repository: ImportRepository = Depends(get_import_repository),
):
    """
    Get details for a specific import.
    
    Args:
        import_id: Import ID
        user_id: Current user ID from JWT token
        import_repository: Import repository instance
        
    Returns:
        ImportHistoryResponse with import details
        
    Raises:
        401: Invalid or expired token
        404: Import not found or doesn't belong to user
    """
    import_history = await import_repository.get_import_by_id(import_id, user_id)
    
    if not import_history:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Import not found"
        )
    
    return ImportHistoryResponse(
        import_id=import_history.import_id,
        import_type=import_history.import_type,
        account_id=import_history.account_id,
        filename=import_history.filename,
        rows_total=int(import_history.rows_total),
        rows_inserted=int(import_history.rows_inserted),
        rows_skipped=int(import_history.rows_skipped),
        status=import_history.status,
        error_message=import_history.error_message,
        created_at=import_history.created_at
    )
