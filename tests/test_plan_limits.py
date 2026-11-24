"""Test suite for Plan Limits enforcement (Starter: 15 rooms, Pro: 50 rooms)."""
import pytest
from app.auth import get_password_hash
from app.models import Organization, Room, RoomType, User
from tests.conftest import make_auth_headers


@pytest.mark.asyncio
async def test_starter_plan_rejects_sixteenth_room(client, db_session):
    """Verify starter plan enforces maximum 15 rooms and returns 402 plan_limit on 16th room."""
    # Create starter organization
    org = Organization(
        name="Small Boutique Stay",
        slug="small-boutique",
        plan="starter",
        subscription_status="active",
    )
    db_session.add(org)
    db_session.commit()
    db_session.refresh(org)

    owner = User(
        email="owner@smallboutique.com",
        username="boutique_owner",
        full_name="Boutique Owner",
        role="owner",
        organization_id=org.id,
        is_active=True,
        hashed_password=get_password_hash("AdminPass123!"),
    )
    db_session.add(owner)
    db_session.commit()

    rt = RoomType(
        organization_id=org.id,
        name="Standard Suite",
        code="STD",
        base_rate=4500,
        max_occupancy=2,
    )
    db_session.add(rt)
    db_session.commit()

    # Pre-populate 15 rooms
    for i in range(1, 16):
        db_session.add(Room(
            organization_id=org.id,
            number=f"1{i:02d}",
            floor=1,
            room_type_id=rt.id,
            status="available",
        ))
    db_session.commit()

    headers = make_auth_headers(username="boutique_owner", role="owner", org_id=org.id)

    # Attempt to create 16th room
    resp = await client.post(
        "/api/rooms",
        json={"number": "201", "floor": 2, "room_type_id": rt.id, "status": "available"},
        headers=headers,
    )

    assert resp.status_code == 402, f"Expected 402, got {resp.status_code}: {resp.text}"
    err = resp.json()
    err_obj = err.get("error", err.get("detail", {}).get("error", {}))
    assert err_obj.get("code") == "plan_limit"
    assert "upgrade" in err_obj.get("message", "").lower()
