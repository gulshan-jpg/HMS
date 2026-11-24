"""Tests for Folio Splitting, Line Item Moves, and Balance Transfers."""
from datetime import date, timedelta
from decimal import Decimal
import pytest
from tests.conftest import make_auth_headers
from app.models import Folio, FolioItem, Reservation


@pytest.mark.asyncio
async def test_folio_split_item_move_and_transfer(client, seed_test_data, db_session):
    """Test creating split folios, moving line items, and transferring balances."""
    headers = make_auth_headers(role="admin")
    today = date.today()
    tomorrow = today + timedelta(days=1)

    # 1. Create reservation -> auto creates Primary folio
    res_resp = await client.post(
        "/api/reservations",
        json={
            "guest_id": seed_test_data["guest"].id,
            "room_id": seed_test_data["r101"].id,
            "check_in_date": today.isoformat(),
            "check_out_date": tomorrow.isoformat(),
            "adults": 1,
            "nightly_rate": "150.00",
        },
        headers=headers,
    )
    res_id = res_resp.json()["id"]

    # Check folios
    folios_resp = await client.get(f"/api/reservations/{res_id}/folios", headers=headers)
    assert folios_resp.status_code == 200
    folios = folios_resp.json()
    assert len(folios) == 1
    assert folios[0]["name"] == "Primary"
    assert folios[0]["is_master"] is True
    primary_id = folios[0]["id"]

    # 2. Add two charges to Primary folio
    chg1 = await client.post(
        f"/api/billing/reservations/{res_id}/charges",
        json={"folio_id": primary_id, "date": today.isoformat(), "description": "Room Charge", "category": "room", "amount": "150.00"},
        headers=headers,
    )
    chg1_id = chg1.json()["id"]

    chg2 = await client.post(
        f"/api/billing/reservations/{res_id}/charges",
        json={"folio_id": primary_id, "date": today.isoformat(), "description": "Minibar Snacks", "category": "minibar", "amount": "25.00"},
        headers=headers,
    )
    chg2_id = chg2.json()["id"]

    # 3. Create a split folio named "Company Inc"
    split_resp = await client.post(
        f"/api/reservations/{res_id}/folios",
        json={"name": "Company Inc"},
        headers=headers,
    )
    assert split_resp.status_code == 201
    company_id = split_resp.json()["id"]

    # 4. Move Room Charge (chg1) to Company Inc folio
    move_resp = await client.post(
        f"/api/folio-items/{chg1_id}/move",
        json={"folio_id": company_id},
        headers=headers,
    )
    assert move_resp.status_code == 200
    assert move_resp.json()["folio_id"] == company_id

    # 5. Verify balances: Primary should have 25.00, Company should have 150.00
    check_folios = await client.get(f"/api/reservations/{res_id}/folios", headers=headers)
    f_map = {f["id"]: f for f in check_folios.json()}
    assert Decimal(str(f_map[primary_id]["total_amount"])) == Decimal("25.00")
    assert Decimal(str(f_map[company_id]["total_amount"])) == Decimal("150.00")

    # 6. Cannot delete Company folio while it contains items
    del_blocked = await client.delete(f"/api/folios/{company_id}", headers=headers)
    assert del_blocked.status_code == 400

    # 7. Transfer all items from Company folio back to Primary
    xfer_resp = await client.post(
        f"/api/folios/{company_id}/transfer",
        json={"to_folio_id": primary_id},
        headers=headers,
    )
    assert xfer_resp.status_code == 200
    assert xfer_resp.json()["transferred_count"] == 1

    # 8. Now Company folio is empty and can be deleted
    del_ok = await client.delete(f"/api/folios/{company_id}", headers=headers)
    assert del_ok.status_code == 204
