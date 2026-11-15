import uuid
from datetime import datetime, timezone
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, GUID


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class DevicePrekeyBundle(Base):
    __tablename__ = "device_prekey_bundles"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        primary_key=True,
        default=uuid.uuid4,
    )
    device_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("devices.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    identity_key_pub: Mapped[str] = mapped_column(String(64), nullable=False)
    signed_prekey_pub: Mapped[str] = mapped_column(String(64), nullable=False)
    signed_prekey_sig: Mapped[str] = mapped_column(String(128), nullable=False)
    signed_prekey_id: Mapped[int] = mapped_column(Integer, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    # Relationships
    device: Mapped["Device"] = relationship("Device", back_populates="prekey_bundle")


class DeviceOneTimePrekey(Base):
    __tablename__ = "device_one_time_prekeys"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        primary_key=True,
        default=uuid.uuid4,
    )
    device_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("devices.id", ondelete="CASCADE"), nullable=False
    )
    key_id: Mapped[int] = mapped_column(Integer, nullable=False)
    public_key: Mapped[str] = mapped_column(String(64), nullable=False)
    is_used: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("device_id", "key_id", name="uq_device_otk_id"),
    )

    # Relationships
    device: Mapped["Device"] = relationship("Device", back_populates="one_time_prekeys")
