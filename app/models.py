from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


class JobStatus(str, Enum):
    PENDING = "pending"
    TRANSCRIBING = "transcribing"
    ANALYZING_AUDIO = "analyzing_audio"
    ANALYZING_SENTIMENT = "analyzing_sentiment"
    TRACKING_FACES = "tracking_faces"
    SCORING = "scoring"
    CUTTING_CLIPS = "cutting_clips"
    ADDING_CAPTIONS = "adding_captions"
    DONE = "done"
    FAILED = "failed"


class WordTimestamp(BaseModel):
    word: str
    start: float
    end: float


class TranscriptSegment(BaseModel):
    id: int
    text: str
    start: float
    end: float
    words: list[WordTimestamp] = []


class AudioPeak(BaseModel):
    start: float
    end: float
    energy_score: float  # 0-1 normalized


class SentimentResult(BaseModel):
    segment_id: int
    start: float
    end: float
    sentiment_score: float  # 0-1
    hook_headline: str
    key_insight: str


class FaceFrame(BaseModel):
    timestamp: float
    x: float
    y: float
    w: float
    h: float
    confidence: float


class MomentScore(BaseModel):
    start: float
    end: float
    viral_score: float
    audio_score: float
    sentiment_score: float
    face_score: float
    transcript_text: str
    hook_headline: str
    key_insight: str
    clip_path: Optional[str] = None
    thumbnail_path: Optional[str] = None


class JobResult(BaseModel):
    job_id: str
    status: JobStatus
    progress: int = 0  # 0-100
    message: str = ""
    video_duration: Optional[float] = None
    clips: list[MomentScore] = []
    error: Optional[str] = None


class UploadResponse(BaseModel):
    job_id: str
    filename: str
    message: str


class ClipRequest(BaseModel):
    job_id: str
    clip_indices: list[int] = Field(default_factory=list)
    add_captions: bool = True
    caption_style: str = "karaoke"  # karaoke | static
    add_hook: bool = True
