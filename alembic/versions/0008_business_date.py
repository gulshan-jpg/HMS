"""0008_business_date

Revision ID: 0008_business_date
Revises: 0007_groups
Create Date: 2026-11-23 12:35:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '0008_business_date'
down_revision: Union[str, None] = '0007_groups'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # business_dates
    op.create_table(
        'business_dates',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('hotel_id', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('date', sa.Date(), nullable=False, index=True),
        sa.Column('closed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('closed_by_user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='open'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # daily_snapshots
    op.create_table(
        'daily_snapshots',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('hotel_id', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('business_date', sa.Date(), nullable=False, index=True),
        sa.Column('occupancy_rate', sa.Numeric(precision=5, scale=2), nullable=False, server_default='0.00'),
        sa.Column('adr', sa.Numeric(precision=10, scale=2), nullable=False, server_default='0.00'),
        sa.Column('revpar', sa.Numeric(precision=10, scale=2), nullable=False, server_default='0.00'),
        sa.Column('arrivals', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('departures', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('room_revenue', sa.Numeric(precision=10, scale=2), nullable=False, server_default='0.00'),
        sa.Column('total_revenue', sa.Numeric(precision=10, scale=2), nullable=False, server_default='0.00'),
        sa.Column('tax_collected', sa.Numeric(precision=10, scale=2), nullable=False, server_default='0.00'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # webhook_events (for Stripe idempotency)
    op.create_table(
        'webhook_events',
        sa.Column('id', sa.String(length=100), primary_key=True),
        sa.Column('event_type', sa.String(length=100), nullable=False),
        sa.Column('processed_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table('webhook_events')
    op.drop_table('daily_snapshots')
    op.drop_table('business_dates')
