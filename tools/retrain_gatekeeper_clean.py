#!/usr/bin/env python3
"""Retrain ml_gatekeeper WITHOUT leakage features — config + validation.

Per Mimo data-backed audit 2026-05-12 + reports/quant_rescue_master_plan
THE ONE THING. Documents exactly which features are target-leakage,
computes their cumulative importance percentage, and emits a retrain
config consumed by the next ml_gatekeeper train cycle.

This script does NOT trigger the retrain itself — it writes the config
to ml_gatekeeper/config/retrain_clean.json. The retrain happens via
workflow_dispatch on .github/workflows/enhanced-ml-crypto.yml with
ML_GATE_DROP_LEAKAGE=1 set.

Usage:
    python tools/retrain_gatekeeper_clean.py
    python tools/retrain_gatekeeper_clean.py --dry-run

Expected outcome: WR lift will drop initially (because the leakage was
inflating it). But the lift that remains will be REAL and will
generalize to live trading.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "ml_gatekeeper" / "config" / "retrain_clean.json"

# ── Features that leak future information — MUST be removed ──
# Per Mimo 2026-05-12 audit + investigator ad0d03c475517f6ff:
#   forward_wr      (idx 5,  importance 0.0871)
#   strat_fwd_wr    (idx 6,  importance 0.1344)
#   eb_forward_wr   (idx 19, importance 0.0579)
#   age_hours       (idx 30, importance 0.0841)
# Mimo extends with 3 more downstream-of-target features:
#   strat_fwd_pf    (importance 0.0527) — strategy's forward profit factor
#   forward_trades  (importance 0.0276) — count of pick's forward trades
#   strat_fwd_trades (importance 0.0262) — strategy's forward trade count
LEAKAGE_FEATURES = {
    "forward_wr",
    "strat_fwd_wr",
    "eb_forward_wr",
    "age_hours",
    "strat_fwd_pf",
    "forward_trades",
    "strat_fwd_trades",
}

# Full feature set from ml_gatekeeper/gatekeeper.py FEATURE_NAMES
ALL_FEATURES = [
    "elite_score", "method_a_score", "ml_composite_score", "confidence", "trust_score",
    "forward_wr", "strat_fwd_wr", "strat_fwd_pf", "strat_fwd_trades", "forward_trades",
    "rr_ratio", "tp_dist_pct", "sl_dist_pct",
    "asset_class", "direction",
    "strong_strategy", "weak_strategy", "strong_source", "weak_source",
    "eb_forward_wr", "eb_confidence", "eb_ml_score", "eb_regime_bonus",
    "eb_market_cap_tier", "eb_source_direction_adj", "eb_technical_alignment",
    "eb_copy_trader_edge", "eb_concentration_penalty",
    "wf_pass", "wf_p_value",
    "age_hours", "timeframe_minutes",
]

CLEAN_FEATURES = [f for f in ALL_FEATURES if f not in LEAKAGE_FEATURES]

# Importance values from ml_gatekeeper/models/training_report.json
# (snapshot 2026-05-12T04:05:45Z per ml_staleness_audit_2026-05-12.md)
FEATURE_IMPORTANCE = {
    "strat_fwd_wr": 0.1344,
    "forward_wr": 0.0871,
    "age_hours": 0.0841,
    "sl_dist_pct": 0.0652,
    "rr_ratio": 0.0640,
    "eb_forward_wr": 0.0579,
    "strat_fwd_pf": 0.0527,
    "tp_dist_pct": 0.0519,
    "method_a_score": 0.0411,
    "elite_score": 0.0391,
    "confidence": 0.0379,
    "trust_score": 0.0319,
    "ml_composite_score": 0.0308,
    "eb_source_direction_adj": 0.0295,
    "strat_fwd_trades": 0.0276,
    "forward_trades": 0.0262,
    "wf_p_value": 0.0222,
    "eb_ml_score": 0.0214,
    "eb_confidence": 0.0203,
    "direction": 0.0201,
}

LEAKAGE_IMPORTANCE_PCT = (
    sum(FEATURE_IMPORTANCE.get(f, 0) for f in LEAKAGE_FEATURES)
    / sum(FEATURE_IMPORTANCE.values()) * 100
)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    print("=" * 60)
    print("ML GATEKEEPER LEAKAGE PURGE — RETRAIN CONFIG")
    print("=" * 60)
    print(f"\nTotal features:     {len(ALL_FEATURES)}")
    print(f"Leakage removed:    {len(LEAKAGE_FEATURES)}")
    print(f"Clean features:     {len(CLEAN_FEATURES)}")
    print(f"\nLeakage importance: {LEAKAGE_IMPORTANCE_PCT:.1f}% of top-20 weighted importance")
    print(f"\nRemoved: {sorted(LEAKAGE_FEATURES)}")
    print(f"Keeping (first 10): {CLEAN_FEATURES[:10]}")

    config = {
        "experiment": "gatekeeper_leakage_purge_v1",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "removed_features": sorted(LEAKAGE_FEATURES),
        "kept_features": CLEAN_FEATURES,
        "removal_rationale": (
            "Target leakage: these features carry information only available "
            "after the trade resolves (or strongly correlated with resolution "
            "time). Removing them ensures the model learns predictive patterns "
            "rather than reading the answer key."
        ),
        "leakage_importance_pct": round(LEAKAGE_IMPORTANCE_PCT, 1),
        "expected_outcome": (
            "WR lift will drop initially (the leakage was inflating it). The "
            "lift that remains will be REAL and will generalize to live trading."
        ),
        "validation": {
            "method": "walk_forward_12fold_plus_holdout",
            "success_criteria": {
                "min_folds_positive_lift": "9/12 (vs current inconsistent due to leakage)",
                "min_holdout_auc": 0.55,
                "max_auc_drop_vs_old": 0.15,
            },
        },
        "ab_test": {
            "enabled": True,
            "design_doc": "reports/ml_gatekeeper_ab_sleeve_design_2026-05-12.md",
            "decision_tool": "tools/ml_gatekeeper_ab_decision.py",
            "router": "ml_gatekeeper/gatekeeper.py::score_active_picks_ab",
            "traffic_split": 0.5,
            "split_method": "md5(pick_id) mod 2",
            "min_resolved_per_arm": 30,
            "wr_delta_pp_min": 2.0,
            "p_threshold_one_sided": 0.10,
            "measurement_window_days": 30,
        },
        "operational_steps": [
            "1. workflow_dispatch enhanced-ml-crypto.yml mode=train-quick (no env)",
            "   → produces ml_gatekeeper/models/gatekeeper_model.joblib (OLD baseline)",
            "   → rename to gatekeeper_old.joblib",
            "2. Set ML_GATE_DROP_LEAKAGE=1 and workflow_dispatch again",
            "   → produces gatekeeper_model.joblib (NEW leakage-purged)",
            "   → rename to gatekeeper_new.joblib",
            "3. Wire score_active_picks_ab() as primary scorer in cron",
            "4. Watch ml_gatekeeper_ab_decision.json for 30 days",
            "5. Phase D z-test verdict + Phase E auto-rollback handle decision",
        ],
    }

    if args.dry_run:
        print(json.dumps(config, indent=2))
        return

    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(config, indent=2), encoding="utf-8")
    print(f"\nRetrain config written to: {CONFIG_PATH}")
    print(f"\nNext step: workflow_dispatch with ML_GATE_DROP_LEAKAGE=1 set.")


if __name__ == "__main__":
    main()
