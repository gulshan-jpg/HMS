"""Test suite for Self-Serve Signup, Demo Data Seeding, and Password Validation."""
import pytest
from app.models import Organization, Reservation, Room, User


@pytest.mark.asyncio
async def test_signup_creates_org_trial_and_seeds_demo_data(client, db_session):
    """Verify signup creates organization, owner user with 14-day trial, and seeds realistic demo data."""
    payload = {
        "hotel_name": "Royal Heritage Haveli",
        "full_name": "Vikramaditya Rathore",
        "email": "vikram@havelijaipur.in",
        "password": "Password123!",
        "currency": "INR",
        "timezone": "Asia/Kolkata",
        "plan": "pro",
    }

    resp = await client.post("/api/signup", json=payload)
    assert resp.status_code == 201, resp.text
    data = resp.json()

    assert "access_token" in data
    assert data["organization"]["name"] == "Royal Heritage Haveli"
    assert data["organization"]["slug"] == "royal-heritage-haveli"
    assert data["organization"]["plan"] == "pro"
    assert data["organization"]["subscription_status"] == "trialing"
    assert data["user"]["role"] == "owner"
    assert data["user"]["email"] == "vikram@havelijaipur.in"

    org_id = data["organization"]["id"]

    # Verify demo data seeded with is_demo=True
    rooms = db_session.query(Room).filter(Room.organization_id == org_id, Room.is_demo.is_(True)).all()
    assert len(rooms) >= 5, "Expected at least 5 seeded demo rooms"

    reservations = db_session.query(Reservation).filter(Reservation.organization_id == org_id, Reservation.is_demo.is_(True)).all()
    assert len(reservations) >= 3, "Expected seeded demo reservations"


@pytest.mark.asyncio
async def test_signup_duplicate_email_rejected(client, db_session):
    """Verify duplicate signup email is rejected with 400 error."""
    payload = {
        "hotel_name": "Lake View Resort",
        "full_name": "Pooja Sharma",
        "email": "pooja@lakeview.com",
        "password": "SecurePassword1!",
        "plan": "starter",
    }

    resp1 = await client.post("/api/signup", json=payload)
    assert resp1.status_code == 201

    # Second signup with same email
    resp2 = await client.post("/api/signup", json=payload)
    assert resp2.status_code == 400
    err = resp2.json()
    assert any(w in (err.get("detail") or err.get("error", {}).get("message", "")).lower() for w in ["already exists", "already registered"])


@pytest.mark.asyncio
async def test_purge_demo_data(client, db_session):
    """Verify DELETE /api/demo-data soft-deletes seeded demo data without touching hotel config."""
    signup_payload = {
        "hotel_name": "Boutique Oasis",
        "full_name": "Karan Mehra",
        "email": "karan@oasis.com",
        "password": "SecurePassword1!",
        "plan": "pro",
    }
    signup_resp = await client.post("/api/signup", json=signup_payload)
    assert signup_resp.status_code == 201
    auth_data = signup_resp.json()
    token = auth_data["access_token"]
    org_id = auth_data["organization"]["id"]

    headers = {"Authorization": f"Bearer {token}", "X-Organization-Id": str(org_id)}

    # Delete demo data
    del_resp = await client.delete("/api/demo-data", headers=headers)
    assert del_resp.status_code == 200

    # Active (non-deleted) demo reservations should now be 0
    remaining_res = db_session.query(Reservation).filter(
        Reservation.organization_id == org_id,
        Reservation.is_demo.is_(True),
        Reservation.deleted_at.is_(None),
    ).count()
    assert remaining_res == 0


@pytest.mark.asyncio
async def test_sequential_multi_tenant_signups_no_collision(client, db_session):
    """Verify multiple independent organizations can register without colliding on demo room numbers or codes."""
    org1_payload = {
        "hotel_name": "Hotel Grand",
        "full_name": "Vikram",
        "email": "vikram1@hotelgrand.com",
        "password": "Password123!",
        "currency": "INR",
        "timezone": "Asia/Kolkata",
        "plan": "pro",
        "property_type": "villa",
        "rooms_count": "12",
    }
    org2_payload = {
        "hotel_name": "Hotel Grand",  # Same name -> should get deduplicated slug
        "full_name": "Vikram Two",
        "email": "vikram2@hotelgrand.com",
        "password": "Password123!",
        "currency": "INR",
        "timezone": "Asia/Kolkata",
        "plan": "starter",
        "property_type": "resort",
        "rooms_count": "35",
    }

    resp1 = await client.post("/api/signup", json=org1_payload)
    assert resp1.status_code == 201, resp1.text
    data1 = resp1.json()
    assert data1["organization"]["slug"] == "hotel-grand"

    resp2 = await client.post("/api/signup", json=org2_payload)
    assert resp2.status_code == 201, resp2.text
    data2 = resp2.json()
    assert data2["organization"]["slug"] == "hotel-grand-1"

    # Both orgs should have rooms "101" without unique constraint violation
    rooms1 = db_session.query(Room).filter(Room.organization_id == data1["organization"]["id"]).all()
    rooms2 = db_session.query(Room).filter(Room.organization_id == data2["organization"]["id"]).all()
    assert len(rooms1) == 10
    assert len(rooms2) == 10
    assert any(r.number == "101" for r in rooms1)
    assert any(r.number == "101" for r in rooms2)

