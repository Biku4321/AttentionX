"""
Clip extraction engine using MoviePy.
Handles:
  - Cutting clips from source video by timestamp
  - Smart 9:16 crop centered on speaker face
  - Thumbnail extraction
  - Clip metadata
"""
import os
import logging
from pathlib import Path
from app.models import MomentScore, FaceFrame
from app.core.face_tracker import compute_crop_params

logger = logging.getLogger(__name__)


def extract_clip(
    video_path: str,
    moment: MomentScore,
    face_frames: list[FaceFrame],
    output_dir: str,
    job_id: str,
    clip_idx: int,
    vertical_crop: bool = True,
) -> tuple[str, str]:
    """
    Extract a clip from source video and optionally apply 9:16 vertical crop.
    Returns (clip_path, thumbnail_path).
    """
    try:
        from moviepy.editor import VideoFileClip
        import numpy as np
        from PIL import Image
    except ImportError as e:
        raise RuntimeError(f"MoviePy/Pillow not installed: {e}")

    clip_filename = f"{job_id}_clip_{clip_idx:02d}.mp4"
    thumb_filename = f"{job_id}_thumb_{clip_idx:02d}.jpg"
    clip_path = os.path.join(output_dir, clip_filename)
    thumb_path = os.path.join(output_dir, thumb_filename)

    logger.info(f"Extracting clip {clip_idx}: {moment.start:.1f}s - {moment.end:.1f}s")

    video = VideoFileClip(video_path)
    source_w, source_h = video.size

    # Cut the raw clip
    raw_clip = video.subclip(moment.start, min(moment.end, video.duration))

    if vertical_crop:
        # Compute face-centered crop parameters
        crop = compute_crop_params(
            face_frames,
            moment.start,
            moment.end,
            source_w,
            source_h,
        )

        crop_x = crop["x"]
        crop_y = crop["y"]
        crop_w = crop["width"]
        crop_h = crop["height"]

        # Apply crop using MoviePy
        cropped = raw_clip.crop(
            x1=crop_x,
            y1=crop_y,
            x2=crop_x + crop_w,
            y2=crop_y + crop_h,
        )

        # Resize to standard vertical format (1080x1920)
        final_clip = cropped.resize(height=1920)
        if final_clip.size[0] > 1080:
            final_clip = final_clip.crop(
                x_center=final_clip.size[0] / 2,
                width=1080,
            )
    else:
        final_clip = raw_clip

    # Write video file
    final_clip.write_videofile(
        clip_path,
        codec="libx264",
        audio_codec="aac",
        fps=min(video.fps, 30),
        preset="fast",
        verbose=False,
        logger=None,
    )

    # Extract thumbnail from middle of clip
    try:
        mid_time = (moment.end - moment.start) / 2
        thumb_frame = final_clip.get_frame(mid_time)
        img = Image.fromarray(thumb_frame)
        img.thumbnail((540, 960))
        img.save(thumb_path, "JPEG", quality=85)
    except Exception as e:
        logger.warning(f"Thumbnail extraction failed: {e}")
        thumb_path = ""

    video.close()
    raw_clip.close()
    final_clip.close()

    logger.info(f"Clip saved: {clip_path}")
    return clip_path, thumb_path


def get_video_metadata(video_path: str) -> dict:
    """Extract basic metadata from video file."""
    try:
        from moviepy.editor import VideoFileClip
        video = VideoFileClip(video_path)
        meta = {
            "duration": video.duration,
            "fps": video.fps,
            "width": video.size[0],
            "height": video.size[1],
            "audio": video.audio is not None,
        }
        video.close()
        return meta
    except Exception as e:
        logger.error(f"Failed to get video metadata: {e}")
        return {"duration": 0, "fps": 30, "width": 1920, "height": 1080, "audio": True}
