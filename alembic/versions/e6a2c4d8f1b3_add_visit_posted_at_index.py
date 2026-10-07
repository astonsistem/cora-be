"""add index on customer visits posted_at

Revision ID: e6a2c4d8f1b3
Revises: d5f1b3c7e8a2
Create Date: 2026-10-07 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'e6a2c4d8f1b3'
down_revision: Union[str, Sequence[str], None] = 'd5f1b3c7e8a2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(op.f('ix_customer_visits_posted_at'), 'customer_visits', ['posted_at'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_customer_visits_posted_at'), table_name='customer_visits')
