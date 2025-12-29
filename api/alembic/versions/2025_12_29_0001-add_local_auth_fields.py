"""Add local authentication fields to users table

Revision ID: add_local_auth_fields
Revises: 6d90e326dfc3
Create Date: 2025-12-29

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_local_auth_fields'
down_revision: Union[str, None] = '6d90e326dfc3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add password_hash and email_verified columns for local authentication."""
    # Add password_hash column (nullable for backward compatibility with Cognito users)
    op.add_column('users', sa.Column('password_hash', sa.String(255), nullable=True))
    
    # Add email_verified column (default True for existing users)
    op.add_column('users', sa.Column('email_verified', sa.Boolean(), nullable=False, server_default='true'))
    
    # Make cognito_sub nullable (not required for local auth users)
    op.alter_column('users', 'cognito_sub',
                    existing_type=sa.String(255),
                    nullable=True)


def downgrade() -> None:
    """Remove local authentication fields."""
    # Make cognito_sub not nullable again
    op.alter_column('users', 'cognito_sub',
                    existing_type=sa.String(255),
                    nullable=False)
    
    # Drop columns
    op.drop_column('users', 'email_verified')
    op.drop_column('users', 'password_hash')

