import uuid
from datetime import datetime
from typing import List, Optional, Union
from pydantic import BaseModel, ConfigDict, Field


class IceServerConfig(BaseModel):
    urls: Union[str, List[str]]
    username: Optional[str] = None
    credential: Optional[str] = None


class IceServersResponse(BaseModel):
    ice_servers: List[IceServerConfig]
    ttl: int
    expires_at: int


class CallInitiateRequest(BaseModel):
    conversation_id: uuid.UUID
    callee_id: uuid.UUID
    call_type: str = Field(default="audio", pattern=r"^(audio|video)$")


class CallResponse(BaseModel):
    id: uuid.UUID
    conversation_id: uuid.UUID
    initiator_id: uuid.UUID
    call_type: str
    status: str
    started_at: datetime
    ended_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
