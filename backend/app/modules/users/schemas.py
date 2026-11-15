import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class UserProfileResponse(BaseModel):
    id: uuid.UUID
    username: str
    display_name: str
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserProfileUpdateRequest(BaseModel):
    display_name: Optional[str] = Field(None, min_length=1, max_length=64)


class UserSearchResult(BaseModel):
    id: uuid.UUID
    username: str
    display_name: str

    model_config = ConfigDict(from_attributes=True)
