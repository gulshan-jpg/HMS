"""Tests for Reservation Lifecycle: Overlap Detection, Check-in, Checkout, and Turnover."""
from datetime import date, timedelta
from decimal import Decimal
import pytest
from app.config import settings
from app.models import FolioItem, HousekeepingTask, Payment, Reservation, Room
from tests.conftest import make_auth_headers


@pytest.mark.asyncio
async def test_create_reservation_date_validation(client, seed_test_data):
    """Verify check_out must be strictly greater than check_in."""
    headers = make_auth_headers()
    today = date.today()

    resp = await client.post(
        "/api/reservations",
        json={
            "guest_id": seed_test_data["guest"].id,
            "room_id": seed_test_data["r101"].id,
            "check_in_date": today.isoformat(),
            "check_out_date": today.isoformat(),  # Same day checkout rejected
            "adults": 1,
        },
        headers=headers,
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_reservation_overlap_conflict_409(client, seed_test_data):
    """Verify overlapping active bookings for the same room return HTTP 409 Conflict."""
    headers = make_auth_headers()
    today = date.today()
    check_in = today + timedelta(days=5)
    check_out = today + timedelta(days=8)

    # 1. Create first valid booking
    res1 = await client.post(
        "/api/reservations",
        json={
            "guest_id": seed_test_data["guest"].id,
            "room_id": seed_test_data["r101"].id,
            "check_in_date": check_in.isoformat(),
            "check_out_date": check_out.isoformat(),
            "adults": 1,
        },
        headers=headers,
    )
    assert res1.status_code == 201

    # 2. Attempt overlapping booking on same room (overlap check_in to check_out)
    overlap_in = today + timedelta(days=6)
    overlap_out = today + timedelta(days=9)
    res2 = await client.post(
        "/api/reservations",
        json={
            "guest_id": seed_test_data["guest"].id,
            "room_id": seed_test_data["r101"].id,
            "check_in_date": overlap_in.isoformat(),
            "check_out_date": overlap_out.isoformat(),
            "adults": 1,
        },
        headers=headers,
    )
    assert res2.status_code == 409
    data = res2.json()
    assert "already booked" in data["error"]["message"].lower()


@pytest.mark.asyncio
async def test_check_in_flips_room_occupied_and_posts_charges(client, seed_test_data, db_session):
    """Verify check-in marks room occupied and automatically posts room charge & occupancy tax."""
    headers = make_auth_headers()
    today = date.today()
    tomorrow = today + timedelta(days=2)  # 2 nights

    booking_resp = await client.post(
        "/api/reservations",
        json={
            "guest_id": seed_test_data["guest"].id,
            "room_id": seed_test_data["r101"].id,
            "check_in_date": today.isoformat(),
            "check_out_date": tomorrow.isoformat(),
            "adults": 1,
            "nightly_rate": "129.00",
        },
        headers=headers,
    )
    assert booking_resp.status_code == 201
    res_id = booking_resp.json()["id"]

    # Perform check-in
    check_in_resp = await client.post(f"/api/reservations/{res_id}/check-in", headers=headers)
    assert check_in_resp.status_code == 200
    res_data = check_in_resp.json()
    assert res_data["status"] == "checked_in"

    # Verify room is now marked 'occupied'
    room = db_session.query(Room).filter(Room.id == seed_test_data["r101"].id).first()
    assert room.status == "occupied"

    # Verify folio charges were posted
    folio_items = db_session.query(FolioItem).filter(FolioItem.reservation_id == res_id).all()
    assert len(folio_items) == 2
    room_charge = next(item for item in folio_items if item.category == "room")
    tax_charge = next(item for item in folio_items if item.category == "tax")
    assert Decimal(str(room_charge.amount)) == Decimal("258.00")
    expected_tax = round(Decimal("258.00") * Decimal(str(settings.HOTEL_TAX_RATE)), 2)
    assert Decimal(str(tax_charge.amount)) == expected_tax


@pytest.mark.asyncio
async def test_checkout_blocked_by_unsettled_balance(client, seed_test_data):
    """Verify departure is prevented if folio has an outstanding balance."""
    headers = make_auth_headers()
    today = date.today()
    tomorrow = today + timedelta(days=1)

    booking_resp = await client.post(
        "/api/reservations",
        json={
            "guest_id": seed_test_data["guest"].id,
            "room_id": seed_test_data["r102"].id,
            "check_in_date": today.isoformat(),
            "check_out_date": tomorrow.isoformat(),
            "adults": 1,
            "nightly_rate": "100.00",
        },
        headers=headers,
    )
    res_id = booking_resp.json()["id"]

    # Check in
    await client.post(f"/api/reservations/{res_id}/check-in", headers=headers)

    # Attempt check-out while balance > 0 ($110.00)
    checkout_resp = await client.post(f"/api/reservations/{res_id}/check-out", headers=headers)
    assert checkout_resp.status_code == 400
    assert "outstanding folio balance" in checkout_resp.json()["error"]["message"].lower()


@pytest.mark.asyncio
async def test_checkout_succeeds_when_settled_and_triggers_housekeeping(client, seed_test_data, db_session):
    """Verify checkout succeeds when fully settled, marks room dirty, and creates turnover task."""
    headers = make_auth_headers()
    today = date.today()
    tomorrow = today + timedelta(days=1)

    booking_resp = await client.post(
        "/api/reservations",
        json={
            "guest_id": seed_test_data["guest"].id,
            "room_id": seed_test_data["r201"].id,
            "check_in_date": today.isoformat(),
            "check_out_date": tomorrow.isoformat(),
            "adults": 1,
            "nightly_rate": "100.00",
        },
        headers=headers,
    )
    res_id = booking_resp.json()["id"]

    # Check in
    await client.post(f"/api/reservations/{res_id}/check-in", headers=headers)

    # Total posted is room + tax. Post exact payment to settle folio
    expected_tax = round(Decimal("100.00") * Decimal(str(settings.HOTEL_TAX_RATE)), 2)
    total_due = Decimal("100.00") + expected_tax
    pmt_resp = await client.post(
        f"/api/billing/reservations/{res_id}/payments",
        json={
            "date": today.isoformat(),
            "amount": str(total_due),
            "method": "credit_card",
            "reference": "TEST-AUTH-999",
        },
        headers=headers,
    )
    assert pmt_resp.status_code == 201

    # Check out guest
    checkout_resp = await client.post(f"/api/reservations/{res_id}/check-out", headers=headers)
    assert checkout_resp.status_code == 200
    assert checkout_resp.json()["status"] == "checked_out"

    # Verify room flipped to 'dirty'
    room = db_session.query(Room).filter(Room.id == seed_test_data["r201"].id).first()
    assert room.status == "dirty"

    # Verify housekeeping turnover task was generated
    task = db_session.query(HousekeepingTask).filter(HousekeepingTask.room_id == room.id).first()
    assert task is not None
    assert task.task_type == "checkout_clean"
    assert task.status == "pending"


@pytest.mark.asyncio
async def test_cancel_reservation(client, seed_test_data):
    """Verify reservation cancellation releases booking status."""
    headers = make_auth_headers()
    today = date.today()
    check_in = today + timedelta(days=10)
    check_out = today + timedelta(days=12)

    res = await client.post(
        "/api/reservations",
        json={
            "guest_id": seed_test_data["guest"].id,
            "room_id": seed_test_data["r101"].id,
            "check_in_date": check_in.isoformat(),
            "check_out_date": check_out.isoformat(),
            "adults": 1,
        },
        headers=headers,
    )
    res_id = res.json()["id"]

    cancel_resp = await client.post(f"/api/reservations/{res_id}/cancel", headers=headers)
    assert cancel_resp.status_code == 200
    assert cancel_resp.json()["status"] == "cancelled"
