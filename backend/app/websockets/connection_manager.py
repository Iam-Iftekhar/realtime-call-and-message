import json
import logging
import uuid
from typing import Dict, List, Optional
from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self):
        # device_id -> WebSocket
        self.active_sockets: Dict[uuid.UUID, WebSocket] = {}
        # user_id -> set of device_ids
        self.user_devices: Dict[uuid.UUID, set[uuid.UUID]] = {}
        # socket -> (user_id, device_id)
        self.socket_info: Dict[WebSocket, tuple[uuid.UUID, uuid.UUID]] = {}

    async def connect(self, device_id: uuid.UUID, user_id: uuid.UUID, websocket: WebSocket):
        await websocket.accept()
        self.active_sockets[device_id] = websocket
        if user_id not in self.user_devices:
            self.user_devices[user_id] = set()
        self.user_devices[user_id].add(device_id)
        self.socket_info[websocket] = (user_id, device_id)
        logger.info(f"[WS] Device {device_id} (User {user_id}) connected.")

    def disconnect(self, websocket: WebSocket) -> Optional[tuple[uuid.UUID, uuid.UUID]]:
        info = self.socket_info.pop(websocket, None)
        if info:
            user_id, device_id = info
            self.active_sockets.pop(device_id, None)
            if user_id in self.user_devices:
                self.user_devices[user_id].discard(device_id)
                if not self.user_devices[user_id]:
                    del self.user_devices[user_id]
            logger.info(f"[WS] Device {device_id} (User {user_id}) disconnected.")
            return user_id, device_id
        return None

    def is_connected(self, device_id: uuid.UUID) -> bool:
        return device_id in self.active_sockets

    def get_user_active_devices(self, user_id: uuid.UUID) -> List[uuid.UUID]:
        return list(self.user_devices.get(user_id, set()))

    async def send_frame_to_device(self, device_id: uuid.UUID, frame: dict) -> bool:
        ws = self.active_sockets.get(device_id)
        if ws:
            try:
                await ws.send_text(json.dumps(frame))
                return True
            except Exception as e:
                logger.warning(f"[WS] Failed to send to device {device_id}: {e}")
                self.disconnect(ws)
        return False

    async def send_frame_to_user(self, user_id: uuid.UUID, frame: dict, exclude_device: Optional[uuid.UUID] = None) -> int:
        count = 0
        devices = self.get_user_active_devices(user_id)
        for dev_id in devices:
            if exclude_device and dev_id == exclude_device:
                continue
            if await self.send_frame_to_device(dev_id, frame):
                count += 1
        return count


manager = ConnectionManager()
