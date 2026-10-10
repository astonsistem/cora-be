"""replace asis missing marker with soft delete on customers

Revision ID: g8c4e6f0b2d5
Revises: f7b3d5e9a1c4
Create Date: 2026-10-09 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'g8c4e6f0b2d5'
down_revision: Union[str, Sequence[str], None] = 'f7b3d5e9a1c4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('customers', sa.Column('deleted_at', sa.DateTime(), nullable=True))
    op.create_index(op.f('ix_customers_deleted_at'), 'customers', ['deleted_at'], unique=False)
    op.drop_column('customers', 'asis_missing_at')


def downgrade() -> None:
    op.add_column('customers', sa.Column('asis_missing_at', sa.DateTime(), nullable=True))
    op.drop_index(op.f('ix_customers_deleted_at'), table_name='customers')
    op.drop_column('customers', 'deleted_at')
