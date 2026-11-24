"""0012_backups_exports

Revision ID: 0012_backups_exports
Revises: 0011_email_templates
Create Date: 2026-11-23 14:15:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '0012_backups_exports'
down_revision: Union[str, None] = '0011_email_templates'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = inspector.get_table_names()

    if 'backups' not in existing_tables:
        op.create_table(
            'backups',
            sa.Column('id', sa.Integer(), primary_key=True, index=True),
            sa.Column('organization_id', sa.Integer(), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False, server_default='1'),
            sa.Column('s3_key', sa.String(length=255), nullable=False),
            sa.Column('size_bytes', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('status', sa.String(length=30), nullable=False, server_default='completed'),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )

    if 'export_jobs' not in existing_tables:
        op.create_table(
            'export_jobs',
            sa.Column('id', sa.String(length=50), primary_key=True),
            sa.Column('organization_id', sa.Integer(), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False, server_default='1'),
            sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
            sa.Column('status', sa.String(length=30), nullable=False, server_default='pending'),
            sa.Column('file_path', sa.String(length=255), nullable=True),
            sa.Column('s3_key', sa.String(length=255), nullable=True),
            sa.Column('error_message', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        )


def downgrade() -> None:
    op.drop_table('export_jobs')
    op.drop_table('backups')
