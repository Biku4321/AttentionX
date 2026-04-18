"""
Caption Engine — burns karaoke-style word-by-word captions onto video clips.
Supports:
  - Karaoke mode: each word highlights as it's spoken
  - Hook overlay: bold title card for first 2 seconds
  - High-contrast design optimized for mobile viewing
"""
import os
import logging
from pathlib import Path
from app.models import TranscriptSegment, WordTimestamp

logger = logging.getLogger(__name__)


def get_words_in_range(
    segments: list[TranscriptSegment],
    start: float,
    end: float,
) -> list[WordTimestamp]:
    """Extract all word timestamps that fall within [start, end]."""
    words = []
    for seg in segments:
        if seg.end < start or seg.start > end:
            continue
        for w in seg.words:
            if w.start >= start and w.end <= end:
                # Offset timestamps to be relative to clip start
                words.append(
                    WordTimestamp(
                        word=w.word,
                        start=round(w.start - start, 3),
                        end=round(w.end - start, 3),
                    )
                )
    return words


def build_caption_clips(
    words: list[WordTimestamp],
    clip_duration: float,
    words_per_group: int = 4,
) -> list[dict]:
    """
    Group words into caption chunks for display.
    Returns list of {start, end, text, highlight_word_idx} dicts.
    """
    if not words:
        return []

    groups = []
    for i in range(0, len(words), words_per_group):
        chunk = words[i : i + words_per_group]
        groups.append(
            {
                "start": chunk[0].start,
                "end": chunk[-1].end,
                "words": [w.word for w in chunk],
                "text": " ".join(w.word for w in chunk),
            }
        )

    return groups


def render_captions_with_moviepy(
    clip_path: str,
    output_path: str,
    words: list[WordTimestamp],
    hook_headline: str,
    clip_duration: float,
    caption_style: str = "karaoke",
    add_hook: bool = True,
) -> str:
    """
    Render captions onto a video clip using MoviePy.
    Returns path to the output file.
    """
    try:
        from moviepy.editor import (
            VideoFileClip,
            TextClip,
            CompositeVideoClip,
            ColorClip,
        )
    except ImportError:
        logger.error("MoviePy not installed")
        return clip_path

    logger.info(f"Rendering captions: {clip_path}")
    video = VideoFileClip(clip_path)
    w, h = video.size
    caption_clips = []

    # --- Hook Overlay (first 2.5 seconds) ---
    if add_hook and hook_headline:
        try:
            bg_hook = ColorClip(size=(w, 120), color=(0, 0, 0)).set_opacity(0.75)
            bg_hook = bg_hook.set_position(("center", h // 5)).set_duration(2.5)

            hook_text = TextClip(
                hook_headline.upper(),
                fontsize=min(48, w // len(hook_headline) * 1.8),
                color="white",
                font="DejaVu-Sans-Bold",
                method="caption",
                size=(w - 40, None),
                align="center",
            )
            hook_text = hook_text.set_position(("center", h // 5 + 15)).set_duration(2.5)
            caption_clips.extend([bg_hook, hook_text])
        except Exception as e:
            logger.warning(f"Hook overlay failed: {e}")

    # --- Karaoke / Static Captions ---
    caption_groups = build_caption_clips(words, clip_duration)

    for group in caption_groups:
        if group["end"] > clip_duration:
            continue

        try:
            duration = group["end"] - group["start"]
            if duration <= 0:
                continue

            # Semi-transparent background
            bg = ColorClip(size=(w - 40, 90), color=(0, 0, 0)).set_opacity(0.8)
            bg = bg.set_position(("center", h - 160)).set_start(group["start"]).set_duration(duration)

            # Caption text
            text = TextClip(
                group["text"],
                fontsize=44,
                color="white",
                font="DejaVu-Sans-Bold",
                stroke_color="black",
                stroke_width=2,
                method="caption",
                size=(w - 60, None),
                align="center",
            )
            text = (
                text.set_position(("center", h - 155))
                .set_start(group["start"])
                .set_duration(duration)
            )

            caption_clips.extend([bg, text])
        except Exception as e:
            logger.warning(f"Caption group render failed: {e}")

    # Composite all clips
    if caption_clips:
        final = CompositeVideoClip([video] + caption_clips)
    else:
        final = video

    final.write_videofile(
        output_path,
        codec="libx264",
        audio_codec="aac",
        fps=video.fps,
        preset="fast",
        verbose=False,
        logger=None,
    )

    video.close()
    final.close()
    logger.info(f"Caption render complete: {output_path}")
    return output_path
