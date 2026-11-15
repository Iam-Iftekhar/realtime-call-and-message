import pytest
from httpx import AsyncClient

from app.modules.auth.models import Invite


@pytest.mark.asyncio
async def test_health_endpoints(client: AsyncClient):
    res1 = await client.get("/health")
    assert res1.status_code == 200
    assert res1.json()["status"] == "healthy"

    res2 = await client.get("/api/v1/health")
    assert res2.status_code == 200
    assert res2.json()["service"] == "Project Spectra"


@pytest.mark.asyncio
async def test_register_requires_invite(client: AsyncClient):
    payload = {
        "username": "alice",
        "password": "Password12345!",
        "display_name": "Alice C.",
        "initial_device": {
            "device_identifier": "web-chrome-linux-1",
            "device_name": "Alice ThinkPad",
            "client_platform": "web",
            "client_version": "1.0.0",
        },
    }
    res = await client.post("/api/v1/auth/register", json=payload)
    assert res.status_code == 403
    assert res.json()["code"] == "AUTH_INVITE_REQUIRED"


@pytest.mark.asyncio
async def test_register_and_login_success(client: AsyncClient, valid_invite: Invite):
    # 1. Register with valid invite code
    register_payload = {
        "username": "alice_test",
        "password": "Password12345!",
        "display_name": "Alice Cooper",
        "invite_code": valid_invite.code,
        "initial_device": {
            "device_identifier": "web-chrome-linux-1",
            "device_name": "Alice ThinkPad",
            "client_platform": "web",
            "client_version": "1.0.0",
        },
    }
    reg_res = await client.post("/api/v1/auth/register", json=register_payload)
    assert reg_res.status_code == 201
    reg_data = reg_res.json()
    assert reg_data["user"]["username"] == "alice_test"
    assert reg_data["device"]["device_identifier"] == "web-chrome-linux-1"
    assert "access_token" in reg_data["tokens"]
    assert "refresh_token" in reg_data["tokens"]

    access_token = reg_data["tokens"]["access_token"]
    refresh_token = reg_data["tokens"]["refresh_token"]

    # 2. Login with registered user
    login_payload = {
        "username": "alice_test",
        "password": "Password12345!",
        "device": {
            "device_identifier": "web-chrome-linux-1",
            "device_name": "Alice ThinkPad",
            "client_platform": "web",
            "client_version": "1.0.0",
        },
    }
    login_res = await client.post("/api/v1/auth/login", json=login_payload)
    assert login_res.status_code == 200
    login_data = login_res.json()
    assert login_data["user"]["username"] == "alice_test"
    assert "access_token" in login_data["tokens"]

    # 3. Test refresh token rotation
    rf_res = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": refresh_token}
    )
    assert rf_res.status_code == 200
    rf_data = rf_res.json()
    new_refresh_token = rf_data["refresh_token"]
    assert new_refresh_token != refresh_token

    # 4. Re-using the consumed refresh token triggers reuse detection
    reused_res = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": refresh_token}
    )
    assert reused_res.status_code == 401
    assert reused_res.json()["code"] == "AUTH_TOKEN_COMPROMISED"


@pytest.mark.asyncio
async def test_register_duplicate_username_fails(client: AsyncClient, valid_invite: Invite):
    payload = {
        "username": "bob_duplicate",
        "password": "Password12345!",
        "display_name": "Bob D.",
        "invite_code": valid_invite.code,
        "initial_device": {
            "device_identifier": "web-chrome-1",
            "device_name": "Bob Device",
            "client_platform": "web",
            "client_version": "1.0.0",
        },
    }
    res1 = await client.post("/api/v1/auth/register", json=payload)
    assert res1.status_code == 201

    res2 = await client.post("/api/v1/auth/register", json=payload)
    assert res2.status_code == 409
    assert res2.json()["code"] == "AUTH_USERNAME_TAKEN"


@pytest.mark.asyncio
async def test_sessions_and_logout(client: AsyncClient, valid_invite: Invite):
    reg_payload = {
        "username": "charlie_sess",
        "password": "Password12345!",
        "display_name": "Charlie",
        "invite_code": valid_invite.code,
        "initial_device": {
            "device_identifier": "web-safari-1",
            "device_name": "Charlie MacBook",
            "client_platform": "web",
            "client_version": "1.0.0",
        },
    }
    reg_res = await client.post("/api/v1/auth/register", json=reg_payload)
    token = reg_res.json()["tokens"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # List sessions
    sess_res = await client.get("/api/v1/auth/sessions", headers=headers)
    assert sess_res.status_code == 200
    sessions = sess_res.json()
    assert len(sessions) == 1
    session_id = sessions[0]["id"]

    # Logout
    logout_res = await client.post("/api/v1/auth/logout", headers=headers)
    assert logout_res.status_code == 204

    # Now using the old token fails because the session is revoked
    check_res = await client.get("/api/v1/auth/sessions", headers=headers)
    assert check_res.status_code == 401
    assert check_res.json()["code"] == "AUTH_SESSION_REVOKED"
