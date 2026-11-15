import uuid
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.modules.auth.models import Session
from app.modules.devices.models import Device
from app.modules.devices.schemas import DeviceRegisterRequest, DeviceUpdateRequest


class DeviceService:
    @staticmethod
    async def list_user_devices(db: AsyncSession, user_id: uuid.UUID) -> List[Device]:
        result = await db.execute(
            select(Device)
            .where(Device.user_id == user_id, Device.is_active.is_(True))
            .order_by(Device.last_seen_at.desc())
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_device(db: AsyncSession, user_id: uuid.UUID, device_id: uuid.UUID) -> Device:
        result = await db.execute(
            select(Device).where(Device.id == device_id, Device.user_id == user_id)
        )
        device = result.scalar_one_or_none()
        if not device:
            raise NotFoundError(detail="Device not found", code="DEVICE_NOT_FOUND")
        return device

    @staticmethod
    async def register_device(
        db: AsyncSession, user_id: uuid.UUID, req: DeviceRegisterRequest
    ) -> Device:
        res = await db.execute(
            select(Device).where(
                Device.user_id == user_id,
                Device.device_identifier == req.device_identifier,
            )
        )
        device = res.scalar_one_or_none()
        if device:
            device.is_active = True
            device.device_name = req.device_name
            device.client_platform = req.client_platform
            device.client_version = req.client_version
            device.last_seen_at = datetime.now(timezone.utc)
        else:
            device = Device(
                id=uuid.uuid4(),
                user_id=user_id,
                device_identifier=req.device_identifier,
                device_name=req.device_name,
                client_platform=req.client_platform,
                client_version=req.client_version,
                is_active=True,
            )
            db.add(device)
        await db.flush()
        return device

    @staticmethod
    async def update_device(
        db: AsyncSession, user_id: uuid.UUID, device_id: uuid.UUID, req: DeviceUpdateRequest
    ) -> Device:
        device = await DeviceService.get_device(db, user_id, device_id)
        if req.device_name is not None:
            device.device_name = req.device_name
        if req.client_version is not None:
            device.client_version = req.client_version
        device.last_seen_at = datetime.now(timezone.utc)
        await db.flush()
        return device

    @staticmethod
    async def revoke_device(db: AsyncSession, user_id: uuid.UUID, device_id: uuid.UUID) -> None:
        device = await DeviceService.get_device(db, user_id, device_id)
        device.is_active = False

        # Invalidate all active sessions for this device
        await db.execute(
            update(Session)
            .where(Session.device_id == device_id, Session.user_id == user_id)
            .values(revoked_at=datetime.now(timezone.utc))
        )
        await db.flush()
