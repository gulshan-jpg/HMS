"""Test suite for Row-Level Tenant Isolation."""
from datetime import date, timedelta
from decimal import Decimal
import pytest
from app.auth import get_password_hash
from app.models import Guest, Organization, Reservation, Room, RoomType, User
from tests.conftest import make_auth_headers


@pytest.mark.asyncio
async def test_tenant_cannot_access_other_organization_data(client, db_session):
    """Verify strict multi-tenant isolation: User in Org A cannot view or manipulate Org B's records."""
    # Organization A
    org_a = Organization(name="Hotel Alpha", slug="hotel-alpha", plan="pro", subscription_status="active")
    db_session.add(org_a)
    db_session.commit()
    db_session.refresh(org_a)

    user_a = User(
        email="staff@alpha.com",
        username="staff_alpha",
        full_name="Alpha Staff",
        role="front_desk",
        organization_id=org_a.id,
        is_active=True,
        hashed_password=get_password_hash("AdminPass123!"),
    )
    db_session.add(user_a)

    rt_a = RoomType(organization_id=org_a.id, name="Alpha King", code="AK", base_rate=Decimal("6000"), max_occupancy=2)
    db_session.add(rt_a)
    db_session.commit()

    rm_a = Room(organization_id=org_a.id, number="A101", floor=1, room_type_id=rt_a.id, status="available")
    guest_a = Guest(organization_id=org_a.id, first_name="Alpha", last_name="Guest", email="alpha@guest.com", phone="+919876543210")
    db_session.add_all([rm_a, guest_a])
    db_session.commit()

    today = date.today()
    res_a = Reservation(
        organization_id=org_a.id,
        guest_id=guest_a.id,
        room_id=rm_a.id,
        confirmation_number="HTL-ALPHA1",
        check_in_date=today,
        check_out_date=today + timedelta(days=2),
        adults=2,
        children=0,
        nightly_rate=Decimal("6000"),
        status="booked",
    )
    db_session.add(res_a)
    db_session.commit()
    db_session.refresh(res_a)

    # Organization B
    org_b = Organization(name="Hotel Beta", slug="hotel-beta", plan="pro", subscription_status="active")
    db_session.add(org_b)
    db_session.commit()
    db_session.refresh(org_b)

    user_b = User(
        email="staff@beta.com",
        username="staff_beta",
        full_name="Beta Staff",
        role="front_desk",
        organization_id=org_b.id,
        is_active=True,
        hashed_password=get_password_hash("AdminPass123!"),
    )
    db_session.add(user_b)
    db_session.commit()

    headers_b = make_auth_headers(username="staff_beta", role="front_desk", org_id=org_b.id)

    # 1. User B lists reservations: Must not see Alpha's reservation
    list_resp = await client.get("/api/reservations", headers=headers_b)
    assert list_resp.status_code == 200
    b_reservations = list_resp.json()["items"]
    assert all(r["confirmation_number"] != "HTL-ALPHA1" for r in b_reservations)

    # 2. User B tries to fetch Alpha's reservation directly by ID: Must return 404
    direct_resp = await client.get(f"/api/reservations/{res_a.id}", headers=headers_b)
    assert direct_resp.status_code == 404, f"Expected 404 for cross-tenant query, got {direct_resp.status_code}"
