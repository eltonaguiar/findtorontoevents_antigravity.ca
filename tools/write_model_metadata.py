#!/usr/bin/env python3
"""
A4.1 — Training Metadata Writer
================================
Writes a standardised JSON metadata file alongside a trained model so that
downstream gates (A3.1 regression check, audit dashboard) have a stable,
machine-readable record of every training run.

Output path (default):
  alpha_engine/data/model_metadata_{model_name}.json

Usage — standalone after a training run:
  python tools/write_model_metadata.py \\
      --model-name ml_consensus \\
      --dataset-path signal_aggregator/models/training_data.csv \\
      --win-rate 0.573 \\
      --accuracy 0.612 \\
      --sharpe 1.84 \\
      --hyperparams '{"n_estimators": 200, "max_depth": 6}'

Usage — from Python inside a training script:
  from tools.write_model_metadata import write_metadata

  write_metadata(
      model_name="ml_consensus",
      dataset_path="signal_aggregator/models/training_data.csv",
      metrics={"win_rate": 0.573, "accuracy": 0.612, "sharpe": 1.84},
      hyperparams={"n_estimators": 200, "max_depth": 6},
  )

Fields written to JSON:
  model_name    — string identifier (e.g. "ml_consensus")
  trained_at    — ISO-8601 UTC timestamp
  git_commit    — current HEAD SHA (or "unknown" if git unavailable)
  dataset_sha   — sha256 hex of the training dataset file (or "unknown")
  metrics       — dict with keys: win_rate, accuracy, sharpe
                  (all floats; missing keys replaced with null)
  hyperparams   — arbitrary dict of model configuration

The file is written atomically (temp file + rename) so a partial write
never leaves a corrupt JSON behind.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Default output directory (relative to repo root)
_DEFAULT_OUTPUT_DIR = Path("alpha_engine/data")


# ── Public API ────────────────────────────────────────────────────────────────


def write_metadata(
    model_name: str,
    metrics: dict[str, Optional[float]],
    dataset_path: Optional[str] = None,
    hyperparams: Optional[dict[str, Any]] = None,
    output_dir: Optional[str] = None,
) -> Path:
    """Write model training metadata to JSON.

    Args:
        model_name:   Short identifier for the model (e.g. "ml_consensus").
        metrics:      Dict with any of: win_rate, accuracy, sharpe.
                      Missing keys are written as null.
        dataset_path: Path to the training dataset file used to compute
                      dataset_sha.  If None or file not found, sha is "unknown".
        hyperparams:  Arbitrary dict of hyperparameter key-value pairs.
        output_dir:   Directory to write the JSON file.  Defaults to
                      alpha_engine/data/ (relative to cwd).

    Returns:
        Path of the written JSON file.

    Raises:
        ValueError: If model_name is empty.
        OSError:    If the output directory cannot be created or written to.
    """
    if not model_name or not model_name.strip():
        raise ValueError("model_name must be a non-empty string")

    out_dir = Path(output_dir) if output_dir else _DEFAULT_OUTPUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    metadata = {
        "model_name": model_name,
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "git_commit": _get_git_commit(),
        "dataset_sha": _sha256_of_file(dataset_path),
        "metrics": {
            "win_rate": _safe_float(metrics.get("win_rate")),
            "accuracy": _safe_float(metrics.get("accuracy")),
            "sharpe": _safe_float(metrics.get("sharpe")),
        },
        "hyperparams": hyperparams or {},
    }

    out_path = out_dir / f"model_metadata_{model_name}.json"
    _atomic_write_json(out_path, metadata)

    logger.info("Model metadata written: %s", out_path)
    return out_path


# ── Private helpers ───────────────────────────────────────────────────────────


def _get_git_commit() -> str:
    """Return current HEAD SHA or 'unknown' if git is unavailable."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return "unknown"


def _sha256_of_file(path: Optional[str]) -> str:
    """Compute SHA-256 hex digest of a file, or 'unknown' if unavailable."""
    if not path:
        return "unknown"
    try:
        p = Path(path)
        if not p.is_file():
            return "unknown"
        h = hashlib.sha256()
        with p.open("rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return "unknown"


def _safe_float(value: Any) -> Optional[float]:
    """Convert value to float, returning None if conversion fails."""
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _atomic_write_json(path: Path, data: dict) -> None:
    """Write JSON atomically using a temp file + rename."""
    tmp_fd, tmp_path = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
            f.write("\n")
        os.replace(tmp_path, path)
    except Exception:
        # Clean up temp file on failure
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


# ── CLI entry point ───────────────────────────────────────────────────────────


def _parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Write ML model training metadata to JSON (A4.1).",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("--model-name", required=True, help="Model identifier string.")
    p.add_argument("--dataset-path", default=None, help="Path to training dataset file for SHA-256.")
    p.add_argument("--win-rate", type=float, default=None, help="Win rate metric [0,1].")
    p.add_argument("--accuracy", type=float, default=None, help="Classification accuracy [0,1].")
    p.add_argument("--sharpe", type=float, default=None, help="Sharpe ratio.")
    p.add_argument(
        "--hyperparams",
        default="{}",
        help="JSON string of hyperparameters dict.",
    )
    p.add_argument(
        "--output-dir",
        default=str(_DEFAULT_OUTPUT_DIR),
        help="Directory to write the metadata JSON.",
    )
    return p.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    args = _parse_args(argv if argv is not None else sys.argv[1:])

    try:
        hyperparams = json.loads(args.hyperparams)
    except json.JSONDecodeError as exc:
        logger.error("--hyperparams is not valid JSON: %s", exc)
        return 1

    metrics: dict[str, Optional[float]] = {
        "win_rate": args.win_rate,
        "accuracy": args.accuracy,
        "sharpe": args.sharpe,
    }

    try:
        out = write_metadata(
            model_name=args.model_name,
            metrics=metrics,
            dataset_path=args.dataset_path,
            hyperparams=hyperparams,
            output_dir=args.output_dir,
        )
        print(f"Written: {out}")
        return 0
    except Exception as exc:
        logger.error("Failed to write metadata: %s", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
