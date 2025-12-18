"""create_import_history_table

Revision ID: 8af60f182141
Revises: 2ec02625c3e8
Create Date: 2025-12-06 18:12:16.466045

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8af60f182141'
down_revision: Union[str, None] = '2ec02625c3e8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create import_history table
    op.create_table(
        'import_history',
        sa.Column('import_id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(36), nullable=False),
        sa.Column('import_type', sa.String(50), nullable=False),
        sa.Column('account_id', sa.String(100), nullable=False),
        sa.Column('filename', sa.String(255), nullable=True),
        sa.Column('rows_total', sa.Integer(), nullable=False),
        sa.Column('rows_inserted', sa.Integer(), nullable=False),
        sa.Column('rows_skipped', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(50), nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    
    # Add foreign key constraint to users table
    op.create_foreign_key(
        'fk_import_history_user_id',
        'import_history', 'users',
        ['user_id'], ['user_id']
    )
    
    # Add indexes for performance
    op.create_index('idx_import_history_user_id', 'import_history', ['user_id'])
    op.create_index('idx_import_history_created_at', 'import_history', ['created_at'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('idx_import_history_created_at', 'import_history')
    op.drop_index('idx_import_history_user_id', 'import_history')
    
    # Drop foreign key constraint
    op.drop_constraint('fk_import_history_user_id', 'import_history', type_='foreignkey')
    
    # Drop table
    op.drop_table('import_history')
