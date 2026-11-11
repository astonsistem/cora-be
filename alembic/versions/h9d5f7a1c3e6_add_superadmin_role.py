"""add superadmin role

Revision ID: h9d5f7a1c3e6
Revises: 18bf771376f6
Create Date: 2026-11-10 09:00:00.000000

"""
from typing import Sequence, Union

from alembic import op

revision: str = 'h9d5f7a1c3e6'
down_revision: Union[str, Sequence[str], None] = '18bf771376f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE user_role ADD VALUE IF NOT EXISTS 'superadmin'")


def downgrade() -> None:
    op.execute("UPDATE users SET user_role = 'operasional_manager' WHERE user_role = 'superadmin'")
