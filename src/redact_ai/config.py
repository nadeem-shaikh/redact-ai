"""Runtime configuration (pydantic-settings).

Server binding is **not** configurable; we hard-code ``127.0.0.1`` and an
ephemeral port to satisfy FR-9.2 / SECURITY §4a.
"""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="REDACT_AI_", extra="ignore")

    max_upload_bytes: int = Field(default=25 * 1024 * 1024, ge=1)
    default_policy_id: str = "default"
    log_level: str = "INFO"
    open_browser: bool = True


def get_settings() -> Settings:
    return Settings()
