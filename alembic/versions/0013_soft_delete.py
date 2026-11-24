"""0013_soft_delete

Revision ID: 0013_soft_delete
Revises: 0012_backups_exports
Create Date: 2026-11-23 14:20:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '0013_soft_delete'
down_revision: Union[str, None] = '0012_backups_exports'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = inspector.get_table_names()

    demo_and_delete_tables = [
        'reservations', 'guests', 'rooms', 'folio_items', 'rate_plans',
        'cancellation_policies', 'tax_rates', 'room_types', 'booking_groups'
    ]

    for tbl in demo_and_delete_tables:
        if tbl in existing_tables:
            cols = [c['name'] for c in inspector.get_columns(tbl)]
            with op.batch_alter_table(tbl) as batch_op:
                if 'is_demo' not in cols:
                    batch_op.add_column(sa.Column('is_demo', sa.Boolean(), nullable=False, server_default='0'))
                if 'deleted_at' not in cols:
                    batch_op.add_column(sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True))

    delete_only_tables = ['payments', 'folios']
    for tbl in delete_only_tables:
        if tbl in existing_tables:
            cols = [c['name'] for c in inspector.get_columns(tbl)]
            if 'deleted_at' not in cols:
                with op.batch_alter_table(tbl) as batch_op:
                    batch_op.add_column(sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    for tbl in ['payments', 'folios']:
        with op.batch_alter_table(tbl) as batch_op:
            batch_op.drop_column('deleted_at')

    for tbl in [
        'booking_groups', 'room_types', 'tax_rates', 'cancellation_policies',
        'rate_plans', 'folio_items', 'rooms', 'guests', 'reservations'
    ]:
        with op.batch_alter_table(tbl) as batch_op:
            batch_op.drop_column('deleted_at')
            batch_op.drop_column('is_demo')
