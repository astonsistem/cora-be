"""category per company

Revision ID: m4c0e2f6b8d1
Revises: l3b9d1e5a7c0
Create Date: 2026-11-20 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'm4c0e2f6b8d1'
down_revision: Union[str, Sequence[str], None] = 'l3b9d1e5a7c0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('category', sa.Column('company_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key('fk_category_company_id', 'category', 'companies', ['company_id'], ['company_id'])
    op.create_index('ix_category_company_id', 'category', ['company_id'])
    op.drop_constraint('uq_category_asis_category_id', 'category', type_='unique')
    op.create_unique_constraint('uq_category_company_asis', 'category', ['company_id', 'asis_category_id'])


def downgrade() -> None:
    op.drop_constraint('uq_category_company_asis', 'category', type_='unique')
    op.create_unique_constraint('uq_category_asis_category_id', 'category', ['asis_category_id'])
    op.drop_index('ix_category_company_id', table_name='category')
    op.drop_constraint('fk_category_company_id', 'category', type_='foreignkey')
    op.drop_column('category', 'company_id')
