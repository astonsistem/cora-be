"""add deleted_at to category sources companies branches

Revision ID: d9b864a277bd
Revises: 18bf771376f6
Create Date: 2026-11-12 11:02:49.295476

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd9b864a277bd'
down_revision: Union[str, Sequence[str], None] = '18bf771376f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLES = ("category", "sources", "companies", "branches")


def upgrade() -> None:
    for table in TABLES:
        op.add_column(table, sa.Column("deleted_at", sa.DateTime(), nullable=True))
        op.create_index(f"ix_{table}_deleted_at", table, ["deleted_at"])


def downgrade() -> None:
    for table in TABLES:
        op.drop_index(f"ix_{table}_deleted_at", table_name=table)
        op.drop_column(table, "deleted_at")