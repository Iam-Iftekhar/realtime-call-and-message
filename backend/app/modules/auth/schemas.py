import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class DeviceRegisterInfo(BaseModel):
    device_identifier: str = Field(..., min_length=4, max_length=64)
    device_name: str = Field(..., min_length=1, max_length=64)
    client_platform: str = Field(default="web", max_length=32)
    client_version: str = Field(default="1.0.0", max_length=32)


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=32, pattern=r"^[a-zA-Z0-9_-]+$")
    password: str = Field(..., min_length=10, max_length=128)
    display_name: str = Field(..., min_length=1, max_length=64)
    invite_code: Optional[str] = Field(default=None, max_length=32)
    initial_device: DeviceRegisterInfo


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=32)
    password: str = Field(..., min_length=1, max_length=128)
    device: DeviceRegisterInfo


class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(..., min_length=10)


class UserResponse(BaseModel):
    id: uuid.UUID
    username: str
    display_name: str
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DeviceResponse(BaseModel):
    id: uuid.UUID
    device_identifier: str
    device_name: str
    client_platform: str
    client_version: str
    is_active: bool
    last_seen_at: datetime
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "Bearer"
    expires_in: int
    refresh_token: str


class RegisterResponse(BaseModel):
    user: UserResponse
    device: DeviceResponse
    tokens: TokenResponse


class LoginResponse(BaseModel):
    user: UserResponse
    device: DeviceResponse
    tokens: TokenResponse


class SessionResponse(BaseModel):
    id: uuid.UUID
    device_id: uuid.UUID
    device_name: Optional[str] = None
    user_agent: Optional[str] = None
    ip_address: Optional[str] = None
    expires_at: datetime
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InviteCreateRequest(BaseModel):
    code: Optional[str] = Field(default=None, max_length=32)
    max_uses: int = Field(default=1, ge=1, le=100)
    valid_days: int = Field(default=7, ge=1, le=365)


class InviteResponse(BaseModel):
    id: uuid.UUID
    code: str
    creator_id: uuid.UUID
    max_uses: int
    uses_count: int
    expires_at: datetime
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
