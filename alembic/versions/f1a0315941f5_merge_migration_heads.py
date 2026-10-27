"""merge migration heads

Revision ID: f1a0315941f5
Revises: 2726b55f2e40, e6a2c4d8f1b3
Create Date: 2026-10-07 15:29:29.821699

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f1a0315941f5'
down_revision: Union[str, Sequence[str], None] = ('2726b55f2e40', 'e6a2c4d8f1b3')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
