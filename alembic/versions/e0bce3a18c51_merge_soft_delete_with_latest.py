"""merge soft delete with latest

Revision ID: e0bce3a18c51
Revises: d9b864a277bd, i0e6a8b2d4f7
Create Date: 2026-11-12 13:42:05.994788

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e0bce3a18c51'
down_revision: Union[str, Sequence[str], None] = ('d9b864a277bd', 'i0e6a8b2d4f7')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
