"""voucher archive

Revision ID: k2a8c0d4f6b9
Revises: j1f7b9c3e5a8
Create Date: 2026-11-20 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'k2a8c0d4f6b9'
down_revision: Union[str, Sequence[str], None] = 'j1f7b9c3e5a8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('vouchers', sa.Column('sold_out_at', sa.DateTime(), nullable=True))
    op.add_column('vouchers', sa.Column('archived_at', sa.DateTime(), nullable=True))
    op.create_index('ix_vouchers_archived_at', 'vouchers', ['archived_at'])
    op.execute(
        "UPDATE vouchers SET sold_out_at = updated_at WHERE used_count > 0 AND used_count >= quota_voucher"
    )


def downgrade() -> None:
    op.drop_index('ix_vouchers_archived_at', table_name='vouchers')
    op.drop_column('vouchers', 'archived_at')
    op.drop_column('vouchers', 'sold_out_at')
