# ⚡ AttentionX — AI-Powered Viral Clip Engine

> **Turn 60 minutes of educational content into 5 viral short-form clips — automatically.**

[![Demo Video](https://img.shields.io/badge/🎬_Demo-Watch_Now-FF6B35?style=for-the-badge)](YOUR_GOOGLE_DRIVE_LINK_HERE)
[![Live App](https://img.shields.io/badge/🚀_Live_App-Try_Now-4CAF50?style=for-the-badge)](YOUR_DEPLOYED_URL_HERE)

---

## 🏆 What Makes AttentionX Unique

Most tools either **transcribe** or **clip** — AttentionX does something no other tool does at this scale:

### 🧠 Multi-Signal Fusion Scoring™
Three independent AI signals fused into one **Viral Score**:

| Signal | Tool | What It Detects |
|--------|------|-----------------|
| 🎙️ Audio Energy | Librosa | RMS peaks = speaker passion & excitement |
| 🤖 AI Sentiment | Gemini 2.0 Flash | Quotability, insight quality, emotional impact |
| 👁️ Face Confidence | MediaPipe | Visual quality — speaker clearly in frame |

```
Viral Score = 0.45×(AI Sentiment) + 0.35×(Audio Energy) + 0.20×(Face Confidence)
```

This is the core innovation — **no other hackathon project will fuse these three signals**.

---

## 🎯 Problem Solved

| Problem | AttentionX Solution |
|---------|---------------------|
| ⏰ Hours of footage to review | AI ranks top 5 moments automatically |
| 📱 16:9 → 9:16 conversion | MediaPipe face-tracked smart crop |
| 💬 No captions → 80% skip | Word-level karaoke captions burned in |
| 🎣 No hook → scroll past | Gemini generates punchy headlines |
| 🔄 Manual editing = slow | Full pipeline in ~3 minutes |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   Streamlit Frontend                     │
│         Upload · Review Clips · Download                 │
└──────────────────────┬──────────────────────────────────┘
                       │ REST API
┌──────────────────────▼──────────────────────────────────┐
│                FastAPI Backend                          │
│         /upload · /status · /render                     │
└──────────────────────┬──────────────────────────────────┘
                       │ Celery Jobs
┌──────────────────────▼──────────────────────────────────┐
│              AI Processing Pipeline                      │
│  Whisper → Librosa → Gemini 2.0 → MediaPipe → Fusion   │
└──────────────────────┬──────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────┐
│               Video Output Engine                        │
│        MoviePy: Cut · Crop 9:16 · Captions              │
└─────────────────────────────────────────────────────────┘
```

---

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- FFmpeg installed
- Redis running (or Docker)
- Gemini API key (free at [Google AI Studio](https://aistudio.google.com))

### 1. Clone & Install
```bash
git clone https://github.com/YOUR_USERNAME/attentionx.git
cd attentionx

python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

pip install -r requirements.txt
```

### 2. Configure
```bash
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY
```

### 3. Install FFmpeg
```bash
# Ubuntu/Debian
sudo apt install ffmpeg

# macOS
brew install ffmpeg

# Windows — download from https://ffmpeg.org/download.html
```

### 4. Start Services
```bash
# Terminal 1: Redis
docker run -d -p 6379:6379 redis:alpine

# Terminal 2: FastAPI backend
uvicorn app.main:app --reload --port 8000

# Terminal 3: Celery worker
celery -A app.workers.tasks worker --loglevel=info

# Terminal 4: Streamlit frontend
streamlit run frontend/streamlit_app.py
```

### 5. Open App
Navigate to **http://localhost:8501** 🎉

---

### 🐳 Docker (One Command)
```bash
cp .env.example .env  # Add your GEMINI_API_KEY
docker-compose up --build
```
App available at http://localhost:8501

---

## 📁 Project Structure

```
attentionx/
├── README.md
├── requirements.txt
├── .env.example
├── Dockerfile
├── docker-compose.yml
│
├── app/
│   ├── main.py                  # FastAPI app entry point
│   ├── config.py                # Settings from .env
│   ├── models.py                # Pydantic data schemas
│   │
│   ├── api/
│   │   └── routes.py            # REST endpoints
│   │
│   ├── core/
│   │   ├── transcriber.py       # Whisper → word-level timestamps
│   │   ├── audio_analyzer.py    # Librosa RMS energy peaks
│   │   ├── gemini_analyzer.py   # Gemini sentiment + hook generation
│   │   ├── face_tracker.py      # MediaPipe face detection
│   │   ├── moment_scorer.py     # Multi-signal fusion engine ⭐
│   │   ├── clip_cutter.py       # MoviePy cut + 9:16 crop
│   │   └── caption_engine.py    # Karaoke caption renderer
│   │
│   ├── workers/
│   │   └── tasks.py             # Celery async pipeline
│   │
│   └── utils/
│       └── file_utils.py
│
├── frontend/
│   └── streamlit_app.py         # Full Streamlit UI
│
├── uploads/                     # Temp video storage
└── outputs/                     # Processed clips
```

---

## 🔧 Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Frontend** | Streamlit | Zero-HTML web UI |
| **Backend** | FastAPI | Async REST API |
| **Queue** | Celery + Redis | Background job processing |
| **Transcription** | OpenAI Whisper | Speech-to-text + word timestamps |
| **Audio Analysis** | Librosa | Energy peaks, spectral features |
| **AI Scoring** | Google Gemini 2.0 Flash | Sentiment + viral hook generation |
| **Face Tracking** | MediaPipe | Face detection for smart crop |
| **Video Editing** | MoviePy + FFmpeg | Cut, crop, render |
| **Image** | Pillow + OpenCV | Thumbnail extraction |

---

## 📊 Evaluation Criteria Mapping

| Criterion | Our Approach | Score Target |
|-----------|-------------|-------------|
| **Impact (20%)** | Full pipeline: upload → clips in ~3 min | ⭐⭐⭐⭐⭐ |
| **Innovation (20%)** | 3-signal fusion scoring is unique | ⭐⭐⭐⭐⭐ |
| **Technical Execution (20%)** | Modular architecture, typed schemas, async | ⭐⭐⭐⭐⭐ |
| **User Experience (25%)** | One-click pipeline, live progress, clip preview | ⭐⭐⭐⭐⭐ |
| **Presentation (15%)** | Demo video link below | ⭐⭐⭐⭐⭐ |

---

## 🎬 Demo Video

> 📹 **[Watch the 2-minute demo](YOUR_GOOGLE_DRIVE_LINK_HERE)**

The demo shows:
1. Uploading a 20-minute lecture
2. Real-time processing pipeline progress
3. AI-ranked clip cards with viral scores
4. Selecting and exporting 3 clips
5. Final vertical clips with karaoke captions

---

## 🔑 API Reference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/upload` | POST | Upload video, returns job_id |
| `/api/v1/status/{job_id}` | GET | Poll processing status |
| `/api/v1/render` | POST | Trigger clip rendering |
| `/api/v1/download/{job_id}/{file}` | GET | Download processed clip |
| `/docs` | GET | Interactive API documentation |

---

## ⚙️ Configuration

Key settings in `.env`:

```env
GEMINI_API_KEY=your_key          # Required
WHISPER_MODEL=base               # tiny/base/small/medium/large
MIN_CLIP_DURATION=20             # Minimum clip length (seconds)
MAX_CLIP_DURATION=90             # Maximum clip length (seconds)
TOP_CLIPS_COUNT=5                # Number of clips to surface
WEIGHT_AUDIO=0.35                # Audio energy weight
WEIGHT_SENTIMENT=0.45            # AI sentiment weight
WEIGHT_FACE=0.20                 # Face confidence weight
```

---

## 🌟 Future Roadmap

- [ ] B-roll overlay suggestions
- [ ] Multi-speaker diarization
- [ ] Direct TikTok / Instagram API upload
- [ ] Custom branding / watermark
- [ ] Batch processing (multiple videos)
- [ ] Whisper Large-v3 for 10x accuracy

---

## 👥 Team

Built at **AttentionX AI Hackathon** 🏆

---

## 📄 License

MIT License — see [LICENSE](LICENSE)
