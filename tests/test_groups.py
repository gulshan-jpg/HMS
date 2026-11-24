"""Tests for Group Bookings, Room Blocks, Cutoff Dates, and Master Folio Aggregation."""
from datetime import date, timedelta
from decimal import Decimal
import pytest
from tests.conftest import make_auth_headers
from app.models import BookingGroup, GroupBlock, Reservation


@pytest.mark.asyncio
async def test_create_and_list_booking_groups(client, seed_test_data):
    """Test creating a group booking with room blocks and listing groups."""
    headers = make_auth_headers(role="admin")
    today = date.today()
    check_in = today + timedelta(days=14)
    check_out = today + timedelta(days=18)
    cutoff = today + timedelta(days=7)
    rt_std_id = seed_test_data["rt_std"].id
    rt_dlx_id = seed_test_data["rt_dlx"].id

    payload = {
        "name": "Global Tech Conference",
        "contact_name": "Marcus Aurelius",
        "contact_email": "marcus@technova.org",
        "contact_phone": "+919876543210",
        "check_in": check_in.isoformat(),
        "check_out": check_out.isoformat(),
        "cutoff_date": cutoff.isoformat(),
        "notes": "Requires AV equipment and high-speed Wi-Fi",
        "room_blocks": [
            {"room_type_id": rt_std_id, "count": 5, "rate": "120.00"},
            {"room_type_id": rt_dlx_id, "count": 3, "rate": "180.00"},
        ],
    }

    create_resp = await client.post("/api/groups", json=payload, headers=headers)
    assert create_resp.status_code == 201
    group_data = create_resp.json()
    assert group_data["name"] == "Global Tech Conference"
    assert group_data["status"] == "confirmed"
    assert group_data["rooms_blocked_total"] == 8
    assert group_data["rooms_picked_up_total"] == 0
    assert len(group_data["room_blocks"]) == 2
    group_id = group_data["id"]

    # List groups
    list_resp = await client.get("/api/groups", headers=headers)
    assert list_resp.status_code == 200
    groups = list_resp.json()
    assert any(g["id"] == group_id for g in groups)

    # Filter groups
    filtered_resp = await client.get("/api/groups?status_filter=confirmed", headers=headers)
    assert filtered_resp.status_code == 200
    assert any(g["id"] == group_id for g in filtered_resp.json())


@pytest.mark.asyncio
async def test_group_reservation_pickup_and_master_folio(client, seed_test_data):
    """Test picking up reservations under a group and aggregating master folio metrics."""
    headers = make_auth_headers(role="admin")
    today = date.today()
    check_in = today + timedelta(days=5)
    check_out = today + timedelta(days=7)
    cutoff = today + timedelta(days=2)
    rt_std_id = seed_test_data["rt_std"].id

    # 1. Create group
    grp_resp = await client.post(
        "/api/groups",
        json={
            "name": "Acme Offsite Retreat",
            "contact_name": "Sarah Connor",
            "contact_email": "sarah@cyberdyne.com",
            "contact_phone": "+919876543211",
            "check_in": check_in.isoformat(),
            "check_out": check_out.isoformat(),
            "cutoff_date": cutoff.isoformat(),
            "room_blocks": [
                {"room_type_id": rt_std_id, "count": 2, "rate": "110.00"},
            ],
        },
        headers=headers,
    )
    assert grp_resp.status_code == 201
    group_id = grp_resp.json()["id"]

    # 2. Pick up a reservation for room 101 under this group
    res_resp = await client.post(
        "/api/reservations",
        json={
            "guest_id": seed_test_data["guest"].id,
            "room_id": seed_test_data["r101"].id,
            "group_id": group_id,
            "check_in_date": check_in.isoformat(),
            "check_out_date": check_out.isoformat(),
            "adults": 1,
            "nightly_rate": "110.00",
        },
        headers=headers,
    )
    assert res_resp.status_code == 201
    res_id = res_resp.json()["id"]

    # 3. Post charges and payments to reservation
    charge_resp = await client.post(
        f"/api/billing/reservations/{res_id}/charges",
        json={
            "date": check_in.isoformat(),
            "description": "Group Room Charge",
            "category": "room",
            "amount": "220.00",
        },
        headers=headers,
    )
    assert charge_resp.status_code == 201

    pay_resp = await client.post(
        f"/api/billing/reservations/{res_id}/payments",
        json={
            "date": check_in.isoformat(),
            "amount": "100.00",
            "method": "credit_card",
        },
        headers=headers,
    )
    assert pay_resp.status_code == 201

    # 4. Fetch group details: verify pickup & master folio totals
    detail_resp = await client.get(f"/api/groups/{group_id}", headers=headers)
    assert detail_resp.status_code == 200
    detail = detail_resp.json()
    assert detail["rooms_picked_up_total"] == 1
    assert len(detail["reservations"]) == 1
    assert detail["reservations"][0]["id"] == res_id
    assert Decimal(str(detail["master_folio_total"])) == Decimal("220.00")
    assert Decimal(str(detail["master_folio_paid"])) == Decimal("100.00")
    assert Decimal(str(detail["master_folio_balance"])) == Decimal("120.00")


@pytest.mark.asyncio
async def test_group_detach_reservation_and_cancel_group(client, seed_test_data, db_session):
    """Test detaching a reservation from a group and cancelling the entire group."""
    headers = make_auth_headers(role="admin")
    today = date.today()
    check_in = today + timedelta(days=20)
    check_out = today + timedelta(days=22)
    cutoff = today + timedelta(days=10)
    rt_std_id = seed_test_data["rt_std"].id

    grp_resp = await client.post(
        "/api/groups",
        json={
            "name": "Wedding Party Sharma",
            "contact_name": "Raj Sharma",
            "contact_email": "raj@example.com",
            "contact_phone": "+919876543212",
            "check_in": check_in.isoformat(),
            "check_out": check_out.isoformat(),
            "cutoff_date": cutoff.isoformat(),
            "room_blocks": [
                {"room_type_id": rt_std_id, "count": 3, "rate": "130.00"},
            ],
        },
        headers=headers,
    )
    group_id = grp_resp.json()["id"]

    res_resp = await client.post(
        "/api/reservations",
        json={
            "guest_id": seed_test_data["guest"].id,
            "room_id": seed_test_data["r101"].id,
            "group_id": group_id,
            "check_in_date": check_in.isoformat(),
            "check_out_date": check_out.isoformat(),
            "adults": 1,
            "nightly_rate": "130.00",
        },
        headers=headers,
    )
    res_id = res_resp.json()["id"]

    # Detach reservation from group
    detach_resp = await client.delete(f"/api/groups/{group_id}/reservations/{res_id}", headers=headers)
    assert detach_resp.status_code == 200

    # Verify reservation has no group_id
    db_session.expire_all()
    res = db_session.query(Reservation).filter(Reservation.id == res_id).first()
    assert res.group_id is None

    # Cancel group
    cancel_resp = await client.post(f"/api/groups/{group_id}/cancel", headers=headers)
    assert cancel_resp.status_code == 200
    assert cancel_resp.json()["status"] == "cancelled"
