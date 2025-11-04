from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable

from ..models import Job, JobMeta, JobOptions, JobStatus


class JobStore:
    """Persist and retrieve :class:`Job` instances from shared storage."""

    def __init__(self, base_dir: Path) -> None:
        self._base_dir = Path(base_dir)
        self._jobs_dir = self._base_dir / "jobs"
        self._jobs_dir.mkdir(parents=True, exist_ok=True)

    def save(self, job: Job) -> None:
        path = self._path_for(job.id)
        data = self._serialise(job)
        tmp_path = path.with_suffix(path.suffix + ".tmp")
        tmp_path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
        tmp_path.replace(path)

    def get(self, job_id: str) -> Job | None:
        path = self._path_for(job_id)
        if not path.exists():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        return self._deserialise(data)

    def delete(self, job_id: str) -> None:
        path = self._path_for(job_id)
        path.unlink(missing_ok=True)

    def list_jobs(self) -> Iterable[Job]:
        for file in sorted(self._jobs_dir.glob("*.json")):
            try:
                data = json.loads(file.read_text(encoding="utf-8"))
                job = self._deserialise(data)
            except (OSError, json.JSONDecodeError, ValueError):  # pragma: no cover - corrupt job data
                continue
            else:
                yield job

    def _path_for(self, job_id: str) -> Path:
        return self._jobs_dir / f"{job_id}.json"

    def _serialise(self, job: Job) -> Dict[str, object]:
        return {
            "id": job.id,
            "created_at": job.created_at.isoformat(),
            "expires_at": job.expires_at.isoformat(),
            "options": job.options.model_dump(),
            "status": job.status.value,
            "progress": job.progress,
            "error": job.error,
            "meta": job.meta.model_dump() if job.meta else None,
            "artifacts": {key: str(path) for key, path in job.artifacts.items()},
            "workdir": str(job.workdir) if job.workdir else None,
        }

    def _deserialise(self, data: Dict[str, object]) -> Job:
        created_at = datetime.fromisoformat(str(data["created_at"]))
        expires_at = datetime.fromisoformat(str(data["expires_at"]))
        options_data = data.get("options") or {}
        if not isinstance(options_data, dict):
            options_data = {}
        options = JobOptions(**options_data)
        status = JobStatus(str(data.get("status", JobStatus.queued.value)))
        progress = int(data.get("progress", 0))
        error = data.get("error")
        meta_data = data.get("meta")
        meta = JobMeta(**meta_data) if isinstance(meta_data, dict) else None
        artifacts_data = data.get("artifacts") or {}
        if not isinstance(artifacts_data, dict):
            artifacts_data = {}
        artifacts = {key: Path(str(value)) for key, value in artifacts_data.items()}
        workdir_value = data.get("workdir")
        workdir = Path(workdir_value) if workdir_value else None
        return Job(
            id=str(data["id"]),
            created_at=created_at,
            expires_at=expires_at,
            options=options,
            status=status,
            progress=progress,
            error=error,
            meta=meta,
            artifacts=artifacts,
            workdir=workdir,
        )

