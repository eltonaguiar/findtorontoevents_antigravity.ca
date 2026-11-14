# ServiceNow SAM Masterclass - Video Production

## Overview
This folder contains the complete pipeline for producing professional SAM (Software Asset Management) educational videos, covering all core concepts needed for CIS-SAM certification and job interviews.

**Source Material**: 
- GitHub: https://github.com/eltonaguiar/alt_parallelswarm_SAM (multi-agent fleet work)
- Live Guide: https://eltonaguiar.github.io/ServiceNow_Learning_TSOM-_CSM_FSM_SalesCRM_HAM_ITSM/docs/modules/sam/sam-guide/

---

## Video Series (6 Core Topics)

| # | Video | Core Concept | Key Interview Value |
|---|-------|--------------|---------------------|
| 1 | **The SAM Chain** | Install → Discovery Model → Software Model → Entitlement → Result | The backbone of every SAM question |
| 2 | **The Four Gates** | Schema, CMDB, Discovery, Normalization prerequisites | "If any gate fails, data is garbage" |
| 3 | **Normalization States** | Six states (not four!) with manual/revert rules | Common exam trap: "How many statuses?" |
| 4 | **Reconciliation Tiers** | Product / Software Model / License Metric results | Three-tier drill-down logic |
| 5 | **Rights Algebra** | Owned, Used, Available, Wasted, Unallocated | The math behind every compliance position |
| 6 | **Top 7 Traps** | Metric mismatch, duplicate installs, unnormalized titles, maintenance-as-license, out-of-scope, first-recon-invoice, dead SaaS | Real-world implementation killers |

---

## Phase 1: Visual-Only Videos (Complete Pipeline)

### Prerequisites
```bash
# System dependencies (Ubuntu/WSL2/Debian)
sudo apt update && sudo apt install -y ffmpeg libcairo2-dev libpango1.0-dev pkg-config python3-dev build-essential

# Python environment
python3 -m venv sam-video-env
source sam-video-env/bin/activate

# Core packages
pip install manim moviepy pillow numpy
# Optional GPU acceleration for Manim:
pip install manim[opengl]
```

### Render Scenes (Manim)
```bash
cd /home/eaguiar2015/findtorontoevents_antigravity.ca/.kilo/worktrees/samvideos-v2/videos

# Render all scenes (1080p60)
python render_all.py

# Or render individually:
manim -pqh scenes/01_chain_diagram.py ChainDiagram
manim -pqh scenes/01_chain_diagram.py FourGates
manim -pqh scenes/01_chain_diagram.py NormalizationStates
manim -pqh scenes/01_chain_diagram.py ReconciliationTiers
manim -pqh scenes/01_chain_diagram.py RightsAlgebra
manim -pqh scenes/01_chain_diagram.py TopTraps
```

**Output**: `media/videos/01_chain_diagram/1080p60/*.mp4`

### Compose Final Videos (MoviePy)
```bash
python compose_final.py
```

**Outputs**:
- `output/SAM_Masterclass_Phase1_VisualOnly.mp4` — Full masterclass (~15-20 min)
- `output/SAM_01_chain_diagram_Phase1.mp4` — Individual topic videos
- `output/SAM_02_four_gates_Phase1.mp4`
- `output/SAM_03_normalization_states_Phase1.mp4`
- `output/SAM_04_reconciliation_tiers_Phase1.mp4`
- `output/SAM_05_rights_algebra_Phase1.mp4`
- `output/SAM_06_top_traps_Phase1.mp4`

---

## Phase 2: Videos with Narration (Add Audio)

### Option A: Piper TTS (Local, Free, Fast) — RECOMMENDED START
```bash
pip install piper-tts

# Download a voice (first run only)
piper --model en_US-lessac-medium --download

# Generate all narrations
python tts_narration.py --provider piper --voice en_US-lessac-medium
```

### Option B: Coqui XTTS v2 (Local, Free, Voice Cloning)
```bash
pip install coqui-tts
python tts_narration.py --provider coqui
```

### Option C: ElevenLabs (Cloud, Best Quality, 10k free chars/mo)
```bash
pip install elevenlabs
export ELEVENLABS_API_KEY="your_key_here"
python tts_narration.py --provider elevenlabs
```

### Option D: OpenAI TTS (Cloud, Pay-per-use, $15/1M chars)
```bash
pip install openai
export OPENAI_API_KEY="your_key_here"
python tts_narration.py --provider openai --voice onyx
```

### Merge Video + Audio
```bash
python merge_audio_video.py
```

**Outputs**:
- `output_final/SAM_01_chain_diagram_FINAL.mp4` — Individual videos with narration
- `output_final/SAM_Masterclass_FINAL.mp4` — Full masterclass with narration

---

## File Structure

```
videos/
├── README.md                      # This file
├── SAM_KEY_CONCEPTS_SUMMARY.md    # Complete concept reference for scripts
├── VIDEO_GENERATION_TOOLS_RESEARCH.md  # Tool evaluation & recommendations
├── render_all.py                  # Batch render all Manim scenes
├── compose_final.py               # Assemble scenes into final videos (Phase 1)
├── tts_narration.py               # Generate TTS narration (Phase 2)
├── merge_audio_video.py           # Merge video + audio (Phase 2)
├── scenes/
│   └── 01_chain_diagram.py        # All 6 Manim scenes
├── output/                        # Phase 1 outputs (visual only)
│   ├── SAM_Masterclass_Phase1_VisualOnly.mp4
│   └── SAM_*_Phase1.mp4
├── narration/                     # Phase 2 audio files
│   ├── 01_chain_diagram.wav
│   ├── 02_four_gates.wav
│   └── ...
└── output_final/                  # Phase 2 outputs (with audio)
    ├── SAM_Masterclass_FINAL.mp4
    └── SAM_*_FINAL.mp4
```

---

## Quick Start (One-Command)

```bash
cd /home/eaguiar2015/findtorontoevents_antigravity.ca/.kilo/worktrees/samvideos-v2/videos

# 1. Setup (run once)
./setup.sh  # Creates venv, installs deps

# 2. Phase 1: Visual videos
source sam-video-env/bin/activate
python render_all.py
python compose_final.py

# 3. Phase 2: Add narration (choose one)
# Local free (Piper):
pip install piper-tts
python tts_narration.py --provider piper
python merge_audio_video.py

# OR Cloud best quality (ElevenLabs):
pip install elevenlabs
export ELEVENLABS_API_KEY="xxx"
python tts_narration.py --provider elevenlabs
python merge_audio_video.py
```

---

## Customization

### Modify Scene Content
Edit `scenes/01_chain_diagram.py` — each scene is a Manim `Scene` class:
- `ChainDiagram` — The SAM chain animation
- `FourGates` — Four gates with checkmarks
- `NormalizationStates` — Color-coded table
- `ReconciliationTiers` — Three-tier cards
- `RightsAlgebra` — Equations + compliance positions
- `TopTraps` — Seven trap cards

### Adjust Timing/Style
- `config.frame_rate = 30` — Frame rate
- `config.pixel_height/width` — Resolution (1080p default)
- `config.background_color = "#0d1117"` — Dark GitHub-style theme
- Colors: `#58a6ff` (blue), `#7ee787` (green), `#d2a8ff` (purple), `#ffa657` (orange), `#ff7b72` (red), `#ffdf5d` (yellow)

### Add New Topics
1. Add narration script to `NARRATION_SCRIPTS` in `tts_narration.py`
2. Create new Manim scene in `scenes/01_chain_diagram.py`
3. Add to `SCENES` list in `render_all.py`
4. Add to `SCENE_FILES` in `compose_final.py` and `merge_audio_video.py`

---

## Publishing Checklist

### YouTube/Video Platform
- [ ] Masterclass video: `output_final/SAM_Masterclass_FINAL.mp4`
- [ ] Individual shorts: `output_final/SAM_*_FINAL.mp4`
- [ ] Thumbnails: Create 1280x720 for each topic
- [ ] Descriptions: Link to GitHub repo and live guide
- [ ] Tags: `ServiceNow`, `SAM`, `CIS-SAM`, `ITAM`, `Software Asset Management`

### GitHub Pages / Documentation
- [ ] Embed in `ServiceNow_Learning` repo under `/docs/modules/sam/videos/`
- [ ] Add to SAM guide "Video Library" section
- [ ] Create playlist page with all 6 videos

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `manim` not found | `pip install manim` in venv |
| Cairo errors | `sudo apt install libcairo2-dev libpango1.0-dev` |
| FFmpeg not found | `sudo apt install ffmpeg` |
| MoviePy TextClip fails | `sudo apt install python3-dev build-free` + ImageMagick |
| Piper voice not found | `piper --model en_US-lessac-medium --download` |
| ElevenLabs quota exceeded | Wait for monthly reset or upgrade plan |
| Audio/video sync off | Check `merge_audio_video.py` duration matching logic |

---

## Credits

**Source Content**: Multi-agent fleet (deepseek-flash, grok-4.6, beam, perplexity) via `alt_parallelswarm_SAM`
**Live Guide**: `ServiceNow_Learning_TSOM-_CSM_FSM_SalesCRM_HAM_ITSM` deployed to GitHub Pages
**Animation Engine**: Manim Community Edition
**Video Composition**: MoviePy
**TTS Options**: Piper, Coqui, ElevenLabs, OpenAI

---

## License
MIT — Free to use, modify, and distribute for educational purposes.