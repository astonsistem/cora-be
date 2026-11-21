"""asis credentials

Revision ID: l3b9d1e5a7c0
Revises: k2a8c0d4f6b9
Create Date: 2026-11-20 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'l3b9d1e5a7c0'
down_revision: Union[str, Sequence[str], None] = 'k2a8c0d4f6b9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'asis_credentials',
        sa.Column('credential_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('company_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('username', sa.String(length=150), nullable=False),
        sa.Column('password_encrypted', sa.String(), nullable=False),
        sa.Column('last_verified_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['company_id'], ['companies.company_id']),
        sa.ForeignKeyConstraint(['created_by'], ['users.user_id']),
        sa.PrimaryKeyConstraint('credential_id'),
        sa.UniqueConstraint('company_id', name='uq_asis_credentials_company_id'),
    )


def downgrade() -> None:
    op.drop_table('asis_credentials')
