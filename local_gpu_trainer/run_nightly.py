"""
Run nightly GPU training. Schedule via Windows Task Scheduler or run manually.
Usage: py -3.14 local_gpu_trainer/run_nightly.py

Trains GRU on latest OHLCV data, saves weights, pushes to GitHub.
Designed to run during off-hours (12am-6am EST) when GPU is free.
"""

import os
import sys
import time
import logging
import subprocess
from datetime import datetime, timezone
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

# Ensure project root is on path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def run_training():
    """Execute full training pipeline."""
    from local_gpu_trainer.train_gru import main as train_main, HAS_TORCH

    if not HAS_TORCH:
        log.error("PyTorch not installed. Install: pip install torch")
        return None

    import torch
    log.info("=" * 60)
    log.info("Nightly GPU Training — Alpha Engine GRU Pipeline")
    log.info(f"Time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    log.info(f"PyTorch: {torch.__version__}")
    log.info(f"CUDA available: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        log.info(f"GPU: {torch.cuda.get_device_name(0)}")
        log.info(f"VRAM: {torch.cuda.get_device_properties(0).total_mem / 1e9:.1f} GB")
    log.info("=" * 60)

    t0 = time.time()
    metrics = train_main()
    elapsed = time.time() - t0

    return metrics


def push_to_github(auto_push: bool = False):
    """Stage model files and push to GitHub."""
    if not auto_push:
        log.info("Auto-push disabled. Set --push flag to enable.")
        return False

    models_dir = PROJECT_ROOT / "local_gpu_trainer" / "models"
    try:
        # Stage model files (not .pt if too large — only metrics + inference wrapper)
        files_to_add = []
        for f in models_dir.iterdir():
            if f.suffix in (".json", ".py"):
                files_to_add.append(str(f))

        # Also stage the .pt model if under 50MB (GitHub limit is 100MB)
        pt_file = models_dir / "gru_crypto.pt"
        if pt_file.exists():
            size_mb = pt_file.stat().st_size / (1024 * 1024)
            if size_mb < 50:
                files_to_add.append(str(pt_file))
                log.info(f"Model file size: {size_mb:.1f} MB — will push")
            else:
                log.warning(f"Model file too large ({size_mb:.1f} MB) — skipping git push for .pt")

        if not files_to_add:
            log.info("No files to push")
            return False

        subprocess.run(["git", "add"] + files_to_add, cwd=str(PROJECT_ROOT), check=True)
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        msg = f"model: GRU nightly training update {timestamp}"
        subprocess.run(["git", "commit", "-m", msg], cwd=str(PROJECT_ROOT), check=True)
        subprocess.run(["git", "push"], cwd=str(PROJECT_ROOT), check=True)
        log.info("Pushed model update to GitHub")
        return True
    except subprocess.CalledProcessError as e:
        log.warning(f"Git push failed: {e}")
        return False


def print_summary(metrics: dict):
    """Print training summary."""
    if not metrics:
        log.error("Training returned no metrics")
        return

    log.info("")
    log.info("=" * 60)
    log.info("TRAINING SUMMARY")
    log.info("=" * 60)
    log.info(f"  Device:           {metrics.get('device', 'unknown')}")
    if metrics.get("gpu_name"):
        log.info(f"  GPU:              {metrics['gpu_name']}")
    log.info(f"  Symbols:          {len(metrics.get('symbols', []))}")
    log.info(f"  Epochs:           {metrics.get('best_epoch', '?')}/{metrics.get('epochs_run', '?')}")
    log.info(f"  Best val loss:    {metrics.get('best_val_loss', '?')}")
    log.info(f"  Val accuracy 4h:  {metrics.get('best_val_acc_4h', 0):.1%}")
    log.info(f"  Val accuracy 24h: {metrics.get('best_val_acc_24h', 0):.1%}")
    log.info(f"  Training time:    {metrics.get('training_time_sec', 0):.0f}s")
    log.info(f"  Model path:       {metrics.get('model_path', 'N/A')}")
    log.info("=" * 60)


def main():
    auto_push = "--push" in sys.argv

    log.info(f"Auto-push to GitHub: {'ON' if auto_push else 'OFF (use --push to enable)'}")

    metrics = run_training()
    if metrics is None:
        sys.exit(1)

    print_summary(metrics)

    if auto_push:
        push_to_github(auto_push=True)

    log.info("Nightly training complete.")


if __name__ == "__main__":
    main()
