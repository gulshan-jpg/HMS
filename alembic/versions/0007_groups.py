"""0007_groups

Revision ID: 0007_groups
Revises: 0006_folios
Create Date: 2026-11-23 12:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '0007_groups'
down_revision: Union[str, None] = '0006_folios'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # booking_groups
    op.create_table(
        'booking_groups',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('hotel_id', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('name', sa.String(length=150), nullable=False),
        sa.Column('contact_name', sa.String(length=100), nullable=False),
        sa.Column('contact_email', sa.String(length=255), nullable=False),
        sa.Column('contact_phone', sa.String(length=50), nullable=False),
        sa.Column('check_in', sa.Date(), nullable=False),
        sa.Column('check_out', sa.Date(), nullable=False),
        sa.Column('cutoff_date', sa.Date(), nullable=False),
        sa.Column('status', sa.String(length=30), nullable=False, server_default='tentative'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # group_blocks
    op.create_table(
        'group_blocks',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('group_id', sa.Integer(), sa.ForeignKey('booking_groups.id', ondelete='CASCADE'), nullable=False),
        sa.Column('room_type_id', sa.Integer(), sa.ForeignKey('room_types.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('count', sa.Integer(), nullable=False),
        sa.Column('rate', sa.Numeric(precision=10, scale=2), nullable=False),
    )

    # reservations: group_id, is_group_master
    with op.batch_alter_table('reservations') as batch_op:
        batch_op.add_column(sa.Column('group_id', sa.Integer(), sa.ForeignKey('booking_groups.id', ondelete='SET NULL'), nullable=True))
        batch_op.add_column(sa.Column('is_group_master', sa.Boolean(), nullable=False, server_default=sa.false()))


def downgrade() -> None:
    with op.batch_alter_table('reservations') as batch_op:
        batch_op.drop_column('is_group_master')
        batch_op.drop_column('group_id')
    op.drop_table('group_blocks')
    op.drop_table('booking_groups')
