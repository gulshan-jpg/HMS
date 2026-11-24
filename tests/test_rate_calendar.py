"""Tests for Rate Calendar: 30-Day Matrix, Overrides Priority, and Bulk Adjustments."""
from datetime import date, timedelta
from decimal import Decimal
import pytest
from tests.conftest import make_auth_headers
from app.models import RateOverride, Room, RoomType


@pytest.mark.asyncio
async def test_rate_calendar_matrix_and_overrides(client, seed_test_data, db_session):
    """Verify 30-day rate calendar returns correct days, rates, and occupancy."""
    headers = make_auth_headers(role="admin")
    today = date.today()
    rt_id = seed_test_data["rt_std"].id

    # 1. Fetch default 30-day calendar
    cal_resp = await client.get(f"/api/rate-calendar?start_date={today.isoformat()}&days=30", headers=headers)
    assert cal_resp.status_code == 200
    cal_data = cal_resp.json()
    assert cal_data["days_count"] == 30
    assert len(cal_data["room_types"]) >= 1

    rt_item = next(rt for rt in cal_data["room_types"] if rt["id"] == rt_id)
    assert len(rt_item["days"]) == 30
    # Day 0 should have base rate = seed base_rate
    assert Decimal(str(rt_item["days"][0]["rate"])) == seed_test_data["rt_std"].base_rate
    assert rt_item["days"][0]["override_id"] is None

    # 2. Set an override for today: 220.00
    override_resp = await client.put(
        "/api/rate-overrides",
        json={
            "room_type_id": rt_id,
            "date": today.isoformat(),
            "rate": "220.00",
            "min_stay": 2,
            "closed": False,
        },
        headers=headers,
    )
    assert override_resp.status_code == 200
    override_id = override_resp.json()["id"]

    # 3. Re-fetch calendar: today must show override rate 220.00 and min_stay 2
    cal_resp2 = await client.get(f"/api/rate-calendar?start_date={today.isoformat()}&days=30", headers=headers)
    assert cal_resp2.status_code == 200
    rt_item2 = next(rt for rt in cal_resp2.json()["room_types"] if rt["id"] == rt_id)
    day0 = rt_item2["days"][0]
    assert Decimal(str(day0["rate"])) == Decimal("220.00")
    assert day0["override_id"] == override_id
    assert day0["min_stay"] == 2

    # 4. Delete override
    del_resp = await client.delete(f"/api/rate-overrides/{override_id}", headers=headers)
    assert del_resp.status_code == 204

    # 5. Re-fetch calendar: reverted to seed base_rate
    cal_resp3 = await client.get(f"/api/rate-calendar?start_date={today.isoformat()}&days=30", headers=headers)
    rt_item3 = next(rt for rt in cal_resp3.json()["room_types"] if rt["id"] == rt_id)
    assert Decimal(str(rt_item3["days"][0]["rate"])) == seed_test_data["rt_std"].base_rate


@pytest.mark.asyncio
async def test_bulk_rate_overrides(client, seed_test_data):
    """Verify bulk override updates multiple dates and room types simultaneously."""
    headers = make_auth_headers(role="admin")
    today = date.today()
    dates = [(today + timedelta(days=i)).isoformat() for i in range(5)]
    rt_ids = [seed_test_data["rt_std"].id, seed_test_data["rt_dlx"].id]

    bulk_resp = await client.post(
        "/api/rate-overrides/bulk",
        json={
            "room_type_ids": rt_ids,
            "dates": dates,
            "rate": "199.00",
            "min_stay": 2,
            "closed": False,
        },
        headers=headers,
    )
    assert bulk_resp.status_code == 200
    assert bulk_resp.json()["cells_updated"] == 10  # 2 room types * 5 dates
