"""0005_rate_overrides

Revision ID: 0005_rate_overrides
Revises: 0004_deposits
Create Date: 2026-11-23 12:20:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '0005_rate_overrides'
down_revision: Union[str, None] = '0004_deposits'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'rate_overrides',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('room_type_id', sa.Integer(), sa.ForeignKey('room_types.id', ondelete='CASCADE'), nullable=False),
        sa.Column('date', sa.Date(), nullable=False, index=True),
        sa.Column('rate', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('min_stay', sa.Integer(), nullable=True),
        sa.Column('closed', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('closed_to_arrival', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('closed_to_departure', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint('room_type_id', 'date', name='uq_rate_override_room_type_date'),
    )


def downgrade() -> None:
    op.drop_table('rate_overrides')
