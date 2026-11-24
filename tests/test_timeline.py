"""Tests for Availability Timeline: Gantt View and Move Reservation Overlap Protection."""
from datetime import date, timedelta
import pytest
from tests.conftest import make_auth_headers
from app.models import Reservation, Room


@pytest.mark.asyncio
async def test_timeline_feed_and_move_reservation(client, seed_test_data):
    """Verify timeline returns room tracks and reservation move endpoint functions."""
    headers = make_auth_headers(role="admin")
    today = date.today()
    in_2d = today + timedelta(days=2)
    in_4d = today + timedelta(days=4)

    # 1. Create a reservation in Room 101
    res1_resp = await client.post(
        "/api/reservations",
        json={
            "guest_id": seed_test_data["guest"].id,
            "room_id": seed_test_data["r101"].id,
            "check_in_date": today.isoformat(),
            "check_out_date": in_2d.isoformat(),
            "adults": 1,
        },
        headers=headers,
    )
    assert res1_resp.status_code == 201
    res1_id = res1_resp.json()["id"]

    # 2. Query timeline
    tl_resp = await client.get(f"/api/timeline?start_date={today.isoformat()}&days=30", headers=headers)
    assert tl_resp.status_code == 200
    tl_data = tl_resp.json()
    assert tl_data["days_count"] == 30

    r101_track = next(r for r in tl_data["rooms"] if r["id"] == seed_test_data["r101"].id)
    assert len(r101_track["reservations"]) >= 1
    assert r101_track["reservations"][0]["id"] == res1_id

    # 3. Move reservation to Room 102 and new dates
    move_resp = await client.patch(
        f"/api/reservations/{res1_id}/move",
        json={
            "room_id": seed_test_data["r102"].id,
            "check_in_date": in_2d.isoformat(),
            "check_out_date": in_4d.isoformat(),
        },
        headers=headers,
    )
    assert move_resp.status_code == 200
    moved_data = move_resp.json()
    assert moved_data["room_id"] == seed_test_data["r102"].id
    assert moved_data["check_in_date"] == in_2d.isoformat()


@pytest.mark.asyncio
async def test_move_reservation_overlap_conflict_409(client, seed_test_data):
    """Moving a reservation into a room already booked for overlapping dates must return 409 Conflict."""
    headers = make_auth_headers(role="admin")
    today = date.today()
    in_3d = today + timedelta(days=3)
    in_5d = today + timedelta(days=5)

    # Res A in Room 101: today -> in_3d
    await client.post(
        "/api/reservations",
        json={
            "guest_id": seed_test_data["guest"].id,
            "room_id": seed_test_data["r101"].id,
            "check_in_date": today.isoformat(),
            "check_out_date": in_3d.isoformat(),
            "adults": 1,
        },
        headers=headers,
    )

    # Res B in Room 102: in_3d -> in_5d
    resB_resp = await client.post(
        "/api/reservations",
        json={
            "guest_id": seed_test_data["guest"].id,
            "room_id": seed_test_data["r102"].id,
            "check_in_date": in_3d.isoformat(),
            "check_out_date": in_5d.isoformat(),
            "adults": 1,
        },
        headers=headers,
    )
    resB_id = resB_resp.json()["id"]

    # Attempt to move Res B to Room 101 with dates overlapping Res A (e.g. today -> in_5d)
    conflict_move = await client.patch(
        f"/api/reservations/{resB_id}/move",
        json={
            "room_id": seed_test_data["r101"].id,
            "check_in_date": today.isoformat(),
            "check_out_date": in_5d.isoformat(),
        },
        headers=headers,
    )
    assert conflict_move.status_code == 409
    assert "is unavailable" in conflict_move.json()["error"]["message"]
