"""
AttentionX — Streamlit Frontend
A beautiful, one-click interface for AI-powered video repurposing.
"""
import streamlit as st
import requests
import time
import os
import json
from pathlib import Path

# ── Page Config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="AttentionX — Viral Clip Engine",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

API_BASE = os.getenv("API_BASE_URL", "http://localhost:8000/api/v1")

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

    .hero-title {
        font-size: 3.2rem; font-weight: 800; letter-spacing: -1px;
        background: linear-gradient(135deg, #FF6B35, #F7C59F, #EFEFD0);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        line-height: 1.1; margin-bottom: 0.3rem;
    }
    .hero-sub {
        font-size: 1.1rem; color: #888; margin-bottom: 2rem;
    }
    .metric-card {
        background: #1a1a2e; border: 1px solid #2a2a4a;
        border-radius: 12px; padding: 1.2rem; text-align: center;
    }
    .metric-num { font-size: 2rem; font-weight: 700; color: #FF6B35; }
    .metric-label { font-size: 0.8rem; color: #888; margin-top: 0.2rem; }

    .clip-card {
        background: linear-gradient(135deg, #1a1a2e, #16213e);
        border: 1px solid #2a2a4a; border-radius: 16px;
        padding: 1.5rem; margin-bottom: 1.2rem;
        transition: border-color 0.2s;
    }
    .clip-card:hover { border-color: #FF6B35; }
    .clip-card.selected { border-color: #FF6B35; background: linear-gradient(135deg, #2a1a0e, #1e2a3e); }

    .score-badge {
        display: inline-block; padding: 4px 12px; border-radius: 20px;
        font-size: 0.75rem; font-weight: 600; letter-spacing: 0.5px;
    }
    .score-high { background: #FF6B3520; color: #FF6B35; border: 1px solid #FF6B3560; }
    .score-med  { background: #F7C59F20; color: #F7C59F; border: 1px solid #F7C59F60; }
    .score-low  { background: #88888820; color: #aaa;    border: 1px solid #88888860; }

    .hook-headline {
        font-size: 1.3rem; font-weight: 700; color: #fff;
        border-left: 3px solid #FF6B35; padding-left: 0.8rem;
        margin: 0.8rem 0;
    }
    .insight-text {
        font-size: 0.9rem; color: #aaa; font-style: italic;
        background: #ffffff08; border-radius: 8px; padding: 0.7rem 1rem;
    }

    .step-indicator {
        display: flex; align-items: center; gap: 0.5rem;
        font-size: 0.85rem; color: #888; margin-bottom: 0.5rem;
    }
    .step-dot { width: 8px; height: 8px; border-radius: 50%; }
    .step-dot.active { background: #FF6B35; }
    .step-dot.done   { background: #4caf50; }
    .step-dot.pending { background: #444; }

    div[data-testid="stProgress"] > div > div { background: #FF6B35 !important; }

    .stButton > button {
        background: linear-gradient(135deg, #FF6B35, #e05a28) !important;
        color: white !important; border: none !important;
        font-weight: 600 !important; border-radius: 10px !important;
        padding: 0.6rem 1.5rem !important;
        transition: transform 0.1s !important;
    }
    .stButton > button:hover { transform: translateY(-1px) !important; }

    .upload-zone {
        border: 2px dashed #FF6B3560; border-radius: 16px;
        padding: 3rem; text-align: center; background: #FF6B3508;
        margin: 1rem 0;
    }

    .signal-bar-container { margin: 0.4rem 0; }
    .signal-label { font-size: 0.75rem; color: #888; margin-bottom: 2px; }
    .signal-bar-bg { background: #2a2a3a; border-radius: 4px; height: 6px; width: 100%; }
    .signal-bar-fill { height: 6px; border-radius: 4px; }
    </style>
    """,
    unsafe_allow_html=True,
)


# ── Helpers ───────────────────────────────────────────────────────────────────
def api_upload(file_bytes, filename) -> dict | None:
    try:
        r = requests.post(
            f"{API_BASE}/upload",
            files={"file": (filename, file_bytes, "video/mp4")},
            timeout=120,
        )
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"Upload failed: {e}")
        return None


def api_status(job_id: str) -> dict | None:
    try:
        r = requests.get(f"{API_BASE}/status/{job_id}", timeout=10)
        if r.status_code == 200:
            return r.json()
        return None
    except Exception:
        return None


def api_render(job_id: str, clip_indices: list[int], add_captions: bool, add_hook: bool):
    try:
        r = requests.post(
            f"{API_BASE}/render",
            json={
                "job_id": job_id,
                "clip_indices": clip_indices,
                "add_captions": add_captions,
                "add_hook": add_hook,
            },
            timeout=30,
        )
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"Render request failed: {e}")
        return None


def score_color_class(score: float) -> str:
    if score >= 0.7:
        return "score-high"
    elif score >= 0.45:
        return "score-med"
    return "score-low"


def score_emoji(score: float) -> str:
    if score >= 0.75:
        return "🔥"
    elif score >= 0.55:
        return "⚡"
    elif score >= 0.4:
        return "✨"
    return "📌"


def format_duration(seconds: float) -> str:
    m = int(seconds // 60)
    s = int(seconds % 60)
    return f"{m}:{s:02d}"


def signal_bar_html(label: str, value: float, color: str) -> str:
    pct = int(value * 100)
    return f"""
    <div class="signal-bar-container">
        <div class="signal-label">{label} — {pct}%</div>
        <div class="signal-bar-bg">
            <div class="signal-bar-fill" style="width:{pct}%;background:{color}"></div>
        </div>
    </div>
    """


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚡ AttentionX")
    st.markdown("*Turn 60 minutes into 60 seconds*")
    st.divider()

    st.markdown("### ⚙️ Export Settings")
    add_captions = st.toggle("Karaoke captions", value=True)
    add_hook = st.toggle("Hook headline overlay", value=True)
    vertical_crop = st.toggle("Smart 9:16 crop", value=True)

    st.divider()
    st.markdown("### 📊 Scoring Weights")
    w_sent = st.slider("AI Sentiment", 0.1, 0.8, 0.45, 0.05)
    w_audio = st.slider("Audio Energy", 0.1, 0.8, 0.35, 0.05)
    w_face = st.slider("Face Confidence", 0.0, 0.5, 0.20, 0.05)
    total_w = w_sent + w_audio + w_face
    if abs(total_w - 1.0) > 0.05:
        st.warning(f"Weights sum to {total_w:.2f} (ideally 1.0)")

    st.divider()
    st.markdown("### ℹ️ Pipeline")
    st.markdown("""
1. 🎙️ **Whisper** transcribes audio
2. 📈 **Librosa** finds energy peaks
3. 🤖 **Gemini 2.0** scores moments
4. 👁️ **MediaPipe** tracks face
5. 🎬 **Fusion** ranks clips
6. ✂️ **MoviePy** cuts & crops
7. 💬 **Captions** added
    """)


# ── Main App ──────────────────────────────────────────────────────────────────
st.markdown('<div class="hero-title">⚡ AttentionX</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="hero-sub">Drop a lecture. Get 5 viral clips. Powered by Gemini + Whisper + MediaPipe.</div>',
    unsafe_allow_html=True,
)

# ── Stats Row ──────────────────────────────────────────────────────────────────
col1, col2, col3, col4 = st.columns(4)
for col, num, label in [
    (col1, "3 min", "Avg Processing Time"),
    (col2, "5", "Clips Generated"),
    (col3, "9:16", "Vertical Format"),
    (col4, "3x", "Signals Fused"),
]:
    with col:
        st.markdown(
            f'<div class="metric-card"><div class="metric-num">{num}</div>'
            f'<div class="metric-label">{label}</div></div>',
            unsafe_allow_html=True,
        )

st.markdown("---")

# ── Upload Section ────────────────────────────────────────────────────────────
st.markdown("### 📤 Upload Your Video")

uploaded_file = st.file_uploader(
    "Drop your video here",
    type=["mp4", "mov", "avi", "mkv", "webm"],
    label_visibility="collapsed",
)

if uploaded_file:
    file_size_mb = len(uploaded_file.getvalue()) / (1024 * 1024)
    st.success(
        f"✅ **{uploaded_file.name}** — {file_size_mb:.1f} MB uploaded"
    )

    col_go, col_info = st.columns([1, 3])
    with col_go:
        start_btn = st.button("🚀 Analyze & Find Viral Clips", use_container_width=True)
    with col_info:
        st.caption(
            "AI will transcribe, detect passion peaks, score moments, and find your best clips automatically."
        )

    # ── Processing ─────────────────────────────────────────────────────────────
    if start_btn or st.session_state.get("job_id"):
        if start_btn:
            with st.spinner("Uploading video..."):
                resp = api_upload(uploaded_file.getvalue(), uploaded_file.name)
                if resp:
                    st.session_state["job_id"] = resp["job_id"]
                    st.session_state["clips"] = []
                    st.session_state["render_done"] = False
                else:
                    st.stop()

        job_id = st.session_state.get("job_id")

        # ── Progress Tracking ───────────────────────────────────────────────────
        if job_id and not st.session_state.get("analysis_done"):
            st.markdown("### 🔄 Processing Pipeline")

            STEPS = [
                ("transcribing", "🎙️ Transcribing with Whisper"),
                ("analyzing_audio", "📈 Analyzing audio energy"),
                ("analyzing_sentiment", "🤖 Gemini AI scoring moments"),
                ("tracking_faces", "👁️ Tracking speaker face"),
                ("scoring", "🏆 Fusing signals & ranking"),
                ("done", "✅ Complete!"),
            ]

            progress_bar = st.progress(0)
            status_text = st.empty()
            step_cols = st.columns(len(STEPS))

            poll_placeholder = st.empty()

            for _ in range(300):  # poll for up to 5 minutes
                result = api_status(job_id)
                if not result:
                    time.sleep(2)
                    continue

                status = result.get("status", "pending")
                progress = result.get("progress", 0)
                message = result.get("message", "")

                progress_bar.progress(progress / 100)
                status_text.markdown(f"**{message}**")

                # Step indicator dots
                for i, (step_key, step_label) in enumerate(STEPS):
                    with step_cols[i]:
                        done = progress >= (i + 1) * (100 // len(STEPS))
                        active = step_key in status
                        icon = "✅" if done else ("⏳" if active else "⬜")
                        st.caption(f"{icon} {step_label.split(' ', 1)[1]}")

                if status == "done":
                    st.session_state["analysis_done"] = True
                    st.session_state["clips"] = result.get("clips", [])
                    st.session_state["all_moments"] = result.get("all_moments", [])
                    st.session_state["video_duration"] = result.get("video_duration", 0)
                    st.balloons()
                    st.rerun()
                    break

                elif status == "failed":
                    st.error(f"❌ Processing failed: {result.get('error', 'Unknown error')}")
                    if st.button("🔄 Try Again"):
                        for k in ["job_id", "analysis_done", "clips", "render_done"]:
                            st.session_state.pop(k, None)
                        st.rerun()
                    break

                time.sleep(3)

        # ── Results: Clip Selection ─────────────────────────────────────────────
        if st.session_state.get("analysis_done") and not st.session_state.get("render_done"):
            clips = st.session_state.get("clips", [])
            video_duration = st.session_state.get("video_duration", 0)

            st.markdown(
                f"### 🎯 AI Found **{len(clips)} High-Impact Moments**"
                f" in your {format_duration(video_duration)} video"
            )
            st.caption("Review and select which clips to export. AI ranks by viral potential.")

            # Select all / none
            col_all, col_none, col_count = st.columns([1, 1, 4])
            with col_all:
                if st.button("✅ Select All"):
                    st.session_state["selected_clips"] = list(range(len(clips)))
            with col_none:
                if st.button("⬜ Select None"):
                    st.session_state["selected_clips"] = []

            if "selected_clips" not in st.session_state:
                st.session_state["selected_clips"] = list(range(min(3, len(clips))))

            # Clip cards
            for i, clip in enumerate(clips):
                score = clip.get("viral_score", 0)
                hook = clip.get("hook_headline", "Watch this clip")
                insight = clip.get("key_insight", "")
                start = clip.get("start", 0)
                end = clip.get("end", 0)
                audio_s = clip.get("audio_score", 0)
                sent_s = clip.get("sentiment_score", 0)
                face_s = clip.get("face_score", 0)
                dur = end - start

                is_selected = i in st.session_state["selected_clips"]
                card_class = "clip-card selected" if is_selected else "clip-card"

                st.markdown(
                    f"""
                    <div class="{card_class}">
                        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.5rem">
                            <span style="color:#888;font-size:0.85rem">
                                Clip #{i+1} &nbsp;·&nbsp; {format_duration(start)} → {format_duration(end)}
                                &nbsp;·&nbsp; {format_duration(dur)}
                            </span>
                            <span class="score-badge {score_color_class(score)}">
                                {score_emoji(score)} Viral Score: {score:.0%}
                            </span>
                        </div>
                        <div class="hook-headline">"{hook}"</div>
                        <div class="insight-text">{insight}</div>
                        {signal_bar_html("AI Sentiment", sent_s, "#FF6B35")}
                        {signal_bar_html("Audio Energy", audio_s, "#F7C59F")}
                        {signal_bar_html("Face Confidence", face_s, "#4CAF50")}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                toggle_col, _ = st.columns([1, 5])
                with toggle_col:
                    checked = st.checkbox(
                        f"Export clip #{i+1}",
                        value=is_selected,
                        key=f"clip_check_{i}",
                    )
                    if checked and i not in st.session_state["selected_clips"]:
                        st.session_state["selected_clips"].append(i)
                    elif not checked and i in st.session_state["selected_clips"]:
                        st.session_state["selected_clips"].remove(i)

            # Export button
            selected = st.session_state.get("selected_clips", [])
            st.markdown("---")
            st.markdown(f"**{len(selected)} clip(s) selected for export**")

            col_exp, col_settings = st.columns([1, 3])
            with col_exp:
                export_btn = st.button(
                    f"🎬 Export {len(selected)} Clip(s)",
                    disabled=len(selected) == 0,
                    use_container_width=True,
                )
            with col_settings:
                st.caption(
                    f"{'✅' if add_captions else '❌'} Karaoke captions &nbsp;·&nbsp; "
                    f"{'✅' if add_hook else '❌'} Hook overlay &nbsp;·&nbsp; "
                    f"{'✅' if vertical_crop else '❌'} 9:16 crop"
                )

            if export_btn and selected:
                with st.spinner(f"Rendering {len(selected)} clips with captions..."):
                    api_render(
                        st.session_state["job_id"],
                        selected,
                        add_captions,
                        add_hook,
                    )
                    # Poll render status
                    for _ in range(120):
                        time.sleep(4)
                        result = api_status(st.session_state["job_id"])
                        if result and result.get("rendered_clips"):
                            st.session_state["rendered_clips"] = result["rendered_clips"]
                            st.session_state["render_done"] = True
                            st.rerun()
                            break
                    else:
                        st.error("Rendering timed out. Please check server logs.")

        # ── Download Section ────────────────────────────────────────────────────
        if st.session_state.get("render_done"):
            rendered = st.session_state.get("rendered_clips", [])
            st.markdown(f"### 🎉 {len(rendered)} Clips Ready to Download!")
            st.success(
                "Your clips are vertical (9:16), captioned, and ready for TikTok, Reels & Shorts!"
            )

            for i, clip in enumerate(rendered):
                clip_file = clip.get("clip_path", "")
                hook = clip.get("hook_headline", f"Clip {i+1}")
                score = clip.get("viral_score", 0)
                start = clip.get("start", 0)
                end = clip.get("end", 0)

                with st.container():
                    col_info2, col_dl = st.columns([3, 1])
                    with col_info2:
                        st.markdown(f"**{score_emoji(score)} {hook}**")
                        st.caption(
                            f"{format_duration(start)} → {format_duration(end)} · "
                            f"Viral Score: {score:.0%}"
                        )
                    with col_dl:
                        if clip_file:
                            dl_url = f"{API_BASE}/download/{job_id}/{clip_file}"
                            st.link_button(f"⬇️ Download Clip {i+1}", dl_url, use_container_width=True)

            st.divider()
            col_new, _ = st.columns([1, 3])
            with col_new:
                if st.button("🔄 Process Another Video"):
                    for k in list(st.session_state.keys()):
                        del st.session_state[k]
                    st.rerun()

# ── Empty state ────────────────────────────────────────────────────────────────
else:
    st.markdown(
        """
        <div class="upload-zone">
            <div style="font-size:3rem">🎬</div>
            <div style="font-size:1.2rem;font-weight:600;color:#ccc;margin:0.5rem 0">
                Drop your lecture, podcast, or workshop video here
            </div>
            <div style="color:#666;font-size:0.9rem">
                Supports MP4, MOV, AVI, MKV, WebM · Up to 500MB
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("### 🚀 How It Works")
    col1, col2, col3, col4 = st.columns(4)
    steps = [
        ("1️⃣", "Upload Video", "Any long-form video up to 500MB"),
        ("2️⃣", "AI Analysis", "3 signals fused: audio, sentiment, face"),
        ("3️⃣", "Review Clips", "Browse AI-ranked moments, select keepers"),
        ("4️⃣", "Export & Share", "Get vertical clips with karaoke captions"),
    ]
    for col, (icon, title, desc) in zip([col1, col2, col3, col4], steps):
        with col:
            st.markdown(
                f"""
                <div style="text-align:center;padding:1.2rem;background:#1a1a2e;
                border-radius:12px;border:1px solid #2a2a4a">
                    <div style="font-size:2rem">{icon}</div>
                    <div style="font-weight:600;color:#fff;margin:0.5rem 0">{title}</div>
                    <div style="font-size:0.82rem;color:#888">{desc}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
