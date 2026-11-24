"""0017_multi_tenant_unique_indexes

Revision ID: 0017_multi_tenant_unique_indexes
Revises: 0016_user_org_memberships
Create Date: 2026-11-23 20:45:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '0017_multi_tenant_unique_indexes'
down_revision: Union[str, None] = '0016_user_org_memberships'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # 1. Rooms index
    room_indexes = {idx['name']: idx for idx in inspector.get_indexes('rooms')}
    if 'ix_rooms_number' in room_indexes and room_indexes['ix_rooms_number'].get('unique'):
        op.drop_index('ix_rooms_number', table_name='rooms')
        op.create_index('ix_rooms_number', 'rooms', ['number'], unique=False)
    if 'uq_rooms_org_number' not in room_indexes:
        op.create_index('uq_rooms_org_number', 'rooms', ['organization_id', 'number'], unique=True)

    # 2. Guests email index
    guest_indexes = {idx['name']: idx for idx in inspector.get_indexes('guests')}
    if 'ix_guests_email' in guest_indexes and guest_indexes['ix_guests_email'].get('unique'):
        op.drop_index('ix_guests_email', table_name='guests')
        op.create_index('ix_guests_email', 'guests', ['email'], unique=False)
    if 'uq_guests_org_email' not in guest_indexes:
        op.create_index('uq_guests_org_email', 'guests', ['organization_id', 'email'], unique=False)

    # 3. Rate plans code index
    rate_plan_indexes = {idx['name']: idx for idx in inspector.get_indexes('rate_plans')}
    if 'ix_rate_plans_code' in rate_plan_indexes and rate_plan_indexes['ix_rate_plans_code'].get('unique'):
        op.drop_index('ix_rate_plans_code', table_name='rate_plans')
        op.create_index('ix_rate_plans_code', 'rate_plans', ['code'], unique=False)
    if 'uq_rate_plans_org_code' not in rate_plan_indexes:
        op.create_index('uq_rate_plans_org_code', 'rate_plans', ['organization_id', 'code'], unique=True)


def downgrade() -> None:
    pass
