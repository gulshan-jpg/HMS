"""Tests for Gmail and WhatsApp Inbound Channel Sync & Auto-Reservations."""
import pytest
from httpx import AsyncClient
from tests.conftest import make_auth_headers


@pytest.mark.asyncio
async def test_channel_sync_status(client: AsyncClient, seed_test_data):
    """Verify channel sync connectivity status and webhook endpoints."""
    headers = make_auth_headers()
    resp = await client.get(
        "/api/integrations/status",
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "operational"
    assert "whatsapp" in data
    assert "gmail" in data
    assert data["whatsapp"]["status"] == "connected"
    assert data["gmail"]["status"] == "connected"


@pytest.mark.asyncio
async def test_whatsapp_inbound_booking(client: AsyncClient, seed_test_data):
    """Verify WhatsApp message is parsed and an available room is booked automatically."""
    headers = make_auth_headers()
    payload = {
        "channel": "whatsapp",
        "sender": "+91 99887 76655",
        "sender_name": "Arjun Kapoor",
        "raw_text": "Hi, I want to book a Deluxe room from 2026-11-28 to 2026-11-30 for Arjun Kapoor, 2 guests. Phone: +91 99887 76655.",
    }
    resp = await client.post(
        "/api/integrations/inbox-sync",
        json=payload,
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["channel"] == "whatsapp"
    assert "HTL-WA-" in data["confirmation_number"]
    assert "Arjun Kapoor" in data["guest_name"]
    assert data["nights"] == 2
    assert data["room_number"] is not None
    assert data["total_amount"] > 0


@pytest.mark.asyncio
async def test_gmail_inbound_booking(client: AsyncClient, seed_test_data):
    """Verify Gmail confirmation email is parsed and an available room is booked automatically."""
    headers = make_auth_headers()
    payload = {
        "channel": "gmail",
        "sender": "confirmations@booking.com",
        "sender_name": "Booking.com Inbound",
        "subject": "Booking Confirmed: Sunita Rao (#BK-91823)",
        "raw_text": "Booking ID #BK-91823. Guest Name: Sunita Rao. Email: sunita.rao@example.com. Phone: +91 98765 00112. Room: Standard. Check-in: 2026-11-29, Check-out: 2026-12-01. 1 adult.",
    }
    resp = await client.post(
        "/api/integrations/inbox-sync",
        json=payload,
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["channel"] == "gmail"
    assert "HTL-GM-" in data["confirmation_number"]
    assert "Sunita Rao" in data["guest_name"]
    assert data["nights"] == 2


@pytest.mark.asyncio
async def test_ota_inbound_parsers(client: AsyncClient, seed_test_data):
    """Verify OYO, Airbnb, and Agoda booking voucher messages are recognized and booked."""
    headers = make_auth_headers()

    # 1. Test OYO Booking Alert
    oyo_payload = {
        "channel": "whatsapp",
        "sender": "+91 80100 00099",
        "sender_name": "OYO Central Bookings",
        "raw_text": "OYO Booking Alert! Booking ID: OYO-94821. New booking received for Rohan Mehta (2 guests). Check-in: 2026-11-26, Check-out: 2026-11-28. Room: Deluxe King. Total Amount: INR 15,000. Phone: +91 91234 56789.",
    }
    resp1 = await client.post("/api/integrations/inbox-sync", json=oyo_payload, headers=headers)
    assert resp1.status_code == 200
    d1 = resp1.json()
    assert d1["success"] is True
    assert d1["ota_provider"] == "OYO"
    assert "OYO" in d1["confirmation_number"]
    assert "Rohan Mehta" in d1["guest_name"]

    # 2. Test Airbnb Reservation Notification
    airbnb_payload = {
        "channel": "gmail",
        "sender": "automated@airbnb.com",
        "sender_name": "Airbnb Host Notifications",
        "raw_text": "Subject: Reservation confirmed - Sarah Jenkins arrives 26 Nov\n\nAirbnb Confirmation Code: HM489X2P\nGuest: Sarah Jenkins\nGuests: 2 adults\nDates: Nov 26 - Nov 29, 2026 (3 nights)\nListing: Executive Suite\nTotal Host Payout: INR 49,500\nGuest Contact: +1 415 555 2671",
    }
    resp2 = await client.post("/api/integrations/inbox-sync", json=airbnb_payload, headers=headers)
    assert resp2.status_code == 200
    d2 = resp2.json()
    assert d2["success"] is True
    assert d2["ota_provider"] == "Airbnb"
    assert "Sarah Jenkins" in d2["guest_name"]

    # 3. Test Agoda Booking Voucher
    agoda_payload = {
        "channel": "gmail",
        "sender": "express-booking@agoda.com",
        "sender_name": "Agoda Bookings",
        "raw_text": "Agoda Booking Voucher - ID: 7892143\n\nGuest Name: Hiroshi Tanaka\nStay Dates: 2026-11-27 to 2026-11-30 (3 nights)\nBooked Room Type: Standard Suite\nNumber of Guests: 1 adult\nAmount Collected by Agoda: INR 18,000\nGuest Email: h.tanaka@agoda-guest.com",
    }
    resp3 = await client.post("/api/integrations/inbox-sync", json=agoda_payload, headers=headers)
    assert resp3.status_code == 200
    d3 = resp3.json()
    assert d3["success"] is True
    assert d3["ota_provider"] == "Agoda"
    assert "Hiroshi Tanaka" in d3["guest_name"]


@pytest.mark.asyncio
async def test_channel_sync_feed(client: AsyncClient, seed_test_data):
    """Verify feed returns recently ingested channel reservations."""
    headers = make_auth_headers()
    # First create an inbound booking
    await client.post(
        "/api/integrations/inbox-sync",
        json={
            "channel": "whatsapp",
            "sender": "+91 91234 56789",
            "sender_name": "Kiran Bedi",
            "raw_text": "Please book room from 2026-11-26 to 2026-11-28 for Kiran Bedi.",
        },
        headers=headers,
    )
    resp = await client.get(
        "/api/integrations/feed",
        headers=headers,
    )
    assert resp.status_code == 200
    feed = resp.json()
    assert isinstance(feed, list)
    assert len(feed) >= 1
    channels = [item["channel"] for item in feed]
    assert "whatsapp" in channels or "gmail" in channels
    assert any("ota_provider" in item for item in feed)
