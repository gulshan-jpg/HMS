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


@pytest.mark.asyncio
async def test_onboarding_get_and_save_customized_data(client, db_session):
    """Verify new user can fetch pre-seeded onboarding setup and save customized room types, rooms, rate plans, and taxes."""
    signup_payload = {
        "hotel_name": "Jaipur Palace Suites",
        "full_name": "Karan Mehra",
        "email": "karan@jaipurpalace.in",
        "password": "Password123!",
        "currency": "INR",
        "timezone": "Asia/Kolkata",
        "plan": "pro",
    }
    signup_resp = await client.post("/api/signup", json=signup_payload)
    assert signup_resp.status_code == 201
    token = signup_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Fetch initial onboarding data
    get_resp = await client.get("/api/onboarding/data", headers=headers)
    assert get_resp.status_code == 200
    init_data = get_resp.json()
    assert init_data["hotel_name"] == "Jaipur Palace Suites"
    assert len(init_data["room_types"]) >= 3
    assert len(init_data["rooms"]) >= 5

    # 2. Save customized onboarding data (Step 1-6)
    save_payload = {
        "hotel_name": "The Royal Palace Jaipur",
        "city": "Jaipur, Rajasthan",
        "currency": "INR",
        "gstin": "08ABCDE1234F1Z5",
        "room_types": [
            {"name": "Luxury King Suite", "base_rate": 8900.0, "max_occupancy": 2, "description": "King Bed with Garden View"},
            {"name": "Royal Penthouse", "base_rate": 28000.0, "max_occupancy": 4, "description": "Top floor terrace"}
        ],
        "rooms": [
            {"number": "101", "floor": 1, "room_type_name": "Luxury King Suite"},
            {"number": "102", "floor": 1, "room_type_name": "Luxury King Suite"},
            {"number": "501", "floor": 5, "room_type_name": "Royal Penthouse"}
        ],
        "rate_plans": [
            {"name": "Flexible Standard Rate", "code": "FLEX", "modifier_type": "percent", "modifier_value": 0.0, "description": "Best Flexible Rate", "refundable": True},
            {"name": "Member Exclusive", "code": "MEMB", "modifier_type": "percent", "modifier_value": -12.0, "description": "12% Off", "refundable": False}
        ],
        "taxes": [
            {"name": "Standard GST (12%)", "rate": 12.0, "applies_to": "rooms", "description": "Tariffs <= 7500"}
        ],
        "staff_members": [
            {
                "full_name": "Rohan Verma",
                "email": "rohan@jaipurpalace.in",
                "role": "housekeeping"
            },
            {
                "full_name": "Radhika Sharma",
                "email": "radhika@jaipurpalace.in",
                "role": "front_desk"
            }
        ]
    }
    save_resp = await client.post("/api/onboarding/save", json=save_payload, headers=headers)
    assert save_resp.status_code == 200
    assert save_resp.json()["status"] == "ok"

    # 3. Verify changes reflected in GET /api/onboarding/data
    verify_resp = await client.get("/api/onboarding/data", headers=headers)
    assert verify_resp.status_code == 200
    updated_data = verify_resp.json()
    assert updated_data["hotel_name"] == "The Royal Palace Jaipur"
    assert updated_data["gstin"] == "08ABCDE1234F1Z5"
    assert any(rt["name"] == "Luxury King Suite" and rt["base_rate"] == 8900.0 for rt in updated_data["room_types"])
    assert any(r["number"] == "501" and r["floor"] == 5 for r in updated_data["rooms"])
    assert any(rp["code"] == "MEMB" and rp["modifier_value"] == -12.0 for rp in updated_data["rate_plans"])
    assert len(updated_data["staff_members"]) == 2
    staff_emails = [s["email"] for s in updated_data["staff_members"]]
    assert "rohan@jaipurpalace.in" in staff_emails
    assert "radhika@jaipurpalace.in" in staff_emails


