"""Test suite for Stripe Webhook Processing and Idempotency."""
import pytest
from app.models import Organization, WebhookEvent


@pytest.mark.asyncio
async def test_checkout_session_completed_activates_subscription(client, db_session):
    """Verify Stripe checkout.session.completed webhook activates organization subscription."""
    org = Organization(
        name="Stripe Test Resort",
        slug="stripe-test-resort",
        plan="starter",
        subscription_status="trialing",
    )
    db_session.add(org)
    db_session.commit()
    db_session.refresh(org)

    event_payload = {
        "id": "evt_test_checkout_12345",
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "id": "cs_test_abc123",
                "customer": "cus_stripe_cust_999",
                "subscription": "sub_stripe_sub_888",
                "metadata": {
                    "organization_id": str(org.id),
                    "plan": "pro",
                },
            }
        },
    }

    resp = await client.post("/api/billing/webhook", json=event_payload)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["status"] == "processed"

    # Refresh org from DB and verify active status and pro plan
    db_session.refresh(org)
    assert org.subscription_status == "active"
    assert org.plan == "pro"
    assert org.stripe_subscription_id == "sub_stripe_sub_888"
    assert org.stripe_customer_id == "cus_stripe_cust_999"


@pytest.mark.asyncio
async def test_webhook_idempotency_prevents_duplicate_processing(client, db_session):
    """Verify that sending the same webhook event ID twice is safely handled as idempotent."""
    org = Organization(
        name="Idempotent Test Hotel",
        slug="idempotent-test-hotel",
        plan="starter",
        subscription_status="trialing",
    )
    db_session.add(org)
    db_session.commit()
    db_session.refresh(org)

    event_payload = {
        "id": "evt_duplicate_test_999",
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "customer": "cus_abc",
                "subscription": "sub_xyz",
                "metadata": {
                    "organization_id": str(org.id),
                    "plan": "enterprise",
                },
            }
        },
    }

    # First delivery
    resp1 = await client.post("/api/billing/webhook", json=event_payload)
    assert resp1.status_code == 200
    assert resp1.json()["status"] == "processed"

    # Second delivery with same event ID
    resp2 = await client.post("/api/billing/webhook", json=event_payload)
    assert resp2.status_code == 200
    assert resp2.json()["status"] == "already_processed"
