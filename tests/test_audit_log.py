"""Test suite for Audit Logging with Before/After State Diff."""
import json
from decimal import Decimal
import pytest
from app.auth import get_password_hash
from app.models import AuditLog, Organization, Room, RoomType, User
from tests.conftest import make_auth_headers


@pytest.mark.asyncio
async def test_room_update_creates_audit_log_entry(client, db_session):
    """Verify that updating a room generates a before/after state audit log entry."""
    org = Organization(name="Audit Test Hotel", slug="audit-test", plan="pro", subscription_status="active")
    db_session.add(org)
    db_session.commit()
    db_session.refresh(org)

    manager = User(
        email="manager@audit.com",
        username="audit_mgr",
        full_name="Audit Manager",
        role="manager",
        organization_id=org.id,
        is_active=True,
        hashed_password=get_password_hash("AdminPass123!"),
    )
    db_session.add(manager)

    rt = RoomType(organization_id=org.id, name="Deluxe", code="DLX", base_rate=Decimal("4000"), max_occupancy=2)
    db_session.add(rt)
    db_session.commit()

    rm = Room(organization_id=org.id, number="701", floor=7, room_type_id=rt.id, status="available", version=1)
    db_session.add(rm)
    db_session.commit()
    db_session.refresh(rm)

    headers = make_auth_headers(username="audit_mgr", role="manager", org_id=org.id)

    # Update room status
    resp = await client.patch(
        f"/api/rooms/{rm.id}/status",
        json={"status": "dirty", "notes": "Guest checked out", "version": 1},
        headers=headers,
    )
    assert resp.status_code == 200

    # Query audit logs
    log_resp = await client.get("/api/audit-log?entity_type=room", headers=headers)
    assert log_resp.status_code == 200
    logs = log_resp.json()
    assert len(logs) >= 1

    target_log = next((l for l in logs if l["entity_id"] == rm.id), None)
    assert target_log is not None
    assert target_log["action"] == "room_status_changed"

    before_state = json.loads(target_log["before_json"])
    after_state = json.loads(target_log["after_json"])
    assert before_state["status"] == "available"
    assert after_state["status"] == "dirty"
