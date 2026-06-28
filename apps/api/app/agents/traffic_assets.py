"""Traffic Asset agent — one parametric generator for every catalog source.

Instead of 25 near-identical agents, this single agent reads the source's
catalog metadata (what it's for, what content it needs, which asset types it
supports) and generates the requested assets for a campaign. The LLM produces
the copy; a deterministic fallback returns useful, structured scaffolding (never
fabricated metrics) when no LLM is configured.

Output payload:
    {
      "source_slug": "...",
      "source_name": "...",
      "assets": [ {asset_type, title, content}, ... ],
      "compliance_notes": [ "...", ... ]
    }
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

from app.agents.base import BaseAgent
from app.agents.types import AgentContext, AgentResult, SkillOutputRecord, TaskRecord
from app.models.agent_task import AgentTaskStatus
from app.traffic import catalog as cat

# Human-readable labels for asset_type slugs (used in titles + fallbacks).
_ASSET_LABELS: dict[str, str] = {
    "ad_angles": "Ad angles",
    "headlines": "Headlines",
    "primary_text": "Primary text",
    "cta": "Call-to-action options",
    "landing_angle": "Landing page angle",
    "keywords": "Keyword ideas",
    "negative_keywords": "Negative keywords",
    "hooks": "Hooks",
    "script_15s": "15-second script",
    "script_30s": "30-second script",
    "caption": "Caption",
    "hashtags": "Hashtags",
    "ugc_brief": "UGC creator brief",
    "creator_brief": "Creator brief",
    "subject_lines": "Subject lines",
    "email_swipe": "Email swipe copy",
    "preheader": "Preheader text",
    "landing_headline": "Landing page headline",
    "followup_sequence": "Omnisend follow-up sequence",
    "vendor_screening": "Vendor screening checklist",
    "pin_titles": "Pin titles",
    "pin_descriptions": "Pin descriptions",
    "pin_image_prompts": "Pin image prompts",
    "board_strategy": "Board strategy",
    "board_names": "Board names",
    "instream_script": "In-stream video script",
    "bumper_script": "Bumper ad script",
    "shorts_script": "Shorts script",
    "storyboard": "Storyboard",
    "blog_topics": "Blog topics",
    "keyword_clusters": "Keyword clusters",
    "content_brief": "Content brief",
    "meta_title": "Meta title",
    "meta_description": "Meta description",
    "faq": "FAQ",
    "post_ideas": "Post ideas",
    "post_drafts": "Post drafts",
    "founder_posts": "Founder posts",
    "carousel_outline": "Carousel outline",
    "case_study_post": "Case study post",
    "value_answers": "Value-first answers",
    "soft_cta": "Soft CTA",
    "subreddit_research": "Subreddit research",
    "lead_magnet_ideas": "Lead magnet ideas",
    "welcome_sequence": "Welcome sequence",
}

# Source-specific compliance reminders (subset; generic ones always added).
_SOURCE_COMPLIANCE: dict[str, list[str]] = {
    "solo_ads": [
        "Solo ads do NOT guarantee sales — start with a small test order and track vendor quality.",
        "Use a dedicated UTM link + Omnisend segment per vendor; watch spam complaints and unsubscribes.",
    ],
    "affiliate_traffic": ["Include a clear affiliate disclosure; avoid earnings or income guarantees."],
    "reddit_ads": ["Reddit users punish overt selling — keep copy community-safe and value-first."],
    "reddit_organic": ["Read each subreddit's rules; lead with value, disclose affiliation, avoid spam."],
    "quora_organic": ["Answer the question genuinely first; keep any product mention soft and relevant."],
    "amazon_ads": ["Follow Amazon listing/ad policies; no unverified claims or competitor disparagement."],
}


class TrafficAssetAgent(BaseAgent):
    type = "traffic_assets"
    title = "Traffic asset generator"
    description = (
        "Generates ready-to-edit assets (ad copy, scripts, email swipes, pins, "
        "briefs, SEO content) for any traffic source, grounded in your offer."
    )

    def run(self, ctx: AgentContext) -> AgentResult:
        result = AgentResult()
        started = datetime.now(timezone.utc)
        inp = ctx.input_payload or {}

        source_slug = (inp.get("source_slug") or "").strip()
        source = cat.SOURCE_BY_SLUG.get(source_slug)
        if source is None:
            result.tasks.append(
                TaskRecord(
                    skill_name="traffic.assets",
                    status=AgentTaskStatus.FAILED,
                    input_payload={"source_slug": source_slug},
                    error_message=f"Unknown traffic source '{source_slug}'.",
                    started_at=started,
                    completed_at=datetime.now(timezone.utc),
                )
            )
            result.output_payload = {"error": "unknown_source", "source_slug": source_slug}
            return result

        requested = inp.get("asset_types") or source.asset_types
        # Only keep asset types this source actually supports.
        asset_types = [a for a in requested if a in source.asset_types] or source.asset_types

        generated = self._llm_generate(ctx, source, asset_types, inp)
        if generated:
            assets = [
                {
                    "asset_type": a,
                    "title": _ASSET_LABELS.get(a, a.replace("_", " ").title()),
                    "content": _stringify(generated.get(a)),
                }
                for a in asset_types
                if generated.get(a)
            ]
            source_kind = "llm"
        else:
            assets = [self._fallback_asset(source, a, inp) for a in asset_types]
            source_kind = "deterministic"

        compliance = self._compliance(source)
        payload = {
            "source_slug": source.slug,
            "source_name": source.name,
            "generation": source_kind,
            "assets": assets,
            "compliance_notes": compliance,
        }

        result.tasks.append(
            TaskRecord(
                skill_name="traffic.assets",
                status=AgentTaskStatus.SUCCEEDED,
                input_payload={"source_slug": source.slug, "asset_types": asset_types},
                output_payload={"count": len(assets), "generation": source_kind},
                started_at=started,
                completed_at=datetime.now(timezone.utc),
            )
        )
        result.skill_outputs.append(
            SkillOutputRecord(
                skill_name="traffic.assets",
                output_type="traffic_assets",
                payload=payload,
                task_index=1,
            )
        )
        result.output_payload = payload
        return result

    # ------------------------------------------------------------------

    def _llm_generate(self, ctx: AgentContext, source: cat.TrafficSource, asset_types: list[str], inp: dict) -> dict:
        from app.llm.client import LlmMessage, get_llm_client_for_workspace

        context = {
            "campaign_name": inp.get("campaign_name"),
            "offer_name": inp.get("offer_name"),
            "offer_url": inp.get("offer_url"),
            "audience": inp.get("audience"),
            "goal": inp.get("goal"),
            "notes": inp.get("notes"),
            "source": source.name,
            "best_for": source.best_for,
            "content_required": source.content_required,
        }
        labels = {a: _ASSET_LABELS.get(a, a) for a in asset_types}
        system = (
            f"You are an expert {source.name} marketer. Generate ready-to-edit assets for the "
            "given offer. Return STRICT JSON only (no prose, no code fences): an object whose keys "
            f"are EXACTLY these asset type slugs: {json.dumps(asset_types)}. "
            "For list-like assets (subject_lines, hooks, headlines, keywords, hashtags, post_ideas, "
            "faq, etc.) return an array of strings. For long-form assets (email_swipe, *_script, "
            "content_brief, storyboard, *_sequence, carousel_outline) return a single string with "
            "newlines. Asset labels for reference: " + json.dumps(labels) + ". "
            "Keep copy clear and benefit-driven; avoid exaggerated guarantees or misleading claims. "
            "Do not invent statistics."
        )
        user = "Offer + campaign context JSON:\n" + json.dumps({k: v for k, v in context.items() if v})
        try:
            client = get_llm_client_for_workspace(ctx.db, ctx.workspace_id)
            completion = client.complete_metered(
                db=ctx.db,
                workspace_id=ctx.workspace_id,
                messages=[LlmMessage(role="system", content=system), LlmMessage(role="user", content=user)],
                max_tokens=1800,
                temperature=0.6,
                purpose="traffic_assets",
            )
            return _parse_json(completion.text)
        except Exception as exc:  # noqa: BLE001 — any LLM/budget failure → deterministic scaffolding
            from app.core.logging import get_logger

            get_logger(__name__).info("traffic_assets.llm_fallback", error=str(exc))
            return {}

    def _fallback_asset(self, source: cat.TrafficSource, asset_type: str, inp: dict) -> dict:
        """Useful, honest scaffolding (a checklist/template) — never fake output."""
        label = _ASSET_LABELS.get(asset_type, asset_type.replace("_", " ").title())
        offer = inp.get("offer_name") or "your offer"
        audience = inp.get("audience") or "your audience"
        content = (
            f"[{label} for {source.name}]\n\n"
            f"Offer: {offer}\nAudience: {audience}\n\n"
            "Connect an LLM key (Settings → API keys / Providers) to auto-generate this asset. "
            f"Until then, draft it manually: {source.content_required}. Keep it benefit-driven, "
            "match the angle to the audience's pain point, and end with one clear call to action."
        )
        return {"asset_type": asset_type, "title": label, "content": content}

    def _compliance(self, source: cat.TrafficSource) -> list[str]:
        notes = list(_SOURCE_COMPLIANCE.get(source.slug, []))
        notes.append("Avoid prohibited claims and unrealistic promises; add disclaimers for financial/health/earnings offers.")
        if source.source_type == cat.SOURCE_TYPE_PAID_EMAIL:
            notes.append("Honor CAN-SPAM/GDPR: clear sender, valid unsubscribe, and accurate subject lines.")
        return notes


# ---------------------------------------------------------------------------
# Module helpers
# ---------------------------------------------------------------------------


def _stringify(value) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, list):
        return "\n".join(f"- {_stringify(v)}" if not str(v).startswith("-") else str(v) for v in value)
    if isinstance(value, dict):
        return "\n".join(f"{k}: {_stringify(v)}" for k, v in value.items())
    return str(value)


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
