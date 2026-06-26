"""Growth Content Studio skill.

Turns a workspace's Growth DNA Profile into a bundle of ready-to-use copy
artifacts, one (or more) per section/segment of the profile:

  * Keyword plan          — paid search + SEO (from offer/industry/audience/geo)
  * Ad copy               — one set per recommended-first-campaign platform
  * Landing-page copy      — hero + benefits + CTA (from offer positioning)
  * Lifecycle emails       — one per Growth DNA email flow
  * Social hooks           — one set per content pillar
  * SEO meta tags          — homepage title tag + meta description

A single metered LLM call produces the whole bundle, grounded in the profile +
the already-generated marketing strategy. Without an LLM — or if the call fails,
returns malformed JSON, or the workspace is credit-capped — a deterministic
builder derives the same bundle from real onboarding inputs and the strategy
text (no fabricated metrics, customers, or claims), so the surface always
returns usable artifacts (per the production-rule "honest fallback").
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from urllib.parse import urlparse
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import AdVantaError
from app.llm.client import LlmError, LlmMessage, get_llm_client_for_workspace
from app.models.growth_dna_profile import GrowthDnaProfile
from app.models.onboarding_profile import OnboardingProfile
from app.models.suggested_copy import SuggestedCopyType

# Map LLM/string copy types onto the enum, tolerant of minor variations.
_TYPE_ALIASES = {
    "keywords": SuggestedCopyType.KEYWORDS,
    "keyword_plan": SuggestedCopyType.KEYWORDS,
    "ad_copy": SuggestedCopyType.AD_COPY,
    "ad": SuggestedCopyType.AD_COPY,
    "ads": SuggestedCopyType.AD_COPY,
    "landing_page": SuggestedCopyType.LANDING_PAGE,
    "landing": SuggestedCopyType.LANDING_PAGE,
    "email": SuggestedCopyType.EMAIL,
    "social_post": SuggestedCopyType.SOCIAL_POST,
    "social": SuggestedCopyType.SOCIAL_POST,
    "blog_outline": SuggestedCopyType.BLOG_OUTLINE,
    "blog": SuggestedCopyType.BLOG_OUTLINE,
    "meta_tags": SuggestedCopyType.META_TAGS,
    "meta": SuggestedCopyType.META_TAGS,
}


@dataclass
class GeneratedCopy:
    copy_type: SuggestedCopyType
    section: str
    title: str
    body: str


@dataclass
class CopyBundle:
    copies: list[GeneratedCopy]
    source: str          # "llm" | "deterministic"
    model_used: str | None


# ---------------------------------------------------------------------------
# Public entrypoint
# ---------------------------------------------------------------------------


def generate_suggested_copies(
    db: Session,
    *,
    workspace_id: UUID,
    profile: OnboardingProfile,
    dna: GrowthDnaProfile,
    product_name: str,
) -> CopyBundle:
    """Produce the full copy bundle. LLM-tailored when configured + within
    budget; deterministic otherwise. Never raises on LLM problems — it degrades
    to the deterministic builder."""
    llm = get_llm_client_for_workspace(db, workspace_id)
    if llm.is_configured():
        try:
            copies, model = _bundle_via_llm(
                db,
                workspace_id=workspace_id,
                profile=profile,
                dna=dna,
                product_name=product_name,
            )
            if copies:
                return CopyBundle(copies=copies, source="llm", model_used=model)
        except (LlmError, AdVantaError, ValueError):
            # PlanLimitExceededError (an AdVantaError) lands here too, so a
            # credit-capped workspace gets the deterministic bundle, not a 402.
            pass
    return CopyBundle(
        copies=_bundle_deterministic(profile=profile, dna=dna, product_name=product_name),
        source="deterministic",
        model_used=None,
    )


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _clean(text: str | None, *, fallback: str = "") -> str:
    return " ".join(str(text).split()) if text and str(text).strip() else fallback


def _first_sentence(text: str | None, *, max_len: int = 160) -> str:
    raw = _clean(text)
    if not raw:
        return ""
    for sep in (". ", "! ", "? ", "\n"):
        if sep in raw:
            raw = raw.split(sep)[0]
            break
    return raw[:max_len].rstrip(" ,.;:-")


def _recommended_campaigns(dna: GrowthDnaProfile) -> list[dict]:
    rows = dna.recommended_first_campaigns or []
    if isinstance(rows, list) and rows:
        return [r for r in rows if isinstance(r, dict)]
    return [
        {"platform": "Google Ads", "objective": "Capture high-intent search demand"},
        {"platform": "Meta Ads", "objective": "Build problem-aware demand + retarget warm visitors"},
    ]


def _content_pillars(dna: GrowthDnaProfile) -> list[dict]:
    ms = dna.marketing_strategy or {}
    pillars = ms.get("content_pillars") or []
    return [p for p in pillars if isinstance(p, dict)][:5]


def _email_flows(dna: GrowthDnaProfile) -> list[dict]:
    ms = dna.marketing_strategy or {}
    flows = (ms.get("email_strategy") or {}).get("flows") or []
    return [f for f in flows if isinstance(f, dict)][:4]


# ---------------------------------------------------------------------------
# LLM path — one structured call returns the whole bundle
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = (
    "You are AdVanta's Growth Content Studio — a senior performance copywriter. "
    "Given a business profile and its marketing strategy, produce a bundle of "
    "ready-to-use copy artifacts, one or more per requested section. Ground every "
    "line in the business's ACTUAL offer, audience, and outcomes. Do NOT invent "
    "metrics, customer names, testimonials, or claims you can't support — leave a "
    "clearly-marked [placeholder] where a real proof point belongs. Match the brand "
    "voice. Return STRICT JSON only (no prose, no code fences) of the form:\n"
    '{"copies": [{"copy_type": str, "section": str, "title": str, "body": str}, ...]}\n'
    "copy_type MUST be one of: keywords, ad_copy, landing_page, email, social_post, "
    "meta_tags. `body` is plain text and may use simple markdown (## headings, - bullets). "
    "Produce: ONE keywords plan (grouped: brand, problem, solution/category, competitor, "
    "long-tail); ONE ad_copy set per recommended platform (3 headlines + 2 descriptions + "
    "1 CTA each); ONE landing_page (hero headline, subhead, 3 benefit bullets, CTA); ONE "
    "email per email flow (subject line + body); ONE social_post set per content pillar "
    "(2-3 hooks + caption direction); ONE meta_tags (title tag <=60 chars + meta "
    "description <=155 chars). Be concrete and concise; do not pad."
)


def _bundle_via_llm(
    db: Session,
    *,
    workspace_id: UUID,
    profile: OnboardingProfile,
    dna: GrowthDnaProfile,
    product_name: str,
) -> tuple[list[GeneratedCopy], str | None]:
    llm = get_llm_client_for_workspace(db, workspace_id)
    ms = dna.marketing_strategy or {}
    facts = {
        "product_name": product_name,
        "industry": profile.industry,
        "website_url": profile.website_url,
        "target_audience": profile.target_audience,
        "offer_description": profile.offer_description,
        "pain_points": profile.pain_points,
        "primary_conversion_goal": profile.primary_conversion_goal,
        "geographic_target": profile.geographic_target,
        "brand_voice": profile.brand_voice,
        "offer_positioning": dna.offer_positioning,
        "competitors": [
            c.get("name") if isinstance(c, dict) else c
            for c in (profile.competitors or [])
        ][:6],
        "recommended_campaigns": [
            {"platform": c.get("platform"), "objective": c.get("objective")}
            for c in _recommended_campaigns(dna)
        ],
        "content_pillars": [p.get("name") for p in _content_pillars(dna)],
        "email_flows": [
            {"name": f.get("name"), "trigger": f.get("trigger"), "goal": f.get("goal")}
            for f in _email_flows(dna)
        ],
        "business_model": (ms.get("overview") or {}).get("model"),
    }
    user = LlmMessage(
        role="user",
        content=(
            "BUSINESS + STRATEGY (JSON):\n"
            + json.dumps(facts, ensure_ascii=False)
            + "\n\nReturn the copy bundle as JSON only."
        ),
    )
    completion = llm.complete_metered(
        db=db,
        workspace_id=workspace_id,
        messages=[LlmMessage(role="system", content=_SYSTEM_PROMPT), user],
        max_tokens=6000,
        temperature=0.6,
        purpose="growth_content.copies",
    )
    data = _coerce_json(completion.text)
    raw = data.get("copies") if isinstance(data, dict) else None
    if not isinstance(raw, list):
        raise LlmError("Copy studio LLM did not return a 'copies' array.")

    copies: list[GeneratedCopy] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        ctype = _TYPE_ALIASES.get(str(item.get("copy_type", "")).strip().lower())
        title = _clean(item.get("title"))
        body = str(item.get("body") or "").strip()
        if ctype is None or not title or not body:
            continue
        copies.append(
            GeneratedCopy(
                copy_type=ctype,
                section=_clean(item.get("section"), fallback=ctype.value)[:255],
                title=title[:512],
                body=body,
            )
        )
    if not copies:
        raise LlmError("Copy studio LLM produced no usable copies.")
    return copies, completion.model


def _coerce_json(text: str) -> dict:
    body = (text or "").strip()
    if body.startswith("```"):
        lines = body.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        body = "\n".join(lines)
    if not body.startswith("{") and "{" in body:
        body = body[body.index("{"):]
    if body.endswith("```"):
        body = body[: body.rindex("```")]
    parsed = json.loads(body)
    if not isinstance(parsed, dict):
        raise ValueError("Copy studio LLM output was not a JSON object.")
    return parsed


# ---------------------------------------------------------------------------
# Deterministic builder — derived from real inputs + the strategy
# ---------------------------------------------------------------------------


def _bundle_deterministic(
    *,
    profile: OnboardingProfile,
    dna: GrowthDnaProfile,
    product_name: str,
) -> list[GeneratedCopy]:
    copies: list[GeneratedCopy] = []
    copies.append(_keywords(profile, product_name))
    for campaign in _recommended_campaigns(dna):
        copies.append(_ad_copy(profile, product_name, campaign))
    copies.append(_landing_page(profile, dna, product_name))
    for flow in _email_flows(dna):
        copies.append(_email(profile, product_name, flow))
    for pillar in _content_pillars(dna):
        copies.append(_social(profile, product_name, pillar))
    copies.append(_meta_tags(profile, product_name))
    return copies


def _keywords(p: OnboardingProfile, product_name: str) -> GeneratedCopy:
    industry = _clean(p.industry, fallback="your category")
    audience = _clean(p.target_audience, fallback="your buyers")
    geo = _clean(p.geographic_target)
    brand = product_name
    competitors = [
        _clean(c.get("name")) if isinstance(c, dict) else _clean(c)
        for c in (p.competitors or [])
    ]
    competitors = [c for c in competitors if c][:4]

    brand_kws = [brand, f"{brand} reviews", f"{brand} pricing", f"{brand} alternative"]
    problem_kws = [
        f"how to improve {industry.lower()}",
        f"best way to {_first_sentence(p.primary_conversion_goal, max_len=40).lower() or 'grow'}",
        f"{industry.lower()} problems",
    ]
    solution_kws = [
        f"best {industry.lower()} solution",
        f"{industry.lower()} for {audience.lower()[:40]}",
        f"{industry.lower()} software",
        f"{industry.lower()} tools",
    ]
    competitor_kws = [f"{c} alternative" for c in competitors] or [
        f"top {industry.lower()} companies"
    ]
    longtail = [
        f"{industry.lower()} for {audience.lower()[:30]}{(' in ' + geo) if geo else ''}",
        f"affordable {industry.lower()}",
        f"{industry.lower()} that works",
    ]

    def _bullets(items: list[str]) -> str:
        return "\n".join(f"- {kw}" for kw in items if kw)

    body = (
        f"Keyword plan for {product_name}. Group campaigns by intent; add negatives weekly.\n\n"
        f"## Brand\n{_bullets(brand_kws)}\n\n"
        f"## Problem / pain-aware\n{_bullets(problem_kws)}\n\n"
        f"## Solution / category\n{_bullets(solution_kws)}\n\n"
        f"## Competitor\n{_bullets(competitor_kws)}\n\n"
        f"## Long-tail / intent\n{_bullets(longtail)}"
    )
    return GeneratedCopy(
        copy_type=SuggestedCopyType.KEYWORDS,
        section="Paid Search & SEO",
        title=f"Keyword plan — {product_name}",
        body=body,
    )


def _ad_copy(p: OnboardingProfile, product_name: str, campaign: dict) -> GeneratedCopy:
    platform = _clean(campaign.get("platform"), fallback="Ads")
    objective = _clean(campaign.get("objective"))
    audience = _clean(p.target_audience, fallback="your buyers")
    industry = _clean(p.industry, fallback="your category")
    offer = _first_sentence(p.offer_description, max_len=90) or f"Built for {industry} teams"
    cta = "Get started"

    headlines = [
        f"Built for {industry}"[:30],
        f"For {audience[:24]}"[:30],
        "Less guessing, more growth"[:30],
    ]
    descriptions = [
        offer[:90],
        f"{product_name}: {objective or 'turn interest into customers'}."[:90],
    ]
    body = (
        f"{platform} ad copy for {product_name}."
        + (f" Objective: {objective}." if objective else "")
        + "\n\n## Headlines\n"
        + "\n".join(f"- {h}" for h in headlines)
        + "\n\n## Descriptions\n"
        + "\n".join(f"- {d}" for d in descriptions)
        + f"\n\n## CTA\n- {cta}"
    )
    return GeneratedCopy(
        copy_type=SuggestedCopyType.AD_COPY,
        section=f"Paid: {platform}",
        title=f"{platform} ad copy — {product_name}",
        body=body,
    )


def _landing_page(
    p: OnboardingProfile, dna: GrowthDnaProfile, product_name: str
) -> GeneratedCopy:
    audience = _clean(p.target_audience, fallback="your buyers")
    offer = _first_sentence(p.offer_description, max_len=140) or _first_sentence(
        dna.offer_positioning, max_len=140
    )
    goal = _first_sentence(p.primary_conversion_goal, max_len=60) or "get started"
    body = (
        f"# {product_name}\n\n"
        f"## Hero headline\nThe {_clean(p.industry, fallback='growth')} platform built for {audience}.\n\n"
        f"## Subhead\n{offer or 'A focused way to move from interest to outcome.'}\n\n"
        "## Benefit bullets\n"
        f"- Made for {audience} — not a generic, one-size tool.\n"
        "- Clear setup, fast time-to-value, no busywork.\n"
        "- [Add a proof point: result, metric, or customer logo].\n\n"
        "## Social proof\n[Add 1-2 real testimonials or recognizable logos here.]\n\n"
        f"## Primary CTA\n{goal.capitalize()} →\n\n"
        "## Secondary CTA\nSee how it works"
    )
    return GeneratedCopy(
        copy_type=SuggestedCopyType.LANDING_PAGE,
        section="Landing page / CRO",
        title=f"Landing page copy — {product_name}",
        body=body,
    )


def _email(p: OnboardingProfile, product_name: str, flow: dict) -> GeneratedCopy:
    name = _clean(flow.get("name"), fallback="Lifecycle email")
    trigger = _clean(flow.get("trigger"))
    goal = _clean(flow.get("goal"))
    audience = _clean(p.target_audience, fallback="there")
    offer = _first_sentence(p.offer_description, max_len=140)
    subject = f"{product_name}: {goal[:50]}" if goal else f"Welcome to {product_name}"
    body = (
        f"Flow: {name}." + (f" Trigger: {trigger}." if trigger else "")
        + (f" Goal: {goal}." if goal else "")
        + f"\n\n## Subject line\n{subject}\n\n"
        "## Preview text\n"
        f"{offer[:90] if offer else 'A quick note to help you get value fast.'}\n\n"
        "## Body\n"
        f"Hi {audience.split(' ')[0] if audience else 'there'},\n\n"
        f"{offer or f'Thanks for your interest in {product_name}.'}\n\n"
        f"{('Here is the next step: ' + goal + '.') if goal else 'Here is a simple next step to get value.'}\n\n"
        "[One clear CTA button →]\n\n"
        f"Thanks,\nThe {product_name} team"
    )
    return GeneratedCopy(
        copy_type=SuggestedCopyType.EMAIL,
        section=f"Email: {name}",
        title=f"{name} email — {product_name}",
        body=body,
    )


def _social(p: OnboardingProfile, product_name: str, pillar: dict) -> GeneratedCopy:
    name = _clean(pillar.get("name"), fallback="Content")
    desc = _clean(pillar.get("description"))
    hooks = [h for h in (pillar.get("example_hooks") or []) if _clean(h)]
    audience = _clean(p.target_audience, fallback="your audience")
    if not hooks:
        hooks = [
            f"The {name.lower()} mistake most {audience.lower()[:30]} make (and the fix).",
            f"3 things we learned about {name.lower()} building {product_name}.",
        ]
    body = (
        f"Content pillar: {name}." + (f" {desc}" if desc else "")
        + "\n\n## Post hooks\n"
        + "\n".join(f"- {h}" for h in hooks[:3])
        + "\n\n## Caption direction\n"
        f"Open with the hook, give one concrete takeaway for {audience}, "
        f"close with a soft CTA to {product_name}."
    )
    return GeneratedCopy(
        copy_type=SuggestedCopyType.SOCIAL_POST,
        section=f"Content pillar: {name}",
        title=f"Social posts — {name}",
        body=body,
    )


def _meta_tags(p: OnboardingProfile, product_name: str) -> GeneratedCopy:
    industry = _clean(p.industry, fallback="growth")
    audience = _clean(p.target_audience, fallback="teams")
    offer = _first_sentence(p.offer_description, max_len=120)
    host = ""
    if p.website_url:
        host = urlparse(p.website_url).netloc or ""
    title_tag = f"{product_name} — {industry} for {audience}"[:60]
    meta_desc = (offer or f"{product_name} helps {audience} with {industry}. Get started today.")[:155]
    body = (
        (f"Homepage meta tags for {host or product_name}.\n\n")
        + f"## Title tag (<=60 chars)\n{title_tag}\n\n"
        f"## Meta description (<=155 chars)\n{meta_desc}"
    )
    return GeneratedCopy(
        copy_type=SuggestedCopyType.META_TAGS,
        section="SEO meta tags",
        title=f"Homepage meta tags — {product_name}",
        body=body,
    )
