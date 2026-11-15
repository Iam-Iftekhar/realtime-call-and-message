import uuid
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, PermissionDeniedError
from app.core.security import generate_coturn_credentials
from app.modules.calling.models import Call, CallParticipant
from app.modules.calling.schemas import CallInitiateRequest, IceServersResponse


class CallingService:
    @staticmethod
    def get_ice_servers(user_id: uuid.UUID) -> IceServersResponse:
        cred_dict = generate_coturn_credentials(str(user_id))
        return IceServersResponse.model_validate(cred_dict)

    @staticmethod
    async def initiate_call(
        db: AsyncSession, caller_id: uuid.UUID, caller_device_id: uuid.UUID, req: CallInitiateRequest
    ) -> Call:
        call = Call(
            id=uuid.uuid4(),
            conversation_id=req.conversation_id,
            initiator_id=caller_id,
            call_type=req.call_type,
            status="ringing",
        )
        db.add(call)
        await db.flush()

        # Add caller participant
        caller_part = CallParticipant(
            id=uuid.uuid4(),
            call_id=call.id,
            user_id=caller_id,
            device_id=caller_device_id,
            status="accepted",
            joined_at=datetime.now(timezone.utc),
        )
        # Add callee participant
        callee_part = CallParticipant(
            id=uuid.uuid4(),
            call_id=call.id,
            user_id=req.callee_id,
            device_id=None,
            status="invited",
        )
        db.add(caller_part)
        db.add(callee_part)
        await db.flush()

        return call

    @staticmethod
    async def end_call(db: AsyncSession, user_id: uuid.UUID, call_id: uuid.UUID) -> Call:
        res = await db.execute(select(Call).where(Call.id == call_id))
        call = res.scalar_one_or_none()
        if not call:
            raise NotFoundError(detail="Call session not found", code="CALL_NOT_FOUND")

        call.status = "ended"
        call.ended_at = datetime.now(timezone.utc)
        await db.flush()
        return call

    @staticmethod
    async def get_call(db: AsyncSession, call_id: uuid.UUID) -> Call:
        res = await db.execute(select(Call).where(Call.id == call_id))
        call = res.scalar_one_or_none()
        if not call:
            raise NotFoundError(detail="Call session not found", code="CALL_NOT_FOUND")
        return call
