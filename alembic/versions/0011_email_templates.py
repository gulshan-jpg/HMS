"""0011_email_templates

Revision ID: 0011_email_templates
Revises: 0010_subscriptions
Create Date: 2026-11-23 14:10:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '0011_email_templates'
down_revision: Union[str, None] = '0010_subscriptions'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = inspector.get_table_names()

    if 'email_templates' not in existing_tables:
        op.create_table(
            'email_templates',
            sa.Column('id', sa.Integer(), primary_key=True, index=True),
            sa.Column('organization_id', sa.Integer(), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False, server_default='1'),
            sa.Column('key', sa.String(length=50), nullable=False),
            sa.Column('name', sa.String(length=100), nullable=False),
            sa.Column('subject', sa.String(length=255), nullable=False),
            sa.Column('body', sa.Text(), nullable=False),
            sa.Column('variables_hint', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
            sa.UniqueConstraint('organization_id', 'key', name='uq_email_template_org_key'),
        )

    if 'invoice_logs' not in existing_tables:
        op.create_table(
            'invoice_logs',
            sa.Column('id', sa.Integer(), primary_key=True, index=True),
            sa.Column('organization_id', sa.Integer(), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False, server_default='1'),
            sa.Column('reservation_id', sa.Integer(), sa.ForeignKey('reservations.id', ondelete='CASCADE'), nullable=False),
            sa.Column('invoice_number', sa.String(length=50), unique=True, index=True, nullable=False),
            sa.Column('generated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column('generated_by', sa.String(length=100), nullable=False),
            sa.Column('pdf_path', sa.String(length=255), nullable=True),
        )


def downgrade() -> None:
    op.drop_table('invoice_logs')
    op.drop_table('email_templates')
