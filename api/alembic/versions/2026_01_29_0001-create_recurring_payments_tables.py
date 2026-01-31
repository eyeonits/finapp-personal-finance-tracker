"""create_recurring_payments_tables

Revision ID: a1b2c3d4e5f6
Revises: 2025_12_29_0001-add_local_auth_fields
Create Date: 2026-01-29 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = 'add_local_auth_fields'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create recurring_payments table
    op.create_table(
        'recurring_payments',
        sa.Column('payment_id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(36), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.String(500), nullable=True),
        sa.Column('amount', sa.Numeric(10, 2), nullable=False),
        sa.Column('frequency', sa.String(50), nullable=False),  # 'weekly', 'monthly', 'quarterly', 'yearly'
        sa.Column('due_day', sa.Integer(), nullable=True),  # Day of month (1-31) or day of week (1-7)
        sa.Column('category', sa.String(100), nullable=True),
        sa.Column('payee', sa.String(255), nullable=True),
        sa.Column('account_id', sa.String(100), nullable=True),  # Which account pays this
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('start_date', sa.Date(), nullable=False),
        sa.Column('end_date', sa.Date(), nullable=True),  # Null means ongoing
        sa.Column('reminder_days', sa.Integer(), nullable=True, server_default='3'),  # Days before due to remind
        sa.Column('auto_pay', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    
    # Add foreign key constraint to users table
    op.create_foreign_key(
        'fk_recurring_payments_user_id',
        'recurring_payments', 'users',
        ['user_id'], ['user_id']
    )
    
    # Add indexes for performance
    op.create_index('idx_recurring_payments_user_id', 'recurring_payments', ['user_id'])
    op.create_index('idx_recurring_payments_due_day', 'recurring_payments', ['due_day'])
    op.create_index('idx_recurring_payments_is_active', 'recurring_payments', ['is_active'])
    
    # Create payment_records table to track actual payments made
    op.create_table(
        'payment_records',
        sa.Column('record_id', sa.String(36), primary_key=True),
        sa.Column('payment_id', sa.String(36), nullable=False),
        sa.Column('user_id', sa.String(36), nullable=False),
        sa.Column('due_date', sa.Date(), nullable=False),
        sa.Column('paid_date', sa.Date(), nullable=True),
        sa.Column('amount_due', sa.Numeric(10, 2), nullable=False),
        sa.Column('amount_paid', sa.Numeric(10, 2), nullable=True),
        sa.Column('status', sa.String(50), nullable=False, server_default='pending'),  # 'pending', 'paid', 'overdue', 'skipped'
        sa.Column('transaction_id', sa.String(36), nullable=True),  # Link to actual transaction if matched
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    
    # Add foreign key constraints
    op.create_foreign_key(
        'fk_payment_records_payment_id',
        'payment_records', 'recurring_payments',
        ['payment_id'], ['payment_id']
    )
    op.create_foreign_key(
        'fk_payment_records_user_id',
        'payment_records', 'users',
        ['user_id'], ['user_id']
    )
    op.create_foreign_key(
        'fk_payment_records_transaction_id',
        'payment_records', 'transactions',
        ['transaction_id'], ['transaction_id']
    )
    
    # Add indexes for performance
    op.create_index('idx_payment_records_payment_id', 'payment_records', ['payment_id'])
    op.create_index('idx_payment_records_user_id', 'payment_records', ['user_id'])
    op.create_index('idx_payment_records_due_date', 'payment_records', ['due_date'])
    op.create_index('idx_payment_records_status', 'payment_records', ['status'])


def downgrade() -> None:
    # Drop indexes for payment_records
    op.drop_index('idx_payment_records_status', 'payment_records')
    op.drop_index('idx_payment_records_due_date', 'payment_records')
    op.drop_index('idx_payment_records_user_id', 'payment_records')
    op.drop_index('idx_payment_records_payment_id', 'payment_records')
    
    # Drop foreign keys for payment_records
    op.drop_constraint('fk_payment_records_transaction_id', 'payment_records', type_='foreignkey')
    op.drop_constraint('fk_payment_records_user_id', 'payment_records', type_='foreignkey')
    op.drop_constraint('fk_payment_records_payment_id', 'payment_records', type_='foreignkey')
    
    # Drop payment_records table
    op.drop_table('payment_records')
    
    # Drop indexes for recurring_payments
    op.drop_index('idx_recurring_payments_is_active', 'recurring_payments')
    op.drop_index('idx_recurring_payments_due_day', 'recurring_payments')
    op.drop_index('idx_recurring_payments_user_id', 'recurring_payments')
    
    # Drop foreign key for recurring_payments
    op.drop_constraint('fk_recurring_payments_user_id', 'recurring_payments', type_='foreignkey')
    
    # Drop recurring_payments table
    op.drop_table('recurring_payments')
