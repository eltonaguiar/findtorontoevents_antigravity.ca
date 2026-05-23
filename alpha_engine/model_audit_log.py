#!/usr/bin/env python3
"""
Model Audit Log -- tracks training runs, metrics, and enables rollback.

Every model training run is logged with:
- Timestamp, model version, hyperparameters
- Training metrics (AUC, accuracy, feature importance)
- Data snapshot hash (SHA256 of training data)
- Model artifact path

Rollback: if a new model's validation AUC drops below the previous
model's AUC by more than 5%, automatically restore the previous model.
"""

import json
import hashlib
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any

AUDIT_DIR = Path(__file__).resolve().parent / "data" / "model_audit"
AUDIT_LOG_PATH = AUDIT_DIR / "audit_log.json"
MODEL_ARCHIVE_DIR = AUDIT_DIR / "archived_models"


def _ensure_dirs():
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    MODEL_ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)


def _load_log() -> list:
    if AUDIT_LOG_PATH.exists():
        try:
            with open(AUDIT_LOG_PATH) as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return []


def _save_log(log: list):
    _ensure_dirs()
    with open(AUDIT_LOG_PATH, "w") as f:
        json.dump(log, f, indent=2, default=str)


def compute_data_hash(data_path: str) -> str:
    """Compute SHA256 hash of training data for reproducibility."""
    h = hashlib.sha256()
    try:
        with open(data_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()[:16]
    except (FileNotFoundError, IOError):
        return "unknown"


def log_training_run(
    system_name: str,
    model_type: str,
    version: str,
    metrics: Dict[str, Any],
    hyperparameters: Dict[str, Any],
    feature_names: list,
    training_samples: int,
    data_hash: str = "unknown",
    model_artifact_path: Optional[str] = None,
    notes: str = "",
) -> dict:
    """Log a model training run to the audit log."""
    _ensure_dirs()
    log = _load_log()

    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "system_name": system_name,
        "model_type": model_type,
        "version": version,
        "metrics": metrics,
        "hyperparameters": hyperparameters,
        "feature_count": len(feature_names),
        "feature_names": feature_names,
        "training_samples": training_samples,
        "data_hash": data_hash,
        "model_artifact_path": model_artifact_path,
        "notes": notes,
        "rolled_back": False,
    }

    # Archive model artifact if provided
    if model_artifact_path and Path(model_artifact_path).exists():
        archive_name = f"{system_name}_v{version}_{entry['timestamp'][:10]}.pkl"
        archive_path = MODEL_ARCHIVE_DIR / archive_name
        shutil.copy2(model_artifact_path, archive_path)
        entry["archived_path"] = str(archive_path)

    log.append(entry)
    _save_log(log)
    print(f"  [AUDIT] Logged {system_name} v{version}: "
          f"AUC={metrics.get('auc', metrics.get('roc_auc', '?'))}, "
          f"samples={training_samples}, hash={data_hash[:8]}")
    return entry


def check_and_rollback(
    system_name: str,
    new_metrics: Dict[str, Any],
    model_artifact_path: str,
    rollback_threshold: float = 0.05,
) -> bool:
    """Check if new model is worse than previous. If so, rollback.

    Returns True if rollback occurred.
    """
    log = _load_log()
    prev_entries = [e for e in log if e["system_name"] == system_name and not e.get("rolled_back")]

    if len(prev_entries) < 2:
        return False  # No previous model to compare against

    prev = prev_entries[-2]  # Second-to-last entry
    prev_auc = prev["metrics"].get("auc", prev["metrics"].get("roc_auc", 0))
    new_auc = new_metrics.get("auc", new_metrics.get("roc_auc", 0))

    if prev_auc > 0 and new_auc < prev_auc - rollback_threshold:
        # New model is significantly worse -- rollback
        archived = prev.get("archived_path")
        if archived and Path(archived).exists():
            shutil.copy2(archived, model_artifact_path)
            log[-1]["rolled_back"] = True
            log[-1]["rollback_reason"] = (
                f"AUC dropped {prev_auc:.3f} -> {new_auc:.3f} "
                f"(delta={new_auc - prev_auc:.3f}, threshold={rollback_threshold})"
            )
            _save_log(log)
            print(f"  [AUDIT] ROLLBACK: {system_name} reverted to v{prev['version']} "
                  f"(AUC {new_auc:.3f} < {prev_auc:.3f} - {rollback_threshold})")
            return True

    return False


def get_model_history(system_name: str) -> list:
    """Get training history for a specific system."""
    log = _load_log()
    return [e for e in log if e["system_name"] == system_name]


def get_latest_version(system_name: str) -> Optional[str]:
    """Get the latest non-rolled-back version for a system."""
    history = get_model_history(system_name)
    active = [e for e in history if not e.get("rolled_back")]
    return active[-1]["version"] if active else None
