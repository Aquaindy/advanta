"""Smart UTM Builder service.

Builds consistent, deterministically-formatted tracking links for any traffic
source and stores them per workspace. UTM parameter values are normalized to
lowercase snake_case so the same campaign/source/content always tracks the same
way and rolls up cleanly in analytics.
"""

from __future__ import annotations

import re
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse
from uuid import UUID

from fastapi import Request
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.core.exceptions import AdGenieError
from app.models.audit_log import AuditActorType
from app.models.utm_link import UtmLink
from app.services import audit_service


class UtmLinkNotFoundError(AdGenieError):
    status_code = 404
    code = "utm_link_not_found"


class InvalidDestinationUrlError(AdGenieError):
    status_code = 400
    code = "invalid_destination_url"


def normalize_value(value: str | None) -> str | None:
    """Lowercase, trim, and collapse non-alphanumerics to underscores."""
    if value is None:
        return None
    s = str(value).strip().lower()
    s = re.sub(r"[^a-z0-9]+", "_", s).strip("_")
    return s or None


def build_url(
    destination_url: str,
    *,
    source: str,
    medium: str,
    campaign: str,
    content: str | None = None,
    term: str | None = None,
) -> str:
    parsed = urlparse(destination_url.strip())
    if not parsed.scheme or not parsed.netloc:
        raise InvalidDestinationUrlError("Destination URL must include http(s):// and a domain.")

    # Preserve any existing query params, then set/override the utm_* ones.
    params = dict(parse_qsl(parsed.query, keep_blank_values=True))
    params["utm_source"] = source
    params["utm_medium"] = medium
    params["utm_campaign"] = campaign
    if content:
        params["utm_content"] = content
    if term:
        params["utm_term"] = term

    new_query = urlencode(params)
    return urlunparse(parsed._replace(query=new_query))


def create_link(
    db: Session,
    *,
    workspace_id: UUID,
    actor_user_id: UUID,
    destination_url: str,
    source: str,
    medium: str,
    campaign: str,
    content: str | None = None,
    term: str | None = None,
    vendor_name: str | None = None,
    campaign_id: UUID | None = None,
    request: Request | None = None,
) -> UtmLink:
    n_source = normalize_value(source)
    n_medium = normalize_value(medium)
    n_campaign = normalize_value(campaign)
    n_content = normalize_value(content)
    n_term = normalize_value(term)
    if not (n_source and n_medium and n_campaign):
        raise AdGenieError("source, medium and campaign are required.", code="missing_utm_fields")

    generated = build_url(
        destination_url,
        source=n_source,
        medium=n_medium,
        campaign=n_campaign,
        content=n_content,
        term=n_term,
    )

    link = UtmLink(
        workspace_id=workspace_id,
        created_by=actor_user_id,
        campaign_id=campaign_id,
        destination_url=destination_url.strip()[:1024],
        source=n_source,
        medium=n_medium,
        campaign=n_campaign,
        content=n_content,
        term=n_term,
        vendor_name=(vendor_name or None),
        generated_url=generated,
    )
    db.add(link)
    db.flush()

    audit_service.log_event(
        db,
        workspace_id=workspace_id,
        actor_type=AuditActorType.USER,
        actor_id=actor_user_id,
        action="utm_link.created",
        resource_type="utm_link",
        resource_id=link.id,
        metadata={"source": n_source, "medium": n_medium, "campaign": n_campaign},
        request=request,
    )
    db.commit()
    db.refresh(link)
    return link


def list_links(
    db: Session,
    *,
    workspace_id: UUID,
    campaign_id: UUID | None = None,
    limit: int = 200,
) -> list[UtmLink]:
    query = db.query(UtmLink).filter(UtmLink.workspace_id == workspace_id)
    if campaign_id is not None:
        query = query.filter(UtmLink.campaign_id == campaign_id)
    return query.order_by(desc(UtmLink.created_at)).limit(limit).all()


def delete_link(
    db: Session,
    *,
    workspace_id: UUID,
    link_id: UUID,
    actor_user_id: UUID,
    request: Request | None = None,
) -> None:
    link = (
        db.query(UtmLink)
        .filter(UtmLink.id == link_id, UtmLink.workspace_id == workspace_id)
        .first()
    )
    if link is None:
        raise UtmLinkNotFoundError("UTM link not found in this workspace.")
    db.delete(link)
    audit_service.log_event(
        db,
        workspace_id=workspace_id,
        actor_type=AuditActorType.USER,
        actor_id=actor_user_id,
        action="utm_link.deleted",
        resource_type="utm_link",
        resource_id=link_id,
        metadata={},
        request=request,
    )
    db.commit()
