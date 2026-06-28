"""Solo Ads endpoints (Paid Email Traffic, Phase 4).

Vendor management, click orders (with derived economics), the Quality Guard
score, and the Solo Ads playbook generator. Workspace-scoped; reads need
membership, writes need Marketer+.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.workspace_member import WorkspaceMember
from app.schemas.solo_ads import (
    CreateOrderRequest,
    CreateVendorRequest,
    PlaybookRequest,
    SoloAdOrderPublic,
    SoloAdVendorPublic,
    UpdateOrderRequest,
    UpdateVendorRequest,
)
from app.security.dependencies import get_current_member, require_role
from app.security.permissions import Role
from app.services import solo_ad_service

router = APIRouter()


# --- Vendors ---


@router.get("/{workspace_id}/solo-ads/vendors", response_model=list[SoloAdVendorPublic])
def list_vendors(
    workspace_id: UUID,
    _member: WorkspaceMember = Depends(get_current_member),
    db: Session = Depends(get_db),
) -> list[SoloAdVendorPublic]:
    rows = solo_ad_service.list_vendors(db, workspace_id=workspace_id)
    return [SoloAdVendorPublic.model_validate(r) for r in rows]


@router.post(
    "/{workspace_id}/solo-ads/vendors",
    response_model=SoloAdVendorPublic,
    status_code=status.HTTP_201_CREATED,
)
def create_vendor(
    workspace_id: UUID,
    payload: CreateVendorRequest,
    request: Request,
    member: WorkspaceMember = Depends(require_role(Role.MARKETER)),
    db: Session = Depends(get_db),
) -> SoloAdVendorPublic:
    vendor = solo_ad_service.create_vendor(
        db, workspace_id=workspace_id, actor_user_id=member.user_id,
        data=payload.model_dump(exclude_unset=True), request=request,
    )
    return SoloAdVendorPublic.model_validate(vendor)


@router.patch("/{workspace_id}/solo-ads/vendors/{vendor_id}", response_model=SoloAdVendorPublic)
def update_vendor(
    workspace_id: UUID,
    vendor_id: UUID,
    payload: UpdateVendorRequest,
    request: Request,
    member: WorkspaceMember = Depends(require_role(Role.MARKETER)),
    db: Session = Depends(get_db),
) -> SoloAdVendorPublic:
    vendor = solo_ad_service.update_vendor(
        db, workspace_id=workspace_id, vendor_id=vendor_id, actor_user_id=member.user_id,
        updates=payload.model_dump(exclude_unset=True), request=request,
    )
    return SoloAdVendorPublic.model_validate(vendor)


@router.delete(
    "/{workspace_id}/solo-ads/vendors/{vendor_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_vendor(
    workspace_id: UUID,
    vendor_id: UUID,
    request: Request,
    member: WorkspaceMember = Depends(require_role(Role.MARKETER)),
    db: Session = Depends(get_db),
) -> None:
    solo_ad_service.delete_vendor(
        db, workspace_id=workspace_id, vendor_id=vendor_id, actor_user_id=member.user_id, request=request,
    )


# --- Orders ---


@router.get("/{workspace_id}/solo-ads/orders", response_model=list[SoloAdOrderPublic])
def list_orders(
    workspace_id: UUID,
    vendor_id: UUID | None = None,
    _member: WorkspaceMember = Depends(get_current_member),
    db: Session = Depends(get_db),
) -> list[SoloAdOrderPublic]:
    rows = solo_ad_service.list_orders(db, workspace_id=workspace_id, vendor_id=vendor_id)
    return [SoloAdOrderPublic.model_validate(r) for r in rows]


@router.post(
    "/{workspace_id}/solo-ads/orders",
    response_model=SoloAdOrderPublic,
    status_code=status.HTTP_201_CREATED,
)
def create_order(
    workspace_id: UUID,
    payload: CreateOrderRequest,
    request: Request,
    member: WorkspaceMember = Depends(require_role(Role.MARKETER)),
    db: Session = Depends(get_db),
) -> SoloAdOrderPublic:
    order = solo_ad_service.create_order(
        db, workspace_id=workspace_id, actor_user_id=member.user_id,
        data=payload.model_dump(exclude_unset=True), request=request,
    )
    return SoloAdOrderPublic.model_validate(order)


@router.patch("/{workspace_id}/solo-ads/orders/{order_id}", response_model=SoloAdOrderPublic)
def update_order(
    workspace_id: UUID,
    order_id: UUID,
    payload: UpdateOrderRequest,
    request: Request,
    member: WorkspaceMember = Depends(require_role(Role.MARKETER)),
    db: Session = Depends(get_db),
) -> SoloAdOrderPublic:
    order = solo_ad_service.update_order(
        db, workspace_id=workspace_id, order_id=order_id, actor_user_id=member.user_id,
        updates=payload.model_dump(exclude_unset=True), request=request,
    )
    return SoloAdOrderPublic.model_validate(order)


@router.delete(
    "/{workspace_id}/solo-ads/orders/{order_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_order(
    workspace_id: UUID,
    order_id: UUID,
    request: Request,
    member: WorkspaceMember = Depends(require_role(Role.MARKETER)),
    db: Session = Depends(get_db),
) -> None:
    solo_ad_service.delete_order(
        db, workspace_id=workspace_id, order_id=order_id, actor_user_id=member.user_id, request=request,
    )


@router.post("/{workspace_id}/solo-ads/orders/{order_id}/quality-score", response_model=SoloAdOrderPublic)
def score_order(
    workspace_id: UUID,
    order_id: UUID,
    request: Request,
    member: WorkspaceMember = Depends(require_role(Role.MARKETER)),
    db: Session = Depends(get_db),
) -> SoloAdOrderPublic:
    order = solo_ad_service.score_order_quality(
        db, workspace_id=workspace_id, order_id=order_id, actor_user_id=member.user_id, request=request,
    )
    return SoloAdOrderPublic.model_validate(order)


# --- Playbook ---


@router.post("/{workspace_id}/solo-ads/playbook", response_model=dict)
def generate_playbook(
    workspace_id: UUID,
    payload: PlaybookRequest,
    request: Request,
    member: WorkspaceMember = Depends(require_role(Role.MARKETER)),
    db: Session = Depends(get_db),
) -> dict:
    return solo_ad_service.generate_playbook(
        db, workspace_id=workspace_id, actor_user_id=member.user_id,
        context=payload.model_dump(exclude_none=True), request=request,
    )
