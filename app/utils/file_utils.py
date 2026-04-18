import os
import shutil
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def cleanup_job_uploads(job_id: str, upload_dir: str, keep_outputs: bool = True):
    """Delete source video after processing to save disk space."""
    for f in os.listdir(upload_dir):
        if f.startswith(job_id):
            path = os.path.join(upload_dir, f)
            os.remove(path)
            logger.info(f"Cleaned up: {path}")


def get_file_size_mb(path: str) -> float:
    return os.path.getsize(path) / (1024 * 1024)


def ensure_dirs(*dirs):
    for d in dirs:
        Path(d).mkdir(parents=True, exist_ok=True)
