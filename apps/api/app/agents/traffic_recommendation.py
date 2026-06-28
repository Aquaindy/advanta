"""Traffic Recommendation agent.

Given a workspace's offer/audience/budget/goal/preference, deterministically
scores the traffic catalog and recommends a growth path (primary + secondary +
organic support + retargeting channel + Omnisend follow-up + tracking + a 7-day
launch plan and a 30-day optimization plan). The LLM only writes the "why"
narrative and the plan prose; the channel selection is deterministic and
explainable, and the agent degrades to a fully deterministic plan with no LLM.
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
from app.traffic import catalog as cat

_PAID_TYPES = {cat.SOURCE_TYPE_PAID, cat.SOURCE_TYPE_PAID_EMAIL}
_SPEED_RANK = {cat.SPEED_FAST: 3, cat.SPEED_MEDIUM: 2, cat.SPEED_SLOW: 1}
_COST_RANK = {cat.COST_FREE: 0, cat.COST_LOW: 1, cat.COST_MEDIUM: 2, cat.COST_HIGH: 3}

# Keyword hints that nudge a source up when they appear in the user's inputs.
_B2B_SOURCES = {"linkedin_ads", "linkedin_organic", "google_ads", "microsoft_ads", "reddit_organic", "seo_content"}
_B2C_SOURCES = {"meta_ads", "tiktok_ads", "tiktok_organic", "pinterest_ads", "pinterest_organic", "instagram_reels", "snapchat_ads"}
_ECOM_SOURCES = {"meta_ads", "tiktok_ads", "pinterest_ads", "pinterest_organic", "amazon_ads", "google_ads"}


class TrafficRecommendationAgent(BaseAgent):
    type = "traffic_recommendation"
    title = "Traffic recommendation"
    description = (
        "Recommends the best traffic sources for your offer, budget and goal — "
        "primary + secondary channels, organic support, retargeting, an Omnisend "
        "follow-up journey, tracking, and 7-day + 30-day plans."
    )

    def run(self, ctx: AgentContext) -> AgentResult:
        result = AgentResult()
        started = datetime.now(timezone.utc)
        inp = ctx.input_payload or {}

        scored = self._score_sources(inp)
        plan = self._build_plan(inp, scored)

        enrich = self._llm_enrich(ctx, inp, plan)
        plan["why"] = enrich.get("why") or self._fallback_why(plan)
        if enrich.get("launch_plan_7_day"):
            plan["launch_plan_7_day"] = enrich["launch_plan_7_day"]
        if enrich.get("optimization_plan_30_day"):
            plan["optimization_plan_30_day"] = enrich["optimization_plan_30_day"]

        result.tasks.append(
            TaskRecord(
                skill_name="traffic.recommend",
                status=AgentTaskStatus.SUCCEEDED,
                input_payload={k: inp.get(k) for k in ("goal", "preference", "monthly_budget")},
                output_payload={"primary": plan.get("primary_source", {}).get("slug")},
                started_at=started,
                completed_at=datetime.now(timezone.utc),
            )
        )
        result.skill_outputs.append(
            SkillOutputRecord(
                skill_name="traffic.recommend",
                output_type="traffic_recommendation",
                payload=plan,
                task_index=1,
            )
        )
        primary = plan.get("primary_source") or {}
        result.recommendations.append(
            RecommendationRecord(
                title=f"Start with {primary.get('name', 'a primary traffic source')}",
                summary=plan["why"][:480],
                recommendation_type="traffic.recommended_path",
                risk_level=RiskLevel.LOW,
                expected_impact="A focused growth path matched to your budget and goal.",
                suggested_action=(
                    f"Launch a {primary.get('name', 'primary')} campaign, support it with "
                    f"{(plan.get('organic_support') or {}).get('name', 'organic content')}, and set up "
                    f"the {plan.get('follow_up_journey', 'Omnisend welcome')} follow-up."
                ),
                platform="traffic",
                metadata={"primary": primary.get("slug"), "secondary": (plan.get("secondary_source") or {}).get("slug")},
            )
        )
        result.output_payload = plan
        return result

    # ------------------------------------------------------------------

    def _score_sources(self, inp: dict) -> list[tuple[float, cat.TrafficSource]]:
        preference = (inp.get("preference") or "hybrid").lower()  # paid | organic | hybrid
        budget = _to_float(inp.get("monthly_budget"))
        speed_pref = (inp.get("speed") or "").lower()
        blob = " ".join(
            str(inp.get(k) or "")
            for k in ("business_type", "product", "audience", "goal", "business_model", "industry")
        ).lower()
        is_b2b = "b2b" in blob or any(w in blob for w in ("saas", "agency", "consult", "enterprise"))
        is_ecom = any(w in blob for w in ("ecommerce", "e-commerce", "shop", "store", "product", "dtc"))

        scored: list[tuple[float, cat.TrafficSource]] = []
        for s in cat.SOURCES:
            score = 10.0
            is_paid = s.source_type in _PAID_TYPES

            # Preference filter / weighting.
            if preference == "paid" and not is_paid:
                score -= 6
            elif preference == "organic" and is_paid:
                score -= 6

            # Budget gating for paid sources.
            if is_paid and budget is not None:
                if budget < 300 and _COST_RANK[s.cost] >= 3:
                    score -= 5  # can't afford high-cost paid on a tiny budget
                elif budget >= 2000 and _COST_RANK[s.cost] >= 2:
                    score += 1.5
            if not is_paid:
                score += 1  # organic is always budget-friendly

            # Speed preference.
            if speed_pref:
                if speed_pref.startswith("fast") and s.speed == cat.SPEED_FAST:
                    score += 2
                if speed_pref.startswith("slow") and s.speed == cat.SPEED_SLOW:
                    score += 1

            # Audience / model fit.
            if is_b2b and s.slug in _B2B_SOURCES:
                score += 3
            if (not is_b2b) and s.slug in _B2C_SOURCES:
                score += 2
            if is_ecom and s.slug in _ECOM_SOURCES:
                score += 2

            # Prefer already-integrated platforms slightly (lower setup friction).
            if s.status == cat.STATUS_ACTIVE:
                score += 1

            scored.append((score, s))

        scored.sort(key=lambda t: (t[0], _SPEED_RANK[t[1].speed]), reverse=True)
        return scored

    def _build_plan(self, inp: dict, scored: list[tuple[float, cat.TrafficSource]]) -> dict:
        ordered = [s for _, s in scored]
        paid = [s for s in ordered if s.source_type in _PAID_TYPES]
        organic = [s for s in ordered if s.source_type == cat.SOURCE_TYPE_ORGANIC]
        preference = (inp.get("preference") or "hybrid").lower()

        if preference == "organic":
            primary = organic[0] if organic else ordered[0]
            secondary = organic[1] if len(organic) > 1 else (paid[0] if paid else None)
        else:
            primary = (paid or ordered)[0]
            secondary = ordered[1] if len(ordered) > 1 and ordered[1] is not primary else (
                organic[0] if organic else None
            )

        organic_support = next((s for s in organic if s not in (primary, secondary)), None)
        retargeting = cat.SOURCE_BY_SLUG.get("meta_ads") or cat.SOURCE_BY_SLUG.get("programmatic_display")

        def card(s: cat.TrafficSource | None) -> dict | None:
            return cat.source_to_dict(s) if s else None

        assets_needed = sorted(set((primary.asset_types if primary else []) + (secondary.asset_types if secondary else [])))
        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "inputs_echo": {
                "goal": inp.get("goal"),
                "preference": preference,
                "monthly_budget": inp.get("monthly_budget"),
                "audience": inp.get("audience"),
            },
            "primary_source": card(primary),
            "secondary_source": card(secondary),
            "organic_support": card(organic_support),
            "retargeting_channel": card(retargeting),
            "follow_up_journey": (primary.recommended_followup if primary else "Omnisend welcome flow"),
            "tracking_setup": (
                "Build a Smart UTM link per source, confirm your pixel/GA4 conversion events fire, "
                "and tag new leads with their source in Omnisend."
            ),
            "estimated_difficulty": primary.difficulty if primary else cat.DIFF_MEDIUM,
            "estimated_speed": primary.speed if primary else cat.SPEED_MEDIUM,
            "assets_needed": assets_needed,
            "launch_plan_7_day": self._fallback_7_day(primary, secondary),
            "optimization_plan_30_day": self._fallback_30_day(primary, organic_support, retargeting),
        }

    # ------------------------------------------------------------------
    # LLM enrichment (narrative only) — deterministic fallback on failure
    # ------------------------------------------------------------------

    def _llm_enrich(self, ctx: AgentContext, inp: dict, plan: dict) -> dict:
        from app.llm.client import LlmMessage, get_llm_client_for_workspace

        compact = {
            "inputs": plan["inputs_echo"],
            "primary": (plan.get("primary_source") or {}).get("name"),
            "secondary": (plan.get("secondary_source") or {}).get("name"),
            "organic_support": (plan.get("organic_support") or {}).get("name"),
            "retargeting": (plan.get("retargeting_channel") or {}).get("name"),
            "follow_up": plan.get("follow_up_journey"),
        }
        system = (
            "You are a growth strategist. You are given a recommended traffic mix that was "
            "selected deterministically. Return STRICT JSON only (no prose, no code fences) with keys: "
            "why (string, 3-5 sentences explaining why this mix fits the business — reference the "
            "channels by name), launch_plan_7_day (array of 5-7 short string steps), "
            "optimization_plan_30_day (array of 4-6 short string steps). Be specific and practical. "
            "Do not invent metrics or guarantee results."
        )
        user = "Recommended mix JSON:\n" + json.dumps(compact)
        try:
            client = get_llm_client_for_workspace(ctx.db, ctx.workspace_id)
            completion = client.complete_metered(
                db=ctx.db,
                workspace_id=ctx.workspace_id,
                messages=[LlmMessage(role="system", content=system), LlmMessage(role="user", content=user)],
                max_tokens=900,
                temperature=0.5,
                purpose="traffic_recommendation",
            )
            return _parse_json(completion.text)
        except Exception as exc:  # noqa: BLE001 — any LLM/budget failure → deterministic plan
            from app.core.logging import get_logger

            get_logger(__name__).info("traffic_recommendation.llm_fallback", error=str(exc))
            return {}

    def _fallback_why(self, plan: dict) -> str:
        p = (plan.get("primary_source") or {}).get("name", "your primary channel")
        s = (plan.get("secondary_source") or {}).get("name")
        o = (plan.get("organic_support") or {}).get("name")
        parts = [f"{p} is your fastest path to your goal given your budget and audience."]
        if s:
            parts.append(f"{s} adds a complementary channel to diversify reach.")
        if o:
            parts.append(f"{o} builds compounding organic visibility over time.")
        parts.append("Capture every lead with UTM tracking and an Omnisend follow-up so paid traffic keeps paying off.")
        return " ".join(parts)

    def _fallback_7_day(self, primary, secondary) -> list[str]:
        p = primary.name if primary else "your primary source"
        s = secondary.name if secondary else None
        steps = [
            f"Day 1: Finalize the offer + lead magnet and write the {p} angle.",
            f"Day 2: Generate {p} assets (in Traffic Genie) and build a Smart UTM link.",
            "Day 3: Set up the landing page + Omnisend welcome flow and confirm tracking fires.",
            f"Day 4: Launch the {p} campaign with a small test budget.",
        ]
        if s:
            steps.append(f"Day 5: Layer in {s} and start one organic content thread.")
        steps += [
            "Day 6: Review early opt-ins and pause anything with no engagement.",
            "Day 7: Double down on the best-performing angle and plan week 2.",
        ]
        return steps

    def _fallback_30_day(self, primary, organic_support, retargeting) -> list[str]:
        out = [
            "Week 1: Establish baseline CPL/EPC and confirm lead quality in Omnisend.",
            f"Week 2: Scale the winning {primary.name if primary else 'primary'} angle; cut losers.",
        ]
        if organic_support:
            out.append(f"Week 3: Publish a consistent {organic_support.name} cadence for compounding reach.")
        if retargeting:
            out.append(f"Week 4: Turn on {retargeting.name} retargeting for non-converters.")
        out.append("Ongoing: Compare sources by quality (opt-in + downstream conversion), not just clicks.")
        return out


# ---------------------------------------------------------------------------
# Module helpers
# ---------------------------------------------------------------------------


def _to_float(value) -> float | None:
    try:
        if value is None or value == "":
            return None
        return float(str(value).replace(",", "").replace("$", "").strip())
    except (ValueError, TypeError):
        return None


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
