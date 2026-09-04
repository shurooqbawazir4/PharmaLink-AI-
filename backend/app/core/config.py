"""Application settings, sourced from environment variables / .env.

A single `Settings` instance (`settings`) is the one source of truth for
configuration — nothing else in the codebase should call `os.environ`
directly, so every config value stays typed, validated, and discoverable
in one place.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- App -------------------------------------------------------------
    app_name: str = Field(default="PharmaLink AI", alias="APP_NAME")
    env: Literal["development", "staging", "production", "test"] = Field(
        default="development", alias="ENV"
    )
    debug: bool = Field(default=True, alias="DEBUG")
    api_v1_prefix: str = Field(default="/api/v1", alias="API_V1_PREFIX")

    # --- Database ----------------------------------------------------------
    database_url: str = Field(
        default="postgresql+asyncpg://medcycle:medcycle_dev_password@localhost:5432/medcycle",
        alias="DATABASE_URL",
    )

    @field_validator("database_url", mode="before")
    @classmethod
    def use_async_postgres_driver(cls, value: object) -> object:
        """Accept standard managed-host URLs with the app's async engine."""
        if isinstance(value, str) and value.startswith("postgresql://"):
            return value.replace("postgresql://", "postgresql+asyncpg://", 1)
        return value

    # --- Redis / Celery ------------------------------------------------------
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")

    # --- Auth / JWT ----------------------------------------------------------
    jwt_secret_key: str = Field(default="dev-only-insecure-secret", alias="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(default=30, alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    refresh_token_expire_days: int = Field(default=7, alias="REFRESH_TOKEN_EXPIRE_DAYS")

    # --- CORS ------------------------------------------------------------------
    cors_origins: str = Field(default="http://localhost:3000", alias="CORS_ORIGINS")

    # --- LLM explanation layer ---------------------------------------------------
    # Groq speaks the OpenAI wire protocol (chat completions), so the `openai`
    # SDK works unmodified once `base_url` points at Groq — see
    # infrastructure/external/llm/groq_provider.py.
    groq_api_key: str | None = Field(default=None, alias="GROQ_API_KEY")
    groq_model: str = Field(default="openai/gpt-oss-120b", alias="GROQ_MODEL")
    groq_base_url: str = Field(default="https://api.groq.com/openai/v1", alias="GROQ_BASE_URL")

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def is_production(self) -> bool:
        return self.env == "production"


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton — safe to call repeatedly (e.g. from Depends)."""
    return Settings()


settings = get_settings()
