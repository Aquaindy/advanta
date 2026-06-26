"""Manage/cancel billing flow.

Paddle frequently omits `management_urls` from subscription webhooks, so the
"Manage billing" button must still appear for any active Paddle subscription and
resolve the portal URL on demand from the API.
"""

from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.integrations import paddle_billing
from app.models.billing_subscription import (
    BillingSubscription,
    SubscriptionSource,
    SubscriptionStatus,
)
from app.services import billing_service


def _owner_workspace(client: TestClient, email: str = "owner@example.com") -> str:
    reg = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "correct-horse-9", "full_name": "Owner"},
    )
    client.headers.update({"Authorization": f"Bearer {reg.json()['access_token']}"})
    return client.post("/api/v1/workspaces", json={"name": "Acme"}).json()["id"]


def _add_paddle_sub(db: Session, workspace_id: str, *, management_url=None) -> None:
    db.add(
        BillingSubscription(
            workspace_id=UUID(workspace_id),
            plan_code="starter",
            source=SubscriptionSource.PADDLE,
            status=SubscriptionStatus.ACTIVE,
            external_subscription_id="sub_abc123",
            management_url=management_url,
        )
    )
    db.commit()


def test_manage_button_shows_without_stored_url(
    client: TestClient, db_session: Session
) -> None:
    workspace_id = _owner_workspace(client)
    _add_paddle_sub(db_session, workspace_id, management_url=None)

    status = client.get(f"/api/v1/workspaces/{workspace_id}/billing/status").json()
    # Even with no stored management_url, the button must show for a real sub.
    assert status["has_billing_customer"] is True
    assert status["subscription_status"] == "active"


def test_portal_resolves_management_url_on_demand(
    client: TestClient, db_session: Session, monkeypatch
) -> None:
    workspace_id = _owner_workspace(client)
    _add_paddle_sub(db_session, workspace_id, management_url=None)

    monkeypatch.setattr(
        paddle_billing,
        "fetch_subscription_management_url",
        lambda sid: f"https://paddle.example/cancel/{sid}",
    )

    resp = client.post(f"/api/v1/workspaces/{workspace_id}/billing/portal-session")
    assert resp.status_code == 201, resp.text
    assert resp.json()["url"] == "https://paddle.example/cancel/sub_abc123"

    # Resolved URL is cached on the subscription for next time.
    db_session.expire_all()
    sub = (
        db_session.query(BillingSubscription)
        .filter(BillingSubscription.workspace_id == UUID(workspace_id))
        .first()
    )
    assert sub.management_url == "https://paddle.example/cancel/sub_abc123"


def test_portal_uses_stored_url_when_present(
    client: TestClient, db_session: Session, monkeypatch
) -> None:
    workspace_id = _owner_workspace(client)
    _add_paddle_sub(db_session, workspace_id, management_url="https://paddle.example/stored")

    # Should NOT hit the API when a URL is already stored.
    def _boom(_sid):  # pragma: no cover — must not be called
        raise AssertionError("should not fetch when management_url is stored")

    monkeypatch.setattr(paddle_billing, "fetch_subscription_management_url", _boom)

    resp = client.post(f"/api/v1/workspaces/{workspace_id}/billing/portal-session")
    assert resp.status_code == 201
    assert resp.json()["url"] == "https://paddle.example/stored"


def test_webhook_captures_cancel_management_url(
    client: TestClient, db_session: Session
) -> None:
    workspace_id = _owner_workspace(client)
    billing_service._on_paddle_subscription_changed(
        db_session,
        {
            "id": "sub_xyz",
            "custom_data": {"workspace_id": workspace_id, "plan_code": "starter"},
            "items": [],
            "status": "active",
            "management_urls": {
                "update_payment_method": "https://paddle.example/update",
                "cancel": "https://paddle.example/cancel",
            },
        },
    )
    db_session.commit()

    sub = (
        db_session.query(BillingSubscription)
        .filter(BillingSubscription.workspace_id == UUID(workspace_id))
        .first()
    )
    assert sub is not None
    # Prefers the cancel deep-link.
    assert sub.management_url == "https://paddle.example/cancel"
