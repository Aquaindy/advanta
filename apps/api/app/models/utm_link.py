"""Smart UTM Builder links.

A workspace-owned, consistently-formatted tracking link for any traffic source
(paid, organic, solo ads, etc.). Optionally tied to a `TrafficCampaign`. The
generated_url is built deterministically from the parts so the same campaign +
source + content always tracks the same way.
"""

from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class UtmLink(Base, TimestampMixin):
    __tablename__ = "utm_links"

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
    campaign_id: Mapped[UUID | None] = mapped_column(
        PgUUID(as_uuid=True),
        ForeignKey("traffic_campaigns.id", ondelete="SET NULL"),
        index=True,
    )

    destination_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    source: Mapped[str] = mapped_column(String(128), nullable=False)
    medium: Mapped[str] = mapped_column(String(128), nullable=False)
    campaign: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str | None] = mapped_column(String(255))
    term: Mapped[str | None] = mapped_column(String(255))
    vendor_name: Mapped[str | None] = mapped_column(String(255))

    generated_url: Mapped[str] = mapped_column(Text, nullable=False)
    short_url: Mapped[str | None] = mapped_column(String(512))

    def __repr__(self) -> str:  # pragma: no cover
        return f"<UtmLink {self.source}/{self.medium} campaign={self.campaign}>"
