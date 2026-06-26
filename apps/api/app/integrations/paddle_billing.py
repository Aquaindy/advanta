"""Paddle Billing wiring for *recurring subscriptions* (the AdVanta plans).

This is separate from `app.payments.paddle`, which bills one-off fee invoices.
Here we map our plan catalog to Paddle Price IDs, expose the client-side
checkout config (Paddle.js opens an overlay — there is no server redirect URL
like Stripe), and verify inbound webhook signatures.

Config (all via env, mirroring the Stripe integration so the same code runs
against sandbox + live):
  PADDLE_API_KEY            server API key (shared with the fee adapter)
  PADDLE_CLIENT_TOKEN       publishable client-side token for Paddle.js
  PADDLE_WEBHOOK_SECRET     notification-destination secret (HMAC key)
  PADDLE_ENVIRONMENT        "sandbox" | "production" (default production)
  PADDLE_PRICE_ID_STARTER   monthly Paddle Price ID per paid plan; the yearly
  PADDLE_PRICE_ID_PRO       price for each is PADDLE_PRICE_ID_<PLAN>_ANNUAL
  PADDLE_PRICE_ID_AGENCY    (e.g. PADDLE_PRICE_ID_STARTER_ANNUAL)

Without PADDLE_API_KEY + PADDLE_WEBHOOK_SECRET the subscription endpoints
report not-configured (503) — nothing is ever silently accepted."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
from typing import Any

from app.core.exceptions import AdVantaError
from app.billing.plans import BillingNotConfiguredError, PLANS
from app.models.billing_subscription import SubscriptionStatus


class PaddleSignatureError(AdVantaError):
    status_code = 400
    code = "invalid_webhook_signature"


# Plan code -> env var holding its Paddle Price ID. Only paid, public plans.
_PLAN_PRICE_ENV: dict[str, str] = {
    "starter": "PADDLE_PRICE_ID_STARTER",
    "pro": "PADDLE_PRICE_ID_PRO",
    "agency": "PADDLE_PRICE_ID_AGENCY",
}

# Paddle subscription status -> our SubscriptionStatus.
_STATUS_MAP: dict[str, SubscriptionStatus] = {
    "active": SubscriptionStatus.ACTIVE,
    "trialing": SubscriptionStatus.TRIALING,
    "past_due": SubscriptionStatus.PAST_DUE,
    "paused": SubscriptionStatus.PAUSED,
    "canceled": SubscriptionStatus.CANCELED,
}


def _env(name: str) -> str:
    return os.getenv(name, "").strip()


def is_configured() -> bool:
    """Paddle subscriptions are usable only with both an API key (server) and a
    webhook secret (so inbound events can be trusted)."""
    return bool(_env("PADDLE_API_KEY") and _env("PADDLE_WEBHOOK_SECRET"))


def environment() -> str:
    return _env("PADDLE_ENVIRONMENT") or "production"


def _api_base() -> str:
    """Server API base. Honor an explicit PADDLE_API_BASE override (shared with
    the fee adapter); otherwise derive it from PADDLE_ENVIRONMENT."""
    override = _env("PADDLE_API_BASE")
    if override:
        return override.rstrip("/")
    return (
        "https://sandbox-api.paddle.com"
        if environment() == "sandbox"
        else "https://api.paddle.com"
    )


def fetch_subscription_management_url(subscription_id: str | None) -> str | None:
    """Resolve a subscription's Paddle-hosted management URL (cancel / update
    payment) on demand.

    Paddle frequently omits `management_urls` from webhook payloads, so the URL
    stored at subscribe time can be empty. When a customer wants to manage or
    cancel, we fetch it from the API instead. Returns None on any problem
    (missing key/id, network/API error) so the caller can degrade gracefully.

    Requires the API key to carry the `subscription.read` permission."""
    key = _env("PADDLE_API_KEY")
    if not key or not subscription_id:
        return None
    import httpx

    try:
        resp = httpx.get(
            f"{_api_base()}/subscriptions/{subscription_id}",
            headers={"Authorization": f"Bearer {key}"},
            timeout=20.0,
        )
    except httpx.HTTPError:
        return None
    if resp.status_code >= 400:
        return None
    data = resp.json().get("data") or {}
    mgmt = data.get("management_urls") or {}
    return mgmt.get("cancel") or mgmt.get("update_payment_method")


def client_token() -> str:
    token = _env("PADDLE_CLIENT_TOKEN")
    if not token:
        raise BillingNotConfiguredError("PADDLE_CLIENT_TOKEN is not configured.")
    return token


def _price_env_name(plan_code: str, interval: str) -> str | None:
    """Env var holding the Paddle Price ID for (plan, interval). Annual prices
    live under the `_ANNUAL` suffix."""
    base = _PLAN_PRICE_ENV.get(plan_code)
    if base is None:
        return None
    return base if interval == "month" else f"{base}_ANNUAL"


def price_id_for_plan(plan_code: str, interval: str = "month") -> str:
    """Resolve the Paddle Price ID for a plan + billing interval
    (`"month"` | `"year"`)."""
    env_name = _price_env_name(plan_code, interval)
    if env_name is None:
        raise BillingNotConfiguredError(f"Plan `{plan_code}` is not a paid Paddle plan.")
    value = _env(env_name)
    if not value:
        raise BillingNotConfiguredError(
            f"{env_name} is not configured. Set it to the matching Paddle Price ID."
        )
    return value


def plan_for_price_id(price_id: str | None) -> str | None:
    """Map a Paddle Price ID (monthly OR annual) back to its plan code."""
    if not price_id:
        return None
    for plan_code, base in _PLAN_PRICE_ENV.items():
        if _env(base) == price_id or _env(f"{base}_ANNUAL") == price_id:
            return plan_code
    return None


def map_status(paddle_status: str | None) -> SubscriptionStatus:
    return _STATUS_MAP.get((paddle_status or "").lower(), SubscriptionStatus.ACTIVE)


def _webhook_secret() -> str:
    secret = _env("PADDLE_WEBHOOK_SECRET")
    if not secret:
        raise BillingNotConfiguredError("PADDLE_WEBHOOK_SECRET is not configured.")
    return secret


def verify_webhook(payload: bytes, signature: str | None) -> dict[str, Any]:
    """Verify the `Paddle-Signature: ts=..;h1=..` header against the raw body
    and return the parsed event. Raises PaddleSignatureError on any mismatch."""
    secret = _webhook_secret()
    if not signature:
        raise PaddleSignatureError("Missing Paddle-Signature header.")

    parts = dict(p.split("=", 1) for p in signature.split(";") if "=" in p)
    ts = parts.get("ts")
    h1 = parts.get("h1")
    if not ts or not h1:
        raise PaddleSignatureError("Malformed Paddle-Signature header.")

    signed = ts.encode("utf-8") + b":" + payload
    expected = hmac.new(secret.encode("utf-8"), signed, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, h1):
        raise PaddleSignatureError("Paddle signature verification failed.")

    try:
        return json.loads(payload)
    except json.JSONDecodeError as exc:
        raise PaddleSignatureError("Invalid Paddle webhook body.") from exc


# Plans offered for Paddle checkout (paid + public only).
def public_paid_plan_codes() -> list[str]:
    return [code for code, plan in PLANS.items() if plan.is_public and plan.paid]
