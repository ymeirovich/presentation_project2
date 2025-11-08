import asyncio
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict
from uuid import uuid4

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field, HttpUrl


class TrainingRequest(BaseModel):
    google_slides_url: HttpUrl
    mode: str = "presentation-only"
    voice_profile_name: str = "OpenAI Demo Voice (Your Audio)"
    quality_level: str = "fast"
    use_cache: bool = False
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TrainingResponse(BaseModel):
    success: bool
    job_id: str
    status: str
    progress: int = 10
    download_url: str | None = None
    error: str | None = None
    queued_at: datetime


JOB_STORE: Dict[str, Dict[str, Any]] = {}
JOB_LOCK = asyncio.Lock()
VIDEO_DELAY_SECONDS = int(os.getenv("AVATAR_SIM_DELAY_SECONDS", "4"))
PUBLIC_BASE_URL = os.getenv("AVATAR_PUBLIC_BASE_URL", "http://presgen-avatar:8002").rstrip("/")
JOBS_DIR = Path("/app/jobs")
JOBS_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(
    title="PresGen-Avatar Stub",
    version="0.2.0",
    description="Lightweight implementation of the PresGen-Avatar API for local testing.",
)


async def _download_core_video(job_id: str, source_url: str) -> Path:
    target_dir = JOBS_DIR / job_id
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / f"{job_id}.mp4"

    async with httpx.AsyncClient(timeout=None) as client:
        async with client.stream("GET", source_url) as response:
            try:
                response.raise_for_status()
            except httpx.HTTPError as exc:
                raise RuntimeError(f"Failed to download core video: {exc}") from exc
            with target_path.open("wb") as fh:
                async for chunk in response.aiter_bytes():
                    fh.write(chunk)

    return target_path


async def _complete_job(job_id: str, source_url: str) -> None:
    try:
        await asyncio.sleep(VIDEO_DELAY_SECONDS)
        video_path = await _download_core_video(job_id, source_url)
        async with JOB_LOCK:
            job = JOB_STORE.get(job_id)
            if not job:
                return
            download_url = f"{PUBLIC_BASE_URL}/training/download/{job_id}"
            job.update(
                {
                    "status": "completed",
                    "progress": 100,
                    "download_url": download_url,
                    "video_url": download_url,
                    "file_path": str(video_path),
                    "completed_at": datetime.utcnow().isoformat(),
                    "error": None,
                }
            )
    except Exception as exc:  # pragma: no cover - defensive
        async with JOB_LOCK:
            job = JOB_STORE.get(job_id)
            if job:
                job.update(
                    {
                        "status": "failed",
                        "progress": 0,
                        "download_url": None,
                        "video_url": None,
                        "file_path": None,
                        "error": str(exc),
                        "completed_at": datetime.utcnow().isoformat(),
                    }
                )


@app.get("/healthz")
async def health_check() -> Dict[str, str]:
    return {"status": "ok", "service": "presgen-avatar-stub"}


@app.post("/training/presentation-only", response_model=TrainingResponse)
async def create_training_job(request: TrainingRequest) -> TrainingResponse:
    core_download_url = (request.metadata or {}).get("core_download_url")
    if not core_download_url:
        raise HTTPException(status_code=400, detail="core_download_url metadata is required")

    job_id = uuid4().hex
    record: Dict[str, Any] = {
        "job_id": job_id,
        "status": "processing",
        "progress": 25,
        "download_url": None,
        "video_url": None,
        "queued_at": datetime.utcnow().isoformat(),
        "source_url": core_download_url,
        "file_path": None,
        "error": None,
    }
    async with JOB_LOCK:
        JOB_STORE[job_id] = record

    asyncio.create_task(_complete_job(job_id, core_download_url))

    return TrainingResponse(
        success=True,
        job_id=job_id,
        status="processing",
        progress=25,
        download_url=None,
        queued_at=datetime.utcnow(),
    )


@app.get("/training/status/{job_id}")
async def get_job_status(job_id: str) -> Dict[str, Any]:
    async with JOB_LOCK:
        job = JOB_STORE.get(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        response = {
            "job_id": job_id,
            "status": job["status"],
            "progress": job.get("progress", 25),
            "video_url": job.get("video_url"),
            "error_message": job.get("error"),
            "updated_at": datetime.utcnow().isoformat(),
        }
    return response


@app.get("/training/download/{job_id}")
async def download_video(job_id: str):
    async with JOB_LOCK:
        job = JOB_STORE.get(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        file_path = job.get("file_path")
        status = job.get("status")
    if status != "completed" or not file_path:
        raise HTTPException(status_code=400, detail="Job not completed")
    path = Path(file_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Video file missing")
    return FileResponse(
        path,
        media_type="video/mp4",
        filename=f"{job_id}.mp4",
    )


@app.delete("/training/jobs/{job_id}")
async def delete_job(job_id: str):
    async with JOB_LOCK:
        job = JOB_STORE.pop(job_id, None)
    if job and job.get("file_path"):
        path = Path(job["file_path"])
        if path.exists():
            path.unlink()
        dir_path = path.parent
        if dir_path.exists():
            dir_path.rmdir()
    return JSONResponse({"deleted": job_id})
