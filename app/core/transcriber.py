"""
Whisper-based transcription with word-level timestamps.
Produces segments with per-word timing for karaoke captions.
"""
import whisper
import logging
from pathlib import Path
from app.models import TranscriptSegment, WordTimestamp
from app.config import settings

logger = logging.getLogger(__name__)

_model = None


def get_model():
    global _model
    if _model is None:
        logger.info(f"Loading Whisper model: {settings.whisper_model}")
        _model = whisper.load_model(settings.whisper_model)
    return _model


def transcribe_video(video_path: str) -> list[TranscriptSegment]:
    """
    Transcribe video and return segments with word-level timestamps.
    Uses Whisper's word_timestamps=True for karaoke caption support.
    """
    logger.info(f"Transcribing: {video_path}")
    model = get_model()

    result = model.transcribe(
        video_path,
        word_timestamps=True,
        verbose=False,
        task="transcribe",
        language=None,  # Auto-detect language
        condition_on_previous_text=True,
        temperature=0.0,
    )

    segments = []
    for i, seg in enumerate(result["segments"]):
        words = []
        if "words" in seg:
            for w in seg["words"]:
                words.append(
                    WordTimestamp(
                        word=w["word"].strip(),
                        start=w["start"],
                        end=w["end"],
                    )
                )

        segments.append(
            TranscriptSegment(
                id=i,
                text=seg["text"].strip(),
                start=seg["start"],
                end=seg["end"],
                words=words,
            )
        )

    logger.info(f"Transcribed {len(segments)} segments")
    return segments


def group_segments_into_windows(
    segments: list[TranscriptSegment],
    window_size: int = 30,
    step_size: int = 15,
) -> list[dict]:
    """
    Create overlapping windows of transcript text for analysis.
    Each window has a start/end time and combined text for sentiment scoring.
    """
    if not segments:
        return []

    total_duration = segments[-1].end
    windows = []

    t = 0.0
    while t < total_duration - window_size * 0.5:
        window_end = t + window_size
        window_segs = [
            s for s in segments if s.start >= t and s.end <= window_end + 5
        ]
        if window_segs:
            combined_text = " ".join(s.text for s in window_segs)
            windows.append(
                {
                    "start": t,
                    "end": min(window_end, total_duration),
                    "text": combined_text,
                    "segments": window_segs,
                }
            )
        t += step_size

    return windows
