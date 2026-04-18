"""
FastAPI routes for AttentionX.
Endpoints:
  POST /upload      — Upload video, start processing job
  GET  /status/{id} — Poll job status
  POST /render      — Trigger clip rendering for selected moments
  GET  /download/{id}/{filename} — Download processed clip
  GET  /thumbnail/{id}/{filename} — Serve thumbnail image
  GET  /health      — Health check
"""
import os
import uuid
import shutil
import logging
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from app.config import settings
from app.models import UploadResponse, ClipRequest

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/health")
async def health():
    return {"status": "ok", "service": "AttentionX"}


@router.post("/upload", response_model=UploadResponse)
async def upload_video(file: UploadFile = File(...)):
    """
    Accept video upload and queue processing job.
    Supported formats: mp4, mov, avi, mkv, webm.
    """
    # Validate file type
    allowed = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v"}
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in allowed:
        raise HTTPException(400, f"Unsupported format: {ext}. Use: {', '.join(allowed)}")

    # Check file size
    max_bytes = settings.max_upload_mb * 1024 * 1024
    content = await file.read()
    if len(content) > max_bytes:
        raise HTTPException(413, f"File too large. Max {settings.max_upload_mb}MB")

    # Save file
    job_id = str(uuid.uuid4())
    safe_name = f"{job_id}{ext}"
    video_path = os.path.join(settings.upload_dir, safe_name)

    with open(video_path, "wb") as f:
        f.write(content)

    logger.info(f"Uploaded: {file.filename} → {video_path} (job: {job_id})")

    # Queue Celery task
    try:
        from app.workers.tasks import process_video, update_job_status
        from app.models import JobStatus
        update_job_status(job_id, JobStatus.PENDING, 0, "Job queued...")
        process_video.delay(job_id, video_path)
    except Exception as e:
        logger.error(f"Failed to queue job: {e}")
        raise HTTPException(500, f"Failed to queue processing: {e}")

    return UploadResponse(
        job_id=job_id,
        filename=file.filename,
        message="Video uploaded! Processing started.",
    )


@router.get("/status/{job_id}")
async def get_status(job_id: str):
    """Poll processing status for a job."""
    from app.workers.tasks import get_job_result
    result = get_job_result(job_id)
    if not result:
        raise HTTPException(404, f"Job {job_id} not found")
    return result


@router.post("/render")
async def render_clips(request: ClipRequest):
    """
    Trigger rendering of selected clips with captions.
    Called after user reviews AI-selected moments.
    """
    from app.workers.tasks import get_job_result, render_clips as render_task
    from app.models import JobStatus

    result = get_job_result(request.job_id)
    if not result:
        raise HTTPException(404, f"Job {request.job_id} not found")

    # Find the video file
    upload_dir = settings.upload_dir
    video_files = [
        f for f in os.listdir(upload_dir)
        if f.startswith(request.job_id)
    ]
    if not video_files:
        raise HTTPException(404, "Original video not found (may have been cleaned up)")

    video_path = os.path.join(upload_dir, video_files[0])

    # Queue render task
    clip_indices = request.clip_indices or list(range(settings.top_clips_count))
    render_task.delay(
        request.job_id,
        video_path,
        clip_indices,
        request.add_captions,
        request.add_hook,
    )

    return {"message": "Rendering started", "job_id": request.job_id}


@router.get("/download/{job_id}/{filename}")
async def download_clip(job_id: str, filename: str):
    """Download a processed clip."""
    
    if not filename.startswith(job_id):
        raise HTTPException(403, "Unauthorized")
    path = os.path.join(settings.output_dir, filename)
    if not os.path.exists(path):
        raise HTTPException(404, "File not found")
    return FileResponse(
        path,
        media_type="video/mp4",
        filename=filename,
    )


@router.get("/thumbnail/{job_id}/{filename}")
async def serve_thumbnail(job_id: str, filename: str):
    """Serve a clip thumbnail."""
    if not filename.startswith(job_id):
        raise HTTPException(403, "Unauthorized")
    path = os.path.join(settings.output_dir, filename)
    if not os.path.exists(path):
        raise HTTPException(404, "Thumbnail not found")
    return FileResponse(path, media_type="image/jpeg")
