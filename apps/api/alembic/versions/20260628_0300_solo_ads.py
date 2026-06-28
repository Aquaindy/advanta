"""solo_ads (solo ad vendors + click orders)

Phase 4 — Paid Email Traffic. Vendors you buy email clicks from and the orders
placed against them, with operator-entered numbers, derived economics
(CPC/CPL/EPC/ROI) and a Quality Guard score.

Revision ID: d4b2e8c1a9f6
Revises: c3a1f7e9b2d4
Create Date: 2026-06-28 03:00:00.000000+00:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = 'd4b2e8c1a9f6'
down_revision: Union[str, None] = 'c3a1f7e9b2d4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'solo_ad_vendors',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('website', sa.String(length=512), nullable=True),
        sa.Column('contact_email', sa.String(length=255), nullable=True),
        sa.Column('niche', sa.String(length=255), nullable=True),
        sa.Column('countries', sa.String(length=512), nullable=True),
        sa.Column('average_cpc_cents', sa.BigInteger(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('quality_score', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(length=32), server_default='active', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_solo_ad_vendors_workspace_id', 'solo_ad_vendors', ['workspace_id'])

    op.create_table(
        'solo_ad_orders',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('vendor_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('traffic_campaign_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('name', sa.String(length=255), nullable=True),
        sa.Column('status', sa.String(length=32), server_default='pending', nullable=False),
        sa.Column('currency', sa.String(length=8), nullable=True),
        sa.Column('clicks_purchased', sa.Integer(), server_default='0', nullable=False),
        sa.Column('clicks_delivered', sa.Integer(), server_default='0', nullable=False),
        sa.Column('unique_clicks', sa.Integer(), server_default='0', nullable=False),
        sa.Column('cost_cents', sa.BigInteger(), server_default='0', nullable=False),
        sa.Column('optins', sa.Integer(), server_default='0', nullable=False),
        sa.Column('sales', sa.Integer(), server_default='0', nullable=False),
        sa.Column('revenue_cents', sa.BigInteger(), server_default='0', nullable=False),
        sa.Column('refunds', sa.Integer(), server_default='0', nullable=False),
        sa.Column('cpc_cents', sa.BigInteger(), nullable=True),
        sa.Column('cpl_cents', sa.BigInteger(), nullable=True),
        sa.Column('epc_cents', sa.BigInteger(), nullable=True),
        sa.Column('roi', sa.Float(), nullable=True),
        sa.Column('optin_rate', sa.Float(), nullable=True),
        sa.Column('quality_score', sa.Integer(), nullable=True),
        sa.Column('quality_verdict', sa.String(length=32), nullable=True),
        sa.Column('quality_flags', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('quality_note', sa.Text(), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['vendor_id'], ['solo_ad_vendors.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['traffic_campaign_id'], ['traffic_campaigns.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_solo_ad_orders_workspace_id', 'solo_ad_orders', ['workspace_id'])
    op.create_index('ix_solo_ad_orders_vendor_id', 'solo_ad_orders', ['vendor_id'])
    op.create_index('ix_solo_ad_orders_traffic_campaign_id', 'solo_ad_orders', ['traffic_campaign_id'])


def downgrade() -> None:
    op.drop_index('ix_solo_ad_orders_traffic_campaign_id', table_name='solo_ad_orders')
    op.drop_index('ix_solo_ad_orders_vendor_id', table_name='solo_ad_orders')
    op.drop_index('ix_solo_ad_orders_workspace_id', table_name='solo_ad_orders')
    op.drop_table('solo_ad_orders')
    op.drop_index('ix_solo_ad_vendors_workspace_id', table_name='solo_ad_vendors')
    op.drop_table('solo_ad_vendors')
