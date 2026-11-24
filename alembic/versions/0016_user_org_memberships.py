"""0016_user_org_memberships

Revision ID: 0016_user_org_memberships
Revises: 0015_audit_log
Create Date: 2026-11-23 14:35:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '0016_user_org_memberships'
down_revision: Union[str, None] = '0015_audit_log'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = inspector.get_table_names()

    # 1. user_org_memberships
    if 'user_org_memberships' not in existing_tables:
        op.create_table(
            'user_org_memberships',
            sa.Column('id', sa.Integer(), primary_key=True, index=True),
            sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
            sa.Column('organization_id', sa.Integer(), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False),
            sa.Column('role', sa.String(length=50), nullable=False, server_default='front_desk'),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.UniqueConstraint('user_id', 'organization_id', name='uq_user_organization'),
        )

        # Backfill user memberships for existing users to org 1
        op.execute(
            sa.text(
                "INSERT INTO user_org_memberships (user_id, organization_id, role) "
                "SELECT id, 1, COALESCE(role, 'front_desk') FROM users"
            )
        )
    else:
        # Check if memberships exist, if empty backfill
        cnt = bind.execute(sa.text("SELECT count(*) FROM user_org_memberships")).scalar()
        if cnt == 0:
            op.execute(
                sa.text(
                    "INSERT INTO user_org_memberships (user_id, organization_id, role) "
                    "SELECT id, 1, COALESCE(role, 'front_desk') FROM users"
                )
            )

    # 2. Add token and token_expires_at to housekeeping_tasks
    if 'housekeeping_tasks' in existing_tables:
        cols = [c['name'] for c in inspector.get_columns('housekeeping_tasks')]
        with op.batch_alter_table('housekeeping_tasks') as batch_op:
            if 'token' not in cols:
                batch_op.add_column(sa.Column('token', sa.String(length=100), nullable=True))
            if 'token_expires_at' not in cols:
                batch_op.add_column(sa.Column('token_expires_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('housekeeping_tasks') as batch_op:
        batch_op.drop_column('token_expires_at')
        batch_op.drop_column('token')
    op.drop_table('user_org_memberships')
