"""Test suite for Trial Expiration and Write Locking."""
from datetime import datetime, timedelta, timezone
import pytest
from app.auth import get_password_hash
from app.models import Organization, Room, RoomType, User
from tests.conftest import make_auth_headers


@pytest.mark.asyncio
async def test_locked_trial_blocks_write_requests_but_allows_reads(client, db_session):
    """Verify that when an organization trial has ended and status is locked, POST/PUT return 402 while GET succeeds."""
    org = Organization(
        name="Expired Trial Hotel",
        slug="expired-trial-hotel",
        plan="starter",
        subscription_status="locked",
        trial_ends_at=datetime.now(timezone.utc) - timedelta(days=2),
    )
    db_session.add(org)
    db_session.commit()
    db_session.refresh(org)

    owner = User(
        email="expired@hotel.com",
        username="expired_owner",
        full_name="Expired Owner",
        role="owner",
        organization_id=org.id,
        is_active=True,
        hashed_password=get_password_hash("AdminPass123!"),
    )
    db_session.add(owner)
    db_session.commit()

    rt = RoomType(
        organization_id=org.id,
        name="Cozy Room",
        code="CZY",
        base_rate=3000,
        max_occupancy=2,
    )
    db_session.add(rt)
    db_session.commit()

    headers = make_auth_headers(username="expired_owner", role="owner", org_id=org.id)

    # 1. GET requests must succeed
    get_resp = await client.get("/api/rooms", headers=headers)
    assert get_resp.status_code == 200, f"Expected 200 for read, got {get_resp.status_code}"

    # 2. Write request (POST /api/rooms) must be blocked with 402 Payment Required
    post_resp = await client.post(
        "/api/rooms",
        json={"number": "301", "floor": 3, "room_type_id": rt.id, "status": "available"},
        headers=headers,
    )
    assert post_resp.status_code == 402, f"Expected 402 write lock, got {post_resp.status_code}"
    data = post_resp.json()
    err_obj = data.get("error", data.get("detail", {}).get("error", {}))
    assert err_obj.get("code") in ["trial_expired", "subscription_locked"]
