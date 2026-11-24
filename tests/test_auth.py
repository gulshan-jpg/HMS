"""Tests for Authentication, JWT Validation, Password Policy, and Health Probe."""
from datetime import timedelta
import pytest
from app.auth import create_access_token
from tests.conftest import make_auth_headers


@pytest.mark.asyncio
async def test_healthz_endpoint(client, db_session):
    """Verify system health and database probe."""
    resp = await client.get("/healthz")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["db"] == "ok"


@pytest.mark.asyncio
async def test_login_success(client, seed_test_data):
    """Verify valid credentials return JWT token and user profile."""
    resp = await client.post(
        "/api/auth/login",
        json={"username_or_email": "admin", "password": "admin123"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["username"] == "admin"
    assert data["user"]["role"] == "admin"
    assert "access_token" in resp.cookies


@pytest.mark.asyncio
async def test_login_failure_invalid_password(client, seed_test_data):
    """Verify invalid password returns HTTP 401 with standard error envelope."""
    resp = await client.post(
        "/api/auth/login",
        json={"username_or_email": "admin", "password": "wrongpassword"},
    )
    assert resp.status_code == 401
    data = resp.json()
    assert "error" in data
    assert data["error"]["code"] == "HTTP_401"


@pytest.mark.asyncio
async def test_jwt_expired_token_rejection(client, seed_test_data):
    """Verify expired JWT tokens are rejected with HTTP 401."""
    # Issue token expired 1 hour ago
    expired_token = create_access_token(
        data={"sub": "admin", "role": "admin"},
        expires_delta=timedelta(hours=-1),
    )
    headers = {"Authorization": f"Bearer {expired_token}"}
    resp = await client.get("/api/auth/me", headers=headers)
    assert resp.status_code == 401
    data = resp.json()
    assert "error" in data


@pytest.mark.asyncio
async def test_auth_me_success(client, seed_test_data):
    """Verify valid token retrieves active user info."""
    headers = make_auth_headers("admin", "admin")
    resp = await client.get("/api/auth/me", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["username"] == "admin"
    assert data["email"] == "admin@test.com"


@pytest.mark.asyncio
async def test_password_policy_enforcement(client, seed_test_data):
    """Verify password policy (>=10 chars, 1 letter, 1 number) on user creation."""
    headers = make_auth_headers("admin", "admin")

    # Too short (<10 chars)
    resp = await client.post(
        "/api/users",
        json={
            "email": "short@test.com",
            "username": "shortuser",
            "full_name": "Short User",
            "password": "Abc1",
            "role": "front_desk",
        },
        headers=headers,
    )
    assert resp.status_code == 422

    # No number
    resp = await client.post(
        "/api/users",
        json={
            "email": "nonum@test.com",
            "username": "nonumuser",
            "full_name": "No Num User",
            "password": "LongPasswordWithoutNumbers",
            "role": "front_desk",
        },
        headers=headers,
    )
    assert resp.status_code == 422

    # Valid password
    resp = await client.post(
        "/api/users",
        json={
            "email": "valid@test.com",
            "username": "validuser",
            "full_name": "Valid User",
            "password": "ValidStrongPassword1",
            "role": "front_desk",
        },
        headers=headers,
    )
    assert resp.status_code == 201
    assert resp.json()["username"] == "validuser"
