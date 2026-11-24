"""activity logs

Revision ID: p7f3b5c9e1a4
Revises: o6e2a4b8d0f3
Create Date: 2026-11-24 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'p7f3b5c9e1a4'
down_revision: Union[str, Sequence[str], None] = 'o6e2a4b8d0f3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'activity_logs',
        sa.Column('log_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('user_name', sa.String(), nullable=False),
        sa.Column('user_role', sa.String(), nullable=False),
        sa.Column('action', sa.String(length=20), nullable=False),
        sa.Column('module', sa.String(length=30), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('company_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('branch_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('ip_address', sa.String(length=64), nullable=True),
        sa.Column('user_agent', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.user_id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['company_id'], ['companies.company_id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['branch_id'], ['branches.branch_id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('log_id'),
    )
    op.create_index('ix_activity_logs_created_at', 'activity_logs', ['created_at'])
    op.create_index('ix_activity_logs_company_created', 'activity_logs', ['company_id', 'created_at'])


def downgrade() -> None:
    op.drop_index('ix_activity_logs_company_created', table_name='activity_logs')
    op.drop_index('ix_activity_logs_created_at', table_name='activity_logs')
    op.drop_table('activity_logs')
