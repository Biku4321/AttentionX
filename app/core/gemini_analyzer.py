"""
Gemini 2.0 Flash integration for:
1. Sentiment / impact scoring of transcript windows
2. Generating viral hook headlines for each clip
3. Extracting the key insight / quote for caption overlay
"""
import google.generativeai as genai
import json
import logging
import re
from app.config import settings
from app.models import SentimentResult
import time

logger = logging.getLogger(__name__)


def configure_gemini():
    genai.configure(api_key=settings.gemini_api_key)
    return genai.GenerativeModel(
        model_name="gemini-2.0-flash",
        generation_config=genai.types.GenerationConfig(
            temperature=0.7,
            max_output_tokens=4096,
        ),
    )


BATCH_ANALYSIS_PROMPT = """You are an expert content strategist and viral video analyst specializing in short-form content (TikTok, Reels, YouTube Shorts).

Analyze the following transcript segments from a long-form educational video/lecture/podcast. For each segment, score its viral potential and generate content hooks.

TRANSCRIPT SEGMENTS (JSON):
{segments_json}

For EACH segment, evaluate:
1. VIRAL SCORE (0.0-1.0): Based on:
   - Emotional impact (surprise, inspiration, controversy, humor)
   - Quotability and shareability
   - Educational value ("golden nugget" moments)
   - Story arc completeness (has a clear point)
   - Audience resonance potential

2. HOOK HEADLINE (max 10 words): A scroll-stopping opener in the style of viral TikTok/Reels content. Make it punchy, provocative, or surprising. Use power words.

3. KEY INSIGHT (max 20 words): The core takeaway someone would remember and share.

Respond ONLY with a valid JSON array (no markdown, no explanation):
[
  {{
    "segment_id": <integer>,
    "sentiment_score": <float 0.0-1.0>,
    "hook_headline": "<string>",
    "key_insight": "<string>"
  }},
  ...
]
"""


def analyze_segments_batch(windows: list[dict]) -> list[SentimentResult]:
    """
    Send transcript windows to Gemini for batch sentiment + hook analysis.
    Handles batching to stay within token limits.
    """
    if not settings.gemini_api_key:
        logger.warning("No Gemini API key set — using fallback scoring")
        return _fallback_scoring(windows)

    model = configure_gemini()
    results = []
    batch_size = 10  # Process 10 windows per API call

    for batch_start in range(0, len(windows), batch_size):
        batch = windows[batch_start : batch_start + batch_size]

        segments_for_prompt = [
            {
                "segment_id": batch_start + i,
                "start": round(w["start"], 1),
                "end": round(w["end"], 1),
                "text": w["text"][:800],  # Truncate very long segments
            }
            for i, w in enumerate(batch)
        ]

        prompt = BATCH_ANALYSIS_PROMPT.format(
            segments_json=json.dumps(segments_for_prompt, indent=2)
        )

        try:
            response = model.generate_content(prompt)
            raw = response.text.strip()

            # Strip markdown code fences if present
            raw = re.sub(r"```json\s*", "", raw)
            raw = re.sub(r"```\s*", "", raw)

            parsed = json.loads(raw)

            for item in parsed:
                idx = item["segment_id"]
                if batch_start + (idx - batch_start) < len(batch):
                    w = batch[idx - batch_start]
                    results.append(
                        SentimentResult(
                            segment_id=idx,
                            start=w["start"],
                            end=w["end"],
                            sentiment_score=float(item.get("sentiment_score", 0.5)),
                            hook_headline=item.get("hook_headline", "Watch this clip"),
                            key_insight=item.get("key_insight", w["text"][:100]),
                        )
                    )
            if batch_start + batch_size < len(windows):
                logger.info("Pausing for 35 seconds to respect Gemini API free tier limits...")
                time.sleep(35)

        except (json.JSONDecodeError, Exception) as e:
            logger.error(f"Gemini batch {batch_start} failed: {e}")
            # Fallback for this batch
            for i, w in enumerate(batch):
                results.append(
                    SentimentResult(
                        segment_id=batch_start + i,
                        start=w["start"],
                        end=w["end"],
                        sentiment_score=0.5,
                        hook_headline="This changed how I think about everything",
                        key_insight=w["text"][:100],
                    )
                )

    return results


def _fallback_scoring(windows: list[dict]) -> list[SentimentResult]:
    """Simple keyword-based scoring when Gemini is unavailable."""
    HIGH_IMPACT_WORDS = {
        "never", "always", "secret", "truth", "mistake", "wrong",
        "change", "transform", "real", "actually", "surprising",
        "shocking", "important", "critical", "key", "essential",
        "best", "worst", "only", "every", "nobody", "everyone",
    }

    results = []
    for i, w in enumerate(windows):
        text_lower = w["text"].lower()
        word_count = len(text_lower.split())
        matches = sum(1 for word in HIGH_IMPACT_WORDS if word in text_lower)
        score = min(0.9, 0.3 + (matches / max(word_count, 1)) * 10)

        results.append(
            SentimentResult(
                segment_id=i,
                start=w["start"],
                end=w["end"],
                sentiment_score=round(score, 3),
                hook_headline="You need to hear this",
                key_insight=w["text"][:120].strip(),
            )
        )
    return results
