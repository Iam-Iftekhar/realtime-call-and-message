import asyncio
import base64
import os
import uuid
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from cryptography.hazmat.primitives.asymmetric import ed25519

# Configure test environment variables before importing app
os.environ["ENVIRONMENT"] = "testing"
os.environ["SECRET_KEY"] = "test-secret-key-for-project-spectra-testing-min-32-chars"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["INVITE_REQUIRED"] = "true"

from app.core.config import settings
from app.core.database import Base, get_db
from app.core.security import hash_password
from app.main import app
from app.modules.auth.models import Invite, User


# In-memory SQLite async engine for tests
test_engine = create_async_engine(
    "sqlite+aiosqlite:///:memory:",
    connect_args={"check_same_thread": False},
    future=True,
)

test_async_session_factory = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


@pytest_asyncio.fixture(scope="function")
async def db_session():
    """Create a fresh database for each test function."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with test_async_session_factory() as session:
        yield session

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession):
    """Async HTTP client with overridden database dependency."""
    async def override_get_db():
        try:
            yield db_session
            await db_session.commit()
        except Exception:
            await db_session.rollback()
            raise

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def valid_invite(db_session: AsyncSession) -> Invite:
    """Pre-seeded valid invite code."""
    # Seed a creator user first
    creator = User(
        id=uuid.uuid4(),
        username="admin_creator",
        password_hash=hash_password("SuperSecret123!"),
        display_name="Admin",
        status="active",
    )
    db_session.add(creator)
    await db_session.flush()

    from datetime import datetime, timezone, timedelta
    invite = Invite(
        id=uuid.uuid4(),
        code="SPECTRA-TEST-INVITE-2026",
        creator_id=creator.id,
        max_uses=10,
        uses_count=0,
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
    )
    db_session.add(invite)
    await db_session.commit()
    return invite


@pytest.fixture
def ed25519_keypair():
    """Generates an Ed25519 identity keypair for cryptographic testing."""
    priv_key = ed25519.Ed25519PrivateKey.generate()
    pub_key = priv_key.public_key()
    pub_bytes = pub_key.public_bytes_raw()
    pub_b64 = base64.b64encode(pub_bytes).decode("utf-8")
    return priv_key, pub_b64
