"""0001_initial

Revision ID: 0001_initial
Revises: 
Create Date: 2026-11-23 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '0001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. users
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('email', sa.String(length=255), nullable=False, unique=True),
        sa.Column('username', sa.String(length=100), nullable=False, unique=True),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('full_name', sa.String(length=255), nullable=False),
        sa.Column('role', sa.String(length=50), nullable=False, server_default='front_desk'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    )

    # 2. room_types
    op.create_table(
        'room_types',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('code', sa.String(length=20), nullable=False, unique=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('base_rate', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('max_occupancy', sa.Integer(), nullable=False, server_default='2'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # 3. rooms
    op.create_table(
        'rooms',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('number', sa.String(length=20), nullable=False, unique=True),
        sa.Column('floor', sa.Integer(), nullable=False),
        sa.Column('room_type_id', sa.Integer(), sa.ForeignKey('room_types.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('status', sa.String(length=30), nullable=False, server_default='available'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # 4. guests
    op.create_table(
        'guests',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('first_name', sa.String(length=100), nullable=False),
        sa.Column('last_name', sa.String(length=100), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False, unique=True),
        sa.Column('phone', sa.String(length=50), nullable=False),
        sa.Column('address', sa.Text(), nullable=True),
        sa.Column('id_number', sa.String(length=100), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    )

    # 5. reservations
    op.create_table(
        'reservations',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('confirmation_number', sa.String(length=30), nullable=False, unique=True),
        sa.Column('guest_id', sa.Integer(), sa.ForeignKey('guests.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('room_id', sa.Integer(), sa.ForeignKey('rooms.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('check_in_date', sa.Date(), nullable=False),
        sa.Column('check_out_date', sa.Date(), nullable=False),
        sa.Column('adults', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('children', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('nightly_rate', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('status', sa.String(length=30), nullable=False, server_default='booked'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    )

    # 6. folio_items
    op.create_table(
        'folio_items',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('reservation_id', sa.Integer(), sa.ForeignKey('reservations.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('description', sa.String(length=255), nullable=False),
        sa.Column('category', sa.String(length=50), nullable=False),
        sa.Column('amount', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # 7. payments
    op.create_table(
        'payments',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('reservation_id', sa.Integer(), sa.ForeignKey('reservations.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('amount', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column('method', sa.String(length=50), nullable=False),
        sa.Column('reference', sa.String(length=100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # 8. housekeeping_tasks
    op.create_table(
        'housekeeping_tasks',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('room_id', sa.Integer(), sa.ForeignKey('rooms.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('task_type', sa.String(length=50), nullable=False),
        sa.Column('status', sa.String(length=30), nullable=False, server_default='pending'),
        sa.Column('priority', sa.String(length=20), nullable=False, server_default='medium'),
        sa.Column('assigned_to', sa.String(length=100), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
    )

    # 9. activity_logs
    op.create_table(
        'activity_logs',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('event_type', sa.String(length=50), nullable=False),
        sa.Column('description', sa.String(length=255), nullable=False),
        sa.Column('actor', sa.String(length=100), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table('activity_logs')
    op.drop_table('housekeeping_tasks')
    op.drop_table('payments')
    op.drop_table('folio_items')
    op.drop_table('reservations')
    op.drop_table('guests')
    op.drop_table('rooms')
    op.drop_table('room_types')
    op.drop_table('users')
