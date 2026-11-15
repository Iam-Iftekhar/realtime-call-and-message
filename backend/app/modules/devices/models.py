import uuid
from datetime import datetime, timezone
from sqlalchemy import Boolean, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, GUID


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Device(Base):
    __tablename__ = "devices"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    device_identifier: Mapped[str] = mapped_column(String(64), nullable=False)
    device_name: Mapped[str] = mapped_column(String(64), nullable=False)
    client_platform: Mapped[str] = mapped_column(String(32), default="web", nullable=False)
    client_version: Mapped[str] = mapped_column(String(32), default="1.0.0", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("user_id", "device_identifier", name="uq_user_device_identifier"),
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="devices")
    sessions: Mapped[list["Session"]] = relationship("Session", back_populates="device", cascade="all, delete-orphan")
    prekey_bundle: Mapped["DevicePrekeyBundle | None"] = relationship(
        "DevicePrekeyBundle", back_populates="device", cascade="all, delete-orphan", uselist=False
    )
    one_time_prekeys: Mapped[list["DeviceOneTimePrekey"]] = relationship(
        "DeviceOneTimePrekey", back_populates="device", cascade="all, delete-orphan"
    )
