from __future__ import annotations

import asyncio
from datetime import timedelta

import pytest
from fastapi import FastAPI
from httpx import AsyncClient

from ..config import settings
from ..models import JobOptions, JobStatus
from ..routes import jobs
from ..services.job_manager import JobManager
from ..services.job_store import JobStore


@pytest.mark.asyncio
async def test_job_lookup_from_shared_store(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(settings, "storage_dir", tmp_path, raising=False)

    async def _processor(job) -> None:
        await asyncio.sleep(0)

    store_a = JobStore(settings.storage_dir)
    store_b = JobStore(settings.storage_dir)

    manager_a = JobManager(processor=_processor, retention=timedelta(minutes=5), store=store_a)
    manager_b = JobManager(processor=_processor, retention=timedelta(minutes=5), store=store_b)

    try:
        job = await manager_a.submit(JobOptions())
        await asyncio.wait_for(manager_a._queue.join(), timeout=2)

        await manager_b.load_existing_jobs()
        fetched = await manager_b.get(job.id)
        assert fetched is not None
        assert fetched.status == JobStatus.done

        app = FastAPI()
        app.state.job_manager = manager_b
        app.include_router(jobs.router, prefix="/api")

        async with AsyncClient(app=app, base_url="http://testserver") as client:
            response = await client.get(f"/api/jobs/{job.id}")

        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == JobStatus.done.value
    finally:
        await manager_a.shutdown()
        await manager_b.shutdown()
