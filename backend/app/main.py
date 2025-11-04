from __future__ import annotations

import asyncio
import contextlib

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .config import settings
from .models import Job
from .routes import jobs
from .services.job_manager import JobManager
from .services.pipeline import PipelineDependencies, run_pipeline


app = FastAPI(title="ScoreForge API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

results_dir = settings.storage_dir
results_dir.mkdir(parents=True, exist_ok=True)
app.mount("/results", StaticFiles(directory=str(results_dir)), name="results")


async def process_job(job: Job) -> None:
    deps = PipelineDependencies()
    await run_pipeline(job, deps)


@app.on_event("startup")
async def startup_event() -> None:
    manager = JobManager(processor=process_job)
    app.state.job_manager = manager
    await manager.load_existing_jobs()
    await manager.start()
    app.state.cleanup_task = asyncio.create_task(_cleanup_loop(manager))


@app.on_event("shutdown")
async def shutdown_event() -> None:
    manager: JobManager | None = getattr(app.state, "job_manager", None)
    if manager:
        await manager.shutdown()
    cleanup_task = getattr(app.state, "cleanup_task", None)
    if cleanup_task:
        cleanup_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await cleanup_task


@app.get("/healthz")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(jobs.router, prefix="/api")


async def _cleanup_loop(manager: JobManager) -> None:
    while True:
        await asyncio.sleep(60)
        await manager.cleanup_expired()
