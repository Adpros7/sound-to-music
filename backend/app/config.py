from __future__ import annotations

import os
from pathlib import Path
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    storage_dir: Path = Field(default_factory=lambda: Path(os.getenv("BACKEND_STORAGE_DIR", "storage")))
    job_retention_minutes: int = Field(default=30)
    engraver: str = Field(default_factory=lambda: os.getenv("ENGRAVER", "lilypond"))
    engraver_path: str | None = Field(default_factory=lambda: os.getenv("ENGRAVER_PATH"))
    basic_pitch_model_path: str | None = Field(default_factory=lambda: os.getenv("BASIC_PITCH_MODEL"))
    max_file_mb: int = Field(default=20)
    max_duration_seconds: int = Field(default=5 * 60)
    allowed_mime_types: tuple[str, ...] = ("audio/wav", "audio/x-wav", "audio/mpeg", "audio/mp3", "audio/x-m4a", "audio/flac", "audio/x-flac")

    model_config = SettingsConfigDict(env_prefix="BACKEND_", case_sensitive=False)

    @field_validator("storage_dir", mode="before")
    def _expand_storage_dir(cls, value: Path | str) -> Path:
        return Path(value).expanduser().resolve()


settings = Settings()
settings.storage_dir.mkdir(parents=True, exist_ok=True)
