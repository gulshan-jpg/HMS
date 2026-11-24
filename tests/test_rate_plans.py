"""Tests for Rate Plans: CRUD, Pricing Modifier Math, Min Stay, and Quote Engine."""
from datetime import date, timedelta
from decimal import Decimal
import pytest
from tests.conftest import make_auth_headers
from app.models import RatePlan, RoomType


@pytest.mark.asyncio
async def test_rate_plan_crud(client, seed_test_data):
    """Test full CRUD operations on rate plans."""
    headers = make_auth_headers(role="admin")

    # 1. Create Rate Plan
    create_payload = {
        "code": "TEST-FLEX",
        "name": "Test Flexible Plan",
        "description": "Flexible rate plan with 10% discount",
        "modifier_type": "percent",
        "modifier_value": "-10.00",
        "meal_plan": "breakfast",
        "min_stay": 2,
        "refundable": True,
        "active": True,
    }
    resp = await client.post("/api/rate-plans", json=create_payload, headers=headers)
    assert resp.status_code == 201
    plan = resp.json()
    assert plan["code"] == "TEST-FLEX"
    assert plan["min_stay"] == 2
    assert Decimal(str(plan["modifier_value"])) == Decimal("-10.00")
    plan_id = plan["id"]

    # 2. Get Single
    get_resp = await client.get(f"/api/rate-plans/{plan_id}", headers=headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["name"] == "Test Flexible Plan"

    # 3. List
    list_resp = await client.get("/api/rate-plans", headers=headers)
    assert list_resp.status_code == 200
    codes = [p["code"] for p in list_resp.json()]
    assert "TEST-FLEX" in codes

    # 4. Update
    upd_resp = await client.put(
        f"/api/rate-plans/{plan_id}",
        json={"name": "Updated Plan Name", "min_stay": 3},
        headers=headers,
    )
    assert upd_resp.status_code == 200
    assert upd_resp.json()["name"] == "Updated Plan Name"
    assert upd_resp.json()["min_stay"] == 3

    # 5. Delete
    del_resp = await client.delete(f"/api/rate-plans/{plan_id}", headers=headers)
    assert del_resp.status_code == 204


@pytest.mark.asyncio
async def test_rate_plan_modifier_math_quote(client, seed_test_data):
    """Verify quote calculation math for percent, absolute, and fixed modifiers."""
    headers = make_auth_headers(role="admin")
    today = date.today()
    check_out = today + timedelta(days=2)
    rt_id = seed_test_data["rt_std"].id  # base_rate = 150.00

    # 1. Percent: +10% modifier -> (150 * 1.10) = 165.00/night -> 2 nights = 330.00
    p1 = await client.post(
        "/api/rate-plans",
        json={
            "code": "PCT-PLUS",
            "name": "10 Percent Plus",
            "modifier_type": "percent",
            "modifier_value": "10.00",
            "min_stay": 1,
        },
        headers=headers,
    )
    p1_id = p1.json()["id"]

    q1 = await client.get(
        f"/api/rate-plans/quote?room_type_id={rt_id}&check_in={today}&check_out={check_out}&plan_id={p1_id}",
        headers=headers,
    )
    assert q1.status_code == 200
    data1 = q1.json()
    base_rate = Decimal(str(seed_test_data["rt_std"].base_rate))
    expected_pct = (base_rate * Decimal("1.10")).quantize(Decimal("0.01")) * 2
    assert Decimal(str(data1["subtotal"])) == expected_pct

    # 2. Absolute: +25/night -> (base + 25) * 2 nights
    p2 = await client.post(
        "/api/rate-plans",
        json={
            "code": "ABS-PLUS",
            "name": "Add 25",
            "modifier_type": "absolute",
            "modifier_value": "25.00",
            "min_stay": 1,
        },
        headers=headers,
    )
    p2_id = p2.json()["id"]

    q2 = await client.get(
        f"/api/rate-plans/quote?room_type_id={rt_id}&check_in={today}&check_out={check_out}&plan_id={p2_id}",
        headers=headers,
    )
    assert q2.status_code == 200
    data2 = q2.json()
    expected_abs = (base_rate + Decimal("25.00")) * 2
    assert Decimal(str(data2["subtotal"])) == expected_abs

    # 3. Fixed: 200 flat -> 200.00/night -> 2 nights = 400.00
    p3 = await client.post(
        "/api/rate-plans",
        json={
            "code": "FIX-200",
            "name": "Flat 200",
            "modifier_type": "fixed",
            "modifier_value": "200.00",
            "min_stay": 1,
        },
        headers=headers,
    )
    p3_id = p3.json()["id"]

    q3 = await client.get(
        f"/api/rate-plans/quote?room_type_id={rt_id}&check_in={today}&check_out={check_out}&plan_id={p3_id}",
        headers=headers,
    )
    assert q3.status_code == 200
    data3 = q3.json()
    assert Decimal(str(data3["subtotal"])) == Decimal("400.00")


@pytest.mark.asyncio
async def test_rate_plan_min_stay_enforcement(client, seed_test_data):
    """Attempting to book a stay shorter than rate plan min_stay must fail with 400."""
    headers = make_auth_headers(role="admin")
    today = date.today()
    tomorrow = today + timedelta(days=1)  # 1 night stay

    # Create plan requiring 3 nights
    plan_resp = await client.post(
        "/api/rate-plans",
        json={
            "code": "MIN-3N",
            "name": "Min 3 Nights Plan",
            "modifier_type": "percent",
            "modifier_value": "0.00",
            "min_stay": 3,
        },
        headers=headers,
    )
    plan_id = plan_resp.json()["id"]

    # Booking 1 night should return 400 Bad Request
    res_resp = await client.post(
        "/api/reservations",
        json={
            "guest_id": seed_test_data["guest"].id,
            "room_id": seed_test_data["r101"].id,
            "rate_plan_id": plan_id,
            "check_in_date": today.isoformat(),
            "check_out_date": tomorrow.isoformat(),
            "adults": 1,
        },
        headers=headers,
    )
    assert res_resp.status_code == 400
    assert "minimum stay of 3 night(s)" in res_resp.json()["error"]["message"]
