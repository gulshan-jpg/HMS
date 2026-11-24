"""Tests for Folio Accounting, Payments, Adjustments, and Dashboard KPIs."""
from datetime import date, timedelta
from decimal import Decimal
import pytest
from tests.conftest import make_auth_headers


@pytest.mark.asyncio
async def test_folio_math_charges_payments_and_balance(client, seed_test_data):
    """Verify subtotal, tax aggregation, payment deductions, and net balance calculation."""
    headers = make_auth_headers()
    today = date.today()
    tomorrow = today + timedelta(days=1)

    # Create booking
    booking_resp = await client.post(
        "/api/reservations",
        json={
            "guest_id": seed_test_data["guest"].id,
            "room_id": seed_test_data["r101"].id,
            "check_in_date": today.isoformat(),
            "check_out_date": tomorrow.isoformat(),
            "adults": 1,
            "nightly_rate": "150.00",
        },
        headers=headers,
    )
    res_id = booking_resp.json()["id"]

    # 1. Post room charge: $150
    await client.post(
        f"/api/billing/reservations/{res_id}/charges",
        json={
            "date": today.isoformat(),
            "description": "Room Charge",
            "category": "room",
            "amount": "150.00",
        },
        headers=headers,
    )

    # 2. Post tax: $15
    await client.post(
        f"/api/billing/reservations/{res_id}/charges",
        json={
            "date": today.isoformat(),
            "description": "Occupancy Tax",
            "category": "tax",
            "amount": "15.00",
        },
        headers=headers,
    )

    # 3. Post minibar incidental: $25.50
    await client.post(
        f"/api/billing/reservations/{res_id}/charges",
        json={
            "date": today.isoformat(),
            "description": "Minibar San Pellegrino & Almonds",
            "category": "minibar",
            "amount": "25.50",
        },
        headers=headers,
    )

    # 4. Post adjustment credit: -$5.50
    await client.post(
        f"/api/billing/reservations/{res_id}/charges",
        json={
            "date": today.isoformat(),
            "description": "Minibar Courtesy Adjustment",
            "category": "adjustment",
            "amount": "-5.50",
        },
        headers=headers,
    )

    # Total charges: 150 + 15 + 25.50 - 5.50 = 185.00
    # Subtotal (non-tax): 150 + 25.50 - 5.50 = 170.00
    # Tax: 15.00

    # 5. Post partial payment: $100.00
    await client.post(
        f"/api/billing/reservations/{res_id}/payments",
        json={
            "date": today.isoformat(),
            "amount": "100.00",
            "method": "credit_card",
            "reference": "AUTH-4412",
        },
        headers=headers,
    )

    # Balance due should be 185.00 - 100.00 = 85.00
    folio_resp = await client.get(f"/api/billing/reservations/{res_id}/folio", headers=headers)
    assert folio_resp.status_code == 200
    folio = folio_resp.json()

    assert Decimal(str(folio["subtotal"])) == Decimal("170.00")
    assert Decimal(str(folio["tax_total"])) == Decimal("15.00")
    assert Decimal(str(folio["total_amount"])) == Decimal("185.00")
    assert Decimal(str(folio["total_paid"])) == Decimal("100.00")
    assert Decimal(str(folio["balance_due"])) == Decimal("85.00")


@pytest.mark.asyncio
async def test_payment_amount_must_be_positive(client, seed_test_data):
    """Verify payment endpoints reject non-positive amounts."""
    headers = make_auth_headers()
    today = date.today()

    booking_resp = await client.post(
        "/api/reservations",
        json={
            "guest_id": seed_test_data["guest"].id,
            "room_id": seed_test_data["r102"].id,
            "check_in_date": today.isoformat(),
            "check_out_date": (today + timedelta(days=1)).isoformat(),
            "adults": 1,
        },
        headers=headers,
    )
    res_id = booking_resp.json()["id"]

    # Negative payment should be rejected with 422
    resp = await client.post(
        f"/api/billing/reservations/{res_id}/payments",
        json={
            "date": today.isoformat(),
            "amount": "-50.00",
            "method": "credit_card",
        },
        headers=headers,
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_dashboard_kpis_shape_and_metrics(client, seed_test_data):
    """Verify GET /api/dashboard returns expected KPI structure."""
    headers = make_auth_headers()
    resp = await client.get("/api/dashboard", headers=headers)
    assert resp.status_code == 200
    data = resp.json()

    # Verify keys
    assert "occupancy_rate" in data
    assert "occupied_rooms" in data
    assert "total_rooms" in data
    assert "occupancy_sparkline" in data
    assert len(data["occupancy_sparkline"]) == 7
    assert "arrivals_total" in data
    assert "departures_total" in data
    assert "revenue_today" in data
    assert "occupancy_trend_14d" in data
    assert len(data["occupancy_trend_14d"]) == 14
    assert "room_status_summary" in data
    assert "today_arrivals" in data
    assert "today_departures" in data
    assert "recent_activity" in data
    assert "pending_housekeeping" in data
