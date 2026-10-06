"""add asis partner id to customer visits

Revision ID: c4e8a1b2d9f5
Revises: b7d2e9f10a34
Create Date: 2026-10-06 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c4e8a1b2d9f5'
down_revision: Union[str, Sequence[str], None] = 'b7d2e9f10a34'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('customer_visits', sa.Column('asis_partner_id', sa.String(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('customer_visits', 'asis_partner_id')
