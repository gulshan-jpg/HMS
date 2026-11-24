"""Test suite for Optimistic Concurrency Control (Version Locking)."""
from datetime import date, timedelta
from decimal import Decimal
import pytest
from app.auth import get_password_hash
from app.models import Guest, Organization, Reservation, Room, RoomType, User
from tests.conftest import make_auth_headers


@pytest.mark.asyncio
async def test_optimistic_locking_detects_concurrent_write_conflicts(client, db_session):
    """Verify that updating with an outdated version returns 409 Conflict with code 'conflict'."""
    org = Organization(name="Concurrency Hotel", slug="concurrency-hotel", plan="pro", subscription_status="active")
    db_session.add(org)
    db_session.commit()
    db_session.refresh(org)

    staff = User(
        email="staff@concurrency.com",
        username="concurrency_staff",
        full_name="Front Desk Staff",
        role="front_desk",
        organization_id=org.id,
        is_active=True,
        hashed_password=get_password_hash("AdminPass123!"),
    )
    db_session.add(staff)

    rt = RoomType(organization_id=org.id, name="Deluxe", code="DLX", base_rate=Decimal("5000"), max_occupancy=2)
    db_session.add(rt)
    db_session.commit()

    rm = Room(organization_id=org.id, number="501", floor=5, room_type_id=rt.id, status="available", version=1)
    db_session.add(rm)
    db_session.commit()
    db_session.refresh(rm)

    headers = make_auth_headers(username="concurrency_staff", role="front_desk", org_id=org.id)

    # 1. First user updates room status with matching version=1 -> Succeeds and increments version to 2
    resp1 = await client.patch(
        f"/api/rooms/{rm.id}/status",
        json={"status": "dirty", "version": 1},
        headers=headers,
    )
    assert resp1.status_code == 200
    db_session.refresh(rm)
    assert rm.version == 2
    assert rm.status == "dirty"

    # 2. Second concurrent user submits write with stale version=1 -> Fails with 409 Conflict
    resp2 = await client.patch(
        f"/api/rooms/{rm.id}/status",
        json={"status": "available", "version": 1},
        headers=headers,
    )
    assert resp2.status_code == 409, f"Expected 409 Conflict, got {resp2.status_code}: {resp2.text}"
    err = resp2.json()
    err_obj = err.get("error", err.get("detail", {}).get("error", {}))
    assert err_obj.get("code") == "conflict"
    assert "another user" in err_obj.get("message", "").lower()
