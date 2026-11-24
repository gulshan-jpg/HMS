"""Tests for Request a Demo endpoint and persistence."""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_demo_request_saves_to_database(client: AsyncClient):
    payload = {
        "full_name": "Aarav Patel",
        "email": "aarav@palaceudaipur.in",
        "phone": "+919823456789",
        "hotel_name": "Udaipur Lake Palace",
        "property_type": "boutique",
        "rooms_count": "16-50",
        "city": "Udaipur, Rajasthan",
        "preferred_slot": "Tomorrow Afternoon (3:00 PM)",
        "notes": "Interested in GST invoicing and OTA sync."
    }
    resp = await client.post("/api/demo-request", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "success"
    assert data["message"] == "Demo booked successfully"
    assert data["hotel_name"] == "Udaipur Lake Palace"
    assert data["contact_name"] == "Aarav Patel"
    assert data["phone"] == "+919823456789"
    assert data["email"] == "aarav@palaceudaipur.in"
    assert data["preferred_slot"] == "Tomorrow Afternoon (3:00 PM)"
    assert data["demo_id"] > 0
