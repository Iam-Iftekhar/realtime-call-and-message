import uuid
from datetime import datetime, timezone, timedelta
from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, GUID


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def default_expiry() -> datetime:
    return datetime.now(timezone.utc) + timedelta(days=30)


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        primary_key=True,
        default=uuid.uuid4,
    )
    type: Mapped[str] = mapped_column(String(16), default="direct", nullable=False)  # 'direct' or 'group'
    title: Mapped[str | None] = mapped_column(String(128), nullable=True)
    avatar_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(GUID, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    last_sequence_id: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )

    # Relationships
    members: Mapped[list["ConversationMember"]] = relationship(
        "ConversationMember", back_populates="conversation", cascade="all, delete-orphan"
    )
    envelopes: Mapped[list["MessageEnvelope"]] = relationship(
        "MessageEnvelope", back_populates="conversation", cascade="all, delete-orphan"
    )


class ConversationMember(Base):
    __tablename__ = "conversation_members"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        primary_key=True,
        default=uuid.uuid4,
    )
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[str] = mapped_column(String(16), default="member", nullable=False)  # 'owner', 'admin', 'member'
    last_read_seq: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    muted_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("conversation_id", "user_id", name="uq_conversation_user"),
        Index("idx_conv_members_user", "user_id"),
        Index("idx_conv_members_conv", "conversation_id"),
    )

    # Relationships
    conversation: Mapped["Conversation"] = relationship("Conversation", back_populates="members")


class MessageEnvelope(Base):
    """Untrusted store-and-forward mailbox envelope.
    Contains ONLY opaque ciphertext blobs addressed to a specific recipient device.
    """
    __tablename__ = "message_envelopes"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        primary_key=True,
        default=uuid.uuid4,
    )
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False
    )
    sender_device_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("devices.id", ondelete="CASCADE"), nullable=False
    )
    recipient_device_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("devices.id", ondelete="CASCADE"), nullable=False
    )
    sequence_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    envelope_type: Mapped[str] = mapped_column(String(24), default="olm_msg", nullable=False)
    ciphertext: Mapped[str] = mapped_column(Text, nullable=False)  # Base64 encrypted payload
    iv: Mapped[str | None] = mapped_column(Text, nullable=True)
    salt: Mapped[str | None] = mapped_column(Text, nullable=True)
    auth_tag: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_delivered: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=default_expiry, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    __table_args__ = (
        Index("idx_envelopes_sync", "recipient_device_id", "sequence_id"),
        Index("idx_envelopes_expiry", "expires_at"),
    )

    # Relationships
    conversation: Mapped["Conversation"] = relationship("Conversation", back_populates="envelopes")


class Attachment(Base):
    """Metadata for client-side encrypted media files."""
    __tablename__ = "attachments"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        primary_key=True,
        default=uuid.uuid4,
    )
    uploader_user_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    file_path_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(128), default="application/octet-stream", nullable=False)
    sha256_checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
