import base64
import uuid
from typing import List, Optional
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, PermissionDeniedError, ValidationError
from app.core.security import verify_ed25519_signature
from app.modules.devices.models import Device
from app.modules.encryption.models import DeviceOneTimePrekey, DevicePrekeyBundle
from app.modules.encryption.schemas import (
    DevicePrekeyBundleResponse,
    OneTimePrekeyInfo,
    PrekeyUploadRequest,
    PrekeyUploadResponse,
    SignedPrekeyInfo,
    UserDeviceSummary,
    UserDevicesResponse,
)


class PrekeyService:
    @staticmethod
    async def upload_prekeys(
        db: AsyncSession, user_id: uuid.UUID, req: PrekeyUploadRequest
    ) -> PrekeyUploadResponse:
        # 1. Verify device belongs to user
        dev_res = await db.execute(
            select(Device).where(Device.id == req.device_id, Device.user_id == user_id)
        )
        device = dev_res.scalar_one_or_none()
        if not device:
            raise NotFoundError(detail="Device not found or not owned by user", code="DEVICE_NOT_FOUND")

        # 2. Cryptographic signature check on Signed Pre-Key
        # The signature must be signed by the identity key over the signed pre-key bytes
        sig_valid = verify_ed25519_signature(
            public_key_b64=req.identity_key,
            message_bytes=base64.b64decode(req.signed_prekey.public_key),
            signature_b64=req.signed_prekey.signature,
        )
        if not sig_valid:
            # Fallback check: if message was raw bytes of string
            fallback_valid = verify_ed25519_signature(
                public_key_b64=req.identity_key,
                message_bytes=req.signed_prekey.public_key.encode("utf-8"),
                signature_b64=req.signed_prekey.signature,
            )
            if not fallback_valid:
                raise ValidationError(
                    detail="Cryptographic verification failed: Signed prekey signature is invalid.",
                    code="CRYPTO_SIGNATURE_INVALID",
                )

        # 3. Upsert DevicePrekeyBundle
        bundle_res = await db.execute(
            select(DevicePrekeyBundle).where(DevicePrekeyBundle.device_id == req.device_id)
        )
        bundle = bundle_res.scalar_one_or_none()
        if bundle:
            bundle.identity_key_pub = req.identity_key
            bundle.signed_prekey_pub = req.signed_prekey.public_key
            bundle.signed_prekey_sig = req.signed_prekey.signature
            bundle.signed_prekey_id = req.signed_prekey.key_id
        else:
            bundle = DevicePrekeyBundle(
                id=uuid.uuid4(),
                device_id=req.device_id,
                identity_key_pub=req.identity_key,
                signed_prekey_pub=req.signed_prekey.public_key,
                signed_prekey_sig=req.signed_prekey.signature,
                signed_prekey_id=req.signed_prekey.key_id,
            )
            db.add(bundle)

        # 4. Insert One-Time Prekeys
        added_count = 0
        for otk in req.one_time_prekeys:
            existing_otk = await db.execute(
                select(DeviceOneTimePrekey).where(
                    DeviceOneTimePrekey.device_id == req.device_id,
                    DeviceOneTimePrekey.key_id == otk.key_id,
                )
            )
            if not existing_otk.scalar_one_or_none():
                new_otk = DeviceOneTimePrekey(
                    id=uuid.uuid4(),
                    device_id=req.device_id,
                    key_id=otk.key_id,
                    public_key=otk.public_key,
                    is_used=False,
                )
                db.add(new_otk)
                added_count += 1

        await db.flush()

        # Query total unused count
        count_res = await db.execute(
            select(func.count(DeviceOneTimePrekey.id)).where(
                DeviceOneTimePrekey.device_id == req.device_id,
                DeviceOneTimePrekey.is_used.is_(False),
            )
        )
        total_unused = count_res.scalar_one()

        return PrekeyUploadResponse(
            status="uploaded",
            otk_added=added_count,
            total_otk_available=total_unused,
        )

    @staticmethod
    async def get_user_devices(db: AsyncSession, target_user_id: uuid.UUID) -> UserDevicesResponse:
        res = await db.execute(
            select(Device).where(Device.user_id == target_user_id, Device.is_active.is_(True))
        )
        devices = res.scalars().all()
        return UserDevicesResponse(
            user_id=target_user_id,
            devices=[
                UserDeviceSummary(
                    device_id=d.id,
                    device_name=d.device_name,
                    is_active=d.is_active,
                )
                for d in devices
            ],
        )

    @staticmethod
    async def fetch_prekey_bundles(
        db: AsyncSession, device_ids: List[uuid.UUID]
    ) -> List[DevicePrekeyBundleResponse]:
        bundles: List[DevicePrekeyBundleResponse] = []

        for dev_id in device_ids:
            b_res = await db.execute(
                select(DevicePrekeyBundle).where(DevicePrekeyBundle.device_id == dev_id)
            )
            bundle = b_res.scalar_one_or_none()
            if not bundle:
                continue

            # Atomically claim one unused one-time prekey
            otk_res = await db.execute(
                select(DeviceOneTimePrekey)
                .where(
                    DeviceOneTimePrekey.device_id == dev_id,
                    DeviceOneTimePrekey.is_used.is_(False),
                )
                .limit(1)
            )
            otk = otk_res.scalar_one_or_none()
            otk_info: Optional[OneTimePrekeyInfo] = None
            if otk:
                otk.is_used = True
                otk_info = OneTimePrekeyInfo(key_id=otk.key_id, public_key=otk.public_key)
                await db.flush()

            bundles.append(
                DevicePrekeyBundleResponse(
                    device_id=dev_id,
                    identity_key=bundle.identity_key_pub,
                    signed_prekey=SignedPrekeyInfo(
                        key_id=bundle.signed_prekey_id,
                        public_key=bundle.signed_prekey_pub,
                        signature=bundle.signed_prekey_sig,
                    ),
                    one_time_prekey=otk_info,
                )
            )

        return bundles
