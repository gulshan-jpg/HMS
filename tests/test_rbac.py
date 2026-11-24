"""Tests for Role-Based Access Control (RBAC) - Admin vs Staff Privileges & Data Filtering."""
from datetime import date, timedelta
from decimal import Decimal
import pytest
from tests.conftest import make_auth_headers


@pytest.mark.asyncio
async def test_staff_dashboard_hides_revenue(client, seed_test_data):
    """Staff accounts should see operational arrivals/occupancy but 0.00 for revenue metrics."""
    staff_headers = make_auth_headers(username="staff", role="front_desk")
    admin_headers = make_auth_headers(username="admin", role="admin")

    # Call dashboard as staff
    staff_resp = await client.get("/api/dashboard", headers=staff_headers)
    assert staff_resp.status_code == 200
    staff_data = staff_resp.json()

    # Revenue fields must be suppressed for staff
    assert Decimal(str(staff_data["revenue_today"])) == Decimal("0.00")
    assert staff_data["revenue_trend_pct"] == 0.0

    # Operational fields must remain fully accessible
    assert "arrivals_total" in staff_data
    assert "departures_total" in staff_data
    assert "room_status_summary" in staff_data
    assert "today_arrivals" in staff_data
    assert "today_departures" in staff_data


@pytest.mark.asyncio
async def test_staff_cannot_create_room_403(client, seed_test_data):
    """Staff cannot create rooms or modify property inventory."""
    staff_headers = make_auth_headers(username="staff", role="front_desk")
    admin_headers = make_auth_headers(username="admin", role="admin")

    payload = {
        "number": "301",
        "floor": 3,
        "room_type_id": seed_test_data["rt_std"].id,
        "status": "available",
        "notes": "Penthouse suite",
    }

    # Staff forbidden
    staff_resp = await client.post("/api/rooms", json=payload, headers=staff_headers)
    assert staff_resp.status_code == 403

    # Admin allowed
    admin_resp = await client.post("/api/rooms", json=payload, headers=admin_headers)
    assert admin_resp.status_code == 201
    assert admin_resp.json()["number"] == "301"


@pytest.mark.asyncio
async def test_staff_cannot_cancel_reservation_403(client, seed_test_data):
    """Staff cannot cancel existing reservations."""
    admin_headers = make_auth_headers(username="admin", role="admin")
    staff_headers = make_auth_headers(username="staff", role="front_desk")
    today = date.today()
    tomorrow = today + timedelta(days=2)

    # Admin books a room
    booking_resp = await client.post(
        "/api/reservations",
        json={
            "guest_id": seed_test_data["guest"].id,
            "room_id": seed_test_data["r102"].id,
            "check_in_date": today.isoformat(),
            "check_out_date": tomorrow.isoformat(),
            "adults": 1,
            "nightly_rate": "129.00",
        },
        headers=admin_headers,
    )
    res_id = booking_resp.json()["id"]

    # Staff attempt to cancel must return 403 Forbidden
    cancel_resp = await client.post(f"/api/reservations/{res_id}/cancel", headers=staff_headers)
    assert cancel_resp.status_code == 403

    # Admin cancellation succeeds
    admin_cancel_resp = await client.post(f"/api/reservations/{res_id}/cancel", headers=admin_headers)
    assert admin_cancel_resp.status_code == 200
    assert admin_cancel_resp.json()["status"] == "cancelled"


@pytest.mark.asyncio
async def test_staff_cannot_post_folio_charge_or_payment_403(client, seed_test_data):
    """Staff cannot post folio charges or accept financial payments."""
    admin_headers = make_auth_headers(username="admin", role="admin")
    staff_headers = make_auth_headers(username="staff", role="front_desk")
    today = date.today()
    tomorrow = today + timedelta(days=1)

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
        headers=admin_headers,
    )
    res_id = booking_resp.json()["id"]

    # Staff post charge -> 403 Forbidden
    charge_resp = await client.post(
        f"/api/billing/reservations/{res_id}/charges",
        json={
            "date": today.isoformat(),
            "description": "Room Service Dinner",
            "category": "room_service",
            "amount": "45.00",
        },
        headers=staff_headers,
    )
    assert charge_resp.status_code == 403

    # Staff post payment -> 403 Forbidden
    pay_resp = await client.post(
        f"/api/billing/reservations/{res_id}/payments",
        json={
            "date": today.isoformat(),
            "amount": "100.00",
            "method": "credit_card",
        },
        headers=staff_headers,
    )
    assert pay_resp.status_code == 403


@pytest.mark.asyncio
async def test_staff_guest_total_spend_hidden(client, seed_test_data):
    """Staff browsing guest repository sees lifetime spend suppressed as 0.00."""
    staff_headers = make_auth_headers(username="staff", role="front_desk")

    resp = await client.get("/api/guests", headers=staff_headers)
    assert resp.status_code == 200
    guests = resp.json()["items"]
    assert len(guests) > 0
    for g in guests:
        assert Decimal(str(g["total_spend"])) == Decimal("0.00")
