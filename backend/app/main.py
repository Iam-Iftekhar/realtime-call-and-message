from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.core.exceptions import SpectraException, spectra_exception_handler
from app.core.redis import close_redis
from app.modules.auth.router import router as auth_router
from app.modules.calling.router import router as calling_router
from app.modules.devices.router import router as devices_router
from app.modules.encryption.router import router as encryption_router
from app.modules.messaging.router import router as messaging_router
from app.modules.users.router import router as users_router
from app.websockets.router import ws_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup tasks
    yield
    # Shutdown tasks
    await close_redis()


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Privacy-first, real-time communication platform backend modular monolith.",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan,
)

# Exception handlers
app.add_exception_handler(SpectraException, spectra_exception_handler)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health checks
@app.get("/health", tags=["Health"])
@app.get(f"{settings.API_V1_STR}/health", tags=["Health"])
async def health_check():
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
    }


# Include Module Routers under API_V1_STR
api_v1 = settings.API_V1_STR
app.include_router(auth_router, prefix=api_v1)
app.include_router(users_router, prefix=api_v1)
app.include_router(devices_router, prefix=api_v1)
app.include_router(encryption_router, prefix=api_v1)
app.include_router(messaging_router, prefix=api_v1)
app.include_router(calling_router, prefix=api_v1)

# Include WebSocket Router
app.include_router(ws_router)

# Mount Frontend static files on /
frontend_dir = Path(__file__).resolve().parent.parent.parent / "frontend"
if frontend_dir.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")
