import uuid
import pytest
from httpx import AsyncClient

from app.modules.auth.models import Invite


@pytest.mark.asyncio
async def test_messaging_untrusted_mailbox_and_ack_deletion(client: AsyncClient, valid_invite: Invite):
    # 1. Register Alice
    reg_alice = await client.post(
        "/api/v1/auth/register",
        json={
            "username": "msg_alice",
            "password": "Password12345!",
            "display_name": "Alice M.",
            "invite_code": valid_invite.code,
            "initial_device": {
                "device_identifier": "alice-phone",
                "device_name": "Alice Phone",
            },
        },
    )
    token_alice = reg_alice.json()["tokens"]["access_token"]
    user_alice_id = reg_alice.json()["user"]["id"]
    headers_alice = {"Authorization": f"Bearer {token_alice}"}

    # 2. Register Bob
    reg_bob = await client.post(
        "/api/v1/auth/register",
        json={
            "username": "msg_bob",
            "password": "Password12345!",
            "display_name": "Bob M.",
            "invite_code": valid_invite.code,
            "initial_device": {
                "device_identifier": "bob-phone",
                "device_name": "Bob Phone",
            },
        },
    )
    token_bob = reg_bob.json()["tokens"]["access_token"]
    user_bob_id = reg_bob.json()["user"]["id"]
    device_bob_id = reg_bob.json()["device"]["id"]
    headers_bob = {"Authorization": f"Bearer {token_bob}"}

    # 3. Alice creates conversation with Bob
    conv_res = await client.post(
        "/api/v1/conversations",
        json={
            "type": "direct",
            "participant_user_ids": [user_bob_id],
        },
        headers=headers_alice,
    )
    assert conv_res.status_code == 201
    conv_id = conv_res.json()["id"]

    # 4. Alice sends an encrypted envelope addressed to Bob's device
    send_payload = {
        "conversation_id": conv_id,
        "envelopes": [
            {
                "recipient_device_id": device_bob_id,
                "envelope_type": "olm_msg",
                "ciphertext": "OpaqueBase64CiphertextBlob===",
                "iv": "InitializationVectorMock==",
                "auth_tag": "AuthTagMock==",
            }
        ],
    }
    send_res = await client.post("/api/v1/messages/send-batch", json=send_payload, headers=headers_alice)
    assert send_res.status_code == 200
    sent_envelopes = send_res.json()
    assert len(sent_envelopes) == 1
    env_id = sent_envelopes[0]["id"]
    assert sent_envelopes[0]["sequence_id"] == 1

    # 5. Bob connects and syncs pending envelopes
    sync_res = await client.get("/api/v1/messages/sync?last_seq=0", headers=headers_bob)
    assert sync_res.status_code == 200
    pending_envelopes = sync_res.json()["envelopes"]
    assert len(pending_envelopes) == 1
    assert pending_envelopes[0]["id"] == env_id
    assert pending_envelopes[0]["ciphertext"] == "OpaqueBase64CiphertextBlob==="

    # 6. Bob acknowledges the envelope (Client-side decrypted & committed to local storage)
    ack_res = await client.post(
        "/api/v1/messages/ack",
        json={"envelope_ids": [env_id]},
        headers=headers_bob,
    )
    assert ack_res.status_code == 200
    assert ack_res.json()["acknowledged_count"] == 1

    # 7. Zero-Knowledge Verification: The mailbox is now EMPTY!
    sync_res2 = await client.get("/api/v1/messages/sync?last_seq=0", headers=headers_bob)
    assert sync_res2.status_code == 200
    assert len(sync_res2.json()["envelopes"]) == 0
