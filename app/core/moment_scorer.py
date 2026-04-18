"""
Multi-Signal Fusion Scoring Engine — the core innovation of AttentionX.

Combines three independent signals into a single "viral score":
  - Audio energy (Librosa RMS peaks) — passion, excitement
  - Semantic sentiment (Gemini AI) — insight quality, quotability
  - Face confidence (MediaPipe) — visual quality of the shot

Score = w1*audio + w2*sentiment + w3*face
with deduplication and duration constraints applied.
"""
import logging
import numpy as np
from app.models import AudioPeak, SentimentResult, FaceFrame, MomentScore
from app.core.audio_analyzer import get_energy_at_time
from app.core.face_tracker import compute_crop_params
from app.config import settings

logger = logging.getLogger(__name__)


def score_and_rank_moments(
    sentiment_results: list[SentimentResult],
    audio_peaks: list[AudioPeak],
    face_frames: list[FaceFrame],
    video_w: int,
    video_h: int,
    video_duration: float,
) -> list[MomentScore]:
    """
    Fuse all signals and rank candidate moments by viral score.
    Applies non-maximum suppression to avoid overlapping clips.
    """
    candidates = []

    for sr in sentiment_results:
        clip_dur = sr.end - sr.start
        # Skip segments that are too short or too long
        if clip_dur < settings.min_clip_duration * 0.5:
            continue
        if clip_dur > settings.max_clip_duration * 1.5:
            continue

        # Get audio score for this time window
        audio_score = get_energy_at_time(audio_peaks, sr.start, sr.end)

        # Get face tracking score
        crop = compute_crop_params(face_frames, sr.start, sr.end, video_w, video_h)
        face_score = crop["face_confidence"]

        # Weighted fusion
        viral_score = (
            settings.weight_audio * audio_score
            + settings.weight_sentiment * sr.sentiment_score
            + settings.weight_face * face_score
        )

        # Duration bonus: clips near optimal length get a boost
        optimal_duration = 45  # seconds
        dur_penalty = 1.0 - abs(clip_dur - optimal_duration) / optimal_duration * 0.2
        viral_score *= max(0.7, dur_penalty)

        candidates.append(
            MomentScore(
                start=round(sr.start, 2),
                end=round(sr.end, 2),
                viral_score=round(viral_score, 4),
                audio_score=round(audio_score, 4),
                sentiment_score=round(sr.sentiment_score, 4),
                face_score=round(face_score, 4),
                transcript_text=sr.key_insight,
                hook_headline=sr.hook_headline,
                key_insight=sr.key_insight,
            )
        )

    # Sort by viral score descending
    candidates.sort(key=lambda c: c.viral_score, reverse=True)

    # Non-maximum suppression: remove overlapping clips
    selected = _non_max_suppression(candidates, min_gap=10.0)

    # Enforce clip duration constraints
    final = []
    for m in selected:
        dur = m.end - m.start
        if dur < settings.min_clip_duration:
            # Extend to minimum
            m.end = min(m.start + settings.min_clip_duration, video_duration)
        elif dur > settings.max_clip_duration:
            # Trim to maximum (keep from start)
            m.end = m.start + settings.max_clip_duration
        final.append(m)

    logger.info(f"Scored {len(candidates)} candidates → {len(final)} selected clips")
    return final[: settings.top_clips_count * 2]  # Return top 2x for user selection


def _non_max_suppression(
    moments: list[MomentScore], min_gap: float = 10.0
) -> list[MomentScore]:
    """
    Remove overlapping moment windows.
    Keeps higher-scored moments; suppresses those within min_gap seconds.
    """
    selected = []
    for m in moments:
        overlapping = False
        for s in selected:
            # Check if windows overlap significantly
            overlap_start = max(m.start, s.start)
            overlap_end = min(m.end, s.end)
            if overlap_end - overlap_start > min_gap:
                overlapping = True
                break
        if not overlapping:
            selected.append(m)

    return selected
