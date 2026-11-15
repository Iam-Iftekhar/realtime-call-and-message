import base64
import pytest
from httpx import AsyncClient

from app.modules.auth.models import Invite


@pytest.mark.asyncio
async def test_prekey_bundle_upload_and_claim(
    client: AsyncClient, valid_invite: Invite, ed25519_keypair
):
    priv_key, identity_pub_b64 = ed25519_keypair

    # 1. Register User
    reg_payload = {
        "username": "crypto_alice",
        "password": "Password12345!",
        "display_name": "Crypto Alice",
        "invite_code": valid_invite.code,
        "initial_device": {
            "device_identifier": "browser-chrome-alice",
            "device_name": "Alice Chrome",
            "client_platform": "web",
            "client_version": "1.0.0",
        },
    }
    reg_res = await client.post("/api/v1/auth/register", json=reg_payload)
    token = reg_res.json()["tokens"]["access_token"]
    user_id = reg_res.json()["user"]["id"]
    device_id = reg_res.json()["device"]["id"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Generate signed pre-key and valid Ed25519 signature
    signed_prekey_raw = b"SignedPreKey-MockBytes-32-Bytes!"
    signed_prekey_b64 = base64.b64encode(signed_prekey_raw).decode("utf-8")
    sig_bytes = priv_key.sign(signed_prekey_raw)
    sig_b64 = base64.b64encode(sig_bytes).decode("utf-8")

    # Upload prekey bundle with 2 OTKs
    upload_payload = {
        "device_id": device_id,
        "identity_key": identity_pub_b64,
        "signed_prekey": {
            "key_id": 1,
            "public_key": signed_prekey_b64,
            "signature": sig_b64,
        },
        "one_time_prekeys": [
            {"key_id": 101, "public_key": base64.b64encode(b"OTK-1-KeyBytes-32BytesLongMock!").decode("utf-8")},
            {"key_id": 102, "public_key": base64.b64encode(b"OTK-2-KeyBytes-32BytesLongMock!").decode("utf-8")},
        ],
    }
    up_res = await client.post("/api/v1/crypto/prekeys/upload", json=upload_payload, headers=headers)
    assert up_res.status_code == 200
    assert up_res.json()["status"] == "uploaded"
    assert up_res.json()["otk_added"] == 2
    assert up_res.json()["total_otk_available"] == 2

    # 3. Discovery: get user devices
    dev_res = await client.get(f"/api/v1/crypto/prekeys/{user_id}/devices", headers=headers)
    assert dev_res.status_code == 200
    devices = dev_res.json()["devices"]
    assert len(devices) == 1
    assert devices[0]["device_id"] == device_id

    # 4. Fetch prekey bundle (claim 1 OTK)
    claim_payload = {"device_ids": [device_id]}
    bundle_res = await client.post("/api/v1/crypto/prekeys/bundle", json=claim_payload, headers=headers)
    assert bundle_res.status_code == 200
    bundles = bundle_res.json()["bundles"]
    assert len(bundles) == 1
    assert bundles[0]["device_id"] == device_id
    assert bundles[0]["identity_key"] == identity_pub_b64
    assert bundles[0]["signed_prekey"]["key_id"] == 1
    assert bundles[0]["one_time_prekey"]["key_id"] == 101  # Claimed OTK 101!

    # 5. Fetch prekey bundle again: should claim the next OTK (102)
    bundle_res2 = await client.post("/api/v1/crypto/prekeys/bundle", json=claim_payload, headers=headers)
    assert bundle_res2.status_code == 200
    bundles2 = bundle_res2.json()["bundles"]
    assert bundles2[0]["one_time_prekey"]["key_id"] == 102  # Claimed OTK 102!

    # 6. Fetch again: all OTKs consumed, so one_time_prekey is None
    bundle_res3 = await client.post("/api/v1/crypto/prekeys/bundle", json=claim_payload, headers=headers)
    assert bundle_res3.status_code == 200
    bundles3 = bundle_res3.json()["bundles"]
    assert bundles3[0]["one_time_prekey"] is None


@pytest.mark.asyncio
async def test_forged_prekey_signature_rejected(
    client: AsyncClient, valid_invite: Invite, ed25519_keypair
):
    _, identity_pub_b64 = ed25519_keypair

    # Register User
    reg_payload = {
        "username": "crypto_bob",
        "password": "Password12345!",
        "display_name": "Crypto Bob",
        "invite_code": valid_invite.code,
        "initial_device": {
            "device_identifier": "browser-firefox-bob",
            "device_name": "Bob Firefox",
            "client_platform": "web",
            "client_version": "1.0.0",
        },
    }
    reg_res = await client.post("/api/v1/auth/register", json=reg_payload)
    token = reg_res.json()["tokens"]["access_token"]
    device_id = reg_res.json()["device"]["id"]
    headers = {"Authorization": f"Bearer {token}"}

    # Upload prekey bundle with FORGED signature
    upload_payload = {
        "device_id": device_id,
        "identity_key": identity_pub_b64,
        "signed_prekey": {
            "key_id": 1,
            "public_key": base64.b64encode(b"SignedPreKey-MockBytes-32-Bytes!").decode("utf-8"),
            "signature": base64.b64encode(b"ForgedGarbageSignatureBytes64BytesLongPaddingPaddingPadding123456").decode("utf-8"),
        },
        "one_time_prekeys": [],
    }
    up_res = await client.post("/api/v1/crypto/prekeys/upload", json=upload_payload, headers=headers)
    assert up_res.status_code == 422
    assert up_res.json()["code"] == "CRYPTO_SIGNATURE_INVALID"
