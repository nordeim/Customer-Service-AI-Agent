from __future__ import annotations

from functools import lru_cache
from typing import Optional

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv
import os


class JWTSettings(BaseModel):
    algorithm: str = Field(default="HS256")
    issuer: str = Field(default="https://example.com/")
    audience: str = Field(default="ai-agent")
    access_ttl_seconds: int = Field(default=900)
    refresh_ttl_seconds: int = Field(default=2592000)


class SecuritySettings(BaseModel):
    secret_key: str = Field(min_length=16)
    encryption_key: str = Field(min_length=32, description="Base64 or raw key material")
    hmac_secret: str = Field(min_length=16)
    jwt: JWTSettings = Field(default_factory=JWTSettings)


class DataStoreSettings(BaseModel):
    database_url: str
    redis_url: str


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    env_nested_delimiter="__",  # <-- Add this line
    extra="allow",
    )

    # Environment
    environment: str = Field(default="development")
    log_level: str = Field(default="INFO")

    # Security
    security: SecuritySettings

    # Data stores
    datastore: DataStoreSettings

    # Integrations
    openai_api_key: Optional[str] = Field(default=None)

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    # Ensure .env is loaded into the environment (helps the uvicorn reloader process)
    env_path = os.path.join(os.getcwd(), '.env')
    if os.path.exists(env_path):
        load_dotenv(env_path, override=False)
    return Settings()
