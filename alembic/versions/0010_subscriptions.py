"""0010_subscriptions

Revision ID: 0010_subscriptions
Revises: 0009_organizations
Create Date: 2026-11-23 14:05:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '0010_subscriptions'
down_revision: Union[str, None] = '0009_organizations'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    cols = [c['name'] for c in inspector.get_columns('users')]

    with op.batch_alter_table('users') as batch_op:
        if 'tour_completed' not in cols:
            batch_op.add_column(sa.Column('tour_completed', sa.Boolean(), nullable=False, server_default='0'))
        if 'email_verified' not in cols:
            batch_op.add_column(sa.Column('email_verified', sa.Boolean(), nullable=False, server_default='1'))
        if 'verification_token' not in cols:
            batch_op.add_column(sa.Column('verification_token', sa.String(length=100), nullable=True))
        if 'reset_token' not in cols:
            batch_op.add_column(sa.Column('reset_token', sa.String(length=100), nullable=True))
        if 'reset_token_expires_at' not in cols:
            batch_op.add_column(sa.Column('reset_token_expires_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('users') as batch_op:
        batch_op.drop_column('reset_token_expires_at')
        batch_op.drop_column('reset_token')
        batch_op.drop_column('verification_token')
        batch_op.drop_column('email_verified')
        batch_op.drop_column('tour_completed')
