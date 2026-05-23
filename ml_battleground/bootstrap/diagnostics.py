"""
Writes bootstrap_summary.json after training completes.
Used by GitHub Actions workflow for summary reporting.
"""
import os
import json
from datetime import datetime, timezone

SUMMARY_PATH = os.path.join(os.path.dirname(__file__), "bootstrap_summary.json")


def write_summary(results: dict, elapsed_seconds: float):
    summary = {
        "bootstrapped_at": datetime.now(timezone.utc).isoformat(),
        "elapsed_seconds": round(elapsed_seconds, 1),
        "systems": results,
        "model_paths": {
            "a_filter": "system_a_filter/models/filter_xgb.joblib",
            "a_scaler": "system_a_filter/models/filter_scaler.joblib",
            "b_regime": "system_b_regime/models/regime_xgb.joblib",
            "b_scaler": "system_b_regime/models/regime_scaler.joblib",
            "c_gru": "system_c_deeplearn/models/gru_attention.pt",
            "c_scaler": "system_c_deeplearn/models/feature_scaler.joblib",
            "c_arch": "system_c_deeplearn/models/arch_config.json",
        },
    }
    os.makedirs(os.path.dirname(SUMMARY_PATH), exist_ok=True)
    with open(SUMMARY_PATH, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"[Bootstrap] Summary written: {SUMMARY_PATH}")
    return summary
