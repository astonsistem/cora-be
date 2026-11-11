"""add vouchers

Revision ID: i0e6a8b2d4f7
Revises: h9d5f7a1c3e6
Create Date: 2026-11-10 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'i0e6a8b2d4f7'
down_revision: Union[str, Sequence[str], None] = 'h9d5f7a1c3e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_table(name: str) -> bool:
    return sa.inspect(op.get_bind()).has_table(name)


def upgrade() -> None:
    if not _has_table('vouchers'):
        op.create_table(
            'vouchers',
            sa.Column('voucher_id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('branch_id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('name', sa.String(length=150), nullable=False),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('quota', sa.Integer(), nullable=False),
            sa.Column('used_count', sa.Integer(), server_default='0', nullable=False),
            sa.Column('valid_from', sa.Date(), nullable=True),
            sa.Column('valid_until', sa.Date(), nullable=True),
            sa.Column('is_active', sa.Boolean(), server_default=sa.true(), nullable=False),
            sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
            sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
            sa.ForeignKeyConstraint(['branch_id'], ['branches.branch_id']),
            sa.ForeignKeyConstraint(['created_by'], ['users.user_id']),
            sa.PrimaryKeyConstraint('voucher_id'),
            sa.UniqueConstraint('branch_id', 'name', name='uq_vouchers_branch_name'),
            sa.CheckConstraint('quota >= 0', name='ck_vouchers_quota'),
            sa.CheckConstraint('used_count >= 0 AND used_count <= quota', name='ck_vouchers_used_count'),
            sa.CheckConstraint(
                'valid_from IS NULL OR valid_until IS NULL OR valid_until >= valid_from',
                name='ck_vouchers_valid_range',
            ),
        )
        op.create_index('ix_vouchers_branch_active', 'vouchers', ['branch_id', 'is_active'])

    if not _has_table('voucher_redemptions'):
        op.create_table(
            'voucher_redemptions',
            sa.Column('redemption_id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('voucher_id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('customer_id', postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column('full_name', sa.String(length=150), nullable=False),
            sa.Column('phone', sa.String(length=30), nullable=False),
            sa.Column('phone_norm', sa.String(length=20), nullable=False),
            sa.Column('status', sa.String(length=20), server_default='pending', nullable=False),
            sa.Column('submitted_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
            sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
            sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
            sa.ForeignKeyConstraint(['voucher_id'], ['vouchers.voucher_id']),
            sa.ForeignKeyConstraint(['customer_id'], ['customers.customer_id']),
            sa.PrimaryKeyConstraint('redemption_id'),
            sa.UniqueConstraint('phone_norm', name='uq_voucher_redemptions_phone_norm'),
            sa.CheckConstraint(
                "status IN ('pending', 'redeemed', 'cancelled')",
                name='ck_voucher_redemptions_status',
            ),
        )
        op.create_index('ix_voucher_redemptions_voucher', 'voucher_redemptions', ['voucher_id'])


def downgrade() -> None:
    op.drop_index('ix_voucher_redemptions_voucher', table_name='voucher_redemptions')
    op.drop_table('voucher_redemptions')
    op.drop_index('ix_vouchers_branch_active', table_name='vouchers')
    op.drop_table('vouchers')
