import uuid
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Tuple
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.exceptions import AuthenticationError, ConflictError, NotFoundError, PermissionDeniedError
from app.core.security import (
    create_access_token,
    decode_access_token,
    generate_secure_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.modules.auth.models import Invite, Session, User
from app.modules.auth.schemas import (
    DeviceRegisterInfo,
    InviteCreateRequest,
    LoginRequest,
    RegisterRequest,
    TokenResponse,
)
from app.modules.devices.models import Device


def _ensure_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


class AuthService:
    @staticmethod
    async def register(
        db: AsyncSession,
        req: RegisterRequest,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Tuple[User, Device, TokenResponse]:
        # 1. Verify username uniqueness
        result = await db.execute(select(User).where(User.username == req.username))
        if result.scalar_one_or_none():
            raise ConflictError(detail=f"Username '{req.username}' is already taken", code="AUTH_USERNAME_TAKEN")

        # 2. Check and consume invite code if required
        invite_record: Optional[Invite] = None
        if settings.INVITE_REQUIRED:
            if not req.invite_code:
                raise PermissionDeniedError(detail="Invite code is required for registration", code="AUTH_INVITE_REQUIRED")
            inv_res = await db.execute(select(Invite).where(Invite.code == req.invite_code))
            invite_record = inv_res.scalar_one_or_none()
            now = datetime.now(timezone.utc)
            if not invite_record or _ensure_utc(invite_record.expires_at) < now or invite_record.uses_count >= invite_record.max_uses:
                raise PermissionDeniedError(detail="Invite code is invalid or has expired", code="AUTH_INVITE_INVALID")
            invite_record.uses_count += 1

        # 3. Hash password using Argon2id
        pwd_hash = hash_password(req.password)

        # 4. Create User
        new_user = User(
            id=uuid.uuid4(),
            username=req.username,
            password_hash=pwd_hash,
            display_name=req.display_name,
            status="active",
            invite_code_id=invite_record.id if invite_record else None,
        )
        db.add(new_user)
        await db.flush()

        if invite_record and not invite_record.used_by_id:
            invite_record.used_by_id = new_user.id

        # 5. Create Device
        new_device = Device(
            id=uuid.uuid4(),
            user_id=new_user.id,
            device_identifier=req.initial_device.device_identifier,
            device_name=req.initial_device.device_name,
            client_platform=req.initial_device.client_platform,
            client_version=req.initial_device.client_version,
            is_active=True,
        )
        db.add(new_device)
        await db.flush()

        # 6. Create Session with Refresh Token
        refresh_raw = generate_secure_token(48)
        refresh_hash = hash_token(refresh_raw)
        session_expiry = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

        new_session = Session(
            id=uuid.uuid4(),
            user_id=new_user.id,
            device_id=new_device.id,
            refresh_token_hash=refresh_hash,
            user_agent=user_agent,
            ip_address=ip_address,
            expires_at=session_expiry,
        )
        db.add(new_session)
        await db.flush()

        # 7. Issue Access Token
        access_jwt = create_access_token(
            subject=str(new_user.id),
            device_id=str(new_device.id),
            session_id=str(new_session.id),
        )

        tokens = TokenResponse(
            access_token=access_jwt,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            refresh_token=refresh_raw,
        )

        return new_user, new_device, tokens

    @staticmethod
    async def login(
        db: AsyncSession,
        req: LoginRequest,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Tuple[User, Device, TokenResponse]:
        # 1. Fetch user
        result = await db.execute(select(User).where(User.username == req.username))
        user = result.scalar_one_or_none()
        if not user or not verify_password(req.password, user.password_hash):
            raise AuthenticationError(detail="Invalid username or password", code="AUTH_INVALID_CREDENTIALS")

        if user.status != "active":
            raise PermissionDeniedError(detail="Account is suspended or deactivated", code="AUTH_ACCOUNT_SUSPENDED")

        # 2. Find or register device
        dev_res = await db.execute(
            select(Device).where(
                Device.user_id == user.id,
                Device.device_identifier == req.device.device_identifier,
            )
        )
        device = dev_res.scalar_one_or_none()
        if not device:
            device = Device(
                id=uuid.uuid4(),
                user_id=user.id,
                device_identifier=req.device.device_identifier,
                device_name=req.device.device_name,
                client_platform=req.device.client_platform,
                client_version=req.device.client_version,
                is_active=True,
            )
            db.add(device)
            await db.flush()
        else:
            device.is_active = True
            device.last_seen_at = datetime.now(timezone.utc)
            device.device_name = req.device.device_name
            device.client_version = req.device.client_version

        # 3. Create Session
        refresh_raw = generate_secure_token(48)
        refresh_hash = hash_token(refresh_raw)
        session_expiry = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

        new_session = Session(
            id=uuid.uuid4(),
            user_id=user.id,
            device_id=device.id,
            refresh_token_hash=refresh_hash,
            user_agent=user_agent,
            ip_address=ip_address,
            expires_at=session_expiry,
        )
        db.add(new_session)
        await db.flush()

        access_jwt = create_access_token(
            subject=str(user.id),
            device_id=str(device.id),
            session_id=str(new_session.id),
        )

        tokens = TokenResponse(
            access_token=access_jwt,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            refresh_token=refresh_raw,
        )

        return user, device, tokens

    @staticmethod
    async def refresh_tokens(db: AsyncSession, refresh_token: str) -> TokenResponse:
        rf_hash = hash_token(refresh_token)
        result = await db.execute(
            select(Session).options(selectinload(Session.device)).where(Session.refresh_token_hash == rf_hash)
        )
        session = result.scalar_one_or_none()
        now = datetime.now(timezone.utc)

        if not session:
            # Check if this token was a previously consumed token (reuse detection!)
            prev_result = await db.execute(
                select(Session).where(Session.previous_refresh_token_hash == rf_hash)
            )
            compromised_session = prev_result.scalar_one_or_none()
            if compromised_session:
                # Revoke all sessions for this user family
                await db.execute(
                    update(Session)
                    .where(Session.user_id == compromised_session.user_id)
                    .values(revoked_at=now)
                )
                await db.flush()
                raise AuthenticationError(
                    detail="Compromised refresh token reuse detected. All sessions revoked.",
                    code="AUTH_TOKEN_COMPROMISED",
                )
            raise AuthenticationError(detail="Invalid refresh token", code="AUTH_TOKEN_INVALID")

        # Check if session is already revoked
        if session.revoked_at is not None:
            await db.execute(
                update(Session)
                .where(Session.user_id == session.user_id)
                .values(revoked_at=now)
            )
            await db.flush()
            raise AuthenticationError(
                detail="Compromised refresh token reuse detected. All sessions revoked.",
                code="AUTH_TOKEN_COMPROMISED",
            )

        if _ensure_utc(session.expires_at) < now:
            raise AuthenticationError(detail="Refresh token has expired", code="AUTH_TOKEN_EXPIRED")

        # Rotate Refresh Token
        new_refresh_raw = generate_secure_token(48)
        session.previous_refresh_token_hash = session.refresh_token_hash
        session.refresh_token_hash = hash_token(new_refresh_raw)
        session.expires_at = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        await db.flush()

        access_jwt = create_access_token(
            subject=str(session.user_id),
            device_id=str(session.device_id),
            session_id=str(session.id),
        )

        return TokenResponse(
            access_token=access_jwt,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            refresh_token=new_refresh_raw,
        )

    @staticmethod
    async def logout(db: AsyncSession, session_id: uuid.UUID) -> None:
        await db.execute(
            update(Session)
            .where(Session.id == session_id)
            .values(revoked_at=datetime.now(timezone.utc))
        )
        await db.flush()

    @staticmethod
    async def list_sessions(db: AsyncSession, user_id: uuid.UUID) -> List[Session]:
        now = datetime.now(timezone.utc)
        result = await db.execute(
            select(Session)
            .options(selectinload(Session.device))
            .where(Session.user_id == user_id, Session.revoked_at.is_(None), Session.expires_at > now)
            .order_by(Session.created_at.desc())
        )
        return list(result.scalars().all())

    @staticmethod
    async def revoke_session(db: AsyncSession, user_id: uuid.UUID, session_id: uuid.UUID) -> None:
        result = await db.execute(
            select(Session).where(Session.id == session_id, Session.user_id == user_id)
        )
        session = result.scalar_one_or_none()
        if not session:
            raise NotFoundError(detail="Session not found", code="SESSION_NOT_FOUND")
        session.revoked_at = datetime.now(timezone.utc)
        await db.flush()

    @staticmethod
    async def create_invite(db: AsyncSession, creator_id: uuid.UUID, req: InviteCreateRequest) -> Invite:
        code = req.code or f"SPECTRA-{generate_secure_token(8).upper()}"
        expires_at = datetime.now(timezone.utc) + timedelta(days=req.valid_days)

        invite = Invite(
            id=uuid.uuid4(),
            code=code,
            creator_id=creator_id,
            max_uses=req.max_uses,
            uses_count=0,
            expires_at=expires_at,
        )
        db.add(invite)
        await db.flush()
        return invite
