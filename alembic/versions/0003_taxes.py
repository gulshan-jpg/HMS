"""0003_taxes

Revision ID: 0003_taxes
Revises: 0002_rate_plans_and_policies
Create Date: 2026-11-23 12:10:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '0003_taxes'
down_revision: Union[str, None] = '0002_rate_plans_and_policies'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # tax_rates
    op.create_table(
        'tax_rates',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('hotel_id', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('rate', sa.Numeric(precision=5, scale=2), nullable=False, server_default='0.00'),
        sa.Column('fixed_amount', sa.Numeric(precision=10, scale=2), nullable=False, server_default='0.00'),
        sa.Column('applies_to', sa.String(length=30), nullable=False, server_default='rooms'),
        sa.Column('type', sa.String(length=20), nullable=False, server_default='exclusive'),
        sa.Column('per', sa.String(length=30), nullable=False, server_default='night'),
        sa.Column('active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # folio_items columns: subtotal, tax_total, tax_breakdown
    with op.batch_alter_table('folio_items') as batch_op:
        batch_op.add_column(sa.Column('subtotal', sa.Numeric(precision=10, scale=2), nullable=True))
        batch_op.add_column(sa.Column('tax_total', sa.Numeric(precision=10, scale=2), nullable=False, server_default='0.00'))
        batch_op.add_column(sa.Column('tax_breakdown', sa.Text(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('folio_items') as batch_op:
        batch_op.drop_column('tax_breakdown')
        batch_op.drop_column('tax_total')
        batch_op.drop_column('subtotal')
    op.drop_table('tax_rates')
