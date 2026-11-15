import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class DeviceRegisterRequest(BaseModel):
    device_identifier: str = Field(..., min_length=4, max_length=64)
    device_name: str = Field(..., min_length=1, max_length=64)
    client_platform: str = Field(default="web", max_length=32)
    client_version: str = Field(default="1.0.0", max_length=32)


class DeviceUpdateRequest(BaseModel):
    device_name: Optional[str] = Field(None, min_length=1, max_length=64)
    client_version: Optional[str] = Field(None, max_length=32)


class DeviceDetailResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    device_identifier: str
    device_name: str
    client_platform: str
    client_version: str
    is_active: bool
    last_seen_at: datetime
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
