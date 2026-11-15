"""Initial Project Spectra Schema

Revision ID: 0001_initial_schema
Revises: 
Create Date: 2026-11-15 23:45:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. users
    op.create_table(
        "users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("username", sa.String(32), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("display_name", sa.String(64), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="active"),
        sa.Column("invite_code_id", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("idx_users_username", "users", ["username"])
    op.create_index("idx_users_status", "users", ["status"])

    # 2. invites
    op.create_table(
        "invites",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("code", sa.String(32), nullable=False, unique=True),
        sa.Column("creator_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("used_by_id", sa.String(36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("max_uses", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("uses_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("idx_invites_code", "invites", ["code"])

    # 3. devices
    op.create_table(
        "devices",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("device_identifier", sa.String(64), nullable=False),
        sa.Column("device_name", sa.String(64), nullable=False),
        sa.Column("client_platform", sa.String(32), nullable=False, server_default="web"),
        sa.Column("client_version", sa.String(32), nullable=False, server_default="1.0.0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("user_id", "device_identifier", name="uq_user_device_identifier"),
    )
    op.create_index("idx_devices_user_id", "devices", ["user_id"])

    # 4. sessions
    op.create_table(
        "sessions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("device_id", sa.String(36), sa.ForeignKey("devices.id", ondelete="CASCADE"), nullable=False),
        sa.Column("refresh_token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("previous_refresh_token_hash", sa.String(64), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("idx_sessions_user_device", "sessions", ["user_id", "device_id"])

    # 5. device_prekey_bundles
    op.create_table(
        "device_prekey_bundles",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("device_id", sa.String(36), sa.ForeignKey("devices.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("identity_key_pub", sa.String(64), nullable=False),
        sa.Column("signed_prekey_pub", sa.String(64), nullable=False),
        sa.Column("signed_prekey_sig", sa.String(128), nullable=False),
        sa.Column("signed_prekey_id", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("idx_prekeys_device", "device_prekey_bundles", ["device_id"])

    # 6. device_one_time_prekeys
    op.create_table(
        "device_one_time_prekeys",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("device_id", sa.String(36), sa.ForeignKey("devices.id", ondelete="CASCADE"), nullable=False),
        sa.Column("key_id", sa.Integer(), nullable=False),
        sa.Column("public_key", sa.String(64), nullable=False),
        sa.Column("is_used", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("device_id", "key_id", name="uq_device_otk_id"),
    )
    op.create_index("idx_device_otk_available", "device_one_time_prekeys", ["device_id", "is_used"])

    # 7. conversations
    op.create_table(
        "conversations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("type", sa.String(16), nullable=False, server_default="direct"),
        sa.Column("title", sa.String(128), nullable=True),
        sa.Column("avatar_hash", sa.String(64), nullable=True),
        sa.Column("created_by_id", sa.String(36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("last_sequence_id", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 8. conversation_members
    op.create_table(
        "conversation_members",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("conversation_id", sa.String(36), sa.ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.String(16), nullable=False, server_default="member"),
        sa.Column("last_read_seq", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("muted_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("joined_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("conversation_id", "user_id", name="uq_conversation_user"),
    )
    op.create_index("idx_conv_members_user", "conversation_members", ["user_id"])
    op.create_index("idx_conv_members_conv", "conversation_members", ["conversation_id"])

    # 9. message_envelopes
    op.create_table(
        "message_envelopes",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("conversation_id", sa.String(36), sa.ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sender_device_id", sa.String(36), sa.ForeignKey("devices.id", ondelete="CASCADE"), nullable=False),
        sa.Column("recipient_device_id", sa.String(36), sa.ForeignKey("devices.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sequence_id", sa.BigInteger(), nullable=False),
        sa.Column("envelope_type", sa.String(24), nullable=False, server_default="olm_msg"),
        sa.Column("ciphertext", sa.Text(), nullable=False),
        sa.Column("iv", sa.Text(), nullable=True),
        sa.Column("salt", sa.Text(), nullable=True),
        sa.Column("auth_tag", sa.Text(), nullable=True),
        sa.Column("is_delivered", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("idx_envelopes_sync", "message_envelopes", ["recipient_device_id", "sequence_id"])
    op.create_index("idx_envelopes_expiry", "message_envelopes", ["expires_at"])

    # 10. attachments
    op.create_table(
        "attachments",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("uploader_user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("file_path_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("mime_type", sa.String(128), nullable=False, server_default="application/octet-stream"),
        sa.Column("sha256_checksum", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 11. calls
    op.create_table(
        "calls",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("conversation_id", sa.String(36), sa.ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("initiator_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("call_type", sa.String(16), nullable=False, server_default="audio"),
        sa.Column("status", sa.String(16), nullable=False, server_default="ringing"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("idx_calls_conv", "calls", ["conversation_id"])
    op.create_index("idx_calls_initiator", "calls", ["initiator_id"])

    # 12. call_participants
    op.create_table(
        "call_participants",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("call_id", sa.String(36), sa.ForeignKey("calls.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("device_id", sa.String(36), sa.ForeignKey("devices.id", ondelete="SET NULL"), nullable=True),
        sa.Column("status", sa.String(16), nullable=False, server_default="invited"),
        sa.Column("joined_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("left_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("call_id", "user_id", "device_id", name="uq_call_participant"),
    )
    op.create_index("idx_call_participants_call", "call_participants", ["call_id"])


def downgrade() -> None:
    op.drop_table("call_participants")
    op.drop_table("calls")
    op.drop_table("attachments")
    op.drop_table("message_envelopes")
    op.drop_table("conversation_members")
    op.drop_table("conversations")
    op.drop_table("device_one_time_prekeys")
    op.drop_table("device_prekey_bundles")
    op.drop_table("sessions")
    op.drop_table("devices")
    op.drop_table("invites")
    op.drop_table("users")
