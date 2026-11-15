import uuid
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class ConversationCreateRequest(BaseModel):
    type: str = Field(default="direct", pattern=r"^(direct|group)$")
    title: Optional[str] = Field(None, max_length=128)
    participant_user_ids: List[uuid.UUID] = Field(..., min_length=1)


class ConversationResponse(BaseModel):
    id: uuid.UUID
    type: str
    title: Optional[str] = None
    avatar_hash: Optional[str] = None
    last_sequence_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EnvelopeItem(BaseModel):
    recipient_device_id: uuid.UUID
    envelope_type: str = Field(default="olm_msg", max_length=24)
    ciphertext: str = Field(..., min_length=1)  # Base64 encrypted payload
    iv: Optional[str] = None
    salt: Optional[str] = None
    auth_tag: Optional[str] = None


class EnvelopeBatchSendRequest(BaseModel):
    conversation_id: uuid.UUID
    envelopes: List[EnvelopeItem] = Field(..., min_length=1, max_length=100)


class EnvelopeDetailResponse(BaseModel):
    id: uuid.UUID
    conversation_id: uuid.UUID
    sender_device_id: uuid.UUID
    recipient_device_id: uuid.UUID
    sequence_id: int
    envelope_type: str
    ciphertext: str
    iv: Optional[str] = None
    auth_tag: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EnvelopeSyncResponse(BaseModel):
    envelopes: List[EnvelopeDetailResponse]
    has_more: bool = False


class EnvelopeAckRequest(BaseModel):
    envelope_ids: List[uuid.UUID] = Field(..., min_length=1, max_length=500)


class EnvelopeAckResponse(BaseModel):
    acknowledged_count: int
