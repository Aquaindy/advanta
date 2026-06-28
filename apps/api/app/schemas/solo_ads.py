"""Pydantic schemas for Solo Ads (Paid Email Traffic, Phase 4)."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


# --- Vendors ---

class SoloAdVendorPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    website: str | None = None
    contact_email: str | None = None
    niche: str | None = None
    countries: str | None = None
    average_cpc_cents: int | None = None
    notes: str | None = None
    quality_score: int | None = None
    status: str
    created_at: datetime


class CreateVendorRequest(BaseModel):
    name: str
    website: str | None = None
    contact_email: str | None = None
    niche: str | None = None
    countries: str | None = None
    average_cpc_cents: int | None = None
    notes: str | None = None
    status: str | None = None


class UpdateVendorRequest(BaseModel):
    name: str | None = None
    website: str | None = None
    contact_email: str | None = None
    niche: str | None = None
    countries: str | None = None
    average_cpc_cents: int | None = None
    notes: str | None = None
    quality_score: int | None = None
    status: str | None = None


# --- Orders ---

class SoloAdOrderPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    vendor_id: UUID | None = None
    traffic_campaign_id: UUID | None = None
    name: str | None = None
    status: str
    currency: str | None = None

    clicks_purchased: int
    clicks_delivered: int
    unique_clicks: int
    cost_cents: int
    optins: int
    sales: int
    revenue_cents: int
    refunds: int

    cpc_cents: int | None = None
    cpl_cents: int | None = None
    epc_cents: int | None = None
    roi: float | None = None
    optin_rate: float | None = None

    quality_score: int | None = None
    quality_verdict: str | None = None
    quality_flags: list[str] | None = None
    quality_note: str | None = None

    created_at: datetime


class CreateOrderRequest(BaseModel):
    vendor_id: UUID | None = None
    traffic_campaign_id: UUID | None = None
    name: str | None = None
    status: str | None = None
    currency: str | None = None
    clicks_purchased: int | None = None
    clicks_delivered: int | None = None
    unique_clicks: int | None = None
    cost_cents: int | None = None
    optins: int | None = None
    sales: int | None = None
    revenue_cents: int | None = None
    refunds: int | None = None


class UpdateOrderRequest(CreateOrderRequest):
    pass


# --- Playbook ---

class PlaybookRequest(BaseModel):
    offer_name: str | None = None
    offer_url: str | None = None
    audience: str | None = None
    goal: str | None = None
    niche: str | None = None
    lead_magnet: str | None = None
    vendor_name: str | None = None
    campaign_name: str | None = None
