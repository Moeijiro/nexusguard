"""Application configuration, read from the environment or a local .env file."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DISCORD_API_BASE = "https://discord.com/api/v10"
# identify: who you are. guilds: which servers you're in, with your permissions there.
# Nothing else — NexusGuard never reads your messages or acts as you.
OAUTH_SCOPES = ("identify", "guilds")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(".env", "../.env"), env_file_encoding="utf-8", extra="ignore")

    environment: Literal["development", "production"] = "development"
    app_url: str = "http://localhost:3000"
    api_url: str = "http://localhost:8000"
    database_url: str = "sqlite:///./nexusguard.db"

    secret_key: str = Field(default="dev-only-insecure-secret-replace-before-deploying", min_length=8)
    session_ttl_minutes: int = Field(default=720, ge=5)
    cookie_secure: bool = False
    cookie_samesite: Literal["lax", "strict", "none"] = "lax"

    discord_client_id: str = ""
    discord_client_secret: str = ""
    discord_bot_token: str = ""
    guild_access_ttl_minutes: int = Field(default=720, ge=5)

    demo_enabled: bool = True
    demo_simulator_interval: int = Field(default=25, ge=0, le=3600)

    @field_validator("app_url", "api_url")
    @classmethod
    def _strip_slash(cls, value: str) -> str:
        return value.rstrip("/")

    @model_validator(mode="after")
    def _guard(self) -> "Settings":
        if self.environment == "production":
            if "insecure" in self.secret_key or len(self.secret_key) < 32:
                raise ValueError("SECRET_KEY must be a strong value in production")
            if not self.cookie_secure:
                raise ValueError("COOKIE_SECURE must be true in production")
        return self

    @property
    def discord_configured(self) -> bool:
        return bool(self.discord_client_id and self.discord_client_secret and self.discord_bot_token)

    @property
    def oauth_redirect_uri(self) -> str:
        return f"{self.api_url}/api/auth/callback"

    @property
    def debug_errors(self) -> bool:
        return self.environment == "development"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
