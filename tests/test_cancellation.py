"""Tests for Cancellation Policies: Free Windows, Penalties, and Deposit Refunds."""
from datetime import date, timedelta
from decimal import Decimal
import pytest
from tests.conftest import make_auth_headers
from app.models import FolioItem, Payment, Reservation


@pytest.mark.asyncio
async def test_cancellation_policy_crud(client, seed_test_data):
    """Test CRUD operations on cancellation policies."""
    headers = make_auth_headers(role="admin")

    # Create
    create_resp = await client.post(
        "/api/cancellation-policies",
        json={
            "name": "Strict Non-Ref",
            "description": "Full first night penalty",
            "free_cancel_days": 0,
            "penalty_type": "first_night",
            "penalty_value": "100.00",
            "no_show_penalty": "first_night",
            "active": True,
        },
        headers=headers,
    )
    assert create_resp.status_code == 201
    pol_id = create_resp.json()["id"]

    # List
    list_resp = await client.get("/api/cancellation-policies", headers=headers)
    assert list_resp.status_code == 200
    assert any(p["id"] == pol_id for p in list_resp.json())

    # Update
    upd_resp = await client.put(
        f"/api/cancellation-policies/{pol_id}",
        json={"name": "Strict Updated", "free_cancel_days": 1},
        headers=headers,
    )
    assert upd_resp.status_code == 200
    assert upd_resp.json()["name"] == "Strict Updated"

    # Delete
    del_resp = await client.delete(f"/api/cancellation-policies/{pol_id}", headers=headers)
    assert del_resp.status_code == 204


@pytest.mark.asyncio
async def test_cancellation_quote_free_window(client, seed_test_data):
    """Cancellation well before check-in within free window incurs 0 penalty."""
    headers = make_auth_headers(role="admin")
    today = date.today()
    check_in = today + timedelta(days=10)
    check_out = today + timedelta(days=12)

    # Policy with 3 days free cancel
    pol_resp = await client.post(
        "/api/cancellation-policies",
        json={
            "name": "3-Day Free",
            "free_cancel_days": 3,
            "penalty_type": "first_night",
            "penalty_value": "100.00",
        },
        headers=headers,
    )
    pol_id = pol_resp.json()["id"]

    # Plan attaching policy
    plan_resp = await client.post(
        "/api/rate-plans",
        json={
            "code": "CAN-FLEX",
            "name": "Flexible Plan",
            "modifier_type": "percent",
            "modifier_value": "0.00",
            "cancellation_policy_id": pol_id,
        },
        headers=headers,
    )
    plan_id = plan_resp.json()["id"]

    # Create reservation
    res_resp = await client.post(
        "/api/reservations",
        json={
            "guest_id": seed_test_data["guest"].id,
            "room_id": seed_test_data["r101"].id,
            "rate_plan_id": plan_id,
            "check_in_date": check_in.isoformat(),
            "check_out_date": check_out.isoformat(),
            "adults": 1,
            "nightly_rate": "150.00",
        },
        headers=headers,
    )
    res_id = res_resp.json()["id"]

    # Check cancellation quote (today is 10 days before check-in, free window is 3 days -> free!)
    quote_resp = await client.get(f"/api/reservations/{res_id}/cancellation-quote", headers=headers)
    assert quote_resp.status_code == 200
    quote = quote_resp.json()
    assert quote["can_cancel_free"] is True
    assert Decimal(str(quote["penalty_amount"])) == Decimal("0.00")


@pytest.mark.asyncio
async def test_cancellation_penalty_and_refund(client, seed_test_data, db_session):
    """Late cancellation charges penalty fee to folio and refunds excess deposit."""
    headers = make_auth_headers(role="admin")
    today = date.today()
    tomorrow = today + timedelta(days=1)
    day_after = today + timedelta(days=3)

    # 1. Policy with 7 days free cancel -> cancelling today for tomorrow is late!
    pol_resp = await client.post(
        "/api/cancellation-policies",
        json={
            "name": "Strict 7-Day",
            "free_cancel_days": 7,
            "penalty_type": "first_night",
            "penalty_value": "100.00",
        },
        headers=headers,
    )
    pol_id = pol_resp.json()["id"]

    plan_resp = await client.post(
        "/api/rate-plans",
        json={
            "code": "STR-7D",
            "name": "Strict 7-Day Plan",
            "modifier_type": "percent",
            "modifier_value": "0.00",
            "cancellation_policy_id": pol_id,
            "refundable": True,
        },
        headers=headers,
    )
    plan_id = plan_resp.json()["id"]

    # 2. Book reservation for 2 nights @ 150/night
    res_resp = await client.post(
        "/api/reservations",
        json={
            "guest_id": seed_test_data["guest"].id,
            "room_id": seed_test_data["r101"].id,
            "rate_plan_id": plan_id,
            "check_in_date": tomorrow.isoformat(),
            "check_out_date": day_after.isoformat(),
            "adults": 1,
            "nightly_rate": "150.00",
            "deposit_required": "300.00",
        },
        headers=headers,
    )
    res_id = res_resp.json()["id"]

    # 3. Pay $300 deposit
    dep_resp = await client.post(
        f"/api/reservations/{res_id}/deposit",
        json={"amount": "300.00", "payment_method": "credit_card"},
        headers=headers,
    )
    assert dep_resp.status_code == 200
    assert Decimal(str(dep_resp.json()["deposit_paid"])) == Decimal("300.00")

    # 4. Check quote: late penalty is 1 night ($150), refund is $300 - $150 = $150
    quote_resp = await client.get(f"/api/reservations/{res_id}/cancellation-quote", headers=headers)
    assert quote_resp.status_code == 200
    q = quote_resp.json()
    assert q["can_cancel_free"] is False
    assert Decimal(str(q["penalty_amount"])) == Decimal("150.00")
    assert Decimal(str(q["refund_amount"])) == Decimal("150.00")

    # 5. Cancel reservation
    cancel_resp = await client.post(f"/api/reservations/{res_id}/cancel", headers=headers)
    assert cancel_resp.status_code == 200
    assert cancel_resp.json()["status"] == "cancelled"

    # Verify penalty folio item was posted
    fee_item = (
        db_session.query(FolioItem)
        .filter(FolioItem.reservation_id == res_id, FolioItem.category == "cancellation_fee")
        .first()
    )
    assert fee_item is not None
    assert Decimal(str(fee_item.amount)) == Decimal("150.00")

    # Verify refund payment was posted
    refund_payment = (
        db_session.query(Payment)
        .filter(Payment.reservation_id == res_id, Payment.is_refund.is_(True))
        .first()
    )
    assert refund_payment is not None
    assert Decimal(str(refund_payment.amount)) == Decimal("-150.00")
