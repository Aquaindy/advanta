from fastapi.testclient import TestClient

from app.billing.plans import PLANS


def _auth_client(client: TestClient, email: str) -> tuple[TestClient, str]:
    response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "correct-horse-9", "full_name": email},
    )
    assert response.status_code == 201
    token = response.json()["access_token"]
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client, token


def test_list_workspaces_starts_empty(client: TestClient) -> None:
    _auth_client(client, "alice@example.com")
    response = client.get("/api/v1/workspaces")
    assert response.status_code == 200
    assert response.json() == []


def test_create_workspace_makes_creator_owner(client: TestClient) -> None:
    _auth_client(client, "alice@example.com")

    response = client.post("/api/v1/workspaces", json={"name": "Acme Marketing"})
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Acme Marketing"
    assert body["slug"].startswith("acme-marketing")
    assert body["role"] == "owner"
    assert body["status"] == "active"

    listing = client.get("/api/v1/workspaces").json()
    assert len(listing) == 1
    assert listing[0]["id"] == body["id"]


def test_get_workspace_requires_membership(client: TestClient) -> None:
    _auth_client(client, "alice@example.com")
    workspace = client.post("/api/v1/workspaces", json={"name": "Owner Org"}).json()

    # Different user — no membership
    other = TestClient(client.app)
    other.post(
        "/api/v1/auth/register",
        json={"email": "bob@example.com", "password": "correct-horse-9"},
    )
    other_token = other.cookies.get("advanta_refresh") and None  # not used
    bob_token = (
        other.post(
            "/api/v1/auth/login",
            json={"email": "bob@example.com", "password": "correct-horse-9"},
        )
        .json()["access_token"]
    )
    other.headers.update({"Authorization": f"Bearer {bob_token}"})

    response = other.get(f"/api/v1/workspaces/{workspace['id']}")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "workspace_not_found"


def test_patch_workspace_updates_name(client: TestClient) -> None:
    _auth_client(client, "alice@example.com")
    workspace = client.post("/api/v1/workspaces", json={"name": "Original"}).json()

    response = client.patch(
        f"/api/v1/workspaces/{workspace['id']}",
        json={"name": "Renamed"},
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Renamed"


def test_list_members_returns_owner(client: TestClient) -> None:
    _auth_client(client, "alice@example.com")
    workspace = client.post("/api/v1/workspaces", json={"name": "Single Member"}).json()

    response = client.get(f"/api/v1/workspaces/{workspace['id']}/members")
    assert response.status_code == 200
    members = response.json()
    assert len(members) == 1
    assert members[0]["email"] == "alice@example.com"
    assert members[0]["role"] == "owner"


def test_cannot_demote_sole_owner(client: TestClient) -> None:
    _auth_client(client, "alice@example.com")
    workspace = client.post("/api/v1/workspaces", json={"name": "Solo"}).json()
    members = client.get(f"/api/v1/workspaces/{workspace['id']}/members").json()
    owner_member_id = members[0]["id"]

    response = client.patch(
        f"/api/v1/workspaces/{workspace['id']}/members/{owner_member_id}",
        json={"role": "admin"},
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "cannot_demote_sole_owner"


def test_invite_member_creates_pending_invitation(client: TestClient) -> None:
    """`/members/invite` mints a pending WorkspaceInvitation row + emails the
    invitee. We don't assert delivery here (covered by email_service tests);
    we pin the contract."""

    _auth_client(client, "alice@example.com")
    workspace = client.post("/api/v1/workspaces", json={"name": "InviteTest"}).json()

    response = client.post(
        f"/api/v1/workspaces/{workspace['id']}/members/invite",
        json={"email": "bob@example.com", "role": "marketer"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["email"] == "bob@example.com"
    assert body["role"] == "marketer"
    assert body["status"] == "pending"
    assert body["expires_at"] is not None


def test_superuser_bypasses_seat_cap(client: TestClient) -> None:
    """A superuser hitting an interactive request bypasses plan-limit
    assertions. Once the workspace is at its free seat cap a normal owner's
    next invite 402s — for a superuser it still succeeds.

    The flag is per-request (ContextVar) and only fires for bearer tokens, so
    we verify the bypass via the live invite endpoint."""

    from app.models.user import User
    from tests.conftest import TestSessionLocal

    cap = PLANS["free"].limits.members
    assert cap is not None

    _auth_client(client, "alice-su@example.com")
    workspace = client.post(
        "/api/v1/workspaces", json={"name": "SuperuserBypass"}
    ).json()
    workspace_id = workspace["id"]

    # Fill to the cap as the owner: owner (1 active) + (cap-1) pending invites.
    for i in range(cap - 1):
        ok = client.post(
            f"/api/v1/workspaces/{workspace_id}/members/invite",
            json={"email": f"seat{i}@example.com", "role": "marketer"},
        )
        assert ok.status_code == 200, ok.text

    # Promote alice to superuser AFTER she's logged in. The next request
    # picks up the new flag because get_current_user re-reads the row.
    s = TestSessionLocal()
    try:
        u = s.query(User).filter(User.email == "alice-su@example.com").first()
        u.is_superuser = True
        s.commit()
    finally:
        s.close()

    # At the cap — a normal owner would 402, but the superuser bypass mints it.
    over = client.post(
        f"/api/v1/workspaces/{workspace_id}/members/invite",
        json={"email": "over-cap@example.com", "role": "marketer"},
    )
    assert over.status_code == 200, over.text


def test_invite_blocked_when_seat_cap_reached(client: TestClient) -> None:
    """A new workspace defaults to the free plan. The owner is 1 active seat;
    invites fill the remaining seats, and the invite that would exceed the cap
    is blocked at invite-time with `plan_limit_exceeded`."""

    cap = PLANS["free"].limits.members
    assert cap is not None

    _auth_client(client, "alice@example.com")
    workspace = client.post("/api/v1/workspaces", json={"name": "SeatCap"}).json()
    workspace_id = workspace["id"]

    # owner (1) + (cap-1) invites = cap, all within the limit.
    for i in range(cap - 1):
        ok = client.post(
            f"/api/v1/workspaces/{workspace_id}/members/invite",
            json={"email": f"seat{i}@example.com", "role": "marketer"},
        )
        assert ok.status_code == 200, ok.text

    blocked = client.post(
        f"/api/v1/workspaces/{workspace_id}/members/invite",
        json={"email": "over-cap@example.com", "role": "marketer"},
    )
    assert blocked.status_code == 402, blocked.text
    assert blocked.json()["error"]["code"] == "plan_limit_exceeded"
    # Error message should name the cap so the user knows what to do.
    assert "member" in blocked.json()["error"]["message"].lower()


def test_revoking_pending_invite_frees_a_seat(client: TestClient) -> None:
    """Revoked invitations don't count toward the seat cap, so once a
    pending invite is revoked the workspace can issue another one."""

    cap = PLANS["free"].limits.members
    assert cap is not None

    _auth_client(client, "alice@example.com")
    workspace = client.post("/api/v1/workspaces", json={"name": "SeatCap2"}).json()
    workspace_id = workspace["id"]

    # Fill to the cap.
    invites = []
    for i in range(cap - 1):
        resp = client.post(
            f"/api/v1/workspaces/{workspace_id}/members/invite",
            json={"email": f"seat{i}@example.com", "role": "marketer"},
        )
        assert resp.status_code == 200, resp.text
        invites.append(resp.json())

    # At the cap — the next invite is blocked.
    blocked = client.post(
        f"/api/v1/workspaces/{workspace_id}/members/invite",
        json={"email": "over-cap@example.com", "role": "marketer"},
    )
    assert blocked.status_code == 402

    # Revoke one pending invite — frees a seat.
    revoke = client.post(
        f"/api/v1/workspaces/{workspace_id}/members/invitations/{invites[0]['id']}/revoke"
    )
    assert revoke.status_code == 200, revoke.text

    # Now an invite succeeds again.
    retry = client.post(
        f"/api/v1/workspaces/{workspace_id}/members/invite",
        json={"email": "over-cap@example.com", "role": "marketer"},
    )
    assert retry.status_code == 200, retry.text
