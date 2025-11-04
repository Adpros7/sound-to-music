from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile

from ..config import settings
from ..models import (
    ClefChoice,
    InstrumentChoice,
    JobCreateResponse,
    JobOptions,
    JobStatusResponse,
    QuantizationGrid,
)
from ..services.job_manager import JobManager

router = APIRouter(prefix="/jobs", tags=["jobs"])


async def get_manager(request: Request) -> JobManager:
    manager = getattr(request.app.state, "job_manager", None)
    if not manager:
        raise RuntimeError("Job manager not initialised")
    return manager


def _sanitize_bool(value: str | bool | None, *, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if value is None or value == "":
        return default
    return value.lower() in {"1", "true", "yes", "on"}


@router.post("", response_model=JobCreateResponse)
async def create_job(
    request: Request,
    file: UploadFile = File(...),
    clef: str = Form(ClefChoice.treble.value),
    instrument: str = Form(InstrumentChoice.piano.value),
    tempo: str | None = Form(default=None),
    force_key: str | None = Form(default=None),
    detect_time_signature: str | None = Form(default="true"),
    quantization: str = Form(QuantizationGrid.eighth.value),
    loose_quantization: str | None = Form(default="false"),
) -> JobCreateResponse:
    manager = await get_manager(request)

    if file.content_type and file.content_type not in settings.allowed_mime_types:
        raise HTTPException(status_code=400, detail="Unsupported file type")

    max_bytes = settings.max_file_mb * 1024 * 1024
    suffix = Path(file.filename or "audio").suffix or ".wav"

    try:
        options = JobOptions(
            clef=ClefChoice(clef),
            instrument=InstrumentChoice(instrument),
            tempo=int(tempo) if tempo else None,
            force_key=force_key or None,
            detect_time_signature=_sanitize_bool(detect_time_signature, default=True),
            quantization=QuantizationGrid(quantization),
            loose_quantization=_sanitize_bool(loose_quantization, default=False),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    job = await manager.allocate(options)

    upload_path = job.workdir / f"upload{suffix}"
    written = 0
    try:
        with upload_path.open("wb") as destination:
            while True:
                chunk = await file.read(1024 * 512)
                if not chunk:
                    break
                written += len(chunk)
                if written > max_bytes:
                    raise HTTPException(status_code=400, detail="File exceeds maximum allowed size of 20MB")
                destination.write(chunk)
    except HTTPException:
        upload_path.unlink(missing_ok=True)
        await manager.discard(job.id)
        raise
    finally:
        await file.close()

    if written == 0:
        upload_path.unlink(missing_ok=True)
        await manager.discard(job.id)
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    try:
        await _validate_duration(upload_path)
    except HTTPException:
        upload_path.unlink(missing_ok=True)
        await manager.discard(job.id)
        raise

    await manager.enqueue(job)
    return JobCreateResponse(job_id=job.id)


async def _validate_duration(path: Path) -> None:
    loop = asyncio.get_event_loop()
    duration = await loop.run_in_executor(None, _get_duration, path)
    if duration > settings.max_duration_seconds:
        path.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail="Audio duration exceeds limit of five minutes")


def _get_duration(path: Path) -> float:
    import librosa

    return float(librosa.get_duration(filename=str(path)))


@router.get("/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str, request: Request) -> JobStatusResponse:
    manager = await get_manager(request)
    await manager.cleanup_expired()
    job = await manager.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job.to_response()
