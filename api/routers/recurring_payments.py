"""
Recurring payment endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import Optional
from datetime import date
from decimal import Decimal

from api.models.requests import (
    CreateRecurringPaymentRequest,
    UpdateRecurringPaymentRequest,
    MarkPaymentPaidRequest,
    SkipPaymentRequest,
    GeneratePaymentRecordsRequest,
)
from api.models.responses import (
    RecurringPaymentResponse,
    RecurringPaymentListResponse,
    PaymentRecordResponse,
    PaymentRecordListResponse,
    PaymentSummaryResponse,
)
from api.services.recurring_payment_service import RecurringPaymentService
from api.dependencies import get_recurring_payment_service, get_current_db_user_id
from api.utils.exceptions import NotFoundError, ValidationError

router = APIRouter()


# ==================== Helper Functions ====================

def _payment_to_response(payment) -> RecurringPaymentResponse:
    """Convert domain model to response model."""
    return RecurringPaymentResponse(
        payment_id=payment.payment_id,
        name=payment.name,
        description=payment.description,
        amount=payment.amount,
        frequency=payment.frequency,
        due_day=int(payment.due_day) if payment.due_day else None,
        category=payment.category,
        payee=payment.payee,
        account_id=payment.account_id,
        is_active=payment.is_active,
        start_date=payment.start_date,
        end_date=payment.end_date,
        reminder_days=int(payment.reminder_days) if payment.reminder_days else None,
        auto_pay=payment.auto_pay,
        notes=payment.notes,
        created_at=payment.created_at,
        updated_at=payment.updated_at,
    )


def _record_to_response(record) -> PaymentRecordResponse:
    """Convert domain model to response model."""
    return PaymentRecordResponse(
        record_id=record.record_id,
        payment_id=record.payment_id,
        due_date=record.due_date,
        paid_date=record.paid_date,
        amount_due=record.amount_due,
        amount_paid=record.amount_paid,
        status=record.status,
        transaction_id=record.transaction_id,
        notes=record.notes,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


# ==================== Recurring Payments Endpoints ====================

@router.get("/summary", response_model=PaymentSummaryResponse)
async def get_payment_summary(
    user_id: str = Depends(get_current_db_user_id),
    service: RecurringPaymentService = Depends(get_recurring_payment_service),
):
    """
    Get payment summary for the user.
    
    Returns a summary including total recurring payments, estimated monthly total,
    upcoming payments, and overdue payments.
    """
    summary = await service.get_payment_summary(user_id)
    return PaymentSummaryResponse(**summary)


@router.get("", response_model=RecurringPaymentListResponse)
async def list_recurring_payments(
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    category: Optional[str] = Query(None, description="Filter by category"),
    frequency: Optional[str] = Query(None, description="Filter by frequency"),
    limit: int = Query(100, le=1000, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    user_id: str = Depends(get_current_db_user_id),
    service: RecurringPaymentService = Depends(get_recurring_payment_service),
):
    """
    List recurring payments with optional filters.
    
    Returns a paginated list of recurring payments for the authenticated user.
    """
    payments, total = await service.get_recurring_payments(
        user_id=user_id,
        is_active=is_active,
        category=category,
        frequency=frequency,
        limit=limit,
        offset=offset
    )
    
    return RecurringPaymentListResponse(
        payments=[_payment_to_response(p) for p in payments],
        total=total,
        limit=limit,
        offset=offset
    )


@router.get("/{payment_id}", response_model=RecurringPaymentResponse)
async def get_recurring_payment(
    payment_id: str,
    user_id: str = Depends(get_current_db_user_id),
    service: RecurringPaymentService = Depends(get_recurring_payment_service),
):
    """
    Get a single recurring payment by ID.
    """
    try:
        payment = await service.get_recurring_payment(payment_id, user_id)
        return _payment_to_response(payment)
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "RESOURCE_NOT_FOUND", "message": str(e)}}
        )


@router.post("", response_model=RecurringPaymentResponse, status_code=status.HTTP_201_CREATED)
async def create_recurring_payment(
    request: CreateRecurringPaymentRequest,
    user_id: str = Depends(get_current_db_user_id),
    service: RecurringPaymentService = Depends(get_recurring_payment_service),
):
    """
    Create a new recurring payment.
    
    Creates a recurring payment (bill, subscription) that will generate
    payment records based on the specified frequency.
    """
    try:
        payment = await service.create_recurring_payment(
            user_id=user_id,
            name=request.name,
            amount=request.amount,
            frequency=request.frequency,
            start_date=request.start_date,
            due_day=request.due_day,
            description=request.description,
            category=request.category,
            payee=request.payee,
            account_id=request.account_id,
            end_date=request.end_date,
            reminder_days=request.reminder_days,
            auto_pay=request.auto_pay,
            notes=request.notes
        )
        return _payment_to_response(payment)
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": {"code": "VALIDATION_ERROR", "message": str(e)}}
        )


@router.put("/{payment_id}", response_model=RecurringPaymentResponse)
async def update_recurring_payment(
    payment_id: str,
    request: UpdateRecurringPaymentRequest,
    user_id: str = Depends(get_current_db_user_id),
    service: RecurringPaymentService = Depends(get_recurring_payment_service),
):
    """
    Update a recurring payment.
    """
    try:
        payment = await service.update_recurring_payment(
            payment_id=payment_id,
            user_id=user_id,
            name=request.name,
            description=request.description,
            amount=request.amount,
            frequency=request.frequency,
            due_day=request.due_day,
            category=request.category,
            payee=request.payee,
            account_id=request.account_id,
            is_active=request.is_active,
            end_date=request.end_date,
            reminder_days=request.reminder_days,
            auto_pay=request.auto_pay,
            notes=request.notes
        )
        return _payment_to_response(payment)
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "RESOURCE_NOT_FOUND", "message": str(e)}}
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": {"code": "VALIDATION_ERROR", "message": str(e)}}
        )


@router.delete("/{payment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_recurring_payment(
    payment_id: str,
    user_id: str = Depends(get_current_db_user_id),
    service: RecurringPaymentService = Depends(get_recurring_payment_service),
):
    """
    Delete a recurring payment.
    
    Also deletes all associated payment records.
    """
    try:
        await service.delete_recurring_payment(payment_id, user_id)
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "RESOURCE_NOT_FOUND", "message": str(e)}}
        )


@router.post("/{payment_id}/generate-records", response_model=PaymentRecordListResponse)
async def generate_payment_records(
    payment_id: str,
    request: GeneratePaymentRecordsRequest,
    user_id: str = Depends(get_current_db_user_id),
    service: RecurringPaymentService = Depends(get_recurring_payment_service),
):
    """
    Generate payment records for a recurring payment.
    
    Creates pending payment records for the specified number of months ahead.
    Only creates records that don't already exist.
    """
    try:
        records = await service.generate_payment_records(
            user_id=user_id,
            payment_id=payment_id,
            months_ahead=request.months_ahead
        )
        return PaymentRecordListResponse(
            records=[_record_to_response(r) for r in records],
            total=len(records),
            limit=len(records),
            offset=0
        )
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "RESOURCE_NOT_FOUND", "message": str(e)}}
        )


# ==================== Payment Records Endpoints ====================

@router.get("/records/upcoming", response_model=PaymentRecordListResponse)
async def get_upcoming_payments(
    days_ahead: int = Query(30, ge=1, le=365, description="Number of days to look ahead"),
    user_id: str = Depends(get_current_db_user_id),
    service: RecurringPaymentService = Depends(get_recurring_payment_service),
):
    """
    Get upcoming payment records for the next N days.
    """
    records = await service.get_upcoming_payments(user_id, days_ahead)
    return PaymentRecordListResponse(
        records=[_record_to_response(r) for r in records],
        total=len(records),
        limit=len(records),
        offset=0
    )


@router.get("/records/overdue", response_model=PaymentRecordListResponse)
async def get_overdue_payments(
    user_id: str = Depends(get_current_db_user_id),
    service: RecurringPaymentService = Depends(get_recurring_payment_service),
):
    """
    Get overdue payment records.
    """
    records = await service.get_overdue_payments(user_id)
    return PaymentRecordListResponse(
        records=[_record_to_response(r) for r in records],
        total=len(records),
        limit=len(records),
        offset=0
    )


@router.get("/records/all", response_model=PaymentRecordListResponse)
async def list_payment_records(
    payment_id: Optional[str] = Query(None, description="Filter by recurring payment ID"),
    status: Optional[str] = Query(None, description="Filter by status (pending, paid, overdue, skipped)"),
    start_date: Optional[date] = Query(None, description="Filter by due date >= start_date"),
    end_date: Optional[date] = Query(None, description="Filter by due date <= end_date"),
    limit: int = Query(100, le=1000, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    user_id: str = Depends(get_current_db_user_id),
    service: RecurringPaymentService = Depends(get_recurring_payment_service),
):
    """
    List payment records with optional filters.
    """
    try:
        records, total = await service.get_payment_records(
            user_id=user_id,
            payment_id=payment_id,
            status=status,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
            offset=offset
        )
        return PaymentRecordListResponse(
            records=[_record_to_response(r) for r in records],
            total=total,
            limit=limit,
            offset=offset
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": {"code": "VALIDATION_ERROR", "message": str(e)}}
        )


@router.get("/records/{record_id}", response_model=PaymentRecordResponse)
async def get_payment_record(
    record_id: str,
    user_id: str = Depends(get_current_db_user_id),
    service: RecurringPaymentService = Depends(get_recurring_payment_service),
):
    """
    Get a single payment record by ID.
    """
    try:
        record = await service.get_payment_record(record_id, user_id)
        return _record_to_response(record)
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "RESOURCE_NOT_FOUND", "message": str(e)}}
        )


@router.post("/records/{record_id}/pay", response_model=PaymentRecordResponse)
async def mark_payment_as_paid(
    record_id: str,
    request: MarkPaymentPaidRequest,
    user_id: str = Depends(get_current_db_user_id),
    service: RecurringPaymentService = Depends(get_recurring_payment_service),
):
    """
    Mark a payment record as paid.
    
    Optionally link to a transaction if the payment matches one.
    """
    try:
        record = await service.mark_as_paid(
            record_id=record_id,
            user_id=user_id,
            paid_date=request.paid_date,
            amount_paid=request.amount_paid,
            transaction_id=request.transaction_id
        )
        return _record_to_response(record)
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "RESOURCE_NOT_FOUND", "message": str(e)}}
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": {"code": "VALIDATION_ERROR", "message": str(e)}}
        )


@router.post("/records/{record_id}/skip", response_model=PaymentRecordResponse)
async def skip_payment(
    record_id: str,
    request: SkipPaymentRequest,
    user_id: str = Depends(get_current_db_user_id),
    service: RecurringPaymentService = Depends(get_recurring_payment_service),
):
    """
    Skip a payment record.
    
    Mark a payment as skipped (e.g., waived, cancelled, etc.).
    """
    try:
        record = await service.skip_payment(
            record_id=record_id,
            user_id=user_id,
            notes=request.notes
        )
        return _record_to_response(record)
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "RESOURCE_NOT_FOUND", "message": str(e)}}
        )
