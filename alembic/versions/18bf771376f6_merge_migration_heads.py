"""merge migration heads

Revision ID: 18bf771376f6
Revises: f1a0315941f5, g8c4e6f0b2d5
Create Date: 2026-10-10 10:30:56.670212

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '18bf771376f6'
down_revision: Union[str, Sequence[str], None] = ('f1a0315941f5', 'g8c4e6f0b2d5')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
