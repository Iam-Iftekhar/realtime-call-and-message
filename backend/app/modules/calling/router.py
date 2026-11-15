import uuid
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.auth.dependencies import AuthContext, get_auth_context
from app.modules.calling.schemas import (
    CallInitiateRequest,
    CallResponse,
    IceServersResponse,
)
from app.modules.calling.services import CallingService

router = APIRouter(prefix="/calling", tags=["Calling & WebRTC"])


@router.get("/ice-servers", response_model=IceServersResponse)
async def get_ice_servers(
    auth: AuthContext = Depends(get_auth_context),
):
    return CallingService.get_ice_servers(auth.user.id)


@router.post("/initiate", response_model=CallResponse, status_code=status.HTTP_201_CREATED)
async def initiate_call(
    req: CallInitiateRequest,
    auth: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db),
):
    call = await CallingService.initiate_call(db, auth.user.id, auth.device.id, req)
    return CallResponse.model_validate(call)


@router.post("/{call_id}/end", response_model=CallResponse)
async def end_call(
    call_id: uuid.UUID,
    auth: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db),
):
    call = await CallingService.end_call(db, auth.user.id, call_id)
    return CallResponse.model_validate(call)


@router.get("/{call_id}", response_model=CallResponse)
async def get_call(
    call_id: uuid.UUID,
    auth: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db),
):
    call = await CallingService.get_call(db, call_id)
    return CallResponse.model_validate(call)
