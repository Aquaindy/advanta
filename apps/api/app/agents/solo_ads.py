"""Solo Ads agent — the dedicated Paid Email Traffic playbook (Phase 4).

Given an offer + audience + goal, produces a complete, vendor-ready solo-ads
campaign: an offer-suitability read, subject lines, multiple email swipes,
preheader/CTA/landing copy, a vendor screening checklist, an Omnisend follow-up
sequence, a tracking plan, and the standing solo-ads quality/compliance warnings.

The LLM writes the copy; a deterministic fallback returns useful scaffolding
(checklists + templates, never fabricated results) when no LLM is configured.
Compliance is non-negotiable: this agent never implies solo ads guarantee sales.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

from app.agents.base import BaseAgent
from app.agents.types import (
    AgentContext,
    AgentResult,
    RecommendationRecord,
    SkillOutputRecord,
    TaskRecord,
)
from app.models.agent_task import AgentTaskStatus
from app.models.recommendation import RiskLevel

VENDOR_SCREENING_CHECKLIST = [
    "Does the vendor's list match your niche?",
    "Are the clicks unique (not recycled)?",
    "Which countries are included in the traffic?",
    "Is the traffic mobile, desktop, or mixed?",
    "Does the vendor allow your own tracking links?",
    "Can the vendor show recent, verifiable results?",
    "Can you start with a small test order first?",
    "Are subscribers buyers, leads, or general freebie-seekers?",
    "Does the vendor use bot/fraud filtering?",
    "Are refunds or replacement clicks available if under-delivered?",
]

FOLLOWUP_SEQUENCE = [
    "Email 1 — Welcome + deliver the lead magnet immediately.",
    "Email 2 — Problem awareness: name the pain they're feeling.",
    "Email 3 — Story-based trust: a relatable transformation.",
    "Email 4 — Introduce the product as the bridge to the outcome.",
    "Email 5 — FAQ / objection handling.",
    "Email 6 — Bonus or time-bound urgency.",
    "Email 7 — Final reminder before the offer/bonus expires.",
    "Then — move non-buyers into your long-term weekly nurture.",
]

COMPLIANCE_NOTES = [
    "Solo ads do NOT guarantee sales — start with a small test order and judge by quality.",
    "Use a dedicated UTM link and a dedicated Omnisend segment per vendor.",
    "Monitor spam complaints and unsubscribes; pause vendors that spike them.",
    "Avoid misleading claims and prohibited offers; add disclaimers for earnings/health/financial offers.",
    "Honor CAN-SPAM/GDPR: clear sender, accurate subject lines, working unsubscribe.",
]


class SoloAdsAgent(BaseAgent):
    type = "solo_ads"
    title = "Solo Ads playbook"
    description = (
        "Generates a vendor-ready solo-ads campaign: subject lines, email swipes, "
        "landing copy, a vendor screening checklist, an Omnisend follow-up sequence, "
        "a tracking plan, and the quality/compliance guardrails."
    )

    def run(self, ctx: AgentContext) -> AgentResult:
        result = AgentResult()
        started = datetime.now(timezone.utc)
        inp = ctx.input_payload or {}

        enrich = self._llm_generate(ctx, inp)
        playbook = self._assemble(inp, enrich)

        result.tasks.append(
            TaskRecord(
                skill_name="solo_ads.playbook",
                status=AgentTaskStatus.SUCCEEDED,
                input_payload={"offer_name": inp.get("offer_name"), "goal": inp.get("goal")},
                output_payload={"generation": playbook["generation"]},
                started_at=started,
                completed_at=datetime.now(timezone.utc),
            )
        )
        result.skill_outputs.append(
            SkillOutputRecord(
                skill_name="solo_ads.playbook",
                output_type="solo_ads_playbook",
                payload=playbook,
                task_index=1,
            )
        )
        result.recommendations.append(
            RecommendationRecord(
                title="Test the solo-ads vendor before scaling",
                summary=(
                    "Start with a small click order, track opt-ins/sales/ROI per vendor, and only "
                    "scale vendors that pass the Quality Guard. Solo ads never guarantee sales."
                ),
                recommendation_type="solo_ads.test_first",
                risk_level=RiskLevel.MEDIUM,
                expected_impact="Avoids wasted spend on low-quality lists.",
                suggested_action="Place a small test order, add a dedicated UTM + Omnisend segment, then score quality.",
                platform="solo_ads",
                metadata={"offer_name": inp.get("offer_name")},
            )
        )
        result.output_payload = playbook
        return result

    # ------------------------------------------------------------------

    def _assemble(self, inp: dict, enrich: dict) -> dict:
        offer = inp.get("offer_name") or "your offer"
        generation = "llm" if enrich else "deterministic"
        return {
            "offer_name": inp.get("offer_name"),
            "goal": inp.get("goal"),
            "generation": generation,
            "offer_suitability": enrich.get("offer_suitability") or self._fallback_suitability(inp),
            "subject_lines": enrich.get("subject_lines") or self._fallback_subjects(offer),
            "email_swipes": enrich.get("email_swipes") or self._fallback_swipes(inp),
            "preheader": enrich.get("preheader") or f"A quick way to {inp.get('goal') or 'get started'} — inside.",
            "cta_options": enrich.get("cta_options") or ["Get instant access →", "Claim your free copy →", "Start now →"],
            "landing_headline": enrich.get("landing_headline") or f"Get {offer} — free, instant access",
            "thank_you_cta": enrich.get("thank_you_cta") or "Check your inbox — and grab the next step while you're here.",
            "vendor_screening_checklist": VENDOR_SCREENING_CHECKLIST,
            "followup_sequence": enrich.get("followup_sequence") or FOLLOWUP_SEQUENCE,
            "tracking_plan": self._tracking_plan(inp),
            "compliance_notes": COMPLIANCE_NOTES,
        }

    def _tracking_plan(self, inp: dict) -> list[str]:
        vendor = inp.get("vendor_name")
        seg = f"Solo Ads - {vendor} - {inp.get('campaign_name') or 'Campaign'}" if vendor else "Solo Ads - {Vendor} - {Campaign}"
        return [
            f"Build a Smart UTM link: utm_source={_slug(vendor) or 'vendor_name'}, utm_medium=paid_email, "
            f"utm_campaign={_slug(inp.get('campaign_name')) or 'campaign'}.",
            f"Create an Omnisend segment named: {seg}.",
            "Tag new leads with their vendor as the lead source.",
            "Track clicks → opt-ins → sales → revenue → refunds to compute CPL, EPC and ROI.",
            "Score the order with the Quality Guard once delivery completes.",
        ]

    # ------------------------------------------------------------------
    # LLM generation — deterministic fallback on failure
    # ------------------------------------------------------------------

    def _llm_generate(self, ctx: AgentContext, inp: dict) -> dict:
        from app.llm.client import LlmMessage, get_llm_client_for_workspace

        context = {k: inp.get(k) for k in ("offer_name", "offer_url", "audience", "goal", "niche", "lead_magnet")}
        system = (
            "You are an expert solo-ads (paid email traffic) copywriter. Generate vendor-ready "
            "campaign assets for the given offer. Return STRICT JSON only (no prose, no code fences) "
            "with keys: offer_suitability (string: is this offer a good fit for solo ads and why), "
            "subject_lines (array of 10 strings), email_swipes (array of 3 strings — full short email "
            "bodies with a CTA, written for the VENDOR to send), preheader (string), cta_options "
            "(array of 3 strings), landing_headline (string), thank_you_cta (string), followup_sequence "
            "(array of 7 strings — the buyer's own Omnisend nurture steps). Keep copy benefit-driven and "
            "honest. NEVER imply guaranteed income or results. Add a disclaimer for earnings/health/financial offers."
        )
        user = "Offer context JSON:\n" + json.dumps({k: v for k, v in context.items() if v})
        try:
            client = get_llm_client_for_workspace(ctx.db, ctx.workspace_id)
            completion = client.complete_metered(
                db=ctx.db,
                workspace_id=ctx.workspace_id,
                messages=[LlmMessage(role="system", content=system), LlmMessage(role="user", content=user)],
                max_tokens=2000,
                temperature=0.6,
                purpose="solo_ads_playbook",
            )
            return _parse_json(completion.text)
        except Exception as exc:  # noqa: BLE001 — any LLM/budget failure → deterministic playbook
            from app.core.logging import get_logger

            get_logger(__name__).info("solo_ads.llm_fallback", error=str(exc))
            return {}

    def _fallback_suitability(self, inp: dict) -> str:
        return (
            f"Solo ads work best for lead generation with a free lead magnet, then a low-friction offer. "
            f"For '{inp.get('offer_name') or 'your offer'}', lead with the free value, capture the email, and "
            "sell in the follow-up — don't expect cold solo traffic to buy on the first click. Connect an LLM "
            "key for a tailored suitability read."
        )

    def _fallback_subjects(self, offer: str) -> list[str]:
        return [
            f"Free: {offer} (instant access inside)",
            f"The fastest way to get {offer}",
            "Did you grab this yet?",
            f"{offer} — no cost, no catch",
            "Your free copy is waiting",
            "This took me years to learn (it's free for you)",
            f"Steal my {offer}",
            "Open this before tonight",
            "A simple shortcut most people miss",
            f"Inside: {offer} + a quick next step",
        ]

    def _fallback_swipes(self, inp: dict) -> list[str]:
        offer = inp.get("offer_name") or "this free resource"
        url = inp.get("offer_url") or "[your link]"
        base = (
            "Hi there,\n\n"
            f"If you've been trying to {inp.get('goal') or 'make progress'}, I put together something that helps: "
            f"{offer}.\n\n"
            "It's free, and you can grab it here:\n"
            f"{url}\n\n"
            "{cta}\n\n"
            "Talk soon."
        )
        return [
            base.format(cta="Grab it now →"),
            base.format(cta="Only takes a minute — get it here →"),
            base.format(cta="Claim your free copy before the link changes →"),
        ]


# ---------------------------------------------------------------------------
# Module helpers
# ---------------------------------------------------------------------------


def _slug(value) -> str:
    if not value:
        return ""
    import re

    return re.sub(r"[^a-z0-9]+", "_", str(value).strip().lower()).strip("_")


def _parse_json(text: str) -> dict:
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
    try:
        parsed = json.loads(body)
        return parsed if isinstance(parsed, dict) else {}
    except (ValueError, TypeError):
        return {}
