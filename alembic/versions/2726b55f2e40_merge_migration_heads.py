"""merge migration heads

Revision ID: 2726b55f2e40
Revises: 325642fccb82, d5f1b3c7e8a2
Create Date: 2026-10-06 13:26:56.909306

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2726b55f2e40'
down_revision: Union[str, Sequence[str], None] = ('325642fccb82', 'd5f1b3c7e8a2')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
