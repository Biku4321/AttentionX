from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    gemini_api_key: str = ""
    redis_url: str = "redis://localhost:6379/0"
    upload_dir: str = "uploads"
    output_dir: str = "outputs"
    max_upload_mb: int = 500
    whisper_model: str = "base"

    min_clip_duration: int = 20
    max_clip_duration: int = 90
    top_clips_count: int = 5

    weight_audio: float = 0.35
    weight_sentiment: float = 0.45
    weight_face: float = 0.20

    class Config:
        env_file = ".env"
        extra = "ignore"

    def ensure_dirs(self):
        Path(self.upload_dir).mkdir(exist_ok=True)
        Path(self.output_dir).mkdir(exist_ok=True)


settings = Settings()
settings.ensure_dirs()
