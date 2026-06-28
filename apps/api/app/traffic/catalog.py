"""Traffic Genie catalog — global reference data.

Categories, traffic sources (with card metadata + the asset types the AI can
generate for each), and outcome-based recipes. Consumed by:

  * the catalog API (source cards + recipes in the UI),
  * the Traffic Recommendation agent (scores sources against user inputs),
  * the Traffic Asset agent (knows which assets a source supports).

Adding a source here makes it appear in the UI, become recommendable, and
generate assets — no migration required. `status` follows the spec: existing
integrated ad platforms are "active"; everything new is "manual" (fully usable
for planning + AI asset generation before any API publishing is wired up).
"""

from __future__ import annotations

from dataclasses import dataclass, field

# --- Controlled vocabularies (kept as plain strings for JSON friendliness) ---

SOURCE_TYPE_PAID = "paid"
SOURCE_TYPE_PAID_EMAIL = "paid_email"
SOURCE_TYPE_ORGANIC = "organic"

STATUS_ACTIVE = "active"  # already integrated / first-class
STATUS_MANUAL = "manual"  # usable for planning + AI assets, no API publish yet
STATUS_COMING_SOON = "coming_soon"

SPEED_FAST, SPEED_MEDIUM, SPEED_SLOW = "Fast", "Medium", "Slow"
COST_FREE, COST_LOW, COST_MEDIUM, COST_HIGH = "Free", "Low", "Medium", "High"
DIFF_EASY, DIFF_MEDIUM, DIFF_HARD = "Easy", "Medium", "Hard"


@dataclass(frozen=True)
class TrafficCategory:
    slug: str
    name: str
    description: str


@dataclass(frozen=True)
class TrafficSource:
    slug: str
    name: str
    category: str  # category slug
    source_type: str  # paid | paid_email | organic
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
    # Asset types the Traffic Asset agent can generate for this source.
    asset_types: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Categories
# ---------------------------------------------------------------------------

CATEGORIES: list[TrafficCategory] = [
    TrafficCategory("search_ads", "Search Ads", "Intent-based paid search traffic."),
    TrafficCategory("social_ads", "Social Ads", "Paid discovery across social platforms."),
    TrafficCategory("video_ads", "Video Ads", "Paid video campaigns and scripts."),
    TrafficCategory("marketplace_ads", "Marketplace Ads", "Paid placements on retail marketplaces."),
    TrafficCategory("display_retargeting", "Display & Retargeting", "Awareness and re-engagement."),
    TrafficCategory("paid_email", "Paid Email Traffic", "Bought email placements: solo ads, sponsorships."),
    TrafficCategory("organic_search", "Organic Search", "SEO + Search Console opportunity mining."),
    TrafficCategory("organic_social", "Organic Social", "Owned social content traffic."),
    TrafficCategory("community", "Community & Authority", "Forums, Q&A, podcasts, webinars."),
    TrafficCategory("growth_loops", "Growth Loops", "Referrals, affiliates, creators, partners."),
]

CATEGORY_SLUGS = {c.slug for c in CATEGORIES}


# ---------------------------------------------------------------------------
# Sources
# ---------------------------------------------------------------------------

_AD_COPY_ASSETS = ["ad_angles", "headlines", "primary_text", "cta", "landing_angle"]
_SHORT_VIDEO_ASSETS = ["hooks", "script_15s", "script_30s", "caption", "hashtags", "landing_angle"]
_SEO_ASSETS = ["keyword_clusters", "blog_topics", "content_brief", "meta_title", "meta_description", "faq"]
_POST_ASSETS = ["post_ideas", "post_drafts", "hooks", "cta"]

SOURCES: list[TrafficSource] = [
    # ---- Search Ads ----
    TrafficSource(
        "google_ads", "Google Ads", "search_ads", SOURCE_TYPE_PAID,
        best_for=["SaaS", "B2B", "Local services", "Ecommerce", "Lead gen"],
        speed=SPEED_FAST, cost=COST_HIGH, difficulty=DIFF_MEDIUM,
        content_required="Search ads, keywords, landing page",
        recommended_goal="Capture high-intent demand",
        tracking="UTM links, conversion tracking, GA4",
        recommended_followup="Omnisend demo/nurture flow",
        agents=["Paid Ads Agent"], status=STATUS_ACTIVE,
        asset_types=["keywords", "negative_keywords", *_AD_COPY_ASSETS],
    ),
    TrafficSource(
        "microsoft_ads", "Microsoft Ads", "search_ads", SOURCE_TYPE_PAID,
        best_for=["SaaS", "B2B", "Local services", "Professional services", "Ecommerce"],
        speed=SPEED_FAST, cost=COST_MEDIUM, difficulty=DIFF_MEDIUM,
        content_required="Bing search ads, keywords, landing page",
        recommended_goal="Extend search reach beyond Google",
        tracking="UTM links, UET tag, conversions",
        recommended_followup="Omnisend lead nurture flow",
        agents=["Microsoft Ads Agent"], status=STATUS_MANUAL,
        asset_types=["keywords", "negative_keywords", *_AD_COPY_ASSETS],
    ),
    # ---- Social Ads ----
    TrafficSource(
        "meta_ads", "Meta Ads", "social_ads", SOURCE_TYPE_PAID,
        best_for=["Ecommerce", "Lead gen", "Local", "DTC brands", "Coaching"],
        speed=SPEED_FAST, cost=COST_MEDIUM, difficulty=DIFF_MEDIUM,
        content_required="Creatives, primary text, landing page",
        recommended_goal="Drive leads and sales at scale",
        tracking="UTM links, Meta Pixel + CAPI",
        recommended_followup="Omnisend welcome + retargeting flow",
        agents=["Paid Ads Agent", "Creative Strategy Agent"], status=STATUS_ACTIVE,
        asset_types=_AD_COPY_ASSETS,
    ),
    TrafficSource(
        "linkedin_ads", "LinkedIn Ads", "social_ads", SOURCE_TYPE_PAID,
        best_for=["B2B", "SaaS", "Recruiting", "High-ticket services"],
        speed=SPEED_MEDIUM, cost=COST_HIGH, difficulty=DIFF_MEDIUM,
        content_required="Sponsored content, lead forms, landing page",
        recommended_goal="Reach B2B decision-makers",
        tracking="UTM links, Insight Tag",
        recommended_followup="Omnisend B2B nurture flow",
        agents=["Paid Ads Agent"], status=STATUS_ACTIVE,
        asset_types=_AD_COPY_ASSETS,
    ),
    TrafficSource(
        "tiktok_ads", "TikTok Ads", "social_ads", SOURCE_TYPE_PAID,
        best_for=["Ecommerce", "Digital products", "SaaS demos", "Creator offers"],
        speed=SPEED_FAST, cost=COST_MEDIUM, difficulty=DIFF_MEDIUM,
        content_required="Short UGC-style videos, hooks, captions",
        recommended_goal="Paid short-form discovery",
        tracking="UTM links, TikTok Pixel",
        recommended_followup="Omnisend welcome flow + lead magnet",
        agents=["TikTok Traffic Agent"], status=STATUS_MANUAL,
        asset_types=[*_SHORT_VIDEO_ASSETS, "ugc_brief", "creator_brief"],
    ),
    TrafficSource(
        "pinterest_ads", "Pinterest Ads", "social_ads", SOURCE_TYPE_PAID,
        best_for=["Ecommerce", "Etsy/Shopify", "Printables", "Home/Fashion/Beauty"],
        speed=SPEED_MEDIUM, cost=COST_LOW, difficulty=DIFF_MEDIUM,
        content_required="Pins, keywords, descriptions",
        recommended_goal="Visual discovery for products & offers",
        tracking="UTM links, Pinterest Tag",
        recommended_followup="Omnisend product-education flow",
        agents=["Pinterest Discovery Agent"], status=STATUS_MANUAL,
        asset_types=["keywords", "pin_titles", "pin_descriptions", "pin_image_prompts", "board_strategy"],
    ),
    TrafficSource(
        "reddit_ads", "Reddit Ads", "social_ads", SOURCE_TYPE_PAID,
        best_for=["SaaS", "Dev tools", "Gaming", "Finance/Crypto", "Hobby niches"],
        speed=SPEED_MEDIUM, cost=COST_MEDIUM, difficulty=DIFF_HARD,
        content_required="Community-safe ad copy, subreddit research",
        recommended_goal="Niche community demand",
        tracking="UTM links, Reddit Pixel",
        recommended_followup="Omnisend education-first nurture",
        agents=["Community Intelligence Agent"], status=STATUS_MANUAL,
        asset_types=["subreddit_research", "ad_angles", "soft_sell_copy", "landing_angle", "compliance_notes"],
    ),
    TrafficSource(
        "x_ads", "X / Twitter Ads", "social_ads", SOURCE_TYPE_PAID,
        best_for=["AI tools", "SaaS", "Founder-led brands", "Newsletters", "Crypto"],
        speed=SPEED_FAST, cost=COST_MEDIUM, difficulty=DIFF_MEDIUM,
        content_required="Promoted posts, founder-style copy",
        recommended_goal="Founder-led + tech audience reach",
        tracking="UTM links, X Pixel",
        recommended_followup="Omnisend newsletter welcome flow",
        agents=["Founder Traffic Agent"], status=STATUS_MANUAL,
        asset_types=["promoted_posts", "launch_thread", "thread_to_ad", "audience_interests"],
    ),
    TrafficSource(
        "snapchat_ads", "Snapchat Ads", "social_ads", SOURCE_TYPE_PAID,
        best_for=["Gen Z products", "Beauty", "Fashion", "Apps", "Events"],
        speed=SPEED_FAST, cost=COST_MEDIUM, difficulty=DIFF_MEDIUM,
        content_required="Vertical mobile-first video",
        recommended_goal="Reach younger, mobile-first audiences",
        tracking="UTM links, Snap Pixel",
        recommended_followup="Omnisend mobile-first welcome flow",
        agents=["Snap Ads Agent"], status=STATUS_MANUAL,
        asset_types=["snap_scripts", "vertical_video_concepts", "product_reveal_scripts"],
    ),
    # ---- Video Ads ----
    TrafficSource(
        "youtube_ads", "YouTube Ads", "video_ads", SOURCE_TYPE_PAID,
        best_for=["SaaS demos", "Webinars", "Coaching", "High-ticket", "Education"],
        speed=SPEED_MEDIUM, cost=COST_MEDIUM, difficulty=DIFF_HARD,
        content_required="Video ads: hooks, scripts, storyboards",
        recommended_goal="Video demand + retargeting",
        tracking="UTM links, GA4, conversions",
        recommended_followup="Omnisend webinar/demo follow-up",
        agents=["Video Ad Agent"], status=STATUS_MANUAL,
        asset_types=["instream_script", "bumper_script", "shorts_script", "storyboard", "hooks", "cta"],
    ),
    # ---- Marketplace Ads ----
    TrafficSource(
        "amazon_ads", "Amazon Ads", "marketplace_ads", SOURCE_TYPE_PAID,
        best_for=["Ecommerce", "Amazon sellers", "Private label", "Physical products"],
        speed=SPEED_FAST, cost=COST_MEDIUM, difficulty=DIFF_MEDIUM,
        content_required="Sponsored product/brand copy, keywords",
        recommended_goal="Marketplace product sales",
        tracking="Amazon attribution, ASIN performance",
        recommended_followup="Product-to-email opt-in (insert/QR)",
        agents=["Marketplace Ads Agent"], status=STATUS_MANUAL,
        asset_types=["product_keywords", "sponsored_product_copy", "sponsored_brand_copy", "listing_improvements"],
    ),
    # ---- Display & Retargeting ----
    TrafficSource(
        "programmatic_display", "Programmatic Display", "display_retargeting", SOURCE_TYPE_PAID,
        best_for=["Retargeting", "Brand awareness", "SaaS", "Ecommerce", "Events"],
        speed=SPEED_MEDIUM, cost=COST_MEDIUM, difficulty=DIFF_MEDIUM,
        content_required="Banner sizes, short messaging",
        recommended_goal="Awareness + re-engagement",
        tracking="UTM links, view-through, retargeting pixels",
        recommended_followup="Omnisend re-engagement flow",
        agents=["Display Retargeting Agent"], status=STATUS_MANUAL,
        asset_types=["banner_text", "display_copy", "retargeting_sequence", "audience_segments"],
    ),
    # ---- Paid Email Traffic ----
    TrafficSource(
        "solo_ads", "Solo Ads", "paid_email", SOURCE_TYPE_PAID_EMAIL,
        best_for=["Lead gen", "Webinars", "Digital products", "Affiliate offers", "Newsletter growth"],
        speed=SPEED_FAST, cost=COST_MEDIUM, difficulty=DIFF_MEDIUM,
        content_required="Email swipe, landing page, lead magnet",
        recommended_goal="Generate leads quickly",
        tracking="UTM links, vendor tracking, opt-ins, EPC/CPL/ROI",
        recommended_followup="Omnisend welcome + segmentation by vendor",
        agents=["Solo Ads Agent", "Solo Ads Quality Guard"], status=STATUS_MANUAL,
        asset_types=["subject_lines", "email_swipe", "preheader", "landing_headline", "cta", "followup_sequence", "vendor_screening"],
    ),
    TrafficSource(
        "newsletter_sponsorships", "Newsletter Sponsorships", "paid_email", SOURCE_TYPE_PAID_EMAIL,
        best_for=["SaaS", "Newsletters", "Info products", "B2B"],
        speed=SPEED_MEDIUM, cost=COST_MEDIUM, difficulty=DIFF_MEDIUM,
        content_required="Sponsorship blurb, landing page",
        recommended_goal="Targeted audience placement",
        tracking="UTM links, promo codes, opt-ins",
        recommended_followup="Omnisend welcome flow",
        agents=["Newsletter Growth Agent"], status=STATUS_MANUAL,
        asset_types=["sponsorship_blurb", "subject_lines", "landing_headline", "cta"],
    ),
    TrafficSource(
        "partner_email_promotions", "Partner Email Promotions", "paid_email", SOURCE_TYPE_PAID_EMAIL,
        best_for=["Launches", "Webinars", "Co-marketing", "Affiliate"],
        speed=SPEED_MEDIUM, cost=COST_LOW, difficulty=DIFF_MEDIUM,
        content_required="Partner swipe copy, tracking links",
        recommended_goal="Borrow partner audiences",
        tracking="UTM links, partner-specific tracking",
        recommended_followup="Omnisend launch sequence",
        agents=["Newsletter Growth Agent"], status=STATUS_MANUAL,
        asset_types=["partner_swipe", "subject_lines", "outreach_email", "cta"],
    ),
    # ---- Organic Search ----
    TrafficSource(
        "seo_content", "SEO Content Traffic", "organic_search", SOURCE_TYPE_ORGANIC,
        best_for=["SaaS", "Local", "Content brands", "Affiliate", "Long-term growth"],
        speed=SPEED_SLOW, cost=COST_LOW, difficulty=DIFF_MEDIUM,
        content_required="Long-form articles, on-page SEO",
        recommended_goal="Compounding organic visibility",
        tracking="UTM (internal), GSC, GA4",
        recommended_followup="Omnisend content-to-subscriber flow",
        agents=["SEO Traffic Agent"], status=STATUS_ACTIVE,
        asset_types=_SEO_ASSETS,
    ),
    # ---- Organic Social ----
    TrafficSource(
        "linkedin_organic", "LinkedIn Organic", "organic_social", SOURCE_TYPE_ORGANIC,
        best_for=["B2B", "Founders", "Consultants", "Recruiting"],
        speed=SPEED_MEDIUM, cost=COST_FREE, difficulty=DIFF_MEDIUM,
        content_required="Founder posts, carousels, case studies",
        recommended_goal="B2B trust + inbound",
        tracking="UTM links, profile clicks",
        recommended_followup="Omnisend B2B nurture flow",
        agents=["LinkedIn Authority Agent"], status=STATUS_MANUAL,
        asset_types=["post_ideas", "founder_posts", "carousel_outline", "case_study_post", "cta"],
    ),
    TrafficSource(
        "tiktok_organic", "TikTok Organic", "organic_social", SOURCE_TYPE_ORGANIC,
        best_for=["Ecommerce", "Creators", "SaaS demos", "Lifestyle brands"],
        speed=SPEED_FAST, cost=COST_LOW, difficulty=DIFF_MEDIUM,
        content_required="Short videos, hooks, captions (1-3/day)",
        recommended_goal="Product discovery + virality",
        tracking="UTM links, bio link, opt-ins",
        recommended_followup="Lead magnet + Omnisend welcome flow",
        agents=["Short-Form Traffic Agent"], status=STATUS_MANUAL,
        asset_types=[*_SHORT_VIDEO_ASSETS, "content_calendar_30d"],
    ),
    TrafficSource(
        "instagram_reels", "Instagram Reels", "organic_social", SOURCE_TYPE_ORGANIC,
        best_for=["DTC", "Creators", "Lifestyle", "Local"],
        speed=SPEED_FAST, cost=COST_LOW, difficulty=DIFF_MEDIUM,
        content_required="Reels, hooks, captions",
        recommended_goal="Discovery + brand building",
        tracking="UTM links, bio link",
        recommended_followup="Omnisend welcome flow",
        agents=["Short-Form Traffic Agent"], status=STATUS_MANUAL,
        asset_types=_SHORT_VIDEO_ASSETS,
    ),
    TrafficSource(
        "youtube_organic", "YouTube Organic", "organic_social", SOURCE_TYPE_ORGANIC,
        best_for=["SaaS", "Education", "Coaching", "Reviews"],
        speed=SPEED_SLOW, cost=COST_LOW, difficulty=DIFF_HARD,
        content_required="Long-form videos + Shorts, titles, descriptions",
        recommended_goal="Evergreen video traffic",
        tracking="UTM links, description links",
        recommended_followup="Omnisend subscriber nurture",
        agents=["YouTube Growth Agent"], status=STATUS_MANUAL,
        asset_types=["video_ideas", "titles", "descriptions", "tags", "script", "shorts_script"],
    ),
    TrafficSource(
        "youtube_shorts", "YouTube Shorts", "organic_social", SOURCE_TYPE_ORGANIC,
        best_for=["Creators", "SaaS", "Education", "DTC"],
        speed=SPEED_FAST, cost=COST_LOW, difficulty=DIFF_MEDIUM,
        content_required="Short vertical videos, hooks",
        recommended_goal="Fast discovery",
        tracking="UTM links, pinned comment link",
        recommended_followup="Omnisend welcome flow",
        agents=["YouTube Growth Agent", "Short-Form Traffic Agent"], status=STATUS_MANUAL,
        asset_types=_SHORT_VIDEO_ASSETS,
    ),
    TrafficSource(
        "facebook_organic", "Facebook Organic", "organic_social", SOURCE_TYPE_ORGANIC,
        best_for=["Local", "Communities", "Events", "DTC"],
        speed=SPEED_MEDIUM, cost=COST_FREE, difficulty=DIFF_MEDIUM,
        content_required="Posts, value content",
        recommended_goal="Community + local reach",
        tracking="UTM links",
        recommended_followup="Omnisend welcome flow",
        agents=["Community Growth Agent"], status=STATUS_MANUAL,
        asset_types=_POST_ASSETS,
    ),
    TrafficSource(
        "pinterest_organic", "Pinterest Organic", "organic_social", SOURCE_TYPE_ORGANIC,
        best_for=["Ecommerce", "Bloggers", "Printables", "Home/Fashion/Food"],
        speed=SPEED_SLOW, cost=COST_LOW, difficulty=DIFF_MEDIUM,
        content_required="Pins, descriptions, boards",
        recommended_goal="Evergreen visual traffic",
        tracking="UTM links, pin clicks",
        recommended_followup="Omnisend product-education flow",
        agents=["Pinterest SEO Agent"], status=STATUS_MANUAL,
        asset_types=["pin_titles", "pin_descriptions", "board_names", "keywords", "pin_image_prompts"],
    ),
    TrafficSource(
        "x_organic", "X Organic", "organic_social", SOURCE_TYPE_ORGANIC,
        best_for=["Founders", "AI/SaaS", "Newsletters", "Tech"],
        speed=SPEED_FAST, cost=COST_FREE, difficulty=DIFF_MEDIUM,
        content_required="Posts, threads",
        recommended_goal="Founder-led audience growth",
        tracking="UTM links, bio link",
        recommended_followup="Omnisend newsletter welcome",
        agents=["Founder Traffic Agent"], status=STATUS_MANUAL,
        asset_types=["post_ideas", "threads", "hooks", "cta"],
    ),
    # ---- Community & Authority ----
    TrafficSource(
        "reddit_organic", "Reddit Organic", "community", SOURCE_TYPE_ORGANIC,
        best_for=["SaaS", "Dev tools", "Niche products", "Research"],
        speed=SPEED_MEDIUM, cost=COST_FREE, difficulty=DIFF_HARD,
        content_required="Value-first answers, soft CTAs",
        recommended_goal="Niche credibility + traffic",
        tracking="UTM links (where allowed)",
        recommended_followup="Omnisend education-first nurture",
        agents=["Reddit Research Agent"], status=STATUS_MANUAL,
        asset_types=["subreddit_research", "value_answers", "soft_cta", "pain_point_mining"],
    ),
    TrafficSource(
        "quora_organic", "Quora Organic", "community", SOURCE_TYPE_ORGANIC,
        best_for=["SaaS", "Education", "Services", "Affiliate"],
        speed=SPEED_SLOW, cost=COST_FREE, difficulty=DIFF_MEDIUM,
        content_required="Helpful answers with soft CTAs",
        recommended_goal="Evergreen answer traffic",
        tracking="UTM links",
        recommended_followup="Omnisend welcome flow",
        agents=["Answer Engine Agent"], status=STATUS_MANUAL,
        asset_types=["questions", "answer_drafts", "soft_cta"],
    ),
    TrafficSource(
        "community_groups", "Community & Groups", "community", SOURCE_TYPE_ORGANIC,
        best_for=["Communities", "Coaching", "Local", "Niche brands"],
        speed=SPEED_MEDIUM, cost=COST_FREE, difficulty=DIFF_MEDIUM,
        content_required="Value posts, discussion prompts",
        recommended_goal="Trust-based community traffic",
        tracking="UTM links",
        recommended_followup="Omnisend welcome flow",
        agents=["Community Growth Agent"], status=STATUS_MANUAL,
        asset_types=["value_posts", "discussion_prompts", "soft_offer_post", "event_invite"],
    ),
    TrafficSource(
        "podcast_traffic", "Podcast Traffic", "community", SOURCE_TYPE_ORGANIC,
        best_for=["Founders", "Coaching", "B2B", "Authority brands"],
        speed=SPEED_SLOW, cost=COST_LOW, difficulty=DIFF_MEDIUM,
        content_required="Episodes, guest pitches, show notes",
        recommended_goal="Authority + referral traffic",
        tracking="UTM links, vanity URLs",
        recommended_followup="Omnisend nurture flow",
        agents=["Podcast Traffic Agent"], status=STATUS_MANUAL,
        asset_types=["episode_ideas", "show_notes", "guest_outreach", "podcast_cta"],
    ),
    # ---- Growth Loops ----
    TrafficSource(
        "referral_traffic", "Referral Traffic", "growth_loops", SOURCE_TYPE_ORGANIC,
        best_for=["SaaS", "Ecommerce", "Communities", "Newsletters"],
        speed=SPEED_MEDIUM, cost=COST_LOW, difficulty=DIFF_MEDIUM,
        content_required="Referral offer, share copy",
        recommended_goal="Turn customers into traffic",
        tracking="Referral links, UTM",
        recommended_followup="Omnisend referral automation",
        agents=["Referral Engine Agent"], status=STATUS_MANUAL,
        asset_types=["referral_offer", "invite_copy", "reward_ideas", "post_purchase_email"],
    ),
    TrafficSource(
        "affiliate_traffic", "Affiliate Partner Traffic", "growth_loops", SOURCE_TYPE_ORGANIC,
        best_for=["Info products", "SaaS", "Ecommerce", "Courses"],
        speed=SPEED_MEDIUM, cost=COST_LOW, difficulty=DIFF_MEDIUM,
        content_required="Affiliate assets, swipe copy",
        recommended_goal="Partner-driven sales",
        tracking="Affiliate links, UTM",
        recommended_followup="Omnisend buyer nurture",
        agents=["Creator Partnership Agent"], status=STATUS_MANUAL,
        asset_types=["affiliate_swipe", "bridge_page_copy", "promo_assets"],
    ),
    TrafficSource(
        "influencer_traffic", "Influencer & Creator Traffic", "growth_loops", SOURCE_TYPE_ORGANIC,
        best_for=["DTC", "Apps", "Lifestyle", "Beauty/Fashion"],
        speed=SPEED_MEDIUM, cost=COST_MEDIUM, difficulty=DIFF_MEDIUM,
        content_required="Creator briefs, UGC instructions",
        recommended_goal="Creator-led reach + UGC",
        tracking="Tracking links, promo codes",
        recommended_followup="Omnisend welcome flow",
        agents=["Creator Partnership Agent"], status=STATUS_MANUAL,
        asset_types=["influencer_brief", "creator_outreach", "ugc_brief", "usage_rights_checklist"],
    ),
    TrafficSource(
        "newsletter_growth", "Newsletter Growth", "growth_loops", SOURCE_TYPE_ORGANIC,
        best_for=["Creators", "Newsletters", "Content brands", "SaaS"],
        speed=SPEED_MEDIUM, cost=COST_LOW, difficulty=DIFF_MEDIUM,
        content_required="Lead magnet, signup page, weekly issue",
        recommended_goal="Grow + nurture subscribers",
        tracking="UTM links, signup source",
        recommended_followup="Omnisend welcome + weekly nurture",
        agents=["Newsletter Growth Agent"], status=STATUS_MANUAL,
        asset_types=["lead_magnet_ideas", "signup_copy", "welcome_sequence", "referral_campaign"],
    ),
]

SOURCE_BY_SLUG: dict[str, TrafficSource] = {s.slug: s for s in SOURCES}


# ---------------------------------------------------------------------------
# Recipes (outcome-based campaign bundles)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class TrafficRecipe:
    slug: str
    name: str
    goal: str
    sources: list[str]  # source slugs
    assets: list[str]  # human-readable asset list


RECIPES: list[TrafficRecipe] = [
    TrafficRecipe(
        "first-100-leads", "Get My First 100 Leads",
        "Generate your first 100 leads fast with a lead magnet + paid + organic mix.",
        ["meta_ads", "solo_ads", "tiktok_organic"],
        ["Lead magnet ideas", "Landing page copy", "Meta ad copy", "Solo ad swipe", "TikTok scripts", "Omnisend 7-email welcome", "UTM links"],
    ),
    TrafficRecipe(
        "launch-saas", "Launch My SaaS",
        "Capture intent and build trust for a SaaS launch.",
        ["google_ads", "linkedin_ads", "linkedin_organic", "youtube_ads", "reddit_organic"],
        ["Search ads", "LinkedIn founder posts", "Demo video script", "Reddit pain-point summary", "Trial onboarding emails", "Retargeting ads"],
    ),
    TrafficRecipe(
        "sell-digital-product", "Sell My Digital Product",
        "Drive paid + organic traffic to a digital product offer.",
        ["solo_ads", "pinterest_organic", "meta_ads", "tiktok_organic"],
        ["Solo ad copy", "Pinterest pins", "Meta ads", "TikTok scripts", "Product sales emails", "Bonus reminder emails"],
    ),
    TrafficRecipe(
        "fill-webinar", "Fill My Webinar",
        "Register and remind attendees for a webinar.",
        ["youtube_ads", "solo_ads", "linkedin_organic", "partner_email_promotions"],
        ["Webinar invitation email", "Registration page copy", "Video ad script", "LinkedIn post series", "Reminder sequence", "Replay sequence"],
    ),
    TrafficRecipe(
        "grow-newsletter", "Grow My Newsletter",
        "Compound subscriber growth with organic + referral loops.",
        ["seo_content", "linkedin_organic", "youtube_shorts", "referral_traffic", "newsletter_growth"],
        ["Lead magnet", "Signup page", "Blog plan", "Short video scripts", "Referral invite copy", "Welcome sequence"],
    ),
    TrafficRecipe(
        "local-service-leads", "Local Service Lead Gen",
        "Fill the pipeline for a local service business.",
        ["google_ads", "meta_ads", "seo_content"],
        ["Local search ads", "Facebook lead ads", "Local landing page copy", "Review request emails", "Appointment reminders"],
    ),
    TrafficRecipe(
        "appsumo-launch", "AppSumo Launch",
        "Coordinate a lifetime-deal launch across owned + partner channels.",
        ["linkedin_organic", "youtube_ads", "reddit_organic", "partner_email_promotions", "newsletter_sponsorships"],
        ["Launch announcement posts", "Demo video script", "Partner outreach emails", "Newsletter sponsorship copy", "Retargeting ads", "Launch nurture sequence"],
    ),
    TrafficRecipe(
        "build-affiliate-list", "Build My Affiliate List",
        "Grow an affiliate buyer list with paid email + organic answers.",
        ["solo_ads", "youtube_shorts", "seo_content", "quora_organic"],
        ["Solo ad swipe", "Bridge page copy", "Affiliate disclosure-safe email", "YouTube Shorts scripts", "Quora answers", "Follow-up sequence"],
    ),
]

RECIPE_BY_SLUG: dict[str, TrafficRecipe] = {r.slug: r for r in RECIPES}


# ---------------------------------------------------------------------------
# Serialization helpers (dataclass -> JSON-safe dict for the API)
# ---------------------------------------------------------------------------

def source_to_dict(s: TrafficSource) -> dict:
    return {
        "slug": s.slug,
        "name": s.name,
        "category": s.category,
        "source_type": s.source_type,
        "best_for": list(s.best_for),
        "speed": s.speed,
        "cost": s.cost,
        "difficulty": s.difficulty,
        "content_required": s.content_required,
        "recommended_goal": s.recommended_goal,
        "tracking": s.tracking,
        "recommended_followup": s.recommended_followup,
        "agents": list(s.agents),
        "status": s.status,
        "asset_types": list(s.asset_types),
    }


def category_to_dict(c: TrafficCategory) -> dict:
    return {"slug": c.slug, "name": c.name, "description": c.description}


def recipe_to_dict(r: TrafficRecipe) -> dict:
    return {
        "slug": r.slug,
        "name": r.name,
        "goal": r.goal,
        "sources": list(r.sources),
        "assets": list(r.assets),
    }


def catalog_payload() -> dict:
    return {
        "categories": [category_to_dict(c) for c in CATEGORIES],
        "sources": [source_to_dict(s) for s in SOURCES],
        "recipes": [recipe_to_dict(r) for r in RECIPES],
    }
