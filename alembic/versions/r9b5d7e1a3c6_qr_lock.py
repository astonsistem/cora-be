"""qr lock

Revision ID: r9b5d7e1a3c6
Revises: q8a4c6d0f2b5
Create Date: 2026-11-25 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'r9b5d7e1a3c6'
down_revision: Union[str, Sequence[str], None] = 'q8a4c6d0f2b5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('voucher_qrs', sa.Column('is_locked', sa.Boolean(), server_default='false', nullable=False))


def downgrade() -> None:
    op.drop_column('voucher_qrs', 'is_locked')
