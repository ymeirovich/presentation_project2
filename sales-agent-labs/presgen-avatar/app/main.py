import asyncio
import os
from datetime import datetime
from pathlib import Path
from typing import Dict
from uuid import uuid4

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, HttpUrl


class TrainingRequest(BaseModel):
    google_slides_url: HttpUrl
    mode: str = "presentation-only"
    voice_profile_name: str = "OpenAI Demo Voice (Your Audio)"
    quality_level: str = "fast"
    use_cache: bool = False


class TrainingResponse(BaseModel):
    success: bool
    job_id: str
    status: str
    progress: int = 10
    download_url: str | None = None
    error: str | None = None
    queued_at: datetime


JOB_STORE: Dict[str, Dict[str, str]] = {}
JOB_LOCK = asyncio.Lock()
VIDEO_DELAY_SECONDS = int(os.getenv("AVATAR_SIM_DELAY_SECONDS", "4"))
PUBLIC_BASE_URL = os.getenv("AVATAR_PUBLIC_BASE_URL", "http://presgen-avatar:8002").rstrip("/")
SAMPLE_VIDEO_PATH = Path("/app/assets/sample.mp4")

app = FastAPI(
    title="PresGen-Avatar Stub",
    version="0.1.0",
    description="Lightweight implementation of the PresGen-Avatar API for local testing.",
)


async def _complete_job(job_id: str) -> None:
    await asyncio.sleep(VIDEO_DELAY_SECONDS)
    async with JOB_LOCK:
        job = JOB_STORE.get(job_id)
        if not job:
            return
        job["status"] = "completed"
        job["progress"] = 100
        job["download_url"] = f"{PUBLIC_BASE_URL}/training/download/{job_id}"
        job["video_url"] = job["download_url"]
        job["completed_at"] = datetime.utcnow().isoformat()


@app.get("/healthz")
async def health_check() -> Dict[str, str]:
    return {"status": "ok", "service": "presgen-avatar-stub"}


@app.post("/training/presentation-only", response_model=TrainingResponse)
async def create_training_job(
    request: TrainingRequest,
    background_tasks: BackgroundTasks,
) -> TrainingResponse:
    if not SAMPLE_VIDEO_PATH.exists():
        raise HTTPException(status_code=500, detail="Sample video file missing")

    job_id = uuid4().hex
    record = {
        "job_id": job_id,
        "status": "processing",
        "progress": 25,
        "download_url": None,
        "video_url": None,
        "queued_at": datetime.utcnow().isoformat(),
    }
    async with JOB_LOCK:
        JOB_STORE[job_id] = record

    background_tasks.add_task(_complete_job, job_id)

    return TrainingResponse(
        success=True,
        job_id=job_id,
        status="processing",
        progress=25,
        download_url=None,
        queued_at=datetime.utcnow(),
    )


@app.get("/training/status/{job_id}")
async def get_job_status(job_id: str) -> Dict[str, str | int | None]:
    async with JOB_LOCK:
        job = JOB_STORE.get(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        response = {
            "job_id": job_id,
            "status": job["status"],
            "progress": job.get("progress", 25),
            "video_url": job.get("video_url"),
            "error_message": None if job["status"] != "failed" else "Generation failed",
            "updated_at": datetime.utcnow().isoformat(),
        }
    return response


@app.get("/training/download/{job_id}")
async def download_video(job_id: str):
    if not SAMPLE_VIDEO_PATH.exists():
        raise HTTPException(status_code=404, detail="Sample video unavailable")
    return FileResponse(
        SAMPLE_VIDEO_PATH,
        media_type="video/mp4",
        filename=f"{job_id}.mp4",
    )


@app.delete("/training/jobs/{job_id}")
async def delete_job(job_id: str):
    async with JOB_LOCK:
        JOB_STORE.pop(job_id, None)
    return JSONResponse({"deleted": job_id})

