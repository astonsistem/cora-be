"""activity log archive

Revision ID: q8a4c6d0f2b5
Revises: p7f3b5c9e1a4
Create Date: 2026-11-24 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'q8a4c6d0f2b5'
down_revision: Union[str, Sequence[str], None] = 'p7f3b5c9e1a4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('activity_logs', sa.Column('archived_at', sa.DateTime(), nullable=True))
    op.create_index('ix_activity_logs_archived_at', 'activity_logs', ['archived_at'])


def downgrade() -> None:
    op.drop_index('ix_activity_logs_archived_at', table_name='activity_logs')
    op.drop_column('activity_logs', 'archived_at')
