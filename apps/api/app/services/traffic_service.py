"""Traffic Genie service layer.

Owns workspace-isolated traffic campaigns, runs the Traffic Recommendation and
Traffic Asset agents (reusing the agent runtime for runs/usage/audit), and
persists generated assets as `TrafficCampaignAsset` rows traceable to their run.
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
from app.models.skill_output import SkillOutput
from app.models.traffic_campaign import TrafficCampaign, TrafficCampaignAsset
from app.services import audit_service
from app.traffic import catalog as cat

log = get_logger(__name__)


class TrafficCampaignNotFoundError(AdGenieError):
    status_code = 404
    code = "traffic_campaign_not_found"


class UnknownTrafficSourceError(AdGenieError):
    status_code = 400
    code = "unknown_traffic_source"


class AssetGenerationFailedError(AdGenieError):
    status_code = 500
    code = "traffic_asset_generation_failed"


_EDITABLE = {
    "name",
    "goal",
    "offer_name",
    "offer_url",
    "audience",
    "budget_cents",
    "currency",
    "status",
    "omnisend_segment",
    "omnisend_flow",
}


# ---------------------------------------------------------------------------
# Campaign CRUD
# ---------------------------------------------------------------------------


def create_campaign(
    db: Session,
    *,
    workspace_id: UUID,
    actor_user_id: UUID,
    source_slug: str,
    name: str,
    goal: str | None = None,
    offer_name: str | None = None,
    offer_url: str | None = None,
    audience: str | None = None,
    budget_cents: int | None = None,
    currency: str | None = None,
    omnisend_segment: str | None = None,
    omnisend_flow: str | None = None,
    request: Request | None = None,
) -> TrafficCampaign:
    if source_slug not in cat.SOURCE_BY_SLUG:
        raise UnknownTrafficSourceError(f"Unknown traffic source '{source_slug}'.")

    campaign = TrafficCampaign(
        workspace_id=workspace_id,
        created_by=actor_user_id,
        source_slug=source_slug,
        name=name.strip()[:255],
        goal=goal,
        offer_name=offer_name,
        offer_url=offer_url,
        audience=audience,
        budget_cents=budget_cents,
        currency=currency,
        status="draft",
        omnisend_segment=omnisend_segment,
        omnisend_flow=omnisend_flow,
    )
    db.add(campaign)
    db.flush()

    audit_service.log_event(
        db,
        workspace_id=workspace_id,
        actor_type=AuditActorType.USER,
        actor_id=actor_user_id,
        action="traffic_campaign.created",
        resource_type="traffic_campaign",
        resource_id=campaign.id,
        metadata={"source_slug": source_slug},
        request=request,
    )
    db.commit()
    db.refresh(campaign)
    return campaign


def list_campaigns(
    db: Session,
    *,
    workspace_id: UUID,
    source_slug: str | None = None,
    status: str | None = None,
    limit: int = 100,
) -> list[TrafficCampaign]:
    query = db.query(TrafficCampaign).filter(TrafficCampaign.workspace_id == workspace_id)
    if source_slug:
        query = query.filter(TrafficCampaign.source_slug == source_slug)
    if status:
        query = query.filter(TrafficCampaign.status == status)
    return query.order_by(desc(TrafficCampaign.created_at)).limit(limit).all()


def get_campaign(db: Session, *, workspace_id: UUID, campaign_id: UUID) -> TrafficCampaign:
    row = (
        db.query(TrafficCampaign)
        .filter(
            TrafficCampaign.id == campaign_id,
            TrafficCampaign.workspace_id == workspace_id,
        )
        .first()
    )
    if row is None:
        raise TrafficCampaignNotFoundError("Traffic campaign not found in this workspace.")
    return row


def update_campaign(
    db: Session,
    *,
    workspace_id: UUID,
    campaign_id: UUID,
    actor_user_id: UUID,
    updates: dict,
    request: Request | None = None,
) -> TrafficCampaign:
    campaign = get_campaign(db, workspace_id=workspace_id, campaign_id=campaign_id)
    changed: list[str] = []
    for field, value in updates.items():
        if field not in _EDITABLE or value is None:
            continue
        if getattr(campaign, field) != value:
            setattr(campaign, field, value)
            changed.append(field)
    if not changed:
        return campaign

    audit_service.log_event(
        db,
        workspace_id=workspace_id,
        actor_type=AuditActorType.USER,
        actor_id=actor_user_id,
        action="traffic_campaign.updated",
        resource_type="traffic_campaign",
        resource_id=campaign.id,
        metadata={"fields_changed": changed},
        request=request,
    )
    db.commit()
    db.refresh(campaign)
    return campaign


def delete_campaign(
    db: Session,
    *,
    workspace_id: UUID,
    campaign_id: UUID,
    actor_user_id: UUID,
    request: Request | None = None,
) -> None:
    campaign = get_campaign(db, workspace_id=workspace_id, campaign_id=campaign_id)
    db.delete(campaign)
    audit_service.log_event(
        db,
        workspace_id=workspace_id,
        actor_type=AuditActorType.USER,
        actor_id=actor_user_id,
        action="traffic_campaign.deleted",
        resource_type="traffic_campaign",
        resource_id=campaign_id,
        metadata={"source_slug": campaign.source_slug},
        request=request,
    )
    db.commit()


# ---------------------------------------------------------------------------
# Assets
# ---------------------------------------------------------------------------


def list_assets(db: Session, *, workspace_id: UUID, campaign_id: UUID) -> list[TrafficCampaignAsset]:
    # Validate ownership of the parent campaign first.
    get_campaign(db, workspace_id=workspace_id, campaign_id=campaign_id)
    return (
        db.query(TrafficCampaignAsset)
        .filter(
            TrafficCampaignAsset.workspace_id == workspace_id,
            TrafficCampaignAsset.campaign_id == campaign_id,
        )
        .order_by(desc(TrafficCampaignAsset.created_at))
        .all()
    )


def generate_campaign_assets(
    db: Session,
    *,
    workspace_id: UUID,
    actor_user_id: UUID,
    campaign_id: UUID,
    asset_types: list[str] | None = None,
    request: Request | None = None,
) -> list[TrafficCampaignAsset]:
    """Run the Traffic Asset agent for a campaign's source and persist the
    generated assets. Returns the newly created asset rows."""
    campaign = get_campaign(db, workspace_id=workspace_id, campaign_id=campaign_id)

    run = run_agent(
        db,
        workspace_id=workspace_id,
        agent_type="traffic_assets",
        triggered_by_user_id=actor_user_id,
        input_payload={
            "source_slug": campaign.source_slug,
            "asset_types": asset_types,
            "campaign_name": campaign.name,
            "offer_name": campaign.offer_name,
            "offer_url": campaign.offer_url,
            "audience": campaign.audience,
            "goal": campaign.goal,
        },
    )
    if run.status.value != "succeeded":
        raise AssetGenerationFailedError(
            run.error_message or "Traffic asset agent failed without an error message."
        )

    skill_output = (
        db.query(SkillOutput)
        .filter(
            SkillOutput.agent_run_id == run.id,
            SkillOutput.output_type == "traffic_assets",
        )
        .order_by(SkillOutput.created_at.desc())
        .first()
    )
    payload = (skill_output.payload if skill_output else None) or {}
    items = payload.get("assets") or []
    if not items:
        raise AssetGenerationFailedError("Asset generation produced no assets — check the run details.")

    created: list[TrafficCampaignAsset] = []
    for item in items:
        asset = TrafficCampaignAsset(
            workspace_id=workspace_id,
            campaign_id=campaign.id,
            agent_run_id=run.id,
            asset_type=str(item.get("asset_type") or "asset")[:64],
            title=(item.get("title") or None),
            content=str(item.get("content") or ""),
            platform=campaign.source_slug,
            agent_name="Traffic asset generator",
            metadata_json={"generation": payload.get("generation")},
        )
        db.add(asset)
        created.append(asset)

    # Stamp compliance notes onto the campaign summary so they surface in the UI.
    notes = payload.get("compliance_notes") or []
    if notes:
        campaign.ai_summary = "Compliance: " + " ".join(notes)

    audit_service.log_event(
        db,
        workspace_id=workspace_id,
        actor_type=AuditActorType.USER,
        actor_id=actor_user_id,
        action="traffic_campaign.assets_generated",
        resource_type="traffic_campaign",
        resource_id=campaign.id,
        metadata={"source_slug": campaign.source_slug, "count": len(created), "agent_run_id": str(run.id)},
        request=request,
    )
    db.commit()
    for a in created:
        db.refresh(a)
    return created


# ---------------------------------------------------------------------------
# Recommendation
# ---------------------------------------------------------------------------


def generate_recommendation(
    db: Session,
    *,
    workspace_id: UUID,
    actor_user_id: UUID,
    inputs: dict,
    request: Request | None = None,
) -> dict:
    """Run the Traffic Recommendation agent and return its plan payload."""
    run = run_agent(
        db,
        workspace_id=workspace_id,
        agent_type="traffic_recommendation",
        triggered_by_user_id=actor_user_id,
        input_payload=inputs or {},
    )
    if run.status.value != "succeeded":
        raise AssetGenerationFailedError(
            run.error_message or "Traffic recommendation agent failed."
        )
    return run.output_payload or {}
