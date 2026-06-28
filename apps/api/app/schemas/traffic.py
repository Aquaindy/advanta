"""Pydantic schemas for Traffic Genie."""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


# --- Catalog (reference data) ---

class TrafficCategoryPublic(BaseModel):
    slug: str
    name: str
    description: str


class TrafficSourcePublic(BaseModel):
    slug: str
    name: str
    category: str
    source_type: str
    best_for: list[str]
    speed: str
    cost: str
    difficulty: str
    content_required: str
    recommended_goal: str
    tracking: str
    recommended_followup: str
    agents: list[str]
    status: str
    asset_types: list[str]


class TrafficRecipePublic(BaseModel):
    slug: str
    name: str
    goal: str
    sources: list[str]
    assets: list[str]


class TrafficCatalogResponse(BaseModel):
    categories: list[TrafficCategoryPublic]
    sources: list[TrafficSourcePublic]
    recipes: list[TrafficRecipePublic]


# --- Campaigns + assets ---

class TrafficCampaignAssetPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    campaign_id: UUID
    agent_run_id: UUID | None = None
    asset_type: str
    title: str | None = None
    content: str
    platform: str | None = None
    variation_label: str | None = None
    agent_name: str | None = None
    created_at: datetime


class TrafficCampaignPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    source_slug: str
    name: str
    goal: str | None = None
    offer_name: str | None = None
    offer_url: str | None = None
    audience: str | None = None
    budget_cents: int | None = None
    currency: str | None = None
    status: str
    start_date: date | None = None
    end_date: date | None = None
    omnisend_segment: str | None = None
    omnisend_flow: str | None = None
    ai_summary: str | None = None
    created_at: datetime
    updated_at: datetime


class TrafficCampaignDetail(TrafficCampaignPublic):
    assets: list[TrafficCampaignAssetPublic] = []


class CreateTrafficCampaignRequest(BaseModel):
    source_slug: str
    name: str
    goal: str | None = None
    offer_name: str | None = None
    offer_url: str | None = None
    audience: str | None = None
    budget_cents: int | None = None
    currency: str | None = None
    omnisend_segment: str | None = None
    omnisend_flow: str | None = None


class UpdateTrafficCampaignRequest(BaseModel):
    name: str | None = None
    goal: str | None = None
    offer_name: str | None = None
    offer_url: str | None = None
    audience: str | None = None
    budget_cents: int | None = None
    currency: str | None = None
    status: str | None = None
    omnisend_segment: str | None = None
    omnisend_flow: str | None = None


class GenerateAssetsRequest(BaseModel):
    # Subset of the source's asset types; omit/empty = generate all supported.
    asset_types: list[str] | None = None


# --- Recommendation ---

class RecommendationRequest(BaseModel):
    business_type: str | None = None
    product: str | None = None
    audience: str | None = None
    goal: str | None = None
    monthly_budget: float | None = None
    speed: str | None = None  # fast | medium | slow
    business_model: str | None = None  # b2b | b2c
    industry: str | None = None
    preference: str | None = None  # paid | organic | hybrid


# --- UTM links ---

class UtmLinkPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    campaign_id: UUID | None = None
    destination_url: str
    source: str
    medium: str
    campaign: str
    content: str | None = None
    term: str | None = None
    vendor_name: str | None = None
    generated_url: str
    short_url: str | None = None
    created_at: datetime


class CreateUtmLinkRequest(BaseModel):
    destination_url: str
    source: str
    medium: str
    campaign: str
    content: str | None = None
    term: str | None = None
    vendor_name: str | None = None
    campaign_id: UUID | None = None
