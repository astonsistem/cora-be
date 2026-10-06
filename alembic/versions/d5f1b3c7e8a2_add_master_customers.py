"""add master customers

Revision ID: d5f1b3c7e8a2
Revises: c4e8a1b2d9f5
Create Date: 2026-10-07 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd5f1b3c7e8a2'
down_revision: Union[str, Sequence[str], None] = 'c4e8a1b2d9f5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('customers',
    sa.Column('customer_id', sa.UUID(), nullable=False),
    sa.Column('asis_partner_id', sa.String(), nullable=True),
    sa.Column('name', sa.String(), nullable=False),
    sa.Column('name_search', sa.String(), nullable=False),
    sa.Column('phone', sa.String(), nullable=True),
    sa.Column('phone_norm', sa.String(), nullable=True),
    sa.Column('email', sa.String(), nullable=True),
    sa.Column('branch_id', sa.UUID(), nullable=False),
    sa.Column('category_id', sa.UUID(), nullable=True),
    sa.Column('created_by', sa.UUID(), nullable=True),
    sa.Column('posted_at', sa.DateTime(), nullable=True),
    sa.Column('last_synced_at', sa.DateTime(), nullable=True),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['branch_id'], ['branches.branch_id'], ),
    sa.ForeignKeyConstraint(['category_id'], ['category.category_id'], ),
    sa.ForeignKeyConstraint(['created_by'], ['users.user_id'], ),
    sa.PrimaryKeyConstraint('customer_id'),
    sa.UniqueConstraint('asis_partner_id')
    )
    op.create_index(op.f('ix_customers_customer_id'), 'customers', ['customer_id'], unique=False)
    op.create_index(op.f('ix_customers_name_search'), 'customers', ['name_search'], unique=False)
    op.create_index(op.f('ix_customers_phone_norm'), 'customers', ['phone_norm'], unique=False)
    op.create_index(op.f('ix_customers_branch_id'), 'customers', ['branch_id'], unique=False)

    op.add_column('customer_visits', sa.Column('customer_id', sa.UUID(), nullable=True))
    op.create_foreign_key('fk_customer_visits_customer_id', 'customer_visits', 'customers', ['customer_id'], ['customer_id'])
    op.create_index(op.f('ix_customer_visits_customer_id'), 'customer_visits', ['customer_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_customer_visits_customer_id'), table_name='customer_visits')
    op.drop_constraint('fk_customer_visits_customer_id', 'customer_visits', type_='foreignkey')
    op.drop_column('customer_visits', 'customer_id')
    op.drop_index(op.f('ix_customers_branch_id'), table_name='customers')
    op.drop_index(op.f('ix_customers_phone_norm'), table_name='customers')
    op.drop_index(op.f('ix_customers_name_search'), table_name='customers')
    op.drop_index(op.f('ix_customers_customer_id'), table_name='customers')
    op.drop_table('customers')
