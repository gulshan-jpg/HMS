"""Tests for Deposits: Requirement Computation, Payment Recording, and Check-in Auto-Apply."""
from datetime import date, timedelta
from decimal import Decimal
import pytest
from tests.conftest import make_auth_headers
from app.models import FolioItem, Payment, RatePlan, Reservation


@pytest.mark.asyncio
async def test_deposit_recording_and_status(client, seed_test_data):
    """Test deposit status retrieval and recording advance payments."""
    headers = make_auth_headers(role="admin")
    today = date.today()
    tomorrow = today + timedelta(days=2)

    # 1. Create reservation requiring $200 deposit
    res_resp = await client.post(
        "/api/reservations",
        json={
            "guest_id": seed_test_data["guest"].id,
            "room_id": seed_test_data["r101"].id,
            "check_in_date": today.isoformat(),
            "check_out_date": tomorrow.isoformat(),
            "adults": 1,
            "nightly_rate": "150.00",
            "deposit_required": "200.00",
        },
        headers=headers,
    )
    assert res_resp.status_code == 201
    res_id = res_resp.json()["id"]

    # 2. Check initial deposit status (0 paid, 200 due)
    st1 = await client.get(f"/api/reservations/{res_id}/deposit-status", headers=headers)
    assert st1.status_code == 200
    assert Decimal(str(st1.json()["deposit_paid"])) == Decimal("0.00")
    assert st1.json()["is_satisfied"] is False
    assert Decimal(str(st1.json()["balance_due"])) == Decimal("200.00")

    # 3. Pay $200 deposit
    pay_resp = await client.post(
        f"/api/reservations/{res_id}/deposit",
        json={"amount": "200.00", "payment_method": "credit_card", "reference": "DEP-AUTH-100"},
        headers=headers,
    )
    assert pay_resp.status_code == 200
    st2 = pay_resp.json()
    assert Decimal(str(st2["deposit_paid"])) == Decimal("200.00")
    assert st2["is_satisfied"] is True
    assert Decimal(str(st2["balance_due"])) == Decimal("0.00")


@pytest.mark.asyncio
async def test_checkin_auto_applies_deposit_credit(client, seed_test_data, db_session):
    """Check-in automatically posts negative FolioItem for advance deposit paid."""
    headers = make_auth_headers(role="admin")
    today = date.today()
    tomorrow = today + timedelta(days=1)

    # Create reservation
    res_resp = await client.post(
        "/api/reservations",
        json={
            "guest_id": seed_test_data["guest"].id,
            "room_id": seed_test_data["r101"].id,
            "check_in_date": today.isoformat(),
            "check_out_date": tomorrow.isoformat(),
            "adults": 1,
            "nightly_rate": "150.00",
            "deposit_required": "150.00",
        },
        headers=headers,
    )
    res_id = res_resp.json()["id"]

    # Record full deposit payment
    await client.post(
        f"/api/reservations/{res_id}/deposit",
        json={"amount": "150.00", "payment_method": "credit_card"},
        headers=headers,
    )

    # Perform check-in
    cin_resp = await client.post(f"/api/reservations/{res_id}/check-in", headers=headers)
    assert cin_resp.status_code == 200

    db_session.expire_all()
    # Verify negative deposit_applied item on folio
    dep_item = (
        db_session.query(FolioItem)
        .filter(FolioItem.reservation_id == res_id, FolioItem.category == "deposit_applied")
        .first()
    )
    assert dep_item is not None
    assert Decimal(str(dep_item.amount)) == Decimal("-150.00")
