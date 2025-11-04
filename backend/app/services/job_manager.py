from __future__ import annotations

import asyncio
from contextlib import suppress
from datetime import datetime, timedelta, timezone
from typing import Awaitable, Callable

import shutil

from ..config import settings
from ..models import Job, JobOptions, JobStatus
from .job_store import JobStore


Processor = Callable[[Job], Awaitable[None]]


class JobManager:
    def __init__(
        self,
        *,
        processor: Processor,
        retention: timedelta | None = None,
        base_url: str | None = None,
        store: JobStore | None = None,
    ) -> None:
        self._queue: asyncio.Queue[Job] = asyncio.Queue()
        self._tasks: set[asyncio.Task[None]] = set()
        self._processor = processor
        self._retention = retention or timedelta(minutes=settings.job_retention_minutes)
        self._base_url = base_url
        self._worker_task: asyncio.Task[None] | None = None
        self._lock = asyncio.Lock()
        self._store = store or JobStore(settings.storage_dir)

    async def start(self) -> None:
        if self._worker_task is None:
            self._worker_task = asyncio.create_task(self._worker())

    async def shutdown(self) -> None:
        if self._worker_task:
            self._worker_task.cancel()
            with suppress(asyncio.CancelledError):
                await self._worker_task
            self._worker_task = None
        tasks = list(self._tasks)
        for task in tasks:
            task.cancel()
        for task in tasks:
            with suppress(asyncio.CancelledError):
                await task
        self._tasks.clear()

    async def allocate(self, options: JobOptions) -> Job:
        job = Job.create(options=options, retention=self._retention, workdir=settings.storage_dir)
        job.workdir.mkdir(parents=True, exist_ok=True)
        await self._save(job)
        return job

    async def enqueue(self, job: Job) -> None:
        await self._queue.put(job)
        await self.start()

    async def submit(self, options: JobOptions) -> Job:
        job = await self.allocate(options)
        await self.enqueue(job)
        return job

    async def get(self, job_id: str) -> Job | None:
        job = await self._load(job_id)
        if job and job.expires_at <= self._now():
            await self._remove(job_id)
            return None
        return job

    async def cleanup_expired(self) -> None:
        loop_time = self._now()
        jobs = await self._list_jobs()
        for job in jobs:
            if job.expires_at <= loop_time:
                await self._remove(job.id)

    async def _worker(self) -> None:
        while True:
            job = await self._queue.get()
            job.status = JobStatus.running
            job.progress = 5
            await self._save(job)
            task = asyncio.create_task(self._run_job(job))
            self._tasks.add(task)
            task.add_done_callback(self._tasks.discard)

    async def _run_job(self, job: Job) -> None:
        try:
            await self._processor(job)
            job.status = JobStatus.done
            job.progress = 100
        except Exception as exc:  # pragma: no cover - fallback path
            job.status = JobStatus.error
            job.error = str(exc)
            job.progress = 100
        finally:
            await self._save(job)
            self._queue.task_done()

    async def _remove(self, job_id: str) -> None:
        job = await self._load(job_id)
        await self._delete(job_id)
        if job and job.workdir and job.workdir.exists():
            shutil.rmtree(job.workdir, ignore_errors=True)

    @staticmethod
    def _now():
        return datetime.now(timezone.utc)

    async def discard(self, job_id: str) -> None:
        await self._remove(job_id)

    async def load_existing_jobs(self) -> None:
        jobs = await self._list_jobs()
        now = self._now()
        for job in jobs:
            if job.expires_at <= now:
                await self._remove(job.id)
                continue
            if job.status in {JobStatus.queued, JobStatus.running}:
                job.status = JobStatus.queued
                await self._save(job)
                await self.enqueue(job)

    async def _save(self, job: Job) -> None:
        async with self._lock:
            await asyncio.to_thread(self._store.save, job)

    async def _load(self, job_id: str) -> Job | None:
        return await asyncio.to_thread(self._store.get, job_id)

    async def _delete(self, job_id: str) -> None:
        async with self._lock:
            await asyncio.to_thread(self._store.delete, job_id)

    async def _list_jobs(self) -> list[Job]:
        jobs = await asyncio.to_thread(lambda: list(self._store.list_jobs()))
        return jobs
