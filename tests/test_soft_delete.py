"""Test suite for Soft Delete, Trash Bin, and Record Restoration."""
from datetime import date, timedelta
from decimal import Decimal
import pytest
from app.auth import get_password_hash
from app.models import Guest, Organization, Reservation, Room, RoomType, User
from tests.conftest import make_auth_headers


@pytest.mark.asyncio
async def test_soft_delete_and_restore_cycle(client, db_session):
    """Verify that deleting an entity sets deleted_at, hides it from active queries, and restore recovers it."""
    org = Organization(name="Trash Test Hotel", slug="trash-test", plan="pro", subscription_status="active")
    db_session.add(org)
    db_session.commit()
    db_session.refresh(org)

    owner = User(
        email="owner@trashtest.com",
        username="trash_owner",
        full_name="Trash Owner",
        role="owner",
        organization_id=org.id,
        is_active=True,
        hashed_password=get_password_hash("AdminPass123!"),
    )
    db_session.add(owner)

    rt = RoomType(organization_id=org.id, name="Ocean Suite", code="OS", base_rate=Decimal("8000"), max_occupancy=2)
    db_session.add(rt)
    db_session.commit()

    rm = Room(organization_id=org.id, number="901", floor=9, room_type_id=rt.id, status="available")
    db_session.add(rm)
    db_session.commit()
    db_session.refresh(rm)

    headers = make_auth_headers(username="trash_owner", role="owner", org_id=org.id)

    # 1. Soft delete room via trash endpoint
    del_resp = await client.delete(f"/api/rooms/{rm.id}", headers=headers)
    assert del_resp.status_code == 200

    # Verify room is hidden from active room queries
    list_resp = await client.get("/api/rooms", headers=headers)
    assert list_resp.status_code == 200
    active_rooms = list_resp.json()["items"]
    assert all(r["number"] != "901" for r in active_rooms)

    # 2. Verify room appears in trash bin
    trash_resp = await client.get("/api/trash", headers=headers)
    assert trash_resp.status_code == 200
    trash_data = trash_resp.json()
    assert any(r["id"] == rm.id for r in trash_data.get("rooms", []))

    # 3. Restore room from trash
    restore_resp = await client.post(f"/api/rooms/{rm.id}/restore", headers=headers)
    assert restore_resp.status_code == 200

    # 4. Verify room is back in active list
    relist_resp = await client.get("/api/rooms", headers=headers)
    relist_rooms = relist_resp.json()["items"]
    assert any(r["number"] == "901" for r in relist_rooms)
