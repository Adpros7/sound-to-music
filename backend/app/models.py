from __future__ import annotations

import enum
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class JobStatus(str, enum.Enum):
    queued = "queued"
    running = "running"
    done = "done"
    error = "error"


class QuantizationGrid(str, enum.Enum):
    quarter = "quarter"
    eighth = "eighth"
    sixteenth = "sixteenth"

    def to_fraction(self) -> float:
        mapping = {
            QuantizationGrid.quarter: 1 / 4,
            QuantizationGrid.eighth: 1 / 8,
            QuantizationGrid.sixteenth: 1 / 16,
        }
        return mapping[self]


class ClefChoice(str, enum.Enum):
    treble = "treble"
    alto = "alto"
    tenor = "tenor"


class JobOptions(BaseModel):
    clef: ClefChoice = ClefChoice.treble
    tempo: Optional[int] = None
    force_key: Optional[str] = Field(default=None, description="Override key detection with explicit key e.g. C major")
    detect_time_signature: bool = True
    quantization: QuantizationGrid = QuantizationGrid.eighth
    loose_quantization: bool = False


class JobCreateResponse(BaseModel):
    job_id: str


class JobArtifactUrls(BaseModel):
    pdf: Optional[str]
    musicxml: Optional[str]
    midi: Optional[str]


class JobMeta(BaseModel):
    title: Optional[str] = None
    key: Optional[str] = None
    time_signature: Optional[str] = None
    tempo: Optional[int] = None
    note_count: Optional[int] = None
    duration_seconds: Optional[float] = None


class JobStatusResponse(BaseModel):
    status: JobStatus
    progress: int = 0
    error: Optional[str] = None
    urls: JobArtifactUrls = Field(default_factory=JobArtifactUrls)
    meta: Optional[JobMeta] = None


@dataclass(slots=True)
class Job:
    id: str
    created_at: datetime
    expires_at: datetime
    options: JobOptions
    status: JobStatus = JobStatus.queued
    progress: int = 0
    error: Optional[str] = None
    meta: Optional[JobMeta] = None
    artifacts: Dict[str, Path] = field(default_factory=dict)
    workdir: Path | None = None

    @classmethod
    def create(cls, options: JobOptions, retention: timedelta, workdir: Path) -> "Job":
        job_id = uuid.uuid4().hex
        now = datetime.now(timezone.utc)
        return cls(
            id=job_id,
            created_at=now,
            expires_at=now + retention,
            options=options,
            workdir=workdir / job_id,
        )

    def to_response(self, base_url: str | None = None) -> JobStatusResponse:
        urls = JobArtifactUrls(
            pdf=self._format_url("pdf", base_url),
            musicxml=self._format_url("musicxml", base_url),
            midi=self._format_url("midi", base_url),
        )
        return JobStatusResponse(
            status=self.status,
            progress=self.progress,
            error=self.error,
            urls=urls,
            meta=self.meta,
        )

    def _format_url(self, key: str, base_url: str | None) -> Optional[str]:
        artifact = self.artifacts.get(key)
        if not artifact:
            return None
        if base_url:
            return f"{base_url.rstrip('/')}/{self.id}/{artifact.name}"
        return f"/results/{self.id}/{artifact.name}"
