"""Traffic Genie campaigns + their AI-generated assets.

A `TrafficCampaign` is a workspace-owned plan for driving traffic from one
catalog source (see `app.traffic.catalog`) — e.g. a Solo Ads lead-gen push or a
TikTok organic launch. It is intentionally source-agnostic and works in manual
mode before any platform API publishing exists.

`TrafficCampaignAsset` stores the AI-generated (or manually added) assets for a
campaign — ad copy, email swipes, scripts, pins, etc. — each traceable to the
agent run that produced it, per the project's "all agent outputs saved" rule.
"""

from datetime import date, datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    BigInteger,
    Date,
    DateTime,
    ForeignKey,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class TrafficCampaign(Base, TimestampMixin):
    __tablename__ = "traffic_campaigns"

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_by: Mapped[UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )

    # Catalog source slug (e.g. "solo_ads", "tiktok_organic"). Not a FK — the
    # catalog is code-level reference data, not a tenant table.
    source_slug: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    goal: Mapped[str | None] = mapped_column(String(255))
    offer_name: Mapped[str | None] = mapped_column(String(255))
    offer_url: Mapped[str | None] = mapped_column(String(1024))
    audience: Mapped[str | None] = mapped_column(Text)

    budget_cents: Mapped[int | None] = mapped_column(BigInteger)
    currency: Mapped[str | None] = mapped_column(String(8))

    # draft | active | paused | completed | archived
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft")
    start_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)

    # Omnisend follow-up mapping (free-text references; no live coupling yet).
    omnisend_segment: Mapped[str | None] = mapped_column(String(255))
    omnisend_flow: Mapped[str | None] = mapped_column(String(255))

    ai_summary: Mapped[str | None] = mapped_column(Text)

    assets: Mapped[list["TrafficCampaignAsset"]] = relationship(
        back_populates="campaign",
        cascade="all, delete-orphan",
        order_by="TrafficCampaignAsset.created_at",
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<TrafficCampaign {self.source_slug}:{self.name} status={self.status}>"


class TrafficCampaignAsset(Base, TimestampMixin):
    __tablename__ = "traffic_campaign_assets"

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    workspace_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    campaign_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("traffic_campaigns.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Run that produced this asset (null for manually-added assets).
    agent_run_id: Mapped[UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("agent_runs.id", ondelete="SET NULL")
    )

    asset_type: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str | None] = mapped_column(String(512))
    content: Mapped[str] = mapped_column(Text, nullable=False, default="")
    platform: Mapped[str | None] = mapped_column(String(64))
    variation_label: Mapped[str | None] = mapped_column(String(64))
    agent_name: Mapped[str | None] = mapped_column(String(128))
    metadata_json: Mapped[dict | None] = mapped_column(JSONB)

    campaign: Mapped[TrafficCampaign] = relationship(back_populates="assets")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<TrafficCampaignAsset {self.asset_type} campaign={self.campaign_id}>"
