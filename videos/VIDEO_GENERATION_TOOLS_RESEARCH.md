# Video Generation Tools Research for SAM Video Production

## Phase 1: Visual-Only Video Generation (No Audio)
## Phase 2: Videos with Natural Voice Audio

---

## LOCAL COMPUTE (ASUS GX10 - Assumed RTX 3080/4080/4090 class GPU)

### 1. Manim (Mathematical Animation Engine) - **TOP RECOMMENDATION**
- **Type**: Python library for programmatic animations
- **License**: MIT (free, open source)
- **Local**: Runs entirely local, GPU accelerated via Cairo/FFmpeg
- **Strengths**: 
  - Perfect for diagrams, flowcharts, tables, mathematical concepts
  - Programmatic = version controllable, reproducible
  - Excellent for "chain" animations, table reveals, state machines
  - Used by 3Blue1Brown, great for technical content
- **SAM Fit**: Perfect for the chain diagram, normalization state machine, reconciliation flow, rights algebra
- **Learning Curve**: Medium (Python required)
- **Output**: MP4, GIF, PNG sequences
- **GPU**: Uses Cairo (CPU) but can use OpenGL backend for GPU acceleration

```bash
pip install manim
# or for GPU: pip install manim[opengl]
```

### 2. MoviePy - **VIDEO EDITING/COMPOSITING**
- **Type**: Python video editing library
- **License**: MIT
- **Local**: Pure Python + FFmpeg
- **Strengths**:
  - Composite clips, add text overlays, transitions
  - Concatenate Manim outputs with screenshots, screen recordings
  - Subtitle/caption support
- **SAM Fit**: Assemble final videos from Manim scenes + static assets
- **Dependencies**: FFmpeg (system)

```bash
pip install moviepy
```

### 3. Remotion - **REACT-BASED VIDEO (If You Know React)**
- **Type**: React framework for programmatic video
- **License**: MIT (free for individuals/small teams)
- **Local**: Node.js + FFmpeg + Chrome headless
- **Strengths**:
  - Write videos in React/TypeScript
  - Great for data-driven animations, tables, charts
  - Web tech stack = familiar for frontend devs
- **SAM Fit**: Good if you prefer React over Python
- **GPU**: Chrome headless can use GPU

```bash
npx create-video my-sam-videos
```

### 4. Stable Video Diffusion / AnimateDiff - **AI VIDEO GENERATION**
- **Type**: Diffusion models for video generation
- **License**: Various (mostly open weights)
- **Local**: Requires 8GB+ VRAM (12GB+ recommended)
- **Models**: SVD, SVD-XT, AnimateDiff, Hotshot-XL
- **Strengths**: Generate video from text/image
- **Weaknesses**: Hard to control precise technical diagrams; better for b-roll
- **SAM Fit**: Limited - good for intro/outro animations, not technical content
- **Tools**: ComfyUI, Automatic1111, Diffusers CLI

### 5. OBS Studio + Python Scripting - **SCREEN RECORDING**
- **Type**: Professional screen recording
- **License**: GPL
- **Local**: Native app
- **Strengths**: Record ServiceNow instance demos, live walkthroughs
- **SAM Fit**: Lab flow videos, "show me in ServiceNow" segments
- **Automation**: `obs-websocket` + Python for scripted recordings

---

## CLOUD COMPUTE (Free Tiers / Paid)

### 1. GitHub Actions (Free Tier: 2000 min/mo public, 120 min/mo private)
- **Use Case**: Render Manim/MoviePy videos in CI
- **GPU**: No GPU runners on free tier (self-hosted only)
- **Cost**: Free for public repos
- **Setup**: `.github/workflows/render-videos.yml`

### 2. Google Colab (Free T4 GPU, Pro = A100)
- **Use Case**: Run Manim, Stable Video Diffusion, TTS
- **Free**: T4 GPU, 12hr sessions
- **Pro**: $10/mo for A100, background execution
- **SAM Fit**: Heavy rendering, AI video/audio generation

### 3. Replicate / Fal.ai / RunPod (Pay-per-second GPU)
- **Models**: SVD, AnimateDiff, Whisper, XTTS, Bark, Piper
- **Cost**: ~$0.10-0.50/hr for consumer GPUs
- **API**: Simple HTTP API
- **SAM Fit**: Batch render, TTS generation

### 4. Hugging Face Spaces (Free CPU, Paid GPU)
- **Use Case**: Host video generation demos, TTS endpoints
- **Free**: CPU only
- **GPU**: $0.60/hr (T4) to $3.15/hr (A100)

### 5. ElevenLabs API (Free Tier: 10k chars/mo)
- **Best Natural Voices**: Industry leader
- **Free**: 10,000 characters/month (~10 min audio)
- **Paid**: $5/mo for 30k, $22/mo for 100k
- **API**: Simple REST
- **Voices**: 100+ pre-made, voice cloning

### 6. OpenAI TTS API (Pay-per-use)
- **Voices**: alloy, echo, fable, onyx, nova, shimmer
- **Cost**: $15/1M chars (standard), $30/1M (HD)
- **Quality**: Very natural, good pacing
- **Latency**: Low (streaming available)

### 7. Coqui TTS / XTTS v2 (Local, Open Source)
- **License**: Coqui Public Model License
- **Local**: Runs on GPU (6GB+ VRAM for XTTS)
- **Quality**: Good, multilingual, voice cloning
- **Models**: XTTS v2, VITS, Tacotron2
- **API**: Python library, HTTP server option

### 8. Piper TTS (Local, Fast, Lightweight)
- **License**: MIT
- **Local**: CPU or GPU, very fast
- **Quality**: Good for English, 40+ languages
- **Voices**: 100+ pre-trained
- **Size**: ~50MB per voice
- **Best for**: Local-first, offline, fast iteration

### 9. Bark (Suno) / AudioLM-style (Local)
- **License**: MIT
- **Local**: GPU recommended
- **Quality**: Very expressive, non-verbal sounds
- **Weakness**: Slower, less consistent

---

## RECOMMENDED STACK FOR THIS PROJECT

### Phase 1 (Visual Only) - LOCAL FIRST
```
┌─────────────────────────────────────────────────────────────┐
│  MANIM (Core animations: diagrams, tables, state machines) │
│  MOVIE PY (Compositing: combine scenes, add captions)      │
│  OBS STUDIO (Screen recording: ServiceNow demos)           │
│  FFMPEG (Final encoding, format conversion)                │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
                   MP4 videos (no audio)
```

### Phase 2 (With Audio) - HYBRID
```
Phase 1 Outputs + TTS Audio
                            │
              ┌─────────────┴─────────────┐
              ▼                           ▼
     LOCAL (Piper/Coqui)           CLOUD (ElevenLabs/OpenAI)
     - Free, unlimited             - Best quality
     - Good quality                - Voice cloning
     - Offline                     - 10k free chars/mo
              │                           │
              └─────────────┬─────────────┘
                            ▼
                   MOVIE PY (Merge video + audio)
                            │
                            ▼
                   Final MP4 with narration
```

---

## SPECIFIC SAM VIDEO MAPPING TO TOOLS

| Video Concept | Primary Tool | Why |
|---------------|--------------|-----|
| Chain Diagram Animation | Manim | Programmatic node/edge animation |
| Four Gates Checklist | Manim + MoviePy | Table reveal + checkmarks |
| Normalization State Machine | Manim | State transition diagram |
| Reconciliation 3-Tier Flow | Manim | Sankey/flow diagram |
| Rights Algebra | Manim | Equation build-up animation |
| Key Tables Reference | MoviePy | Static table with highlights |
| Top Traps | Manim + MoviePy | Before/after comparison |
| Publisher Traps | MoviePy | Card grid with logos |
| Lab Flow | OBS + MoviePy | Screen recording + annotations |
| CIS-SAM Exam Map | Manim | Pie chart + topic list |

---

## QUICK START COMMANDS

### Install Local Stack (Ubuntu/WSL2/Linux)
```bash
# System deps
sudo apt update && sudo apt install -y ffmpeg libcairo2-dev libpango1.0-dev \
  pkg-config python3-dev build-essential

# Python env
python3 -m venv sam-video-env
source sam-video-env/bin/activate

# Core packages
pip install manim moviepy pillow numpy

# Optional: OpenGL backend for Manim (GPU)
pip install manim[opengl]

# TTS (Phase 2)
pip install piper-tts  # or coqui-tts for XTTS
```

### Test Manim Install
```bash
manim --version
# Should output: Manim Community v0.18.x

# Quick test
manim -pql -c "from manim import *; class Test(Scene): def construct(self): self.play(Write(Text('SAM Videos Ready!')))"
```

### Render Pipeline Script Template
```python
# render_sam_videos.py
from manim import *
from moviepy.editor import *
import os

OUTPUT_DIR = "videos/output"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 1. Render Manim scenes
# manim -pqh scenes/chain_diagram.py ChainDiagram
# manim -pqh scenes/normalization_states.py NormalizationStates
# ... etc

# 2. Composite with MoviePy
clips = [
    VideoFileClip("media/videos/chain_diagram/1080p60/ChainDiagram.mp4"),
    VideoFileClip("media/videos/normalization_states/1080p60/NormalizationStates.mp4"),
    # ...
]

final = concatenate_videoclips(clips, method="compose")
final.write_videofile(f"{OUTPUT_DIR}/sam_masterclass_phase1.mp4", 
                      codec="libx264", audio_codec="aac", fps=30)
```

---

## FREE TIER BUDGET ESTIMATE (Monthly)

| Resource | Free Tier | Paid Upgrade | Est. Monthly Cost |
|----------|-----------|--------------|-------------------|
| Local GPU (ASUS GX10) | Unlimited | - | $0 (electricity only) |
| GitHub Actions | 2000 min | - | $0 (public repo) |
| Google Colab | T4 GPU | Pro $10 | $0-10 |
| ElevenLabs | 10k chars | $5-22 | $0-22 |
| OpenAI TTS | - | Pay/use | ~$2-5 |
| Replicate/RunPod | - | Pay/sec | ~$5-15 |
| **Total (Phase 1)** | | | **$0** |
| **Total (Phase 2)** | | | **$0-40** |

---

## NEXT STEPS

1. **Set up local environment** (Manim + MoviePy + FFmpeg)
2. **Create Manim scenes** for each core concept (start with Chain Diagram)
3. **Test render pipeline** end-to-end
4. **Phase 1**: Produce 8 visual-only videos
5. **Phase 2**: Add TTS narration (start with Piper local, upgrade to ElevenLabs if needed)
6. **Publish**: YouTube, GitHub Pages, or internal training portal

---

## ALTERNATIVE: NO-CODE / LOW-CODE OPTIONS

If Python is not preferred:

| Tool | Type | Cost | Best For |
|------|------|------|----------|
| Canva | Web video editor | Free tier | Simple slides, animations |
| CapCut | Desktop/Mobile | Free | Quick edits, captions |
| DaVinci Resolve | Desktop | Free | Professional editing |
| Loom | Screen record | Free tier | Walkthroughs |
| OBS + DaVinci | Local | Free | Full production |

**Recommendation**: Stick with Manim + MoviePy for technical content quality and reproducibility. Use DaVinci Resolve only for final polish if needed.