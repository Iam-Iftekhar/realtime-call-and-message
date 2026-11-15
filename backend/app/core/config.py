import os
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    PROJECT_NAME: str = "Project Spectra"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = Field(default="development", validation_alias="ENVIRONMENT")
    DEBUG: bool = Field(default=False, validation_alias="DEBUG")

    # Security & Tokens
    SECRET_KEY: str = Field(
        default="spectra-super-secret-dev-key-change-in-production-min-32-chars",
        validation_alias="SECRET_KEY",
    )
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    ALGORITHM: str = "HS256"

    # Database
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://spectra:spectra_password@localhost:5432/spectra_db",
        validation_alias="DATABASE_URL",
    )

    # Redis
    REDIS_URL: str = Field(
        default="redis://localhost:6379/0",
        validation_alias="REDIS_URL",
    )

    # Coturn TURN Configuration
    COTURN_STATIC_SECRET: str = Field(
        default="spectra-coturn-shared-hmac-secret-key-32b",
        validation_alias="COTURN_STATIC_SECRET",
    )
    COTURN_REALM: str = "turn.spectra.chat"
    COTURN_UDP_PORT: int = 3478
    COTURN_TLS_PORT: int = 5349
    COTURN_HOST: str = "turn.spectra.chat"
    COTURN_CREDENTIAL_TTL_SECONDS: int = 3600

    # Registration & Gating
    INVITE_REQUIRED: bool = True

    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:8000",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8000",
    ]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
