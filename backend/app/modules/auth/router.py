import uuid
from typing import List
from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.auth.dependencies import AuthContext, get_auth_context
from app.modules.auth.schemas import (
    DeviceResponse,
    InviteCreateRequest,
    InviteResponse,
    LoginRequest,
    LoginResponse,
    RefreshTokenRequest,
    RegisterRequest,
    RegisterResponse,
    SessionResponse,
    TokenResponse,
    UserResponse,
)
from app.modules.auth.services import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
async def register(
    req: RegisterRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent")
    user, device, tokens = await AuthService.register(db, req, ip_address=ip, user_agent=ua)
    return RegisterResponse(
        user=UserResponse.model_validate(user),
        device=DeviceResponse.model_validate(device),
        tokens=tokens,
    )


@router.post("/login", response_model=LoginResponse)
async def login(
    req: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent")
    user, device, tokens = await AuthService.login(db, req, ip_address=ip, user_agent=ua)
    return LoginResponse(
        user=UserResponse.model_validate(user),
        device=DeviceResponse.model_validate(device),
        tokens=tokens,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    req: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
):
    return await AuthService.refresh_tokens(db, req.refresh_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    auth: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db),
):
    await AuthService.logout(db, auth.session_id)


@router.get("/sessions", response_model=List[SessionResponse])
async def list_sessions(
    auth: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db),
):
    sessions = await AuthService.list_sessions(db, auth.user.id)
    return [
        SessionResponse(
            id=s.id,
            device_id=s.device_id,
            device_name=s.device.device_name if s.device else None,
            user_agent=s.user_agent,
            ip_address=s.ip_address,
            expires_at=s.expires_at,
            created_at=s.created_at,
        )
        for s in sessions
    ]


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_session(
    session_id: uuid.UUID,
    auth: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db),
):
    await AuthService.revoke_session(db, auth.user.id, session_id)


@router.post("/invites", response_model=InviteResponse, status_code=status.HTTP_201_CREATED)
async def create_invite(
    req: InviteCreateRequest,
    auth: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db),
):
    invite = await AuthService.create_invite(db, auth.user.id, req)
    return InviteResponse.model_validate(invite)
