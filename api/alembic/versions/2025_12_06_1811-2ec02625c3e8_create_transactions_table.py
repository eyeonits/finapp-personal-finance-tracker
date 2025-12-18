"""create_transactions_table

Revision ID: 2ec02625c3e8
Revises: da99dcee9de7
Create Date: 2025-12-06 18:11:48.816336

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2ec02625c3e8'
down_revision: Union[str, None] = 'da99dcee9de7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create transactions table (consolidates cc_transactions and bank_transactions)
    op.create_table(
        'transactions',
        sa.Column('transaction_id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(36), nullable=False),
        sa.Column('transaction_date', sa.Date(), nullable=False),
        sa.Column('post_date', sa.Date(), nullable=False),
        sa.Column('description', sa.String(500), nullable=False),
        sa.Column('category', sa.String(100), nullable=True),
        sa.Column('type', sa.String(50), nullable=True),
        sa.Column('amount', sa.Numeric(10, 2), nullable=False),
        sa.Column('memo', sa.String(500), nullable=True),
        sa.Column('account_id', sa.String(100), nullable=False),
        sa.Column('source', sa.String(50), nullable=False),  # 'credit_card' or 'bank'
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    
    # Add foreign key constraint to users table
    op.create_foreign_key(
        'fk_transactions_user_id',
        'transactions', 'users',
        ['user_id'], ['user_id']
    )
    
    # Add indexes for performance
    op.create_index('idx_transactions_user_id', 'transactions', ['user_id'])
    op.create_index('idx_transactions_date', 'transactions', ['transaction_date'])
    op.create_index('idx_transactions_account_id', 'transactions', ['account_id'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('idx_transactions_account_id', 'transactions')
    op.drop_index('idx_transactions_date', 'transactions')
    op.drop_index('idx_transactions_user_id', 'transactions')
    
    # Drop foreign key constraint
    op.drop_constraint('fk_transactions_user_id', 'transactions', type_='foreignkey')
    
    # Drop table
    op.drop_table('transactions')
