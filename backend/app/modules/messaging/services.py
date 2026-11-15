import uuid
from datetime import datetime, timezone
from typing import List, Tuple
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, PermissionDeniedError
from app.modules.messaging.models import Conversation, ConversationMember, MessageEnvelope
from app.modules.messaging.schemas import (
    ConversationCreateRequest,
    EnvelopeBatchSendRequest,
    EnvelopeDetailResponse,
)


class MessagingService:
    @staticmethod
    async def create_conversation(
        db: AsyncSession, creator_id: uuid.UUID, req: ConversationCreateRequest
    ) -> Conversation:
        conv = Conversation(
            id=uuid.uuid4(),
            type=req.type,
            title=req.title if req.type == "group" else None,
            created_by_id=creator_id,
            last_sequence_id=0,
        )
        db.add(conv)
        await db.flush()

        # Add creator as owner/member
        creator_member = ConversationMember(
            id=uuid.uuid4(),
            conversation_id=conv.id,
            user_id=creator_id,
            role="owner" if req.type == "group" else "member",
        )
        db.add(creator_member)

        # Add other participants
        for uid in set(req.participant_user_ids):
            if uid != creator_id:
                member = ConversationMember(
                    id=uuid.uuid4(),
                    conversation_id=conv.id,
                    user_id=uid,
                    role="member",
                )
                db.add(member)

        await db.flush()
        return conv

    @staticmethod
    async def list_user_conversations(db: AsyncSession, user_id: uuid.UUID) -> List[Conversation]:
        res = await db.execute(
            select(Conversation)
            .join(ConversationMember, ConversationMember.conversation_id == Conversation.id)
            .where(ConversationMember.user_id == user_id)
            .order_by(Conversation.updated_at.desc())
        )
        return list(res.scalars().all())

    @staticmethod
    async def send_envelopes(
        db: AsyncSession,
        sender_user_id: uuid.UUID,
        sender_device_id: uuid.UUID,
        req: EnvelopeBatchSendRequest,
    ) -> List[EnvelopeDetailResponse]:
        # 1. Verify sender is a member of the conversation
        mem_res = await db.execute(
            select(ConversationMember).where(
                ConversationMember.conversation_id == req.conversation_id,
                ConversationMember.user_id == sender_user_id,
            )
        )
        if not mem_res.scalar_one_or_none():
            raise PermissionDeniedError(
                detail="You are not a member of this conversation", code="CONV_NOT_MEMBER"
            )

        # 2. Advance conversation sequence
        conv_res = await db.execute(
            select(Conversation).where(Conversation.id == req.conversation_id)
        )
        conv = conv_res.scalar_one_or_none()
        if not conv:
            raise NotFoundError(detail="Conversation not found", code="CONV_NOT_FOUND")

        created_envelopes: List[EnvelopeDetailResponse] = []

        for env_item in req.envelopes:
            conv.last_sequence_id += 1
            seq = conv.last_sequence_id

            env = MessageEnvelope(
                id=uuid.uuid4(),
                conversation_id=req.conversation_id,
                sender_device_id=sender_device_id,
                recipient_device_id=env_item.recipient_device_id,
                sequence_id=seq,
                envelope_type=env_item.envelope_type,
                ciphertext=env_item.ciphertext,
                iv=env_item.iv,
                salt=env_item.salt,
                auth_tag=env_item.auth_tag,
                is_delivered=False,
            )
            db.add(env)
            created_envelopes.append(
                EnvelopeDetailResponse(
                    id=env.id,
                    conversation_id=env.conversation_id,
                    sender_device_id=env.sender_device_id,
                    recipient_device_id=env.recipient_device_id,
                    sequence_id=env.sequence_id,
                    envelope_type=env.envelope_type,
                    ciphertext=env.ciphertext,
                    iv=env.iv,
                    auth_tag=env.auth_tag,
                    created_at=datetime.now(timezone.utc),
                )
            )

        conv.updated_at = datetime.now(timezone.utc)
        await db.flush()
        return created_envelopes

    @staticmethod
    async def sync_envelopes(
        db: AsyncSession, recipient_device_id: uuid.UUID, last_synced_seq: int = 0, limit: int = 100
    ) -> List[EnvelopeDetailResponse]:
        res = await db.execute(
            select(MessageEnvelope)
            .where(
                MessageEnvelope.recipient_device_id == recipient_device_id,
                MessageEnvelope.sequence_id > last_synced_seq,
                MessageEnvelope.is_delivered.is_(False),
            )
            .order_by(MessageEnvelope.sequence_id.asc())
            .limit(limit)
        )
        envelopes = res.scalars().all()
        return [
            EnvelopeDetailResponse(
                id=e.id,
                conversation_id=e.conversation_id,
                sender_device_id=e.sender_device_id,
                recipient_device_id=e.recipient_device_id,
                sequence_id=e.sequence_id,
                envelope_type=e.envelope_type,
                ciphertext=e.ciphertext,
                iv=e.iv,
                auth_tag=e.auth_tag,
                created_at=e.created_at,
            )
            for e in envelopes
        ]

    @staticmethod
    async def acknowledge_envelopes(
        db: AsyncSession, recipient_device_id: uuid.UUID, envelope_ids: List[uuid.UUID]
    ) -> int:
        """Immediate hard-deletion upon ACK to enforce Untrusted Mailbox Zero-Knowledge invariant."""
        res = await db.execute(
            delete(MessageEnvelope).where(
                MessageEnvelope.id.in_(envelope_ids),
                MessageEnvelope.recipient_device_id == recipient_device_id,
            )
        )
        await db.flush()
        return res.rowcount
