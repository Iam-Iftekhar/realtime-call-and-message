import uuid
from dataclasses import dataclass
from fastapi import Depends, Header
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import AuthenticationError, PermissionDeniedError
from app.core.security import decode_access_token
from app.modules.auth.models import Session, User
from app.modules.devices.models import Device


@dataclass
class AuthContext:
    user: User
    device: Device
    session_id: uuid.UUID


async def get_auth_context(
    authorization: str | None = Header(None, alias="Authorization"),
    db: AsyncSession = Depends(get_db),
) -> AuthContext:
    if not authorization:
        raise AuthenticationError(detail="Missing Authorization header", code="AUTH_HEADER_MISSING")

    parts = authorization.split(" ")
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise AuthenticationError(detail="Invalid Authorization header format. Expected 'Bearer <token>'", code="AUTH_HEADER_MALFORMED")

    token = parts[1]
    payload = decode_access_token(token)

    try:
        user_id = uuid.UUID(payload["sub"])
        device_id = uuid.UUID(payload["dev"])
        session_id = uuid.UUID(payload["sid"])
    except (KeyError, ValueError):
        raise AuthenticationError(detail="Invalid JWT claims structure", code="AUTH_CLAIMS_INVALID")

    # Verify session is still active and not revoked
    sess_res = await db.execute(
        select(Session).where(
            Session.id == session_id,
            Session.user_id == user_id,
            Session.device_id == device_id,
            Session.revoked_at.is_(None),
        )
    )
    session = sess_res.scalar_one_or_none()
    if not session:
        raise AuthenticationError(detail="Session has been revoked or expired", code="AUTH_SESSION_REVOKED")

    # Load User
    user_res = await db.execute(select(User).where(User.id == user_id))
    user = user_res.scalar_one_or_none()
    if not user or user.status != "active":
        raise PermissionDeniedError(detail="User account inactive or not found", code="AUTH_USER_INACTIVE")

    # Load Device
    dev_res = await db.execute(select(Device).where(Device.id == device_id, Device.user_id == user_id))
    device = dev_res.scalar_one_or_none()
    if not device or not device.is_active:
        raise PermissionDeniedError(detail="Device has been revoked or is inactive", code="AUTH_DEVICE_REVOKED")

    return AuthContext(user=user, device=device, session_id=session_id)
