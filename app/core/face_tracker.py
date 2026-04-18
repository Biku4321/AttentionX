"""
MediaPipe face detection to compute per-frame face positions.
Falls back to OpenCV Haar cascade automatically if MediaPipe unavailable.
"""
import cv2
import numpy as np
import logging
from app.models import FaceFrame

logger = logging.getLogger(__name__)


def track_faces_in_video(video_path: str, sample_fps: float = 2.0) -> list[FaceFrame]:
    """Uses MediaPipe if available, falls back to OpenCV Haar cascade."""
    try:
        import mediapipe  # noqa: F401
        return _track_with_mediapipe(video_path, sample_fps)
    except (ImportError, ModuleNotFoundError):
        logger.warning("MediaPipe not installed — using OpenCV Haar cascade fallback")
        return _track_with_opencv(video_path, sample_fps)
    except Exception as e:
        logger.warning(f"MediaPipe failed ({e}) — falling back to OpenCV")
        return _track_with_opencv(video_path, sample_fps)


def _track_with_mediapipe(video_path: str, sample_fps: float) -> list[FaceFrame]:
    import mediapipe as mp
    mp_face = mp.solutions.face_detection
    face_detection = mp_face.FaceDetection(model_selection=1, min_detection_confidence=0.5)

    cap = cv2.VideoCapture(video_path)
    video_fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    sample_every = max(1, int(video_fps / sample_fps))
    frames = []
    frame_idx = 0

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        if frame_idx % sample_every == 0:
            timestamp = frame_idx / video_fps
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = face_detection.process(rgb)
            if results.detections:
                best = max(results.detections, key=lambda d: d.score[0])
                bbox = best.location_data.relative_bounding_box
                frames.append(FaceFrame(timestamp=round(timestamp, 3), x=bbox.xmin,
                    y=bbox.ymin, w=bbox.width, h=bbox.height, confidence=round(best.score[0], 3)))
            else:
                frames.append(FaceFrame(timestamp=round(timestamp, 3), x=0.25, y=0.1, w=0.5, h=0.5, confidence=0.0))
        frame_idx += 1

    cap.release()
    face_detection.close()
    logger.info(f"MediaPipe tracked {len(frames)} face frames")
    return frames


def _track_with_opencv(video_path: str, sample_fps: float) -> list[FaceFrame]:
    """Fallback face detection using OpenCV Haar cascade."""
    cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    cap = cv2.VideoCapture(video_path)
    video_fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    sample_every = max(1, int(video_fps / sample_fps))
    frames = []
    frame_idx = 0

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        if frame_idx % sample_every == 0:
            timestamp = frame_idx / video_fps
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            h, w = frame.shape[:2]
            faces = cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(50, 50))
            if len(faces) > 0:
                fx, fy, fw, fh = faces[0]
                frames.append(FaceFrame(timestamp=round(timestamp, 3), x=fx/w, y=fy/h,
                    w=fw/w, h=fh/h, confidence=0.8))
            else:
                frames.append(FaceFrame(timestamp=round(timestamp, 3), x=0.25, y=0.1, w=0.5, h=0.5, confidence=0.0))
        frame_idx += 1

    cap.release()
    logger.info(f"OpenCV tracked {len(frames)} face frames")
    return frames


def compute_crop_params(face_frames: list[FaceFrame], start: float, end: float,
                        source_w: int, source_h: int) -> dict:
    """Compute 9:16 crop rectangle centered on speaker face."""
    relevant = [f for f in face_frames if start <= f.timestamp <= end]
    cx_rel = np.median([f.x + f.w / 2 for f in relevant]) if relevant else 0.5

    crop_h = source_h
    crop_w = int(crop_h * 9 / 16)
    if crop_w > source_w:
        crop_w = source_w
        crop_h = int(crop_w * 16 / 9)

    cx_px = int(cx_rel * source_w)
    crop_x = max(0, min(cx_px - crop_w // 2, source_w - crop_w))
    crop_y = max(0, (source_h - crop_h) // 2)
    face_confidence = float(np.mean([f.confidence for f in relevant])) if relevant else 0.0

    return {"x": crop_x, "y": crop_y, "width": crop_w, "height": crop_h,
            "face_confidence": round(face_confidence, 3)}
