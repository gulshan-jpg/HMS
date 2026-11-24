"""0006_folios

Revision ID: 0006_folios
Revises: 0005_rate_overrides
Create Date: 2026-11-23 12:25:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '0006_folios'
down_revision: Union[str, None] = '0005_rate_overrides'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'folios',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('reservation_id', sa.Integer(), sa.ForeignKey('reservations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False, server_default='Primary'),
        sa.Column('is_master', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    with op.batch_alter_table('folio_items') as batch_op:
        batch_op.add_column(sa.Column('folio_id', sa.Integer(), sa.ForeignKey('folios.id', ondelete='CASCADE'), nullable=True))

    with op.batch_alter_table('payments') as batch_op:
        batch_op.add_column(sa.Column('folio_id', sa.Integer(), sa.ForeignKey('folios.id', ondelete='SET NULL'), nullable=True))

    # Migration data backfill: Create primary folio for any reservations and attach existing folio_items
    conn = op.get_bind()
    res_rows = conn.execute(sa.text("SELECT id FROM reservations")).fetchall()
    for row in res_rows:
        res_id = row[0]
        conn.execute(
            sa.text("INSERT INTO folios (reservation_id, name, is_master, created_at) VALUES (:res_id, 'Primary', 1, CURRENT_TIMESTAMP)"),
            {"res_id": res_id}
        )
        folio_id = conn.execute(
            sa.text("SELECT id FROM folios WHERE reservation_id = :res_id AND is_master = 1 ORDER BY id DESC LIMIT 1"),
            {"res_id": res_id}
        ).scalar()
        if folio_id:
            conn.execute(
                sa.text("UPDATE folio_items SET folio_id = :folio_id WHERE reservation_id = :res_id"),
                {"folio_id": folio_id, "res_id": res_id}
            )


def downgrade() -> None:
    with op.batch_alter_table('payments') as batch_op:
        batch_op.drop_column('folio_id')
    with op.batch_alter_table('folio_items') as batch_op:
        batch_op.drop_column('folio_id')
    op.drop_table('folios')
