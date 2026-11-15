import uuid
from typing import List
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.auth.dependencies import AuthContext, get_auth_context
from app.modules.messaging.schemas import (
    ConversationCreateRequest,
    ConversationResponse,
    EnvelopeAckRequest,
    EnvelopeAckResponse,
    EnvelopeBatchSendRequest,
    EnvelopeDetailResponse,
    EnvelopeSyncResponse,
)
from app.modules.messaging.services import MessagingService

router = APIRouter(prefix="", tags=["Messaging & Conversations"])


@router.post("/conversations", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    req: ConversationCreateRequest,
    auth: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db),
):
    conv = await MessagingService.create_conversation(db, auth.user.id, req)
    return ConversationResponse.model_validate(conv)


@router.get("/conversations", response_model=List[ConversationResponse])
async def list_conversations(
    auth: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db),
):
    convs = await MessagingService.list_user_conversations(db, auth.user.id)
    return [ConversationResponse.model_validate(c) for c in convs]


@router.post("/messages/send-batch", response_model=List[EnvelopeDetailResponse])
async def send_envelopes(
    req: EnvelopeBatchSendRequest,
    auth: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db),
):
    return await MessagingService.send_envelopes(db, auth.user.id, auth.device.id, req)


@router.get("/messages/sync", response_model=EnvelopeSyncResponse)
async def sync_envelopes(
    last_seq: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    auth: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db),
):
    envelopes = await MessagingService.sync_envelopes(
        db, auth.device.id, last_synced_seq=last_seq, limit=limit
    )
    return EnvelopeSyncResponse(envelopes=envelopes, has_more=len(envelopes) == limit)


@router.post("/messages/ack", response_model=EnvelopeAckResponse)
async def acknowledge_envelopes(
    req: EnvelopeAckRequest,
    auth: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db),
):
    count = await MessagingService.acknowledge_envelopes(db, auth.device.id, req.envelope_ids)
    return EnvelopeAckResponse(acknowledged_count=count)
