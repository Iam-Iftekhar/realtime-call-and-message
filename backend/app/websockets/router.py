import json
import logging
import time
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import select

from app.core.database import async_session_factory
from app.core.security import decode_access_token
from app.modules.auth.models import Session, User
from app.modules.devices.models import Device
from app.modules.messaging.models import ConversationMember
from app.modules.messaging.schemas import EnvelopeBatchSendRequest, EnvelopeItem
from app.modules.messaging.services import MessagingService
from app.websockets.connection_manager import manager

logger = logging.getLogger(__name__)
ws_router = APIRouter(tags=["WebSockets"])


@ws_router.websocket("/ws/v1/connect")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    authenticated = False
    current_user_id: uuid.UUID | None = None
    current_device_id: uuid.UUID | None = None

    try:
        while True:
            raw_data = await websocket.receive_text()
            try:
                frame = json.loads(raw_data)
            except Exception:
                await websocket.send_text(json.dumps({
                    "type": "ERROR",
                    "code": 4005,
                    "message": "Malformed JSON frame",
                }))
                continue

            frame_type = frame.get("type")
            frame_id = frame.get("id", str(uuid.uuid4()))
            payload = frame.get("payload", {})

            # 1. AUTHENTICATION HANDSHAKE
            if frame_type == "AUTH_INIT":
                token = payload.get("token")
                req_dev_id_str = payload.get("device_id")
                if not token or not req_dev_id_str:
                    await websocket.send_text(json.dumps({
                        "type": "ERROR",
                        "code": 4001,
                        "message": "token and device_id are required in AUTH_INIT",
                    }))
                    await websocket.close(code=4001)
                    break

                try:
                    claims = decode_access_token(token)
                    user_id = uuid.UUID(claims["sub"])
                    device_id = uuid.UUID(req_dev_id_str)
                    session_id = uuid.UUID(claims["sid"])

                    async with async_session_factory() as db:
                        # Verify session in DB
                        s_res = await db.execute(
                            select(Session).where(
                                Session.id == session_id,
                                Session.user_id == user_id,
                                Session.device_id == device_id,
                                Session.revoked_at.is_(None),
                            )
                        )
                        session_record = s_res.scalar_one_or_none()
                        if not session_record:
                            await websocket.send_text(json.dumps({
                                "type": "ERROR",
                                "code": 4003,
                                "message": "Session has been revoked",
                            }))
                            await websocket.close(code=4003)
                            break

                    authenticated = True
                    current_user_id = user_id
                    current_device_id = device_id

                    # Register in connection manager
                    manager.active_sockets[device_id] = websocket
                    if user_id not in manager.user_devices:
                        manager.user_devices[user_id] = set()
                    manager.user_devices[user_id].add(device_id)
                    manager.socket_info[websocket] = (user_id, device_id)

                    await websocket.send_text(json.dumps({
                        "version": "1.0",
                        "id": frame_id,
                        "type": "AUTH_SUCCESS",
                        "timestamp": int(time.time() * 1000),
                        "payload": {
                            "session_id": str(session_id),
                            "user_id": str(user_id),
                            "device_id": str(device_id),
                            "server_time": int(time.time() * 1000),
                        },
                    }))
                    logger.info(f"[WS] Device {device_id} authenticated successfully.")
                except Exception as e:
                    logger.warning(f"[WS] Auth failed: {e}")
                    await websocket.send_text(json.dumps({
                        "type": "ERROR",
                        "code": 4001,
                        "message": f"Authentication failed: {str(e)}",
                    }))
                    await websocket.close(code=4001)
                    break
                continue

            if not authenticated or not current_user_id or not current_device_id:
                await websocket.send_text(json.dumps({
                    "type": "ERROR",
                    "code": 4001,
                    "message": "AUTH_INIT required before transmitting frames",
                }))
                await websocket.close(code=4001)
                break

            # 2. HEARTBEAT PING -> PONG
            if frame_type == "PING":
                await websocket.send_text(json.dumps({
                    "version": "1.0",
                    "id": frame_id,
                    "type": "PONG",
                    "timestamp": int(time.time() * 1000),
                    "payload": payload,
                }))

            # 3. REAL-TIME ENVELOPE TRANSMISSION
            elif frame_type == "ENVELOPE_SEND":
                conv_id_str = payload.get("conversation_id")
                envelopes_data = payload.get("envelopes", [])
                if not conv_id_str or not envelopes_data:
                    continue

                try:
                    conv_id = uuid.UUID(conv_id_str)
                    envelope_items = [
                        EnvelopeItem(
                            recipient_device_id=uuid.UUID(e["recipient_device_id"]),
                            envelope_type=e.get("envelope_type", "olm_msg"),
                            ciphertext=e["ciphertext"],
                            iv=e.get("iv"),
                            salt=e.get("salt"),
                            auth_tag=e.get("auth_tag"),
                        )
                        for e in envelopes_data
                    ]

                    async with async_session_factory() as db:
                        saved = await MessagingService.send_envelopes(
                            db,
                            current_user_id,
                            current_device_id,
                            EnvelopeBatchSendRequest(
                                conversation_id=conv_id,
                                envelopes=envelope_items,
                            ),
                        )
                        await db.commit()

                    # Real-time dispatch to connected recipient devices!
                    for s_env in saved:
                        rcpt_dev_id = s_env.recipient_device_id
                        receive_frame = {
                            "version": "1.0",
                            "id": f"f_{uuid.uuid4()}",
                            "type": "ENVELOPE_RECEIVE",
                            "timestamp": int(time.time() * 1000),
                            "payload": {
                                "envelope_id": str(s_env.id),
                                "conversation_id": str(s_env.conversation_id),
                                "sender_device_id": str(s_env.sender_device_id),
                                "sequence_id": s_env.sequence_id,
                                "envelope_type": s_env.envelope_type,
                                "ciphertext": s_env.ciphertext,
                                "iv": s_env.iv,
                                "auth_tag": s_env.auth_tag,
                                "created_at": s_env.created_at.isoformat(),
                            },
                        }
                        await manager.send_frame_to_device(rcpt_dev_id, receive_frame)

                    # Acknowledge to sender that envelopes are stored & routed
                    await websocket.send_text(json.dumps({
                        "version": "1.0",
                        "id": frame_id,
                        "type": "ENVELOPE_STATUS",
                        "timestamp": int(time.time() * 1000),
                        "payload": {
                            "conversation_id": conv_id_str,
                            "sent_count": len(saved),
                        },
                    }))
                except Exception as e:
                    logger.error(f"[WS] Error dispatching envelopes: {e}")
                    await websocket.send_text(json.dumps({
                        "type": "ERROR",
                        "code": 4009,
                        "message": str(e),
                    }))

            # 4. ENVELOPE ACKNOWLEDGMENT (Hard-delete from mailbox)
            elif frame_type == "ENVELOPE_ACK":
                env_ids_raw = payload.get("envelope_ids", [])
                if env_ids_raw:
                    try:
                        env_uuids = [uuid.UUID(i) for i in env_ids_raw]
                        async with async_session_factory() as db:
                            await MessagingService.acknowledge_envelopes(
                                db, current_device_id, env_uuids
                            )
                            await db.commit()
                    except Exception as e:
                        logger.warning(f"[WS] Error processing ACK: {e}")

            # 5. TYPING INDICATORS
            elif frame_type == "TYPING_EVENT":
                conv_id_str = payload.get("conversation_id")
                is_typing = payload.get("is_typing", True)
                if conv_id_str:
                    try:
                        conv_id = uuid.UUID(conv_id_str)
                        async with async_session_factory() as db:
                            m_res = await db.execute(
                                select(ConversationMember.user_id).where(
                                    ConversationMember.conversation_id == conv_id
                                )
                            )
                            member_user_ids = m_res.scalars().all()

                        typing_broadcast = {
                            "version": "1.0",
                            "type": "TYPING_EVENT",
                            "timestamp": int(time.time() * 1000),
                            "payload": {
                                "conversation_id": conv_id_str,
                                "user_id": str(current_user_id),
                                "is_typing": is_typing,
                            },
                        }
                        for m_uid in member_user_ids:
                            if m_uid != current_user_id:
                                await manager.send_frame_to_user(m_uid, typing_broadcast)
                    except Exception as e:
                        logger.warning(f"[WS] Typing event error: {e}")

            # 6. WEBRTC CALL SIGNALING (offer, answer, ice_candidate, ringing, reject, hangup)
            elif frame_type == "CALL_SIGNAL":
                action = payload.get("action")
                target_user_id_str = payload.get("callee_id") or payload.get("target_user_id")
                if not target_user_id_str and "caller_id" in payload:
                    target_user_id_str = payload.get("caller_id")

                logger.info(f"[WS] Routing WebRTC signal '{action}' from User {current_user_id} to User {target_user_id_str}")
                if target_user_id_str:
                    try:
                        target_uid = uuid.UUID(target_user_id_str)
                        signal_frame = {
                            "version": "1.0",
                            "id": frame_id,
                            "type": "CALL_SIGNAL",
                            "timestamp": int(time.time() * 1000),
                            "payload": {
                                **payload,
                                "from_user_id": str(current_user_id),
                                "from_device_id": str(current_device_id),
                            },
                        }
                        delivered = await manager.send_frame_to_user(target_uid, signal_frame)
                        if delivered == 0:
                            # User is offline
                            await websocket.send_text(json.dumps({
                                "version": "1.0",
                                "type": "CALL_SIGNAL",
                                "payload": {
                                    "action": "offline",
                                    "call_id": payload.get("call_id"),
                                    "message": "User is currently offline",
                                },
                            }))
                    except Exception as e:
                        logger.warning(f"[WS] Call signaling routing error: {e}")

    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.warning(f"[WS] Socket exception: {e}")
    finally:
        manager.disconnect(websocket)
