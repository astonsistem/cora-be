"""asis credential per branch

Revision ID: o6e2a4b8d0f3
Revises: n5d1f3a7c9e2
Create Date: 2026-11-24 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'o6e2a4b8d0f3'
down_revision: Union[str, Sequence[str], None] = 'n5d1f3a7c9e2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('asis_credentials', sa.Column('branch_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key('fk_asis_credentials_branch_id', 'asis_credentials', 'branches', ['branch_id'], ['branch_id'])
    op.drop_constraint('uq_asis_credentials_company_id', 'asis_credentials', type_='unique')
    op.create_index(
        'uq_asis_credentials_company', 'asis_credentials', ['company_id'],
        unique=True, postgresql_where=sa.text('branch_id IS NULL'),
    )
    op.create_index('uq_asis_credentials_branch', 'asis_credentials', ['branch_id'], unique=True)


def downgrade() -> None:
    op.execute('DELETE FROM asis_credentials WHERE branch_id IS NOT NULL')
    op.drop_index('uq_asis_credentials_branch', table_name='asis_credentials')
    op.drop_index('uq_asis_credentials_company', table_name='asis_credentials')
    op.create_unique_constraint('uq_asis_credentials_company_id', 'asis_credentials', ['company_id'])
    op.drop_constraint('fk_asis_credentials_branch_id', 'asis_credentials', type_='foreignkey')
    op.drop_column('asis_credentials', 'branch_id')
