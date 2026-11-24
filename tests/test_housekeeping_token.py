"""Test suite for Mobile Housekeeping Token & Public View."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import pytest
from jose import jwt
from app.auth import get_password_hash
from app.config import settings
from app.models import HousekeepingTask, Organization, Room, RoomType, User
from tests.conftest import make_auth_headers


@pytest.mark.asyncio
async def test_mobile_housekeeping_token_lifecycle(client, db_session):
    """Verify generating 24h share token, reading floor dashboard without login, and updating room status."""
    org = Organization(name="Housekeeping Test Hotel", slug="hk-hotel", plan="pro", subscription_status="active")
    db_session.add(org)
    db_session.commit()
    db_session.refresh(org)

    manager = User(
        email="mgr@hk.com",
        username="hk_mgr",
        full_name="HK Manager",
        role="manager",
        organization_id=org.id,
        is_active=True,
        hashed_password=get_password_hash("AdminPass123!"),
    )
    db_session.add(manager)

    rt = RoomType(organization_id=org.id, name="Standard", code="STD", base_rate=Decimal("3500"), max_occupancy=2)
    db_session.add(rt)
    db_session.commit()

    rm1 = Room(organization_id=org.id, number="101", floor=1, room_type_id=rt.id, status="dirty")
    rm2 = Room(organization_id=org.id, number="201", floor=2, room_type_id=rt.id, status="available")
    db_session.add_all([rm1, rm2])
    db_session.commit()
    db_session.refresh(rm1)

    headers = make_auth_headers(username="hk_mgr", role="manager", org_id=org.id)

    # 1. Manager generates signed 24h share token
    token_resp = await client.post("/api/housekeeping/generate-share-token", headers=headers)
    assert token_resp.status_code == 200, token_resp.text
    token_data = token_resp.json()
    token = token_data["token"]
    assert "/hk/" in token_data["share_url"]

    # 2. Public cleaning staff opens token URL (no authorization header needed!)
    public_resp = await client.get(f"/api/housekeeping/token/{token}")
    assert public_resp.status_code == 200, public_resp.text
    board = public_resp.json()
    assert board["org"]["name"] == "Housekeeping Test Hotel"
    assert board["total_rooms"] == 2
    assert board["dirty_count"] == 1
    assert len(board["floors"]) == 2

    # 3. Staff marks Room 101 as clean with one tap
    clean_resp = await client.post(
        f"/api/housekeeping/token/{token}/room/{rm1.id}/status",
        json={"status": "clean"},
    )
    assert clean_resp.status_code == 200
    db_session.refresh(rm1)
    assert rm1.status == "clean"

    # 4. Staff reports a maintenance issue
    maint_resp = await client.post(
        f"/api/housekeeping/token/{token}/room/{rm1.id}/maintenance",
        json={"notes": "Bathroom exhaust fan noisy", "priority": "medium"},
    )
    assert maint_resp.status_code == 200
    maint_data = maint_resp.json()
    assert maint_data["success"] is True

    # 5. Verify expired token is rejected with 401
    expired_payload = {
        "sub": "mobile_hk",
        "org_id": org.id,
        "exp": datetime.now(timezone.utc) - timedelta(hours=1),
    }
    expired_token = jwt.encode(expired_payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    bad_resp = await client.get(f"/api/housekeeping/token/{expired_token}")
    assert bad_resp.status_code == 401
