"""voucher qr flow

Revision ID: j1f7b9c3e5a8
Revises: e0bce3a18c51
Create Date: 2026-11-20 09:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'j1f7b9c3e5a8'
down_revision: Union[str, Sequence[str], None] = 'e0bce3a18c51'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

UUID = postgresql.UUID(as_uuid=True)
TIMESTAMP_NOW = sa.text('now()')


def _create_voucher_qrs() -> None:
    op.create_table(
        'voucher_qrs',
        sa.Column('qr_id', UUID, nullable=False),
        sa.Column('company_id', UUID, nullable=False),
        sa.Column('name', sa.String(length=150), nullable=False),
        sa.Column('branch_id', UUID, nullable=True),
        sa.Column('source_id', UUID, nullable=False),
        sa.Column('category_id', UUID, nullable=True),
        sa.Column('voucher_mode', sa.String(length=20), server_default='single', nullable=False),
        sa.Column('voucher_ids', postgresql.ARRAY(UUID), server_default='{}', nullable=False),
        sa.Column('code', sa.String(length=20), nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column('created_by', UUID, nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=TIMESTAMP_NOW, nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=TIMESTAMP_NOW, nullable=False),
        sa.ForeignKeyConstraint(['company_id'], ['companies.company_id']),
        sa.ForeignKeyConstraint(['branch_id'], ['branches.branch_id']),
        sa.ForeignKeyConstraint(['source_id'], ['sources.source_id']),
        sa.ForeignKeyConstraint(['category_id'], ['category.category_id']),
        sa.ForeignKeyConstraint(['created_by'], ['users.user_id']),
        sa.PrimaryKeyConstraint('qr_id'),
        sa.UniqueConstraint('code', name='voucher_qrs_code_key'),
        sa.CheckConstraint("voucher_mode IN ('single', 'random_one', 'all')", name='ck_voucher_qrs_mode'),
    )
    op.create_index('ix_voucher_qrs_company_id', 'voucher_qrs', ['company_id'])


def _create_visit_questions() -> None:
    op.create_table(
        'visit_questions',
        sa.Column('question_id', UUID, nullable=False),
        sa.Column('company_id', UUID, nullable=False),
        sa.Column('question', sa.String(length=300), nullable=False),
        sa.Column('type', sa.String(length=20), nullable=False),
        sa.Column('answers', postgresql.JSONB(), server_default='[]', nullable=False),
        sa.Column('is_required', sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column('sort_order', sa.Integer(), server_default='0', nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=TIMESTAMP_NOW, nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=TIMESTAMP_NOW, nullable=False),
        sa.ForeignKeyConstraint(['company_id'], ['companies.company_id']),
        sa.PrimaryKeyConstraint('question_id'),
        sa.CheckConstraint("type IN ('rating', 'text', 'choice')", name='ck_visit_questions_type'),
    )
    op.create_index('ix_visit_questions_company_id', 'visit_questions', ['company_id'])


def _upgrade_vouchers() -> None:
    op.add_column('vouchers', sa.Column('company_id', UUID, nullable=True))
    op.add_column('vouchers', sa.Column('code', sa.String(length=40), nullable=True))
    op.add_column('vouchers', sa.Column('status', sa.String(length=20), server_default='active', nullable=False))
    op.add_column('vouchers', sa.Column('branch_ids', postgresql.ARRAY(UUID), nullable=True))
    op.add_column('vouchers', sa.Column('qr_slug', sa.String(length=40), nullable=True))
    op.add_column('vouchers', sa.Column('qr_target_id', UUID, nullable=True))
    op.add_column('vouchers', sa.Column('design', postgresql.JSONB(), nullable=True))

    op.execute(
        """
        UPDATE vouchers v
        SET company_id = b.company_id,
            branch_ids = ARRAY[v.branch_id],
            code = 'VCH-' || upper(substr(md5(v.voucher_id::text), 1, 8)),
            status = CASE WHEN v.is_active THEN 'active' ELSE 'inactive' END
        FROM branches b
        WHERE b.branch_id = v.branch_id
        """
    )
    op.execute(
        """
        WITH ranked AS (
            SELECT voucher_id,
                   row_number() OVER (PARTITION BY company_id, name ORDER BY created_at, voucher_id) AS rn
            FROM vouchers
        )
        UPDATE vouchers v
        SET name = v.name || ' (' || ranked.rn || ')'
        FROM ranked
        WHERE ranked.voucher_id = v.voucher_id AND ranked.rn > 1
        """
    )

    op.drop_constraint('ck_vouchers_quota', 'vouchers', type_='check')
    op.drop_constraint('ck_vouchers_used_count', 'vouchers', type_='check')
    op.drop_constraint('ck_vouchers_valid_range', 'vouchers', type_='check')
    op.drop_constraint('uq_vouchers_branch_name', 'vouchers', type_='unique')
    op.drop_index('ix_vouchers_branch_active', table_name='vouchers')

    op.alter_column('vouchers', 'name', new_column_name='voucher_name')
    op.alter_column('vouchers', 'quota', new_column_name='quota_voucher')
    op.alter_column('vouchers', 'valid_from', new_column_name='date_started')
    op.alter_column('vouchers', 'valid_until', new_column_name='date_expired')

    op.execute("UPDATE vouchers SET date_started = COALESCE(date_started, created_at::date)")
    op.execute("UPDATE vouchers SET date_expired = COALESCE(date_expired, date_started + 365)")

    op.alter_column('vouchers', 'company_id', nullable=False)
    op.alter_column('vouchers', 'code', nullable=False)
    op.alter_column('vouchers', 'date_started', nullable=False)
    op.alter_column('vouchers', 'date_expired', nullable=False)

    op.drop_constraint('vouchers_branch_id_fkey', 'vouchers', type_='foreignkey')
    op.drop_column('vouchers', 'branch_id')
    op.drop_column('vouchers', 'is_active')

    op.create_foreign_key('vouchers_company_id_fkey', 'vouchers', 'companies', ['company_id'], ['company_id'])
    op.create_foreign_key('vouchers_qr_target_id_fkey', 'vouchers', 'voucher_qrs', ['qr_target_id'], ['qr_id'])
    op.create_unique_constraint('vouchers_code_key', 'vouchers', ['code'])
    op.create_unique_constraint('vouchers_qr_slug_key', 'vouchers', ['qr_slug'])
    op.create_unique_constraint('uq_vouchers_company_name', 'vouchers', ['company_id', 'voucher_name'])
    op.create_check_constraint('ck_vouchers_quota', 'vouchers', 'quota_voucher >= 0')
    op.create_check_constraint(
        'ck_vouchers_used_count', 'vouchers', 'used_count >= 0 AND used_count <= quota_voucher'
    )
    op.create_check_constraint('ck_vouchers_date_range', 'vouchers', 'date_expired >= date_started')
    op.create_check_constraint('ck_vouchers_status', 'vouchers', "status IN ('active', 'inactive')")
    op.create_index('ix_vouchers_company_status', 'vouchers', ['company_id', 'status'])


def _upgrade_customer_visits() -> None:
    op.add_column('customer_visits', sa.Column('qr_id', UUID, nullable=True))
    op.add_column('customer_visits', sa.Column('meta', postgresql.JSONB(), server_default='{}', nullable=False))
    op.add_column('customer_visits', sa.Column('claim_token', sa.String(length=64), nullable=True))
    op.add_column('customer_visits', sa.Column('claim_expires_at', sa.DateTime(), nullable=True))
    op.create_foreign_key('customer_visits_qr_id_fkey', 'customer_visits', 'voucher_qrs', ['qr_id'], ['qr_id'])
    op.create_unique_constraint('customer_visits_claim_token_key', 'customer_visits', ['claim_token'])
    op.create_index('ix_customer_visits_qr_id', 'customer_visits', ['qr_id'])


def _create_voucher_codes() -> None:
    op.create_table(
        'voucher_codes',
        sa.Column('code_id', UUID, nullable=False),
        sa.Column('code', sa.String(length=20), nullable=False),
        sa.Column('voucher_id', UUID, nullable=False),
        sa.Column('visit_id', UUID, nullable=False),
        sa.Column('customer_id', UUID, nullable=True),
        sa.Column('issued_at', sa.DateTime(), server_default=TIMESTAMP_NOW, nullable=False),
        sa.ForeignKeyConstraint(['voucher_id'], ['vouchers.voucher_id']),
        sa.ForeignKeyConstraint(['visit_id'], ['customer_visits.visit_id']),
        sa.ForeignKeyConstraint(['customer_id'], ['customers.customer_id']),
        sa.PrimaryKeyConstraint('code_id'),
        sa.UniqueConstraint('code', name='voucher_codes_code_key'),
        sa.UniqueConstraint('voucher_id', 'visit_id', name='uq_voucher_codes_voucher_visit'),
    )
    op.create_index('ix_voucher_codes_voucher_id', 'voucher_codes', ['voucher_id'])
    op.create_index('ix_voucher_codes_visit_id', 'voucher_codes', ['visit_id'])
    op.create_index('ix_voucher_codes_customer_id', 'voucher_codes', ['customer_id'])


def _create_voucher_claims() -> None:
    op.create_table(
        'voucher_claims',
        sa.Column('claim_id', UUID, nullable=False),
        sa.Column('code_id', UUID, nullable=False),
        sa.Column('branch_id', UUID, nullable=False),
        sa.Column('status', sa.String(length=20), server_default='CLAIMED', nullable=False),
        sa.Column('claimed_via', sa.String(length=20), server_default='customer', nullable=False),
        sa.Column('flag_reason', sa.String(length=40), nullable=True),
        sa.Column('claimed_at', sa.DateTime(), server_default=TIMESTAMP_NOW, nullable=False),
        sa.Column('redeemed_at', sa.DateTime(), nullable=True),
        sa.Column('redeemed_by', UUID, nullable=True),
        sa.Column('cancelled_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['code_id'], ['voucher_codes.code_id']),
        sa.ForeignKeyConstraint(['branch_id'], ['branches.branch_id']),
        sa.ForeignKeyConstraint(['redeemed_by'], ['users.user_id']),
        sa.PrimaryKeyConstraint('claim_id'),
        sa.CheckConstraint("status IN ('CLAIMED', 'REDEEMED', 'CANCELLED')", name='ck_voucher_claims_status'),
        sa.CheckConstraint("claimed_via IN ('customer', 'staff')", name='ck_voucher_claims_via'),
    )
    op.create_index('ix_voucher_claims_code_id', 'voucher_claims', ['code_id'])
    op.create_index('ix_voucher_claims_branch_id', 'voucher_claims', ['branch_id'])
    op.create_index(
        'uq_voucher_claims_active_code',
        'voucher_claims',
        ['code_id'],
        unique=True,
        postgresql_where=sa.text("status <> 'CANCELLED'"),
    )


def upgrade() -> None:
    _create_voucher_qrs()
    _create_visit_questions()
    _upgrade_vouchers()
    _upgrade_customer_visits()
    _create_voucher_codes()
    _create_voucher_claims()

    op.drop_index('ix_voucher_redemptions_voucher', table_name='voucher_redemptions')
    op.drop_table('voucher_redemptions')


def _restore_voucher_redemptions() -> None:
    op.create_table(
        'voucher_redemptions',
        sa.Column('redemption_id', UUID, nullable=False),
        sa.Column('voucher_id', UUID, nullable=False),
        sa.Column('customer_id', UUID, nullable=True),
        sa.Column('full_name', sa.String(length=150), nullable=False),
        sa.Column('phone', sa.String(length=30), nullable=False),
        sa.Column('phone_norm', sa.String(length=20), nullable=False),
        sa.Column('status', sa.String(length=20), server_default='pending', nullable=False),
        sa.Column('submitted_at', sa.DateTime(), server_default=TIMESTAMP_NOW, nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=TIMESTAMP_NOW, nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=TIMESTAMP_NOW, nullable=False),
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


def _downgrade_vouchers() -> None:
    op.drop_index('ix_vouchers_company_status', table_name='vouchers')
    for name in ('ck_vouchers_status', 'ck_vouchers_date_range', 'ck_vouchers_used_count', 'ck_vouchers_quota'):
        op.drop_constraint(name, 'vouchers', type_='check')
    for name in ('uq_vouchers_company_name', 'vouchers_qr_slug_key', 'vouchers_code_key'):
        op.drop_constraint(name, 'vouchers', type_='unique')
    op.drop_constraint('vouchers_qr_target_id_fkey', 'vouchers', type_='foreignkey')
    op.drop_constraint('vouchers_company_id_fkey', 'vouchers', type_='foreignkey')

    op.add_column('vouchers', sa.Column('branch_id', UUID, nullable=True))
    op.add_column('vouchers', sa.Column('is_active', sa.Boolean(), server_default=sa.true(), nullable=False))
    op.execute(
        """
        UPDATE vouchers v
        SET branch_id = COALESCE(
                v.branch_ids[1],
                (SELECT b.branch_id FROM branches b WHERE b.company_id = v.company_id ORDER BY b.branch_name LIMIT 1)
            ),
            is_active = (v.status = 'active')
        """
    )
    op.alter_column('vouchers', 'branch_id', nullable=False)
    op.create_foreign_key('vouchers_branch_id_fkey', 'vouchers', 'branches', ['branch_id'], ['branch_id'])

    op.alter_column('vouchers', 'date_expired', new_column_name='valid_until')
    op.alter_column('vouchers', 'date_started', new_column_name='valid_from')
    op.alter_column('vouchers', 'quota_voucher', new_column_name='quota')
    op.alter_column('vouchers', 'voucher_name', new_column_name='name')
    op.alter_column('vouchers', 'valid_from', nullable=True)
    op.alter_column('vouchers', 'valid_until', nullable=True)

    for column in ('design', 'qr_target_id', 'qr_slug', 'branch_ids', 'status', 'code', 'company_id'):
        op.drop_column('vouchers', column)

    op.create_unique_constraint('uq_vouchers_branch_name', 'vouchers', ['branch_id', 'name'])
    op.create_check_constraint('ck_vouchers_quota', 'vouchers', 'quota >= 0')
    op.create_check_constraint('ck_vouchers_used_count', 'vouchers', 'used_count >= 0 AND used_count <= quota')
    op.create_check_constraint(
        'ck_vouchers_valid_range',
        'vouchers',
        'valid_from IS NULL OR valid_until IS NULL OR valid_until >= valid_from',
    )
    op.create_index('ix_vouchers_branch_active', 'vouchers', ['branch_id', 'is_active'])


def downgrade() -> None:
    _restore_voucher_redemptions()

    op.drop_index('uq_voucher_claims_active_code', table_name='voucher_claims')
    op.drop_table('voucher_claims')
    op.drop_table('voucher_codes')

    op.drop_index('ix_customer_visits_qr_id', table_name='customer_visits')
    op.drop_constraint('customer_visits_claim_token_key', 'customer_visits', type_='unique')
    op.drop_constraint('customer_visits_qr_id_fkey', 'customer_visits', type_='foreignkey')
    for column in ('claim_expires_at', 'claim_token', 'meta', 'qr_id'):
        op.drop_column('customer_visits', column)

    _downgrade_vouchers()

    op.drop_table('visit_questions')
    op.drop_table('voucher_qrs')
