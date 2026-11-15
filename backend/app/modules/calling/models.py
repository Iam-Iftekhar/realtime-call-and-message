import uuid
from datetime import datetime, timezone
from sqlalchemy import DateTime, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, GUID


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Call(Base):
    __tablename__ = "calls"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        primary_key=True,
        default=uuid.uuid4,
    )
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False
    )
    initiator_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    call_type: Mapped[str] = mapped_column(String(16), default="audio", nullable=False)  # 'audio' or 'video'
    status: Mapped[str] = mapped_column(String(16), default="ringing", nullable=False)  # 'ringing', 'ongoing', 'ended', 'rejected'
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("idx_calls_conv", "conversation_id"),
        Index("idx_calls_initiator", "initiator_id"),
    )

    # Relationships
    participants: Mapped[list["CallParticipant"]] = relationship(
        "CallParticipant", back_populates="call", cascade="all, delete-orphan"
    )


class CallParticipant(Base):
    __tablename__ = "call_participants"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        primary_key=True,
        default=uuid.uuid4,
    )
    call_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("calls.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    device_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID, ForeignKey("devices.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(16), default="invited", nullable=False)  # 'invited', 'accepted', 'declined', 'left'
    joined_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    left_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint("call_id", "user_id", "device_id", name="uq_call_participant"),
        Index("idx_call_participants_call", "call_id"),
    )

    # Relationships
    call: Mapped["Call"] = relationship("Call", back_populates="participants")
