import uuid
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.auth.dependencies import AuthContext, get_auth_context
from app.modules.encryption.schemas import (
    PrekeyBatchRequest,
    PrekeyBatchResponse,
    PrekeyUploadRequest,
    PrekeyUploadResponse,
    UserDevicesResponse,
)
from app.modules.encryption.services import PrekeyService

router = APIRouter(prefix="/crypto/prekeys", tags=["Cryptographic Prekeys"])


@router.post("/upload", response_model=PrekeyUploadResponse, status_code=status.HTTP_200_OK)
async def upload_prekeys(
    req: PrekeyUploadRequest,
    auth: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db),
):
    return await PrekeyService.upload_prekeys(db, auth.user.id, req)


@router.get("/{user_id}/devices", response_model=UserDevicesResponse)
async def get_user_devices(
    user_id: uuid.UUID,
    auth: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db),
):
    return await PrekeyService.get_user_devices(db, user_id)


@router.post("/bundle", response_model=PrekeyBatchResponse)
async def fetch_prekey_bundles(
    req: PrekeyBatchRequest,
    auth: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db),
):
    bundles = await PrekeyService.fetch_prekey_bundles(db, req.device_ids)
    return PrekeyBatchResponse(bundles=bundles)
