"""
Recurring payment service for business logic.
"""
from typing import Optional, List, Dict, Any
from datetime import date, timedelta
from decimal import Decimal
from dateutil.relativedelta import relativedelta
from api.repositories.recurring_payment_repository import RecurringPaymentRepository
from api.models.domain import RecurringPayment, PaymentRecord
from api.utils.exceptions import NotFoundError, ValidationError


class RecurringPaymentService:
    """Service for recurring payment business logic."""
    
    VALID_FREQUENCIES = ['weekly', 'monthly', 'quarterly', 'yearly']
    VALID_STATUSES = ['pending', 'paid', 'overdue', 'skipped']
    
    def __init__(self, recurring_payment_repo: RecurringPaymentRepository):
        """Initialize service with repository."""
        self.recurring_payment_repo = recurring_payment_repo
    
    # ==================== Recurring Payments ====================
    
    async def get_recurring_payments(
        self,
        user_id: str,
        is_active: Optional[bool] = None,
        category: Optional[str] = None,
        frequency: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> tuple[List[RecurringPayment], int]:
        """
        Get recurring payments for a user with optional filters.
        """
        return await self.recurring_payment_repo.get_recurring_payments(
            user_id=user_id,
            is_active=is_active,
            category=category,
            frequency=frequency,
            limit=limit,
            offset=offset
        )
    
    async def get_recurring_payment(
        self,
        payment_id: str,
        user_id: str
    ) -> RecurringPayment:
        """
        Get a single recurring payment by ID with authorization check.
        
        Raises:
            NotFoundError: If payment not found
        """
        payment = await self.recurring_payment_repo.get_recurring_payment_by_id(
            payment_id=payment_id,
            user_id=user_id
        )
        
        if not payment:
            raise NotFoundError(f"Recurring payment {payment_id} not found")
        
        return payment
    
    async def create_recurring_payment(
        self,
        user_id: str,
        name: str,
        amount: Decimal,
        frequency: str,
        start_date: date,
        due_day: Optional[int] = None,
        description: Optional[str] = None,
        category: Optional[str] = None,
        payee: Optional[str] = None,
        account_id: Optional[str] = None,
        end_date: Optional[date] = None,
        reminder_days: Optional[int] = 3,
        auto_pay: bool = False,
        notes: Optional[str] = None
    ) -> RecurringPayment:
        """
        Create a new recurring payment with validation.
        
        Raises:
            ValidationError: If validation fails
        """
        # Validate name
        if not name or not name.strip():
            raise ValidationError("Name cannot be empty")
        
        # Validate amount
        if amount <= 0:
            raise ValidationError("Amount must be greater than 0")
        
        # Validate frequency
        if frequency not in self.VALID_FREQUENCIES:
            raise ValidationError(f"Invalid frequency: {frequency}. Must be one of: {', '.join(self.VALID_FREQUENCIES)}")
        
        # Validate due_day based on frequency
        if due_day is not None:
            if frequency == 'weekly' and (due_day < 1 or due_day > 7):
                raise ValidationError("For weekly frequency, due_day must be between 1 (Monday) and 7 (Sunday)")
            elif frequency in ['monthly', 'quarterly', 'yearly'] and (due_day < 1 or due_day > 31):
                raise ValidationError("For monthly/quarterly/yearly frequency, due_day must be between 1 and 31")
        
        # Validate end_date
        if end_date is not None and end_date < start_date:
            raise ValidationError("End date cannot be before start date")
        
        # Validate reminder_days
        if reminder_days is not None and reminder_days < 0:
            raise ValidationError("Reminder days cannot be negative")
        
        return await self.recurring_payment_repo.create_recurring_payment(
            user_id=user_id,
            name=name.strip(),
            amount=amount,
            frequency=frequency,
            start_date=start_date,
            due_day=due_day,
            description=description.strip() if description else None,
            category=category.strip() if category else None,
            payee=payee.strip() if payee else None,
            account_id=account_id,
            end_date=end_date,
            reminder_days=reminder_days,
            auto_pay=auto_pay,
            notes=notes.strip() if notes else None
        )
    
    async def update_recurring_payment(
        self,
        payment_id: str,
        user_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        amount: Optional[Decimal] = None,
        frequency: Optional[str] = None,
        due_day: Optional[int] = None,
        category: Optional[str] = None,
        payee: Optional[str] = None,
        account_id: Optional[str] = None,
        is_active: Optional[bool] = None,
        end_date: Optional[date] = None,
        reminder_days: Optional[int] = None,
        auto_pay: Optional[bool] = None,
        notes: Optional[str] = None
    ) -> RecurringPayment:
        """
        Update a recurring payment with authorization check.
        
        Raises:
            NotFoundError: If payment not found
            ValidationError: If validation fails
        """
        # Validate name if provided
        if name is not None and (not name or not name.strip()):
            raise ValidationError("Name cannot be empty")
        
        # Validate amount if provided
        if amount is not None and amount <= 0:
            raise ValidationError("Amount must be greater than 0")
        
        # Validate frequency if provided
        if frequency is not None and frequency not in self.VALID_FREQUENCIES:
            raise ValidationError(f"Invalid frequency: {frequency}. Must be one of: {', '.join(self.VALID_FREQUENCIES)}")
        
        # Validate reminder_days if provided
        if reminder_days is not None and reminder_days < 0:
            raise ValidationError("Reminder days cannot be negative")
        
        payment = await self.recurring_payment_repo.update_recurring_payment(
            payment_id=payment_id,
            user_id=user_id,
            name=name.strip() if name else None,
            description=description.strip() if description else None,
            amount=amount,
            frequency=frequency,
            due_day=due_day,
            category=category.strip() if category else None,
            payee=payee.strip() if payee else None,
            account_id=account_id,
            is_active=is_active,
            end_date=end_date,
            reminder_days=reminder_days,
            auto_pay=auto_pay,
            notes=notes.strip() if notes else None
        )
        
        if not payment:
            raise NotFoundError(f"Recurring payment {payment_id} not found")
        
        return payment
    
    async def delete_recurring_payment(
        self,
        payment_id: str,
        user_id: str
    ) -> None:
        """
        Delete a recurring payment with authorization check.
        
        Raises:
            NotFoundError: If payment not found
        """
        deleted = await self.recurring_payment_repo.delete_recurring_payment(
            payment_id=payment_id,
            user_id=user_id
        )
        
        if not deleted:
            raise NotFoundError(f"Recurring payment {payment_id} not found")
    
    # ==================== Payment Records ====================
    
    async def get_payment_records(
        self,
        user_id: str,
        payment_id: Optional[str] = None,
        status: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        limit: int = 100,
        offset: int = 0
    ) -> tuple[List[PaymentRecord], int]:
        """
        Get payment records for a user with optional filters.
        """
        # Validate status if provided
        if status is not None and status not in self.VALID_STATUSES:
            raise ValidationError(f"Invalid status: {status}. Must be one of: {', '.join(self.VALID_STATUSES)}")
        
        return await self.recurring_payment_repo.get_payment_records(
            user_id=user_id,
            payment_id=payment_id,
            status=status,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
            offset=offset
        )
    
    async def get_payment_record(
        self,
        record_id: str,
        user_id: str
    ) -> PaymentRecord:
        """
        Get a single payment record by ID with authorization check.
        
        Raises:
            NotFoundError: If record not found
        """
        record = await self.recurring_payment_repo.get_payment_record_by_id(
            record_id=record_id,
            user_id=user_id
        )
        
        if not record:
            raise NotFoundError(f"Payment record {record_id} not found")
        
        return record
    
    async def mark_as_paid(
        self,
        record_id: str,
        user_id: str,
        paid_date: date,
        amount_paid: Decimal,
        transaction_id: Optional[str] = None
    ) -> PaymentRecord:
        """
        Mark a payment record as paid.
        
        Raises:
            NotFoundError: If record not found
            ValidationError: If validation fails
        """
        if amount_paid <= 0:
            raise ValidationError("Amount paid must be greater than 0")
        
        record = await self.recurring_payment_repo.mark_record_as_paid(
            record_id=record_id,
            user_id=user_id,
            paid_date=paid_date,
            amount_paid=amount_paid,
            transaction_id=transaction_id
        )
        
        if not record:
            raise NotFoundError(f"Payment record {record_id} not found")
        
        return record
    
    async def skip_payment(
        self,
        record_id: str,
        user_id: str,
        notes: Optional[str] = None
    ) -> PaymentRecord:
        """
        Skip a payment record.
        
        Raises:
            NotFoundError: If record not found
        """
        record = await self.recurring_payment_repo.update_payment_record(
            record_id=record_id,
            user_id=user_id,
            status='skipped',
            notes=notes
        )
        
        if not record:
            raise NotFoundError(f"Payment record {record_id} not found")
        
        return record
    
    async def get_upcoming_payments(
        self,
        user_id: str,
        days_ahead: int = 30
    ) -> List[PaymentRecord]:
        """
        Get upcoming payment records for the next N days.
        """
        return await self.recurring_payment_repo.get_upcoming_payments(
            user_id=user_id,
            days_ahead=days_ahead
        )
    
    async def get_overdue_payments(
        self,
        user_id: str
    ) -> List[PaymentRecord]:
        """
        Get overdue payment records.
        """
        return await self.recurring_payment_repo.get_overdue_payments(user_id=user_id)
    
    async def generate_payment_records(
        self,
        user_id: str,
        payment_id: str,
        months_ahead: int = 3
    ) -> List[PaymentRecord]:
        """
        Generate payment records for a recurring payment for the specified period.
        Only generates records that don't already exist.
        
        Args:
            user_id: User ID
            payment_id: Recurring payment ID
            months_ahead: Number of months to generate records for
            
        Returns:
            List of created payment records
        """
        payment = await self.get_recurring_payment(payment_id, user_id)
        
        if not payment.is_active:
            return []
        
        today = date.today()
        end_generation_date = today + relativedelta(months=months_ahead)
        
        # If payment has an end date, don't generate beyond it
        if payment.end_date and payment.end_date < end_generation_date:
            end_generation_date = payment.end_date
        
        # Get existing records to avoid duplicates
        existing_records, _ = await self.recurring_payment_repo.get_payment_records(
            user_id=user_id,
            payment_id=payment_id,
            start_date=today,
            end_date=end_generation_date,
            limit=1000
        )
        existing_due_dates = {r.due_date for r in existing_records}
        
        # Generate due dates based on frequency
        due_dates = self._generate_due_dates(
            payment=payment,
            start_date=max(today, payment.start_date),
            end_date=end_generation_date
        )
        
        # Create records for dates that don't exist
        created_records = []
        for due_date in due_dates:
            if due_date not in existing_due_dates:
                record = await self.recurring_payment_repo.create_payment_record(
                    user_id=user_id,
                    payment_id=payment_id,
                    due_date=due_date,
                    amount_due=payment.amount,
                    status='pending'
                )
                created_records.append(record)
        
        return created_records
    
    def _generate_due_dates(
        self,
        payment: RecurringPayment,
        start_date: date,
        end_date: date
    ) -> List[date]:
        """
        Generate due dates for a recurring payment.
        """
        due_dates = []
        current_date = start_date
        due_day = int(payment.due_day) if payment.due_day else start_date.day
        
        # Calculate first due date
        if payment.frequency == 'weekly':
            # due_day is 1-7 for Monday-Sunday
            days_until_due = (due_day - current_date.isoweekday()) % 7
            if days_until_due == 0 and current_date > start_date:
                days_until_due = 7
            current_date = current_date + timedelta(days=days_until_due)
        elif payment.frequency in ['monthly', 'quarterly', 'yearly']:
            # Adjust to the due day of the current or next period
            try:
                current_date = current_date.replace(day=min(due_day, 28))
            except ValueError:
                # Handle months with fewer days
                current_date = current_date.replace(day=28)
            
            if current_date < start_date:
                if payment.frequency == 'monthly':
                    current_date = current_date + relativedelta(months=1)
                elif payment.frequency == 'quarterly':
                    current_date = current_date + relativedelta(months=3)
                else:  # yearly
                    current_date = current_date + relativedelta(years=1)
        
        # Generate dates
        while current_date <= end_date:
            due_dates.append(current_date)
            
            if payment.frequency == 'weekly':
                current_date = current_date + timedelta(weeks=1)
            elif payment.frequency == 'monthly':
                current_date = current_date + relativedelta(months=1)
            elif payment.frequency == 'quarterly':
                current_date = current_date + relativedelta(months=3)
            else:  # yearly
                current_date = current_date + relativedelta(years=1)
        
        return due_dates
    
    async def get_payment_summary(
        self,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Get a summary of payments for the user.
        """
        # Get all active recurring payments
        payments, total_payments = await self.recurring_payment_repo.get_recurring_payments(
            user_id=user_id,
            is_active=True,
            limit=1000
        )
        
        # Get upcoming payments for the next 30 days
        upcoming = await self.recurring_payment_repo.get_upcoming_payments(
            user_id=user_id,
            days_ahead=30
        )
        
        # Get overdue payments
        overdue = await self.recurring_payment_repo.get_overdue_payments(user_id=user_id)
        
        # Calculate totals
        total_monthly = sum(
            float(p.amount) * (12 if p.frequency == 'yearly' else 
                              4 if p.frequency == 'quarterly' else 
                              1 if p.frequency == 'monthly' else 
                              4.33)  # weekly
            / 12 for p in payments
        )
        
        upcoming_total = sum(float(r.amount_due) for r in upcoming)
        overdue_total = sum(float(r.amount_due) for r in overdue)
        
        return {
            'total_recurring_payments': total_payments,
            'estimated_monthly_total': round(total_monthly, 2),
            'upcoming_count': len(upcoming),
            'upcoming_total': round(upcoming_total, 2),
            'overdue_count': len(overdue),
            'overdue_total': round(overdue_total, 2)
        }
