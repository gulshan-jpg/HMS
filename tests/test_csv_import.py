"""Test suite for CSV Bulk Import Wizard (Guests and Rooms)."""
import io
import pytest
from app.auth import get_password_hash
from app.models import Guest, Organization, Room, User
from tests.conftest import make_auth_headers


@pytest.mark.asyncio
async def test_csv_import_template_download(client, db_session, seed_test_data):
    """Verify downloading guest and room CSV templates."""
    headers = make_auth_headers(username="admin", role="admin")

    resp_guests = await client.get("/api/import/template/guests", headers=headers)
    assert resp_guests.status_code == 200
    assert "name,email,phone" in resp_guests.text

    resp_rooms = await client.get("/api/import/template/rooms", headers=headers)
    assert resp_rooms.status_code == 200
    assert "number,room_type,floor,rate" in resp_rooms.text


@pytest.mark.asyncio
async def test_csv_import_preview_and_execution(client, db_session):
    """Verify CSV preview identifies validation errors and execute imports valid rows."""
    org = Organization(name="Import Hotel", slug="import-hotel", plan="pro", subscription_status="active")
    db_session.add(org)
    db_session.commit()
    db_session.refresh(org)

    owner = User(
        email="owner@import.com",
        username="import_owner",
        full_name="Import Owner",
        role="owner",
        organization_id=org.id,
        is_active=True,
        hashed_password=get_password_hash("AdminPass123!"),
    )
    db_session.add(owner)
    db_session.commit()

    headers = make_auth_headers(username="import_owner", role="owner", org_id=org.id)

    # Prepare CSV with 2 valid rows and 1 invalid row (invalid email)
    csv_content = (
        "name,email,phone,vip_tier,notes\r\n"
        "Arjun Kapoor,arjun@example.com,+919876543210,gold,VIP guest\r\n"
        "Bad Email Guest,not-an-email,+919812345678,none,Invalid row\r\n"
        "Sunita Rao,sunita@example.com,+919923456789,silver,High floor\r\n"
    )

    # 1. Preview
    preview_resp = await client.post(
        "/api/import/preview",
        data={"type": "guests"},
        files={"file": ("guests.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")},
        headers=headers,
    )
    assert preview_resp.status_code == 200, preview_resp.text
    preview_data = preview_resp.json()
    assert preview_data["total_rows"] == 3
    assert preview_data["valid_rows"] == 2
    assert preview_data["error_rows"] == 1
    assert any("email" in e["field"] for e in preview_data["errors"])

    # 2. Execute
    exec_resp = await client.post(
        "/api/import/execute",
        data={"type": "guests"},
        files={"file": ("guests.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")},
        headers=headers,
    )
    assert exec_resp.status_code == 200, exec_resp.text
    exec_data = exec_resp.json()
    assert exec_data["imported"] == 2
    assert exec_data["skipped"] == 1

    # Verify rows in DB
    arjun = db_session.query(Guest).filter(Guest.organization_id == org.id, Guest.email == "arjun@example.com").first()
    assert arjun is not None
    assert arjun.first_name == "Arjun"
