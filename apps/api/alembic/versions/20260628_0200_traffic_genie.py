"""traffic_genie (traffic campaigns, assets, UTM links)

Adds the Traffic Genie foundation: workspace-owned traffic campaigns, their
AI-generated assets, and Smart UTM Builder links. Traffic sources themselves are
code-level catalog reference data (app.traffic.catalog), so there is no
traffic_sources table.

Revision ID: c3a1f7e9b2d4
Revises: b8d0f2a4c6e9
Create Date: 2026-06-28 02:00:00.000000+00:00
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = 'c3a1f7e9b2d4'
down_revision: Union[str, None] = 'b8d0f2a4c6e9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'traffic_campaigns',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('source_slug', sa.String(length=64), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('goal', sa.String(length=255), nullable=True),
        sa.Column('offer_name', sa.String(length=255), nullable=True),
        sa.Column('offer_url', sa.String(length=1024), nullable=True),
        sa.Column('audience', sa.Text(), nullable=True),
        sa.Column('budget_cents', sa.BigInteger(), nullable=True),
        sa.Column('currency', sa.String(length=8), nullable=True),
        sa.Column('status', sa.String(length=32), server_default='draft', nullable=False),
        sa.Column('start_date', sa.Date(), nullable=True),
        sa.Column('end_date', sa.Date(), nullable=True),
        sa.Column('omnisend_segment', sa.String(length=255), nullable=True),
        sa.Column('omnisend_flow', sa.String(length=255), nullable=True),
        sa.Column('ai_summary', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_traffic_campaigns_workspace_id', 'traffic_campaigns', ['workspace_id'])
    op.create_index('ix_traffic_campaigns_source_slug', 'traffic_campaigns', ['source_slug'])

    op.create_table(
        'traffic_campaign_assets',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('campaign_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('agent_run_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('asset_type', sa.String(length=64), nullable=False),
        sa.Column('title', sa.String(length=512), nullable=True),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('platform', sa.String(length=64), nullable=True),
        sa.Column('variation_label', sa.String(length=64), nullable=True),
        sa.Column('agent_name', sa.String(length=128), nullable=True),
        sa.Column('metadata_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['campaign_id'], ['traffic_campaigns.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['agent_run_id'], ['agent_runs.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_traffic_campaign_assets_workspace_id', 'traffic_campaign_assets', ['workspace_id'])
    op.create_index('ix_traffic_campaign_assets_campaign_id', 'traffic_campaign_assets', ['campaign_id'])

    op.create_table(
        'utm_links',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('workspace_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('campaign_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('destination_url', sa.String(length=1024), nullable=False),
        sa.Column('source', sa.String(length=128), nullable=False),
        sa.Column('medium', sa.String(length=128), nullable=False),
        sa.Column('campaign', sa.String(length=255), nullable=False),
        sa.Column('content', sa.String(length=255), nullable=True),
        sa.Column('term', sa.String(length=255), nullable=True),
        sa.Column('vendor_name', sa.String(length=255), nullable=True),
        sa.Column('generated_url', sa.Text(), nullable=False),
        sa.Column('short_url', sa.String(length=512), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['campaign_id'], ['traffic_campaigns.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_utm_links_workspace_id', 'utm_links', ['workspace_id'])
    op.create_index('ix_utm_links_campaign_id', 'utm_links', ['campaign_id'])


def downgrade() -> None:
    op.drop_index('ix_utm_links_campaign_id', table_name='utm_links')
    op.drop_index('ix_utm_links_workspace_id', table_name='utm_links')
    op.drop_table('utm_links')
    op.drop_index('ix_traffic_campaign_assets_campaign_id', table_name='traffic_campaign_assets')
    op.drop_index('ix_traffic_campaign_assets_workspace_id', table_name='traffic_campaign_assets')
    op.drop_table('traffic_campaign_assets')
    op.drop_index('ix_traffic_campaigns_source_slug', table_name='traffic_campaigns')
    op.drop_index('ix_traffic_campaigns_workspace_id', table_name='traffic_campaigns')
    op.drop_table('traffic_campaigns')
