import asyncio
import uuid
from datetime import datetime, timezone, timedelta
from sqlalchemy import select

from app.core.database import async_session_factory
from app.core.security import hash_password
from app.modules.auth.models import Invite, Session, User
import app.modules.devices.models  # noqa
import app.modules.encryption.models  # noqa
import app.modules.messaging.models  # noqa
import app.modules.calling.models  # noqa


async def seed():
    async with async_session_factory() as db:
        # Check if admin user already exists
        res = await db.execute(select(User).where(User.username == "spectra_admin"))
        admin = res.scalar_one_or_none()
        if not admin:
            admin = User(
                id=uuid.uuid4(),
                username="spectra_admin",
                password_hash=hash_password("SpectraAdmin2026!"),
                display_name="Spectra Administrator",
                status="active",
            )
            db.add(admin)
            await db.flush()
            print(f"[Seed] Created admin user: spectra_admin (ID: {admin.id})")
        else:
            print("[Seed] Admin user already exists.")

        # Check if genesis invite exists
        inv_res = await db.execute(select(Invite).where(Invite.code == "SPECTRA-GENESIS-2026"))
        invite = inv_res.scalar_one_or_none()
        if not invite:
            invite = Invite(
                id=uuid.uuid4(),
                code="SPECTRA-GENESIS-2026",
                creator_id=admin.id,
                max_uses=1000,
                uses_count=0,
                expires_at=datetime.now(timezone.utc) + timedelta(days=365),
            )
            db.add(invite)
            await db.commit()
            print(f"[Seed] Created genesis invite code: SPECTRA-GENESIS-2026 (Max uses: 1000)")
        else:
            print("[Seed] Genesis invite already exists.")


if __name__ == "__main__":
    asyncio.run(seed())
