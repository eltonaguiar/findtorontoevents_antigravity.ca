#!/bin/bash
# Setup script for SAM Video Production Pipeline
# Run from the videos/ directory

set -e

echo "========================================="
echo "SAM Video Production - Environment Setup"
echo "========================================="

# Detect OS
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS="linux"
elif [[ "$OSTYPE" == "darwin"* ]]; then
    OS="macos"
elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" ]]; then
    OS="windows"
else
    OS="unknown"
fi

echo "Detected OS: $OS"

# Install system dependencies
if [[ "$OS" == "linux" ]]; then
    echo ""
    echo "Installing system dependencies (requires sudo)..."
    sudo apt update
    sudo apt install -y \
        ffmpeg \
        libcairo2-dev \
        libpango1.0-dev \
        pkg-config \
        python3-dev \
        python3-venv \
        build-essential \
        libgif-dev \
        libjpeg-dev \
        libpng-dev
elif [[ "$OS" == "macos" ]]; then
    echo ""
    echo "Installing system dependencies via Homebrew..."
    if ! command -v brew &> /dev/null; then
        echo "Homebrew not found. Install from https://brew.sh"
        exit 1
    fi
    brew install ffmpeg cairo pango pkg-config python3 giflib jpeg libpng
elif [[ "$OS" == "windows" ]]; then
    echo ""
    echo "Windows detected. Please install manually:"
    echo "  1. FFmpeg: https://ffmpeg.org/download.html"
    echo "  2. Python 3.10+: https://python.org"
    echo "  3. GTK3 (for Cairo): https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer"
    echo ""
    read -p "Press Enter after installing dependencies..."
fi

# Create Python virtual environment
echo ""
echo "Creating Python virtual environment..."
python3 -m venv sam-video-env
source sam-video-env/bin/activate

# Upgrade pip
pip install --upgrade pip setuptools wheel

# Install core Python packages
echo ""
echo "Installing Python packages..."
pip install manim moviepy pillow numpy

# Optional: OpenGL backend for Manim (GPU acceleration)
echo ""
read -p "Install Manim OpenGL backend for GPU acceleration? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    pip install "manim[opengl]"
fi

# Optional: TTS providers
echo ""
echo "TTS Provider Options (choose one or more):"
echo "  1) Piper TTS (local, free, fast) - RECOMMENDED"
echo "  2) Coqui XTTS v2 (local, free, voice cloning)"
echo "  3) ElevenLabs (cloud, best quality, 10k free chars/mo)"
echo "  4) OpenAI TTS (cloud, pay-per-use)"
echo "  5) Skip TTS for now"
read -p "Select TTS providers (e.g., 1,3): " tts_choice

if [[ $tts_choice == *"1"* ]]; then
    echo "Installing Piper TTS..."
    pip install piper-tts
    echo "Downloading default voice (en_US-lessac-medium)..."
    python -c "import piper; piper.download_voice('en_US-lessac-medium')" 2>/dev/null || echo "Voice will download on first use"
fi

if [[ $tts_choice == *"2"* ]]; then
    echo "Installing Coqui TTS..."
    pip install coqui-tts
fi

if [[ $tts_choice == *"3"* ]]; then
    echo "Installing ElevenLabs..."
    pip install elevenlabs
fi

if [[ $tts_choice == *"4"* ]]; then
    echo "Installing OpenAI..."
    pip install openai
fi

# Verify installation
echo ""
echo "========================================="
echo "Verifying Installation"
echo "========================================="

source sam-video-env/bin/activate

echo -n "Manim: "
manim --version

echo -n "MoviePy: "
python -c "import moviepy; print(moviepy.__version__)"

echo -n "FFmpeg: "
ffmpeg -version | head -1

echo ""
echo "========================================="
echo "Setup Complete!"
echo "========================================="
echo ""
echo "Next steps:"
echo "  1. Activate environment:  source sam-video-env/bin/activate"
echo "  2. Render scenes:         python render_all.py"
echo "  3. Compose videos:        python compose_final.py"
echo "  4. (Phase 2) Generate TTS: python tts_narration.py --provider piper"
echo "  5. (Phase 2) Merge audio:  python merge_audio_video.py"
echo ""
echo "Output directories:"
echo "  Phase 1 (visual):  output/"
echo "  Phase 2 (audio):   narration/"
echo "  Phase 2 (final):   output_final/"
echo ""
echo "See README.md for full documentation."