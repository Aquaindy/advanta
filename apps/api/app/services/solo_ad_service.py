"""Solo Ads service — vendors, click orders, Quality Guard, and the playbook agent.

Owns workspace-isolated solo-ad vendors and orders. Order economics (CPC, CPL,
EPC, ROI, opt-in rate) are computed deterministically from the operator-entered
numbers. The Quality Guard scores an order's traffic quality (0-100) from those
same real numbers and flags the classic low-quality-traffic patterns — never
fabricated, always traceable to what the operator entered.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import Request
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.agents.runtime import run_agent
from app.core.exceptions import AdGenieError
from app.core.logging import get_logger
from app.models.audit_log import AuditActorType
from app.models.solo_ad import SoloAdOrder, SoloAdVendor
from app.services import audit_service

log = get_logger(__name__)


class SoloAdVendorNotFoundError(AdGenieError):
    status_code = 404
    code = "solo_ad_vendor_not_found"


class SoloAdOrderNotFoundError(AdGenieError):
    status_code = 404
    code = "solo_ad_order_not_found"


_VENDOR_EDITABLE = {
    "name", "website", "contact_email", "niche", "countries",
    "average_cpc_cents", "notes", "quality_score", "status",
}
_ORDER_EDITABLE = {
    "name", "vendor_id", "traffic_campaign_id", "status", "currency",
    "clicks_purchased", "clicks_delivered", "unique_clicks", "cost_cents",
    "optins", "sales", "revenue_cents", "refunds",
}


# ---------------------------------------------------------------------------
# Vendors
# ---------------------------------------------------------------------------


def create_vendor(
    db: Session, *, workspace_id: UUID, actor_user_id: UUID, data: dict,
    request: Request | None = None,
) -> SoloAdVendor:
    vendor = SoloAdVendor(
        workspace_id=workspace_id,
        created_by=actor_user_id,
        name=(data.get("name") or "Unnamed vendor").strip()[:255],
        website=data.get("website"),
        contact_email=data.get("contact_email"),
        niche=data.get("niche"),
        countries=data.get("countries"),
        average_cpc_cents=data.get("average_cpc_cents"),
        notes=data.get("notes"),
        status=data.get("status") or "active",
    )
    db.add(vendor)
    db.flush()
    _audit(db, workspace_id, actor_user_id, "solo_ad_vendor.created", "solo_ad_vendor", vendor.id, {"name": vendor.name}, request)
    db.commit()
    db.refresh(vendor)
    return vendor


def list_vendors(db: Session, *, workspace_id: UUID, limit: int = 200) -> list[SoloAdVendor]:
    return (
        db.query(SoloAdVendor)
        .filter(SoloAdVendor.workspace_id == workspace_id)
        .order_by(desc(SoloAdVendor.created_at))
        .limit(limit)
        .all()
    )


def get_vendor(db: Session, *, workspace_id: UUID, vendor_id: UUID) -> SoloAdVendor:
    row = (
        db.query(SoloAdVendor)
        .filter(SoloAdVendor.id == vendor_id, SoloAdVendor.workspace_id == workspace_id)
        .first()
    )
    if row is None:
        raise SoloAdVendorNotFoundError("Solo ad vendor not found in this workspace.")
    return row


def update_vendor(
    db: Session, *, workspace_id: UUID, vendor_id: UUID, actor_user_id: UUID,
    updates: dict, request: Request | None = None,
) -> SoloAdVendor:
    vendor = get_vendor(db, workspace_id=workspace_id, vendor_id=vendor_id)
    for field, value in updates.items():
        if field in _VENDOR_EDITABLE and value is not None:
            setattr(vendor, field, value)
    _audit(db, workspace_id, actor_user_id, "solo_ad_vendor.updated", "solo_ad_vendor", vendor.id, {}, request)
    db.commit()
    db.refresh(vendor)
    return vendor


def delete_vendor(
    db: Session, *, workspace_id: UUID, vendor_id: UUID, actor_user_id: UUID,
    request: Request | None = None,
) -> None:
    vendor = get_vendor(db, workspace_id=workspace_id, vendor_id=vendor_id)
    db.delete(vendor)
    _audit(db, workspace_id, actor_user_id, "solo_ad_vendor.deleted", "solo_ad_vendor", vendor_id, {}, request)
    db.commit()


# ---------------------------------------------------------------------------
# Orders
# ---------------------------------------------------------------------------


def create_order(
    db: Session, *, workspace_id: UUID, actor_user_id: UUID, data: dict,
    request: Request | None = None,
) -> SoloAdOrder:
    if data.get("vendor_id"):
        get_vendor(db, workspace_id=workspace_id, vendor_id=data["vendor_id"])  # ownership check

    order = SoloAdOrder(
        workspace_id=workspace_id,
        created_by=actor_user_id,
        vendor_id=data.get("vendor_id"),
        traffic_campaign_id=data.get("traffic_campaign_id"),
        name=(data.get("name") or None),
        status=data.get("status") or "pending",
        currency=data.get("currency"),
        clicks_purchased=int(data.get("clicks_purchased") or 0),
        clicks_delivered=int(data.get("clicks_delivered") or 0),
        unique_clicks=int(data.get("unique_clicks") or 0),
        cost_cents=int(data.get("cost_cents") or 0),
        optins=int(data.get("optins") or 0),
        sales=int(data.get("sales") or 0),
        revenue_cents=int(data.get("revenue_cents") or 0),
        refunds=int(data.get("refunds") or 0),
    )
    _derive(order)
    db.add(order)
    db.flush()
    _audit(db, workspace_id, actor_user_id, "solo_ad_order.created", "solo_ad_order", order.id, {"vendor_id": str(order.vendor_id) if order.vendor_id else None}, request)
    db.commit()
    db.refresh(order)
    return order


def list_orders(
    db: Session, *, workspace_id: UUID, vendor_id: UUID | None = None, limit: int = 200,
) -> list[SoloAdOrder]:
    query = db.query(SoloAdOrder).filter(SoloAdOrder.workspace_id == workspace_id)
    if vendor_id is not None:
        query = query.filter(SoloAdOrder.vendor_id == vendor_id)
    return query.order_by(desc(SoloAdOrder.created_at)).limit(limit).all()


def get_order(db: Session, *, workspace_id: UUID, order_id: UUID) -> SoloAdOrder:
    row = (
        db.query(SoloAdOrder)
        .filter(SoloAdOrder.id == order_id, SoloAdOrder.workspace_id == workspace_id)
        .first()
    )
    if row is None:
        raise SoloAdOrderNotFoundError("Solo ad order not found in this workspace.")
    return row


def update_order(
    db: Session, *, workspace_id: UUID, order_id: UUID, actor_user_id: UUID,
    updates: dict, request: Request | None = None,
) -> SoloAdOrder:
    order = get_order(db, workspace_id=workspace_id, order_id=order_id)
    if updates.get("vendor_id"):
        get_vendor(db, workspace_id=workspace_id, vendor_id=updates["vendor_id"])
    for field, value in updates.items():
        if field in _ORDER_EDITABLE and value is not None:
            setattr(order, field, value)
    _derive(order)
    _audit(db, workspace_id, actor_user_id, "solo_ad_order.updated", "solo_ad_order", order.id, {}, request)
    db.commit()
    db.refresh(order)
    return order


def delete_order(
    db: Session, *, workspace_id: UUID, order_id: UUID, actor_user_id: UUID,
    request: Request | None = None,
) -> None:
    order = get_order(db, workspace_id=workspace_id, order_id=order_id)
    db.delete(order)
    _audit(db, workspace_id, actor_user_id, "solo_ad_order.deleted", "solo_ad_order", order_id, {}, request)
    db.commit()


# ---------------------------------------------------------------------------
# Quality Guard
# ---------------------------------------------------------------------------


def score_order_quality(
    db: Session, *, workspace_id: UUID, order_id: UUID, actor_user_id: UUID,
    request: Request | None = None,
) -> SoloAdOrder:
    order = get_order(db, workspace_id=workspace_id, order_id=order_id)
    score, verdict, flags, note = _quality(order)
    order.quality_score = score
    order.quality_verdict = verdict
    order.quality_flags = flags
    order.quality_note = note

    # Roll the vendor's quality up as the average of its scored orders. Exclude
    # THIS order from the query and add its fresh score once: the session runs
    # autoflush=False, so the query would otherwise return this in-session
    # instance carrying the just-set quality_score and double-count it on re-score.
    if order.vendor_id:
        scored = [
            o.quality_score
            for o in db.query(SoloAdOrder).filter(
                SoloAdOrder.workspace_id == workspace_id,
                SoloAdOrder.vendor_id == order.vendor_id,
                SoloAdOrder.id != order.id,
                SoloAdOrder.quality_score.isnot(None),
            ).all()
            if o.quality_score is not None
        ]
        if score is not None:
            scored.append(score)
        vendor = db.query(SoloAdVendor).filter(SoloAdVendor.id == order.vendor_id).first()
        if vendor is not None and scored:
            vendor.quality_score = round(sum(scored) / len(scored))

    _audit(db, workspace_id, actor_user_id, "solo_ad_order.quality_scored", "solo_ad_order", order.id, {"score": score, "verdict": verdict}, request)
    db.commit()
    db.refresh(order)
    return order


def _quality(o: SoloAdOrder) -> tuple[int | None, str, list[str], str]:
    delivered = o.clicks_delivered or 0
    if delivered <= 0:
        return (
            None,
            "insufficient_data",
            [],
            "Enter delivered clicks (and opt-ins/sales) to score this order's quality.",
        )

    score = 100.0
    flags: list[str] = []

    # Under / over delivery.
    if o.clicks_purchased and delivered < o.clicks_purchased * 0.95:
        score -= 10
        flags.append("Under-delivered vs clicks purchased — request replacement clicks.")
    if o.clicks_purchased and delivered > o.clicks_purchased * 1.5:
        score -= 8
        flags.append("Suspiciously high over-delivery — could include low-intent filler clicks.")

    # Unique-click ratio (duplicate/bot signal).
    if o.unique_clicks and o.unique_clicks / delivered < 0.7:
        score -= 15
        flags.append("Low unique-click ratio (<70%) — possible duplicate or bot clicks.")

    # Opt-in rate (solo ads should convert clicks → opt-ins well).
    optin_rate = o.optins / delivered if delivered else 0
    if optin_rate < 0.15:
        score -= 22
        flags.append(f"High clicks but low opt-ins ({optin_rate*100:.0f}%) — weak list match or landing page.")
    elif optin_rate < 0.30:
        score -= 8
        flags.append(f"Opt-in rate is soft ({optin_rate*100:.0f}%); strong solo traffic usually opts in 30%+.")

    # Downstream conversion.
    if o.optins >= 20 and o.sales == 0:
        score -= 15
        flags.append("Opt-ins but zero sales — the front-end offer isn't converting this traffic.")

    # ROI.
    if o.roi is not None and o.roi < 0:
        score -= 15
        flags.append(f"Negative ROI ({o.roi*100:.0f}%) on this order.")

    # Refunds (buyer quality).
    if o.sales > 0 and o.refunds / o.sales > 0.2:
        score -= 15
        flags.append("High refund rate (>20%) — buyer quality concern.")

    score_int = max(0, min(100, round(score)))
    verdict = (
        "Excellent" if score_int >= 85 else
        "Strong" if score_int >= 70 else
        "Promising" if score_int >= 55 else
        "Weak" if score_int >= 40 else
        "Risky" if score_int >= 25 else
        "Poor Quality"
    )
    if flags:
        note = (
            f"This order scored {score_int}/100 ({verdict}). " + " ".join(flags) +
            " Consider a smaller re-test, a stronger landing page, or pausing this vendor."
        )
    else:
        note = f"This order scored {score_int}/100 ({verdict}). Metrics look healthy — a good candidate to scale carefully."
    return score_int, verdict, flags, note


# ---------------------------------------------------------------------------
# Playbook (Solo Ads agent)
# ---------------------------------------------------------------------------


def generate_playbook(
    db: Session, *, workspace_id: UUID, actor_user_id: UUID, context: dict,
    request: Request | None = None,
) -> dict:
    run = run_agent(
        db,
        workspace_id=workspace_id,
        agent_type="solo_ads",
        triggered_by_user_id=actor_user_id,
        input_payload=context or {},
    )
    if run.status.value != "succeeded":
        raise AdGenieError(run.error_message or "Solo ads agent failed.", code="solo_ads_generation_failed")
    return run.output_payload or {}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _derive(order: SoloAdOrder) -> None:
    delivered = order.clicks_delivered or 0
    base_clicks = delivered or order.clicks_purchased or 0
    cost = order.cost_cents or 0
    revenue = order.revenue_cents or 0
    order.cpc_cents = round(cost / base_clicks) if base_clicks else None
    order.cpl_cents = round(cost / order.optins) if order.optins else None
    order.epc_cents = round(revenue / base_clicks) if base_clicks else None
    order.roi = round((revenue - cost) / cost, 4) if cost else None
    order.optin_rate = round(order.optins / delivered, 4) if delivered else None


def _audit(db, workspace_id, actor_user_id, action, resource_type, resource_id, metadata, request) -> None:
    audit_service.log_event(
        db,
        workspace_id=workspace_id,
        actor_type=AuditActorType.USER,
        actor_id=actor_user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        metadata=metadata,
        request=request,
    )
