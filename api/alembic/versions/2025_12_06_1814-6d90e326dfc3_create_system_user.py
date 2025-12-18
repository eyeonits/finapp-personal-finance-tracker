"""create_system_user

Revision ID: 6d90e326dfc3
Revises: 8af60f182141
Create Date: 2025-12-06 18:14:04.308410

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6d90e326dfc3'
down_revision: Union[str, None] = '8af60f182141'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create a system user for existing data migration
    # This user will be used to associate any pre-existing transactions
    # that were created before the multi-user system was implemented
    op.execute("""
        INSERT INTO users (user_id, cognito_sub, email, is_active)
        VALUES (
            'system-user-id',
            'system',
            'system@finapp.local',
            true
        )
        ON CONFLICT (cognito_sub) DO NOTHING
    """)


def downgrade() -> None:
    # Remove the system user
    op.execute("""
        DELETE FROM users WHERE user_id = 'system-user-id'
    """)
