import uuid
import pytest
from httpx import AsyncClient

from app.modules.auth.models import Invite


@pytest.mark.asyncio
async def test_calling_ice_servers_and_call_lifecycle(client: AsyncClient, valid_invite: Invite):
    # 1. Register User A
    reg_a = await client.post(
        "/api/v1/auth/register",
        json={
            "username": "caller_alice",
            "password": "Password12345!",
            "display_name": "Caller Alice",
            "invite_code": valid_invite.code,
            "initial_device": {
                "device_identifier": "caller-dev-1",
                "device_name": "Alice Laptop",
            },
        },
    )
    token_a = reg_a.json()["tokens"]["access_token"]
    user_a_id = reg_a.json()["user"]["id"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # 2. Register User B
    reg_b = await client.post(
        "/api/v1/auth/register",
        json={
            "username": "callee_bob",
            "password": "Password12345!",
            "display_name": "Callee Bob",
            "invite_code": valid_invite.code,
            "initial_device": {
                "device_identifier": "callee-dev-1",
                "device_name": "Bob Laptop",
            },
        },
    )
    user_b_id = reg_b.json()["user"]["id"]

    # 3. Test GET /api/v1/calling/ice-servers
    ice_res = await client.get("/api/v1/calling/ice-servers", headers=headers_a)
    assert ice_res.status_code == 200
    ice_data = ice_res.json()
    assert "ice_servers" in ice_data
    assert len(ice_data["ice_servers"]) == 2  # STUN + TURN
    turn_server = ice_data["ice_servers"][1]
    assert "username" in turn_server
    assert "credential" in turn_server
    assert str(user_a_id) in turn_server["username"]

    # 4. Initiate Call
    conv_id = str(uuid.uuid4())
    call_payload = {
        "conversation_id": conv_id,
        "callee_id": user_b_id,
        "call_type": "video",
    }
    call_res = await client.post("/api/v1/calling/initiate", json=call_payload, headers=headers_a)
    assert call_res.status_code == 201
    call_data = call_res.json()
    assert call_data["status"] == "ringing"
    assert call_data["call_type"] == "video"
    call_id = call_data["id"]

    # 5. End Call
    end_res = await client.post(f"/api/v1/calling/{call_id}/end", headers=headers_a)
    assert end_res.status_code == 200
    assert end_res.json()["status"] == "ended"
    assert end_res.json()["ended_at"] is not None
