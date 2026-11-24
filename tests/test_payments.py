"""Tests for Stripe Integration, PaymentIntents, Webhook Idempotency, and Refunds."""
from datetime import date, timedelta
from decimal import Decimal
import pytest
from tests.conftest import make_auth_headers
from app.models import Payment, Reservation, WebhookEvent


@pytest.mark.asyncio
async def test_payment_intent_manual_mode_fallback(client, seed_test_data):
    """When Stripe keys are absent or test mode, create-intent returns graceful fallback intent."""
    headers = make_auth_headers(role="admin")
    today = date.today()
    tomorrow = today + timedelta(days=1)

    res_resp = await client.post(
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
    res_id = res_resp.json()["id"]

    intent_resp = await client.post(
        "/api/payments/create-intent",
        json={"reservation_id": res_id, "amount": "129.00"},
        headers=headers,
    )
    assert intent_resp.status_code == 200
    intent = intent_resp.json()
    assert intent["manual_mode"] is True
    assert intent["currency"] == "INR"
    assert "client_secret" in intent
    assert "payment_intent_id" in intent
    assert Decimal(str(intent["amount"])) == Decimal("129.00")


@pytest.mark.asyncio
async def test_stripe_webhook_and_idempotency(client, seed_test_data, db_session):
    """Webhook correctly records payment on payment_intent.succeeded and enforces idempotency."""
    headers = make_auth_headers(role="admin")
    today = date.today()
    tomorrow = today + timedelta(days=1)

    res_resp = await client.post(
        "/api/reservations",
        json={
            "guest_id": seed_test_data["guest"].id,
            "room_id": seed_test_data["r101"].id,
            "check_in_date": today.isoformat(),
            "check_out_date": tomorrow.isoformat(),
            "adults": 1,
            "nightly_rate": "250.00",
        },
        headers=headers,
    )
    res_id = res_resp.json()["id"]

    event_id = "evt_stripe_test_idempotent_001"
    webhook_payload = {
        "id": event_id,
        "type": "payment_intent.succeeded",
        "data": {
            "object": {
                "id": "pi_test_99887766",
                "amount": 25000,  # 25000 paise = 250.00
                "currency": "inr",
                "metadata": {
                    "reservation_id": str(res_id),
                },
            }
        },
    }

    # 1. First webhook delivery -> success and payment recorded
    wh_resp1 = await client.post("/api/payments/webhook", json=webhook_payload)
    assert wh_resp1.status_code == 200
    assert wh_resp1.json()["status"] == "success"

    db_session.expire_all()
    payments = db_session.query(Payment).filter(Payment.reservation_id == res_id).all()
    assert len(payments) == 1
    assert Decimal(str(payments[0].amount)) == Decimal("250.00")
    assert payments[0].method == "stripe"
    assert payments[0].stripe_payment_intent_id == "pi_test_99887766"

    # Verify WebhookEvent logged
    evt = db_session.query(WebhookEvent).filter(WebhookEvent.id == event_id).first()
    assert evt is not None

    # 2. Second webhook delivery (duplicate event) -> already_processed, no second payment
    wh_resp2 = await client.post("/api/payments/webhook", json=webhook_payload)
    assert wh_resp2.status_code == 200
    assert wh_resp2.json()["status"] == "already_processed"

    db_session.expire_all()
    payments_after = db_session.query(Payment).filter(Payment.reservation_id == res_id).all()
    assert len(payments_after) == 1


@pytest.mark.asyncio
async def test_refund_payment_full_and_partial(client, seed_test_data, db_session):
    """Test full and partial payment refund with over-refund rejection."""
    headers = make_auth_headers(role="admin")
    today = date.today()
    tomorrow = today + timedelta(days=1)

    res_resp = await client.post(
        "/api/reservations",
        json={
            "guest_id": seed_test_data["guest"].id,
            "room_id": seed_test_data["r101"].id,
            "check_in_date": today.isoformat(),
            "check_out_date": tomorrow.isoformat(),
            "adults": 1,
            "nightly_rate": "300.00",
        },
        headers=headers,
    )
    res_id = res_resp.json()["id"]

    # Post original payment of 300.00
    pay_resp = await client.post(
        f"/api/billing/reservations/{res_id}/payments",
        json={"amount": "300.00", "method": "credit_card", "date": today.isoformat()},
        headers=headers,
    )
    assert pay_resp.status_code == 201
    payment_id = pay_resp.json()["id"]

    # 1. Attempt to refund 400.00 -> should fail with 400 Bad Request
    fail_refund = await client.post(
        f"/api/payments/{payment_id}/refund",
        json={"amount": "400.00", "reason": "Over-refund test"},
        headers=headers,
    )
    assert fail_refund.status_code == 400
    err_msg = fail_refund.json().get("error", {}).get("message") or fail_refund.json().get("detail", "")
    assert "cannot exceed original payment" in err_msg

    # 2. Refund partial 100.00 -> should succeed
    ok_refund = await client.post(
        f"/api/payments/{payment_id}/refund",
        json={"amount": "100.00", "reason": "Guest checkout early"},
        headers=headers,
    )
    assert ok_refund.status_code == 200
    refund_data = ok_refund.json()
    assert Decimal(str(refund_data["amount"])) == Decimal("-100.00")
    assert refund_data["is_refund"] is True
    refund_payment_id = refund_data["id"]

    # 3. Attempt to refund the refund record itself -> should fail with 400 Bad Request
    double_refund = await client.post(
        f"/api/payments/{refund_payment_id}/refund",
        json={"amount": "50.00"},
        headers=headers,
    )
    assert double_refund.status_code == 400
    double_err = double_refund.json().get("error", {}).get("message") or double_refund.json().get("detail", "")
    assert "Cannot refund a credit/refund" in double_err
