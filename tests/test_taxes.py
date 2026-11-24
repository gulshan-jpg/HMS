"""Tests for Tax Engine: Inclusive/Exclusive Tax Math, Multiple Taxes, and Folio Breakdown."""
from datetime import date, timedelta
from decimal import Decimal
import json
import pytest
from tests.conftest import make_auth_headers
from app.models import FolioItem, TaxRate
from app.routers.taxes import compute_tax_breakdown


@pytest.mark.asyncio
async def test_tax_rate_crud(client, seed_test_data):
    """Test CRUD operations on tax rates."""
    headers = make_auth_headers(role="admin")

    # Create
    create_resp = await client.post(
        "/api/taxes",
        json={
            "name": "State Lodging Tax",
            "rate": "5.50",
            "fixed_amount": "0.00",
            "applies_to": "rooms",
            "type": "exclusive",
            "per": "night",
            "active": True,
            "sort_order": 1,
        },
        headers=headers,
    )
    assert create_resp.status_code == 201
    tax_id = create_resp.json()["id"]

    # List
    list_resp = await client.get("/api/taxes", headers=headers)
    assert list_resp.status_code == 200
    assert any(t["id"] == tax_id for t in list_resp.json())

    # Update
    upd_resp = await client.put(
        f"/api/taxes/{tax_id}",
        json={"name": "State Lodging Tax Updated", "rate": "6.00"},
        headers=headers,
    )
    assert upd_resp.status_code == 200
    assert Decimal(str(upd_resp.json()["rate"])) == Decimal("6.00")

    # Delete
    del_resp = await client.delete(f"/api/taxes/{tax_id}", headers=headers)
    assert del_resp.status_code == 204


def test_compute_tax_breakdown_inclusive_and_exclusive(db_session):
    """Test tax calculation engine for both inclusive and exclusive taxes."""
    # Seed 10% inclusive tax + 5% exclusive tax
    inc_tax = TaxRate(
        name="VAT Inclusive",
        rate=Decimal("10.00"),
        fixed_amount=Decimal("0.00"),
        applies_to="rooms",
        type="inclusive",
        per="night",
        active=True,
        sort_order=1,
    )
    exc_tax = TaxRate(
        name="City Surcharge Exclusive",
        rate=Decimal("5.00"),
        fixed_amount=Decimal("0.00"),
        applies_to="rooms",
        type="exclusive",
        per="night",
        active=True,
        sort_order=2,
    )
    db_session.add_all([inc_tax, exc_tax])
    db_session.commit()

    # Base charge = 110.00
    # 1. Inclusive 10%: subtotal = 110 / 1.10 = 100.00. Inc tax = 10.00
    # 2. Exclusive 5% on 100.00: 5.00
    res = compute_tax_breakdown(
        amount=Decimal("110.00"),
        category="room",
        nights=1,
        adults=1,
        db=db_session,
    )

    assert Decimal(str(res["subtotal"])) == Decimal("100.00")
    assert Decimal(str(res["tax_total"])) == Decimal("5.00")
    assert len(res["breakdown"]) == 2
    names = [b["name"] for b in res["breakdown"]]
    assert "VAT Inclusive" in names
    assert "City Surcharge Exclusive" in names


@pytest.mark.asyncio
async def test_checkin_populates_tax_breakdown_on_folio(client, seed_test_data, db_session):
    """Check-in creates room folio item with JSON tax breakdown."""
    headers = make_auth_headers(role="admin")
    today = date.today()
    tomorrow = today + timedelta(days=1)

    # Seed City Tax: 5%
    tax = TaxRate(
        name="Test City Tax",
        rate=Decimal("5.00"),
        fixed_amount=Decimal("0.00"),
        applies_to="rooms",
        type="exclusive",
        per="night",
        active=True,
        sort_order=1,
    )
    db_session.add(tax)
    db_session.commit()

    # Create reservation
    res_resp = await client.post(
        "/api/reservations",
        json={
            "guest_id": seed_test_data["guest"].id,
            "room_id": seed_test_data["r101"].id,
            "check_in_date": today.isoformat(),
            "check_out_date": tomorrow.isoformat(),
            "adults": 1,
            "nightly_rate": "200.00",
        },
        headers=headers,
    )
    res_id = res_resp.json()["id"]

    # Check in
    cin_resp = await client.post(f"/api/reservations/{res_id}/check-in", headers=headers)
    assert cin_resp.status_code == 200

    # Query room folio item
    item = (
        db_session.query(FolioItem)
        .filter(FolioItem.reservation_id == res_id, FolioItem.category == "room")
        .first()
    )
    assert item is not None
    assert item.tax_breakdown is not None
    breakdown = json.loads(item.tax_breakdown)
    assert any(b["name"] == "Test City Tax" for b in breakdown)
