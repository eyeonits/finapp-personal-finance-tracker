"""create_users_table

Revision ID: da99dcee9de7
Revises: 
Create Date: 2025-12-06 18:10:36.831248

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'da99dcee9de7'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create users table
    op.create_table(
        'users',
        sa.Column('user_id', sa.String(36), primary_key=True),
        sa.Column('cognito_sub', sa.String(255), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
    )
    
    # Add unique constraints
    op.create_unique_constraint('uq_users_cognito_sub', 'users', ['cognito_sub'])
    op.create_unique_constraint('uq_users_email', 'users', ['email'])
    
    # Add indexes
    op.create_index('idx_users_cognito_sub', 'users', ['cognito_sub'])
    op.create_index('idx_users_email', 'users', ['email'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('idx_users_email', 'users')
    op.drop_index('idx_users_cognito_sub', 'users')
    
    # Drop unique constraints
    op.drop_constraint('uq_users_email', 'users', type_='unique')
    op.drop_constraint('uq_users_cognito_sub', 'users', type_='unique')
    
    # Drop table
    op.drop_table('users')
