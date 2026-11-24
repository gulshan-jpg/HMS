"""0014_versions

Revision ID: 0014_versions
Revises: 0013_soft_delete
Create Date: 2026-11-23 14:25:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '0014_versions'
down_revision: Union[str, None] = '0013_soft_delete'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = inspector.get_table_names()

    version_tables = ['reservations', 'rooms', 'folio_items']
    for tbl in version_tables:
        if tbl in existing_tables:
            cols = [c['name'] for c in inspector.get_columns(tbl)]
            if 'version' not in cols:
                with op.batch_alter_table(tbl) as batch_op:
                    batch_op.add_column(sa.Column('version', sa.Integer(), nullable=False, server_default='1'))


def downgrade() -> None:
    version_tables = ['reservations', 'rooms', 'folio_items']
    for tbl in version_tables:
        with op.batch_alter_table(tbl) as batch_op:
            batch_op.drop_column('version')
