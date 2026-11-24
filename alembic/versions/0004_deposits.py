"""0004_deposits

Revision ID: 0004_deposits
Revises: 0003_taxes
Create Date: 2026-11-23 12:15:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '0004_deposits'
down_revision: Union[str, None] = '0003_taxes'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('reservations') as batch_op:
        batch_op.add_column(sa.Column('rate_plan_id', sa.Integer(), sa.ForeignKey('rate_plans.id', ondelete='SET NULL'), nullable=True))
        batch_op.add_column(sa.Column('deposit_required', sa.Numeric(precision=10, scale=2), nullable=False, server_default='0.00'))
        batch_op.add_column(sa.Column('deposit_paid', sa.Numeric(precision=10, scale=2), nullable=False, server_default='0.00'))
        batch_op.add_column(sa.Column('deposit_due_at', sa.Date(), nullable=True))

    with op.batch_alter_table('payments') as batch_op:
        batch_op.add_column(sa.Column('is_deposit', sa.Boolean(), nullable=False, server_default=sa.false()))
        batch_op.add_column(sa.Column('is_refund', sa.Boolean(), nullable=False, server_default=sa.false()))
        batch_op.add_column(sa.Column('stripe_payment_intent_id', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('stripe_charge_id', sa.String(length=100), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('payments') as batch_op:
        batch_op.drop_column('stripe_charge_id')
        batch_op.drop_column('stripe_payment_intent_id')
        batch_op.drop_column('is_refund')
        batch_op.drop_column('is_deposit')

    with op.batch_alter_table('reservations') as batch_op:
        batch_op.drop_column('deposit_due_at')
        batch_op.drop_column('deposit_paid')
        batch_op.drop_column('deposit_required')
        batch_op.drop_column('rate_plan_id')
