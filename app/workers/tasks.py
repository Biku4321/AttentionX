"""
Celery async task pipeline for AttentionX.
Orchestrates the full processing pipeline:
  upload → transcribe → audio_analysis → sentiment → face_track → score → cut → caption
"""
import json
import logging
import os
from celery import Celery
from app.config import settings
from app.models import JobStatus, JobResult, MomentScore

logger = logging.getLogger(__name__)

celery_app = Celery(
    "attentionx",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    result_expires=3600,  # Results expire after 1 hour
)


def update_job_status(job_id: str, status: JobStatus, progress: int, message: str):
    """Store job status in Redis for polling."""
    import redis
    r = redis.from_url(settings.redis_url)
    data = {
        "job_id": job_id,
        "status": status.value,
        "progress": progress,
        "message": message,
        "clips": [],
        "error": None,
    }
    r.setex(f"job:{job_id}", 3600, json.dumps(data))


def get_job_result(job_id: str) -> dict | None:
    """Retrieve job status from Redis."""
    import redis
    r = redis.from_url(settings.redis_url)
    data = r.get(f"job:{job_id}")
    return json.loads(data) if data else None


def save_job_result(job_id: str, result: dict):
    """Save full job result including clips to Redis."""
    import redis
    r = redis.from_url(settings.redis_url)
    r.setex(f"job:{job_id}", 3600, json.dumps(result))


@celery_app.task(bind=True, name="process_video")
def process_video(self, job_id: str, video_path: str):
    """
    Main pipeline task. Runs all processing steps sequentially.
    Updates status at each step for real-time progress.
    """
    from app.core.transcriber import transcribe_video, group_segments_into_windows
    from app.core.audio_analyzer import analyze_audio_energy
    from app.core.gemini_analyzer import analyze_segments_batch
    from app.core.face_tracker import track_faces_in_video
    from app.core.moment_scorer import score_and_rank_moments
    from app.core.clip_cutter import get_video_metadata

    try:
        # Step 1: Get video metadata
        update_job_status(job_id, JobStatus.PENDING, 5, "Reading video metadata...")
        meta = get_video_metadata(video_path)
        video_w = meta["width"]
        video_h = meta["height"]
        video_duration = meta["duration"]

        # Step 2: Transcribe
        update_job_status(job_id, JobStatus.TRANSCRIBING, 15, "Transcribing audio with Whisper...")
        segments = transcribe_video(video_path)
        windows = group_segments_into_windows(
            segments,
            window_size=settings.max_clip_duration,
            step_size=settings.min_clip_duration,
        )

        # Step 3: Audio energy analysis
        update_job_status(job_id, JobStatus.ANALYZING_AUDIO, 35, "Detecting passion peaks...")
        audio_peaks = analyze_audio_energy(video_path, top_n=30)

        # Step 4: Gemini sentiment + hook generation
        update_job_status(job_id, JobStatus.ANALYZING_SENTIMENT, 55, "AI analyzing content quality...")
        sentiment_results = analyze_segments_batch(windows)

        # Step 5: Face tracking
        update_job_status(job_id, JobStatus.TRACKING_FACES, 70, "Tracking speaker for smart crop...")
        face_frames = track_faces_in_video(video_path, sample_fps=1.0)

        # Step 6: Multi-signal fusion scoring
        update_job_status(job_id, JobStatus.SCORING, 80, "Ranking viral moments...")
        moments = score_and_rank_moments(
            sentiment_results,
            audio_peaks,
            face_frames,
            video_w,
            video_h,
            video_duration,
        )

        # Save intermediate results (clips not yet rendered)
        result = {
            "job_id": job_id,
            "status": JobStatus.DONE.value,
            "progress": 100,
            "message": f"Found {len(moments)} high-impact moments! Ready to export.",
            "video_duration": video_duration,
            "clips": [m.dict() for m in moments[: settings.top_clips_count]],
            "all_moments": [m.dict() for m in moments],
            "segments": [s.dict() for s in segments],
            "face_frames": [f.dict() for f in face_frames],
            "error": None,
        }
        save_job_result(job_id, result)
        logger.info(f"Job {job_id} complete. {len(moments)} moments found.")
        return result

    except Exception as e:
        logger.exception(f"Job {job_id} failed: {e}")
        error_result = {
            "job_id": job_id,
            "status": JobStatus.FAILED.value,
            "progress": 0,
            "message": "Processing failed",
            "error": str(e),
            "clips": [],
        }
        save_job_result(job_id, error_result)
        raise


@celery_app.task(bind=True, name="render_clips")
def render_clips(
    self,
    job_id: str,
    video_path: str,
    clip_indices: list[int],
    add_captions: bool = True,
    add_hook: bool = True,
):
    """
    Render selected clips with captions and vertical crop.
    Called after user reviews and approves clips.
    """
    from app.core.clip_cutter import extract_clip
    from app.core.caption_engine import get_words_in_range, render_captions_with_moviepy
    from app.models import MomentScore, TranscriptSegment, FaceFrame

    result = get_job_result(job_id)
    if not result:
        raise ValueError(f"Job {job_id} not found")

    all_moments = [MomentScore(**m) for m in result.get("all_moments", [])]
    segments = [TranscriptSegment(**s) for s in result.get("segments", [])]
    face_frames = [FaceFrame(**f) for f in result.get("face_frames", [])]
    output_dir = settings.output_dir

    rendered_clips = []
    total = len(clip_indices)

    for i, idx in enumerate(clip_indices):
        if idx >= len(all_moments):
            continue

        moment = all_moments[idx]
        progress = int(80 * i / total) + 10
        update_job_status(
            job_id,
            JobStatus.CUTTING_CLIPS,
            progress,
            f"Rendering clip {i+1}/{total}...",
        )

        # Extract and crop clip
        clip_path, thumb_path = extract_clip(
            video_path,
            moment,
            face_frames,
            output_dir,
            job_id,
            i,
            vertical_crop=True,
        )

        # Add captions
        if add_captions:
            update_job_status(
                job_id,
                JobStatus.ADDING_CAPTIONS,
                progress + 5,
                f"Burning captions onto clip {i+1}...",
            )
            words = get_words_in_range(segments, moment.start, moment.end)
            captioned_path = clip_path.replace(".mp4", "_captioned.mp4")
            clip_path = render_captions_with_moviepy(
                clip_path,
                captioned_path,
                words,
                moment.hook_headline if add_hook else "",
                moment.end - moment.start,
                add_hook=add_hook,
            )

        moment.clip_path = os.path.basename(clip_path)
        moment.thumbnail_path = os.path.basename(thumb_path) if thumb_path else ""
        rendered_clips.append(moment.dict())

    # Update result with rendered clip paths
    result["rendered_clips"] = rendered_clips
    result["status"] = JobStatus.DONE.value
    result["progress"] = 100
    result["message"] = f"✅ {len(rendered_clips)} clips ready to download!"
    save_job_result(job_id, result)
    return result
