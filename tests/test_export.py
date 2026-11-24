"""Test suite for One-Click Full Data Export (ZIP containing 6 CSVs + README.txt)."""
import io
import zipfile
import pytest
from app.models import Organization, User
from tests.conftest import make_auth_headers


@pytest.mark.asyncio
async def test_admin_export_produces_valid_zip_with_six_csvs(client, db_session, seed_test_data):
    """Verify POST /api/admin/export returns a valid ZIP archive containing 6 CSVs and README.txt."""
    headers = make_auth_headers(username="admin", role="admin")

    resp = await client.post("/api/admin/export", headers=headers)
    assert resp.status_code == 200, resp.text
    assert "application/zip" in resp.headers.get("content-type", "")

    # Read zip archive
    zip_bytes = resp.content
    with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as z:
        names = z.namelist()
        expected_files = [
            "reservations.csv",
            "rooms.csv",
            "guests.csv",
            "folios.csv",
            "folio_items.csv",
            "payments.csv",
            "README.txt",
        ]
        for ef in expected_files:
            assert ef in names, f"Expected {ef} to be included in data export ZIP"

        readme_text = z.read("README.txt").decode("utf-8")
        assert "Data Export Archive" in readme_text
