"""Solo Ads — vendors + click orders (Paid Email Traffic, Phase 4).

A `SoloAdVendor` is a workspace-owned record of an email list owner you buy
clicks from. A `SoloAdOrder` is one purchase from a vendor, with the real
numbers the operator enters (clicks, opt-ins, sales, revenue, refunds) plus
derived economics (CPC/CPL/EPC/ROI) and a deterministic Quality Guard score.

Orders optionally link to a `TrafficCampaign` so a solo-ads buy sits inside the
broader Traffic Genie campaign it supports. No fabricated metrics — every number
is operator-entered or computed from those entries.
"""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    BigInteger,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class SoloAdVendor(Base, TimestampMixin):
    __tablename__ = "solo_ad_vendors"

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

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    website: Mapped[str | None] = mapped_column(String(512))
    contact_email: Mapped[str | None] = mapped_column(String(255))
    niche: Mapped[str | None] = mapped_column(String(255))
    countries: Mapped[str | None] = mapped_column(String(512))  # comma-separated
    average_cpc_cents: Mapped[int | None] = mapped_column(BigInteger)
    notes: Mapped[str | None] = mapped_column(Text)

    # Rolling quality (0-100), updated as orders are scored; manual override allowed.
    quality_score: Mapped[int | None] = mapped_column(Integer)
    # active | testing | paused | blacklisted
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")

    orders: Mapped[list["SoloAdOrder"]] = relationship(
        back_populates="vendor", passive_deletes=True
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<SoloAdVendor {self.name} status={self.status}>"


class SoloAdOrder(Base, TimestampMixin):
    __tablename__ = "solo_ad_orders"

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
    vendor_id: Mapped[UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("solo_ad_vendors.id", ondelete="SET NULL"),
        index=True,
    )
    traffic_campaign_id: Mapped[UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("traffic_campaigns.id", ondelete="SET NULL"),
        index=True,
    )

    name: Mapped[str | None] = mapped_column(String(255))
    # pending | running | completed
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    currency: Mapped[str | None] = mapped_column(String(8))

    # --- Operator-entered numbers ---
    clicks_purchased: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    clicks_delivered: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    unique_clicks: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cost_cents: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    optins: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    sales: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    revenue_cents: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    refunds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # --- Derived economics (computed from the above on write) ---
    cpc_cents: Mapped[int | None] = mapped_column(BigInteger)
    cpl_cents: Mapped[int | None] = mapped_column(BigInteger)
    epc_cents: Mapped[int | None] = mapped_column(BigInteger)
    roi: Mapped[float | None] = mapped_column(Float)
    optin_rate: Mapped[float | None] = mapped_column(Float)

    # --- Quality Guard ---
    quality_score: Mapped[int | None] = mapped_column(Integer)
    quality_verdict: Mapped[str | None] = mapped_column(String(32))
    quality_flags: Mapped[list | None] = mapped_column(JSONB)
    quality_note: Mapped[str | None] = mapped_column(Text)

    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    vendor: Mapped[SoloAdVendor | None] = relationship(back_populates="orders")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<SoloAdOrder {self.name or self.id} roi={self.roi}>"
