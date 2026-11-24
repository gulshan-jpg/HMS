"""0002_rate_plans_and_policies

Revision ID: 0002_rate_plans_and_policies
Revises: 0001_initial
Create Date: 2026-11-23 12:05:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '0002_rate_plans_and_policies'
down_revision: Union[str, None] = '0001_initial'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # cancellation_policies
    op.create_table(
        'cancellation_policies',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('free_cancel_days', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('penalty_type', sa.String(length=30), nullable=False, server_default='first_night'),
        sa.Column('penalty_value', sa.Numeric(precision=10, scale=2), nullable=False, server_default='0.00'),
        sa.Column('no_show_penalty', sa.String(length=30), nullable=False, server_default='first_night'),
        sa.Column('no_show_value', sa.Numeric(precision=10, scale=2), nullable=False, server_default='0.00'),
        sa.Column('active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # rate_plans
    op.create_table(
        'rate_plans',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('hotel_id', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('code', sa.String(length=20), nullable=False, unique=True, index=True),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('room_type_id', sa.Integer(), sa.ForeignKey('room_types.id', ondelete='SET NULL'), nullable=True),
        sa.Column('modifier_type', sa.String(length=20), nullable=False, server_default='percent'),
        sa.Column('modifier_value', sa.Numeric(precision=10, scale=2), nullable=False, server_default='0.00'),
        sa.Column('meal_plan', sa.String(length=30), nullable=False, server_default='room_only'),
        sa.Column('min_stay', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('max_stay', sa.Integer(), nullable=True),
        sa.Column('cancellation_policy_id', sa.Integer(), sa.ForeignKey('cancellation_policies.id', ondelete='SET NULL'), nullable=True),
        sa.Column('refundable', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('valid_from', sa.Date(), nullable=True),
        sa.Column('valid_to', sa.Date(), nullable=True),
        sa.Column('closed_to_arrival', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('closed_to_departure', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('requires_deposit', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('deposit_percent', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('deposit_fixed_amount', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table('rate_plans')
    op.drop_table('cancellation_policies')
