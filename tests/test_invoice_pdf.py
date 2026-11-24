"""Test suite for ReportLab PDF Invoice Generation."""
from datetime import date, timedelta
from decimal import Decimal
import pytest
from app.auth import get_password_hash
from app.models import Folio, FolioItem, Guest, Organization, Reservation, Room, RoomType, User
from tests.conftest import make_auth_headers


@pytest.mark.asyncio
async def test_reservation_invoice_pdf_generation(client, db_session):
    """Verify GET /api/reservations/{id}/invoice.pdf generates a valid A4 PDF tax invoice."""
    org = Organization(name="Invoice Test Hotel", slug="invoice-hotel", plan="pro", subscription_status="active")
    db_session.add(org)
    db_session.commit()
    db_session.refresh(org)

    owner = User(
        email="owner@invoice.com",
        username="invoice_owner",
        full_name="Invoice Owner",
        role="owner",
        organization_id=org.id,
        is_active=True,
        hashed_password=get_password_hash("AdminPass123!"),
    )
    db_session.add(owner)

    rt = RoomType(organization_id=org.id, name="Royal Suite", code="RS", base_rate=Decimal("10000"), max_occupancy=2)
    db_session.add(rt)
    db_session.commit()

    rm = Room(organization_id=org.id, number="401", floor=4, room_type_id=rt.id, status="occupied")
    guest = Guest(organization_id=org.id, first_name="Deepak", last_name="Verma", email="deepak@example.com", phone="+919876543210")
    db_session.add_all([rm, guest])
    db_session.commit()

    today = date.today()
    res = Reservation(
        organization_id=org.id,
        guest_id=guest.id,
        room_id=rm.id,
        confirmation_number="HTL-PDF01",
        check_in_date=today,
        check_out_date=today + timedelta(days=2),
        adults=2,
        children=0,
        nightly_rate=Decimal("10000"),
        status="checked_in",
    )
    db_session.add(res)
    db_session.commit()
    db_session.refresh(res)

    folio = Folio(organization_id=org.id, reservation_id=res.id, name="Primary Folio", is_master=True)
    db_session.add(folio)
    db_session.commit()
    db_session.refresh(folio)

    item = FolioItem(
        organization_id=org.id,
        folio_id=folio.id,
        reservation_id=res.id,
        date=today,
        category="room",
        description="Room 401 Accommodation",
        amount=Decimal("20000"),
        subtotal=Decimal("20000"),
        tax_total=Decimal("2400"),
    )
    db_session.add(item)
    db_session.commit()

    headers = make_auth_headers(username="invoice_owner", role="owner", org_id=org.id)

    # Fetch PDF invoice
    resp = await client.get(f"/api/reservations/{res.id}/invoice.pdf", headers=headers)
    assert resp.status_code == 200, resp.text
    assert resp.headers.get("content-type") == "application/pdf"
    assert "attachment; filename=" in resp.headers.get("content-disposition", "")
    assert resp.content.startswith(b"%PDF-"), "Expected valid PDF binary stream"
