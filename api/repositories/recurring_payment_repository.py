"""
Recurring payment repository for database operations.
"""
from typing import Optional, List
from datetime import date
from decimal import Decimal
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from api.models.domain import RecurringPayment, PaymentRecord
from api.repositories.base_repository import BaseRepository


class RecurringPaymentRepository(BaseRepository):
    """Repository for recurring payment database operations."""
    
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
        
        Args:
            user_id: User ID to filter by
            is_active: Filter by active status (optional)
            category: Filter by category (optional)
            frequency: Filter by frequency (optional)
            limit: Maximum number of results to return
            offset: Number of results to skip
            
        Returns:
            Tuple of (list of recurring payments, total count)
        """
        conditions = [RecurringPayment.user_id == user_id]
        
        if is_active is not None:
            conditions.append(RecurringPayment.is_active == is_active)
        if category:
            conditions.append(RecurringPayment.category == category)
        if frequency:
            conditions.append(RecurringPayment.frequency == frequency)
        
        # Build query for recurring payments
        query = select(RecurringPayment).where(and_(*conditions)).order_by(
            RecurringPayment.due_day.asc(),
            RecurringPayment.name.asc()
        )
        
        # Get total count
        count_query = select(RecurringPayment).where(and_(*conditions))
        count_result = await self.db.execute(count_query)
        total = len(count_result.scalars().all())
        
        # Apply pagination
        query = query.limit(limit).offset(offset)
        
        # Execute query
        result = await self.db.execute(query)
        payments = result.scalars().all()
        
        return list(payments), total
    
    async def get_recurring_payment_by_id(
        self,
        payment_id: str,
        user_id: str
    ) -> Optional[RecurringPayment]:
        """
        Get a single recurring payment by ID, ensuring it belongs to the user.
        
        Args:
            payment_id: Payment ID
            user_id: User ID to verify ownership
            
        Returns:
            RecurringPayment if found and belongs to user, None otherwise
        """
        query = select(RecurringPayment).where(
            and_(
                RecurringPayment.payment_id == payment_id,
                RecurringPayment.user_id == user_id
            )
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
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
        Create a new recurring payment.
        
        Args:
            user_id: User ID who owns the payment
            name: Name of the recurring payment
            amount: Payment amount
            frequency: Payment frequency ('weekly', 'monthly', 'quarterly', 'yearly')
            start_date: When the recurring payment starts
            due_day: Day of month/week when payment is due
            description: Optional description
            category: Optional category
            payee: Optional payee name
            account_id: Optional account ID that pays this
            end_date: Optional end date (None means ongoing)
            reminder_days: Days before due to remind
            auto_pay: Whether this is auto-paid
            notes: Optional notes
            
        Returns:
            Created recurring payment
        """
        payment = RecurringPayment(
            user_id=user_id,
            name=name,
            description=description,
            amount=amount,
            frequency=frequency,
            due_day=due_day,
            category=category,
            payee=payee,
            account_id=account_id,
            is_active=True,
            start_date=start_date,
            end_date=end_date,
            reminder_days=reminder_days,
            auto_pay=auto_pay,
            notes=notes
        )
        
        self.db.add(payment)
        await self.db.commit()
        await self.db.refresh(payment)
        
        return payment
    
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
    ) -> Optional[RecurringPayment]:
        """
        Update a recurring payment, ensuring it belongs to the user.
        
        Returns:
            Updated recurring payment if found and belongs to user, None otherwise
        """
        payment = await self.get_recurring_payment_by_id(payment_id, user_id)
        if not payment:
            return None
        
        if name is not None:
            payment.name = name
        if description is not None:
            payment.description = description
        if amount is not None:
            payment.amount = amount
        if frequency is not None:
            payment.frequency = frequency
        if due_day is not None:
            payment.due_day = due_day
        if category is not None:
            payment.category = category
        if payee is not None:
            payment.payee = payee
        if account_id is not None:
            payment.account_id = account_id
        if is_active is not None:
            payment.is_active = is_active
        if end_date is not None:
            payment.end_date = end_date
        if reminder_days is not None:
            payment.reminder_days = reminder_days
        if auto_pay is not None:
            payment.auto_pay = auto_pay
        if notes is not None:
            payment.notes = notes
        
        await self.db.commit()
        await self.db.refresh(payment)
        
        return payment
    
    async def delete_recurring_payment(
        self,
        payment_id: str,
        user_id: str
    ) -> bool:
        """
        Delete a recurring payment, ensuring it belongs to the user.
        Also deletes associated payment records.
        
        Returns:
            True if deleted, False if not found or doesn't belong to user
        """
        payment = await self.get_recurring_payment_by_id(payment_id, user_id)
        if not payment:
            return False
        
        # Delete associated payment records first
        records_query = select(PaymentRecord).where(
            and_(
                PaymentRecord.payment_id == payment_id,
                PaymentRecord.user_id == user_id
            )
        )
        records_result = await self.db.execute(records_query)
        records = records_result.scalars().all()
        for record in records:
            await self.db.delete(record)
        
        await self.db.delete(payment)
        await self.db.commit()
        
        return True
    
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
        
        Args:
            user_id: User ID to filter by
            payment_id: Filter by recurring payment ID (optional)
            status: Filter by status (optional)
            start_date: Filter by due date >= start_date (optional)
            end_date: Filter by due date <= end_date (optional)
            limit: Maximum number of results to return
            offset: Number of results to skip
            
        Returns:
            Tuple of (list of payment records, total count)
        """
        conditions = [PaymentRecord.user_id == user_id]
        
        if payment_id:
            conditions.append(PaymentRecord.payment_id == payment_id)
        if status:
            conditions.append(PaymentRecord.status == status)
        if start_date:
            conditions.append(PaymentRecord.due_date >= start_date)
        if end_date:
            conditions.append(PaymentRecord.due_date <= end_date)
        
        # Build query
        query = select(PaymentRecord).where(and_(*conditions)).order_by(
            PaymentRecord.due_date.desc()
        )
        
        # Get total count
        count_query = select(PaymentRecord).where(and_(*conditions))
        count_result = await self.db.execute(count_query)
        total = len(count_result.scalars().all())
        
        # Apply pagination
        query = query.limit(limit).offset(offset)
        
        # Execute query
        result = await self.db.execute(query)
        records = result.scalars().all()
        
        return list(records), total
    
    async def get_payment_record_by_id(
        self,
        record_id: str,
        user_id: str
    ) -> Optional[PaymentRecord]:
        """
        Get a single payment record by ID, ensuring it belongs to the user.
        """
        query = select(PaymentRecord).where(
            and_(
                PaymentRecord.record_id == record_id,
                PaymentRecord.user_id == user_id
            )
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def create_payment_record(
        self,
        user_id: str,
        payment_id: str,
        due_date: date,
        amount_due: Decimal,
        status: str = 'pending',
        paid_date: Optional[date] = None,
        amount_paid: Optional[Decimal] = None,
        transaction_id: Optional[str] = None,
        notes: Optional[str] = None
    ) -> PaymentRecord:
        """
        Create a new payment record.
        """
        record = PaymentRecord(
            user_id=user_id,
            payment_id=payment_id,
            due_date=due_date,
            amount_due=amount_due,
            status=status,
            paid_date=paid_date,
            amount_paid=amount_paid,
            transaction_id=transaction_id,
            notes=notes
        )
        
        self.db.add(record)
        await self.db.commit()
        await self.db.refresh(record)
        
        return record
    
    async def update_payment_record(
        self,
        record_id: str,
        user_id: str,
        status: Optional[str] = None,
        paid_date: Optional[date] = None,
        amount_paid: Optional[Decimal] = None,
        transaction_id: Optional[str] = None,
        notes: Optional[str] = None
    ) -> Optional[PaymentRecord]:
        """
        Update a payment record, ensuring it belongs to the user.
        """
        record = await self.get_payment_record_by_id(record_id, user_id)
        if not record:
            return None
        
        if status is not None:
            record.status = status
        if paid_date is not None:
            record.paid_date = paid_date
        if amount_paid is not None:
            record.amount_paid = amount_paid
        if transaction_id is not None:
            record.transaction_id = transaction_id
        if notes is not None:
            record.notes = notes
        
        await self.db.commit()
        await self.db.refresh(record)
        
        return record
    
    async def mark_record_as_paid(
        self,
        record_id: str,
        user_id: str,
        paid_date: date,
        amount_paid: Decimal,
        transaction_id: Optional[str] = None
    ) -> Optional[PaymentRecord]:
        """
        Mark a payment record as paid.
        """
        return await self.update_payment_record(
            record_id=record_id,
            user_id=user_id,
            status='paid',
            paid_date=paid_date,
            amount_paid=amount_paid,
            transaction_id=transaction_id
        )
    
    async def get_upcoming_payments(
        self,
        user_id: str,
        days_ahead: int = 30
    ) -> List[PaymentRecord]:
        """
        Get upcoming payment records for the next N days.
        """
        from datetime import timedelta
        today = date.today()
        end_date = today + timedelta(days=days_ahead)
        
        conditions = [
            PaymentRecord.user_id == user_id,
            PaymentRecord.status == 'pending',
            PaymentRecord.due_date >= today,
            PaymentRecord.due_date <= end_date
        ]
        
        query = select(PaymentRecord).where(and_(*conditions)).order_by(
            PaymentRecord.due_date.asc()
        )
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def get_overdue_payments(
        self,
        user_id: str
    ) -> List[PaymentRecord]:
        """
        Get overdue payment records.
        """
        today = date.today()
        
        conditions = [
            PaymentRecord.user_id == user_id,
            PaymentRecord.status == 'pending',
            PaymentRecord.due_date < today
        ]
        
        query = select(PaymentRecord).where(and_(*conditions)).order_by(
            PaymentRecord.due_date.asc()
        )
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
