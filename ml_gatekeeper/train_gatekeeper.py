"""ML Gatekeeper A/B training entry point — Phase D of leakage purge.

Thin wrapper around `ml_gatekeeper.gatekeeper.main()` that renames the produced
bundle to `gatekeeper_old.joblib` (when `ML_GATE_DROP_LEAKAGE` is unset/false)
or `gatekeeper_new.joblib` (when `ML_GATE_DROP_LEAKAGE=1`). Designed to be
called once per arm by `.github/workflows/ml-gatekeeper-train-ab.yml`.

The underlying training pipeline (data loading, CV, ensemble fit, isotonic
calibration, learned score weights, leakage stamping) lives in
`ml_gatekeeper/gatekeeper.py::train_model` and honours `ML_GATE_DROP_LEAKAGE`
at the feature-extraction layer (`_LEAKAGE_FEATURE_INDICES` masked to 0).

Exit codes:
    0 = bundle produced + renamed
    1 = training produced no bundle (insufficient data / sklearn missing)
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from ml_gatekeeper.gatekeeper import (
    MODEL_DIR,
    _drop_leakage_enabled,
    main as _gatekeeper_main,
)


DEFAULT_BUNDLE = MODEL_DIR / "gatekeeper_model.joblib"
OLD_BUNDLE = MODEL_DIR / "gatekeeper_old.joblib"
NEW_BUNDLE = MODEL_DIR / "gatekeeper_new.joblib"


def _target_bundle_path() -> Path:
    return NEW_BUNDLE if _drop_leakage_enabled() else OLD_BUNDLE


def train_and_rename() -> Path:
    """Run the gatekeeper training pipeline and rename the output bundle.

    Returns the path of the renamed bundle. Raises FileNotFoundError if the
    underlying pipeline did not produce `gatekeeper_model.joblib` (e.g.
    insufficient training data triggered the heuristic fallback).
    """
    _gatekeeper_main()

    if not DEFAULT_BUNDLE.exists():
        raise FileNotFoundError(
            f"Training did not produce {DEFAULT_BUNDLE}. "
            "Likely cause: <100 closed picks in dashboard_data.json or "
            "scikit-learn missing -> heuristic_fallback() path."
        )

    target = _target_bundle_path()
    if target.exists():
        target.unlink()
    DEFAULT_BUNDLE.rename(target)
    print(
        f"[train_gatekeeper] renamed {DEFAULT_BUNDLE.name} -> {target.name} "
        f"(leakage_dropped={_drop_leakage_enabled()})"
    )
    return target


def main() -> int:
    print("=" * 70)
    print("ML GATEKEEPER A/B TRAINING — Phase D")
    print(f"  ML_GATE_DROP_LEAKAGE = {os.environ.get('ML_GATE_DROP_LEAKAGE', '<unset>')}")
    print(f"  leakage_dropped       = {_drop_leakage_enabled()}")
    print(f"  target bundle         = {_target_bundle_path().name}")
    print("=" * 70)

    try:
        path = train_and_rename()
    except FileNotFoundError as exc:
        print(f"[train_gatekeeper] FAIL: {exc}", file=sys.stderr)
        return 1

    print(f"[train_gatekeeper] OK bundle at {path} ({path.stat().st_size:,} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
