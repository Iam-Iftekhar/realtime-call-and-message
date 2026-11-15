import uuid
from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.auth.dependencies import AuthContext, get_auth_context
from app.modules.devices.schemas import (
    DeviceDetailResponse,
    DeviceRegisterRequest,
    DeviceUpdateRequest,
)
from app.modules.devices.services import DeviceService

router = APIRouter(prefix="/devices", tags=["Devices"])


@router.get("", response_model=List[DeviceDetailResponse])
async def list_devices(
    auth: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db),
):
    devices = await DeviceService.list_user_devices(db, auth.user.id)
    return [DeviceDetailResponse.model_validate(d) for d in devices]


@router.post("/register", response_model=DeviceDetailResponse, status_code=status.HTTP_201_CREATED)
async def register_device(
    req: DeviceRegisterRequest,
    auth: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db),
):
    device = await DeviceService.register_device(db, auth.user.id, req)
    return DeviceDetailResponse.model_validate(device)


@router.get("/{device_id}", response_model=DeviceDetailResponse)
async def get_device(
    device_id: uuid.UUID,
    auth: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db),
):
    device = await DeviceService.get_device(db, auth.user.id, device_id)
    return DeviceDetailResponse.model_validate(device)


@router.patch("/{device_id}", response_model=DeviceDetailResponse)
async def update_device(
    device_id: uuid.UUID,
    req: DeviceUpdateRequest,
    auth: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db),
):
    device = await DeviceService.update_device(db, auth.user.id, device_id, req)
    return DeviceDetailResponse.model_validate(device)


@router.delete("/{device_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_device(
    device_id: uuid.UUID,
    auth: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db),
):
    await DeviceService.revoke_device(db, auth.user.id, device_id)
