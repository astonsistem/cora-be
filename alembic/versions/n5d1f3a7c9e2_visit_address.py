"""visit address

Revision ID: n5d1f3a7c9e2
Revises: m4c0e2f6b8d1
Create Date: 2026-11-21 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'n5d1f3a7c9e2'
down_revision: Union[str, Sequence[str], None] = 'm4c0e2f6b8d1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('customer_visits', sa.Column('address', sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column('customer_visits', 'address')
