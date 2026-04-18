"""
Audio analysis using Librosa to detect high-energy "passion" moments.
Combines RMS energy, spectral features, and speaking rate as signal.
"""
import librosa
import numpy as np
import logging
from app.models import AudioPeak

logger = logging.getLogger(__name__)


def analyze_audio_energy(
    video_path: str,
    window_duration: float = 30.0,
    step_duration: float = 5.0,
    top_n: int = 20,
) -> list[AudioPeak]:
    """
    Load audio from video and compute energy scores per time window.
    Returns ranked list of high-energy peaks.
    """
    logger.info(f"Analyzing audio energy: {video_path}")

    # Load audio (librosa handles video files via ffmpeg)
    y, sr = librosa.load(video_path, sr=22050, mono=True)
    duration = librosa.get_duration(y=y, sr=sr)

    # Compute frame-level features
    hop_length = 512
    frame_duration = hop_length / sr  # ~23ms per frame

    # 1. RMS Energy — loudness/passion indicator
    rms = librosa.feature.rms(y=y, hop_length=hop_length)[0]

    # 2. Zero Crossing Rate — speaking speed / articulation
    zcr = librosa.feature.zero_crossing_rate(y, hop_length=hop_length)[0]

    # 3. Spectral Centroid — vocal "brightness" (higher = more energetic speech)
    centroid = librosa.feature.spectral_centroid(y=y, sr=sr, hop_length=hop_length)[0]

    # Normalize all features to 0-1
    def normalize(arr):
        mn, mx = arr.min(), arr.max()
        if mx == mn:
            return np.zeros_like(arr)
        return (arr - mn) / (mx - mn)

    rms_norm = normalize(rms)
    zcr_norm = normalize(zcr)
    cent_norm = normalize(centroid)

    # Combined energy signal (weighted)
    combined = 0.6 * rms_norm + 0.25 * zcr_norm + 0.15 * cent_norm

    # Sliding window to get per-segment scores
    window_frames = int(window_duration / frame_duration)
    step_frames = int(step_duration / frame_duration)

    peaks = []
    i = 0
    while i + window_frames <= len(combined):
        window = combined[i : i + window_frames]
        # Use 75th percentile to reward consistently high energy
        score = float(np.percentile(window, 75))

        start_time = i * frame_duration
        end_time = min((i + window_frames) * frame_duration, duration)

        peaks.append(
            AudioPeak(
                start=round(start_time, 2),
                end=round(end_time, 2),
                energy_score=round(score, 4),
            )
        )
        i += step_frames

    # Sort by score descending
    peaks.sort(key=lambda p: p.energy_score, reverse=True)
    logger.info(f"Found {len(peaks)} audio windows, returning top {top_n}")

    # Return all peaks 
    return peaks


def get_energy_at_time(peaks: list[AudioPeak], start: float, end: float) -> float:
    """Get the max energy score for a given time range."""
    relevant = [
        p.energy_score
        for p in peaks
        if p.start <= end and p.end >= start
    ]
    return max(relevant) if relevant else 0.0
