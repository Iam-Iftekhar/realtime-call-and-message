import uuid
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class SignedPrekeyInfo(BaseModel):
    key_id: int = Field(..., ge=0)
    public_key: str = Field(..., min_length=40, max_length=128)
    signature: str = Field(..., min_length=60, max_length=256)


class OneTimePrekeyInfo(BaseModel):
    key_id: int = Field(..., ge=0)
    public_key: str = Field(..., min_length=40, max_length=128)


class PrekeyUploadRequest(BaseModel):
    device_id: uuid.UUID
    identity_key: str = Field(..., min_length=40, max_length=128)
    signed_prekey: SignedPrekeyInfo
    one_time_prekeys: List[OneTimePrekeyInfo] = Field(default_factory=list)


class PrekeyUploadResponse(BaseModel):
    status: str = "uploaded"
    otk_added: int
    total_otk_available: int


class DevicePrekeyBundleResponse(BaseModel):
    device_id: uuid.UUID
    identity_key: str
    signed_prekey: SignedPrekeyInfo
    one_time_prekey: Optional[OneTimePrekeyInfo] = None


class PrekeyBatchRequest(BaseModel):
    device_ids: List[uuid.UUID] = Field(..., min_length=1, max_length=50)


class PrekeyBatchResponse(BaseModel):
    bundles: List[DevicePrekeyBundleResponse]


class UserDeviceSummary(BaseModel):
    device_id: uuid.UUID
    device_name: str
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class UserDevicesResponse(BaseModel):
    user_id: uuid.UUID
    devices: List[UserDeviceSummary]
