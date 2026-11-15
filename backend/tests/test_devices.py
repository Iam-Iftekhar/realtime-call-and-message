import pytest
from httpx import AsyncClient

from app.modules.auth.models import Invite


@pytest.mark.asyncio
async def test_device_lifecycle(client: AsyncClient, valid_invite: Invite):
    # Register user with device 1
    reg_payload = {
        "username": "device_tester",
        "password": "Password12345!",
        "display_name": "Device Tester",
        "invite_code": valid_invite.code,
        "initial_device": {
            "device_identifier": "laptop-linux-1",
            "device_name": "ThinkPad Work",
            "client_platform": "desktop",
            "client_version": "1.0.0",
        },
    }
    reg_res = await client.post("/api/v1/auth/register", json=reg_payload)
    token = reg_res.json()["tokens"]["access_token"]
    dev1_id = reg_res.json()["device"]["id"]
    headers = {"Authorization": f"Bearer {token}"}

    # Register second device (phone)
    dev2_payload = {
        "device_identifier": "phone-android-1",
        "device_name": "Pixel 8 Pro",
        "client_platform": "android",
        "client_version": "1.0.0",
    }
    dev2_res = await client.post("/api/v1/devices/register", json=dev2_payload, headers=headers)
    assert dev2_res.status_code == 201
    dev2_id = dev2_res.json()["id"]

    # List devices
    list_res = await client.get("/api/v1/devices", headers=headers)
    assert list_res.status_code == 200
    devices = list_res.json()
    assert len(devices) == 2
    dev_ids = {d["id"] for d in devices}
    assert dev1_id in dev_ids
    assert dev2_id in dev_ids

    # Revoke second device
    rev_res = await client.delete(f"/api/v1/devices/{dev2_id}", headers=headers)
    assert rev_res.status_code == 204

    # List devices again: only dev1 remains active
    list_res2 = await client.get("/api/v1/devices", headers=headers)
    assert list_res2.status_code == 200
    devices2 = list_res2.json()
    assert len(devices2) == 1
    assert devices2[0]["id"] == dev1_id
