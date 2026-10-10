"""add asis missing marker to customers

Revision ID: f7b3d5e9a1c4
Revises: e6a2c4d8f1b3
Create Date: 2026-10-09 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f7b3d5e9a1c4'
down_revision: Union[str, Sequence[str], None] = 'e6a2c4d8f1b3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('customers', sa.Column('asis_missing_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column('customers', 'asis_missing_at')
