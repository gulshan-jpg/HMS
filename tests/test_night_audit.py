"""Tests for Night Audit, EOD Room Charge Posting, No-Shows, and Business Date Transition."""
from datetime import date, timedelta
from decimal import Decimal
import pytest
from tests.conftest import make_auth_headers
from app.models import BusinessDate, DailySnapshot, FolioItem, Reservation, Room


@pytest.mark.asyncio
async def test_night_audit_business_date_and_preview(client, seed_test_data):
    """Test retrieving current business date and dry-run audit preview."""
    headers = make_auth_headers(role="admin")

    bd_resp = await client.get("/api/night-audit/business-date", headers=headers)
    assert bd_resp.status_code == 200
    bd = bd_resp.json()
    assert bd["status"] == "open"
    curr_date = date.fromisoformat(bd["date"])

    prev_resp = await client.get("/api/night-audit/preview", headers=headers)
    assert prev_resp.status_code == 200
    preview = prev_resp.json()
    assert preview["business_date"] == curr_date.isoformat()
    assert preview["next_business_date"] == (curr_date + timedelta(days=1)).isoformat()
    assert preview["can_run_without_force"] is True


@pytest.mark.asyncio
async def test_night_audit_unresolved_departures_block_unless_forced(client, seed_test_data, db_session):
    """Unresolved departure due today prevents audit run unless force=True."""
    headers = make_auth_headers(role="admin")

    bd_resp = await client.get("/api/night-audit/business-date", headers=headers)
    curr_date = date.fromisoformat(bd_resp.json()["date"])

    # Create checked-in reservation whose checkout date is today (due departure)
    res = Reservation(
        confirmation_number="HTL-DEPART-01",
        guest_id=seed_test_data["guest"].id,
        room_id=seed_test_data["r101"].id,
        check_in_date=curr_date - timedelta(days=2),
        check_out_date=curr_date,
        adults=1,
        children=0,
        nightly_rate=Decimal("120.00"),
        status="checked_in",
    )
    db_session.add(res)
    db_session.commit()

    # Preview should show unresolved departure
    prev_resp = await client.get("/api/night-audit/preview", headers=headers)
    assert prev_resp.status_code == 200
    preview = prev_resp.json()
    assert preview["unresolved_departures_count"] >= 1
    assert preview["can_run_without_force"] is False

    # Attempt audit without force -> 400 Bad Request
    fail_run = await client.post("/api/night-audit/run", json={"force": False}, headers=headers)
    assert fail_run.status_code == 400
    err_msg = fail_run.json().get("error", {}).get("message") or fail_run.json().get("detail", "")
    assert "Cannot close day" in err_msg

    # Attempt audit with force -> 200 OK
    ok_run = await client.post("/api/night-audit/run", json={"force": True}, headers=headers)
    assert ok_run.status_code == 200
    run_data = ok_run.json()
    assert run_data["success"] is True
    assert run_data["previous_business_date"] == curr_date.isoformat()
    assert run_data["new_business_date"] == (curr_date + timedelta(days=1)).isoformat()


@pytest.mark.asyncio
async def test_night_audit_posts_charges_marks_noshows_and_creates_snapshot(client, seed_test_data, db_session):
    """Audit posts room charges & taxes for in-house guests, marks no-shows, and records snapshot."""
    headers = make_auth_headers(role="admin")

    bd_resp = await client.get("/api/night-audit/business-date", headers=headers)
    curr_date = date.fromisoformat(bd_resp.json()["date"])

    # 1. Checked-in guest in room 101 staying over current date
    res_inhouse = Reservation(
        confirmation_number="HTL-AUDIT-01",
        guest_id=seed_test_data["guest"].id,
        room_id=seed_test_data["r101"].id,
        check_in_date=curr_date,
        check_out_date=curr_date + timedelta(days=2),
        adults=1,
        children=0,
        nightly_rate=Decimal("150.00"),
        status="checked_in",
    )
    # 2. Booked guest who failed to check in today (no-show)
    res_noshow = Reservation(
        confirmation_number="HTL-AUDIT-02",
        guest_id=seed_test_data["guest"].id,
        room_id=seed_test_data["r102"].id,
        check_in_date=curr_date,
        check_out_date=curr_date + timedelta(days=1),
        adults=1,
        children=0,
        nightly_rate=Decimal("130.00"),
        status="booked",
    )
    db_session.add_all([res_inhouse, res_noshow])
    db_session.commit()

    # Run audit
    run_resp = await client.post("/api/night-audit/run", json={"force": True}, headers=headers)
    assert run_resp.status_code == 200
    result = run_resp.json()
    assert result["success"] is True
    assert result["room_charges_posted"] >= 1
    assert result["no_shows_marked"] >= 1

    # Verify room charge posted on res_inhouse
    db_session.expire_all()
    room_charge = (
        db_session.query(FolioItem)
        .filter(FolioItem.reservation_id == res_inhouse.id, FolioItem.category == "room")
        .first()
    )
    assert room_charge is not None
    assert room_charge.date == curr_date

    # Verify res_noshow flipped to no_show
    ns_res = db_session.query(Reservation).filter(Reservation.id == res_noshow.id).first()
    assert ns_res.status == "no_show"

    # Verify history has snapshot
    hist_resp = await client.get("/api/night-audit/history", headers=headers)
    assert hist_resp.status_code == 200
    history = hist_resp.json()
    assert len(history) >= 1
    assert history[0]["business_date"] == curr_date.isoformat()
