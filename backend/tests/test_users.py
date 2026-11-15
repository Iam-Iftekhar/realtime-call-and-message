import pytest
from httpx import AsyncClient

from app.modules.auth.models import Invite


@pytest.mark.asyncio
async def test_user_profile_and_search(client: AsyncClient, valid_invite: Invite):
    # 1. Register User
    reg_res = await client.post(
        "/api/v1/auth/register",
        json={
            "username": "profile_user",
            "password": "Password12345!",
            "display_name": "Original Name",
            "invite_code": valid_invite.code,
            "initial_device": {
                "device_identifier": "user-dev-1",
                "device_name": "Test Device",
            },
        },
    )
    token = reg_res.json()["tokens"]["access_token"]
    user_id = reg_res.json()["user"]["id"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. GET /users/me
    me_res = await client.get("/api/v1/users/me", headers=headers)
    assert me_res.status_code == 200
    assert me_res.json()["username"] == "profile_user"
    assert me_res.json()["display_name"] == "Original Name"

    # 3. PATCH /users/me
    patch_res = await client.patch(
        "/api/v1/users/me",
        json={"display_name": "Updated Display Name"},
        headers=headers,
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["display_name"] == "Updated Display Name"

    # 4. Search users
    search_res = await client.get("/api/v1/users/search?q=profile", headers=headers)
    assert search_res.status_code == 200
    results = search_res.json()
    assert len(results) >= 1
    assert any(r["id"] == user_id for r in results)
