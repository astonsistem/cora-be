"""add asis category id

Revision ID: b7d2e9f10a34
Revises: a3f1c2d4e5b6
Create Date: 2026-10-05 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b7d2e9f10a34'
down_revision: Union[str, Sequence[str], None] = 'a3f1c2d4e5b6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('category', sa.Column('asis_category_id', sa.String(), nullable=True))
    op.create_unique_constraint('uq_category_asis_category_id', 'category', ['asis_category_id'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('uq_category_asis_category_id', 'category', type_='unique')
    op.drop_column('category', 'asis_category_id')
