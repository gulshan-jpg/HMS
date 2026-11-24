"""0009_organizations

Revision ID: 0009_organizations
Revises: 0008_business_date
Create Date: 2026-11-23 14:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '0009_organizations'
down_revision: Union[str, None] = '0008_business_date'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = inspector.get_table_names()

    # 1. Create organizations table if not exists
    if 'organizations' not in existing_tables:
        op.create_table(
            'organizations',
            sa.Column('id', sa.Integer(), primary_key=True, index=True),
            sa.Column('name', sa.String(length=150), nullable=False),
            sa.Column('slug', sa.String(length=100), unique=True, index=True, nullable=False),
            sa.Column('owner_user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
            sa.Column('plan', sa.String(length=50), nullable=False, server_default='starter'),
            sa.Column('trial_ends_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('subscription_status', sa.String(length=50), nullable=False, server_default='trialing'),
            sa.Column('stripe_customer_id', sa.String(length=100), nullable=True),
            sa.Column('stripe_subscription_id', sa.String(length=100), nullable=True),
            sa.Column('logo_url', sa.String(length=255), nullable=True),
            sa.Column('brand_color', sa.String(length=20), nullable=True),
            sa.Column('timezone', sa.String(length=50), nullable=False, server_default='Asia/Kolkata'),
            sa.Column('currency', sa.String(length=10), nullable=False, server_default='INR'),
            sa.Column('address', sa.Text(), nullable=True),
            sa.Column('tax_id', sa.String(length=50), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        )

    # 2. Seed default organization with id=1 if not exists
    res = bind.execute(sa.text("SELECT id FROM organizations WHERE id = 1")).fetchone()
    if not res:
        op.execute(
            sa.text(
                "INSERT INTO organizations (id, name, slug, plan, subscription_status, timezone, currency) "
                "VALUES (1, 'The Grand Palace Bangalore', 'grand-palace', 'pro', 'active', 'Asia/Kolkata', 'INR')"
            )
        )

    # 3. Add organization_id to all tables with default 1
    tables = [
        'users', 'room_types', 'rooms', 'guests', 'reservations',
        'rate_plans', 'cancellation_policies', 'tax_rates', 'rate_overrides',
        'folios', 'folio_items', 'payments', 'housekeeping_tasks',
        'booking_groups', 'group_blocks', 'business_dates', 'daily_snapshots',
        'activity_logs'
    ]

    for tbl in tables:
        if tbl in existing_tables:
            cols = [c['name'] for c in inspector.get_columns(tbl)]
            if 'organization_id' not in cols:
                with op.batch_alter_table(tbl) as batch_op:
                    batch_op.add_column(
                        sa.Column('organization_id', sa.Integer(), nullable=False, server_default='1')
                    )


def downgrade() -> None:
    tables = [
        'activity_logs', 'daily_snapshots', 'business_dates', 'group_blocks',
        'booking_groups', 'housekeeping_tasks', 'payments', 'folio_items',
        'folios', 'rate_overrides', 'tax_rates', 'cancellation_policies',
        'rate_plans', 'reservations', 'guests', 'rooms', 'room_types', 'users'
    ]
    for tbl in tables:
        with op.batch_alter_table(tbl) as batch_op:
            batch_op.drop_column('organization_id')
    op.drop_table('organizations')
