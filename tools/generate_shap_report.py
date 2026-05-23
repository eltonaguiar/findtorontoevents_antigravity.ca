#!/usr/bin/env python3
"""
A8.1 — SHAP Summary Plot Generator
====================================

Generates a SHAP summary bar chart (mean |SHAP values|) for a trained
ML model and saves the result to reports/.

Usage (CLI):
    python tools/generate_shap_report.py --model ml_consensus
    python tools/generate_shap_report.py --model ml_consensus \
        --model-path signal_aggregator/models/ml_consensus_latest.pkl \
        --metadata alpha_engine/data/model_metadata_ml_consensus.json

Falls back gracefully if shap/matplotlib/joblib/the model file are
unavailable — always exits 0 so CI never fails on this step.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

# ── Constants ──────────────────────────────────────────────────────────

REPORTS_DIR = Path("reports")
DEFAULT_MODEL_PATHS = {
    "ml_consensus": "signal_aggregator/models/ml_consensus_latest.pkl",
    "signal_quality": "forward_testing/models/tp_hit_model.pkl",
}
DEFAULT_METADATA_PATHS = {
    "ml_consensus": "alpha_engine/data/model_metadata_ml_consensus.json",
    "signal_quality": "alpha_engine/data/model_metadata_signal_quality.json",
}


# ── Dependency checks ──────────────────────────────────────────────────

def _try_import(name: str):
    try:
        import importlib
        return importlib.import_module(name)
    except ImportError:
        return None


# ── Core logic ─────────────────────────────────────────────────────────

def load_feature_names(metadata_path: str | None, model_name: str) -> list[str]:
    """
    Load feature names from model metadata JSON (A4.1 format).
    Falls back to empty list if the file doesn't exist or has no features.
    """
    if metadata_path and os.path.exists(metadata_path):
        try:
            with open(metadata_path) as f:
                meta = json.load(f)
            feats = meta.get("feature_names") or meta.get("features") or []
            if feats:
                return feats
        except Exception:
            pass
    return []


def generate_text_summary(
    feature_names: list[str],
    shap_values_mean_abs: list[float],
    model_name: str,
    output_path: Path,
) -> None:
    """Write a plain-text feature importance summary when plotting is unavailable."""
    lines = [
        f"SHAP Summary (text fallback) — {model_name}",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        "-" * 50,
        "Feature                          | Mean |SHAP|",
        "-" * 50,
    ]
    pairs = sorted(zip(feature_names, shap_values_mean_abs), key=lambda x: x[1], reverse=True)
    for feat, val in pairs:
        lines.append(f"{feat:<32} | {val:.6f}")
    lines.append("-" * 50)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[A8.1] Text summary written to {output_path}")


def generate_shap_report(
    model_name: str,
    model_path: str | None = None,
    metadata_path: str | None = None,
) -> int:
    """
    Main entry point.

    Returns
    -------
    0 on success or graceful skip, non-zero only on hard logic error
    (we catch those too and return 0 so CI never blocks).
    """
    try:
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        date_str = datetime.now(timezone.utc).strftime("%Y%m%d")

        # Resolve paths
        resolved_model_path = model_path or DEFAULT_MODEL_PATHS.get(model_name)
        resolved_meta_path = metadata_path or DEFAULT_METADATA_PATHS.get(model_name)

        # ── Check model file exists ────────────────────────────────────
        if not resolved_model_path or not os.path.exists(resolved_model_path):
            print(
                f"[A8.1] Model file not found: {resolved_model_path!r} — "
                "skipping SHAP report (no trained model available yet)"
            )
            return 0

        # ── Load model ─────────────────────────────────────────────────
        joblib = _try_import("joblib")
        if joblib is None:
            print("[A8.1] joblib not available — skipping SHAP report")
            return 0

        print(f"[A8.1] Loading model from {resolved_model_path}")
        model = joblib.load(resolved_model_path)

        # ── Load feature names ─────────────────────────────────────────
        feature_names = load_feature_names(resolved_meta_path, model_name)

        # Try to infer feature names from the model itself as a fallback
        if not feature_names:
            if hasattr(model, "feature_names_in_"):
                feature_names = list(model.feature_names_in_)
            elif hasattr(model, "feature_name_"):
                feature_names = list(model.feature_name_())
            elif hasattr(model, "get_booster"):
                try:
                    feature_names = model.get_booster().feature_names or []
                except Exception:
                    pass

        if not feature_names:
            print(
                "[A8.1] Could not determine feature names from metadata or model — "
                "skipping SHAP report"
            )
            return 0

        print(f"[A8.1] Features ({len(feature_names)}): {feature_names}")

        # ── Build background data from feature names (zeros baseline) ──
        np = _try_import("numpy")
        if np is None:
            print("[A8.1] numpy not available — skipping SHAP report")
            return 0

        background = np.zeros((1, len(feature_names)))

        # ── Try SHAP TreeExplainer ─────────────────────────────────────
        shap = _try_import("shap")
        if shap is None:
            print("[A8.1] shap package not installed — producing text summary instead")
            # Fallback: use sklearn feature_importances_ if available
            importance_values = None
            if hasattr(model, "feature_importances_"):
                importance_values = list(model.feature_importances_)
            else:
                importance_values = [0.0] * len(feature_names)

            txt_path = REPORTS_DIR / f"shap_summary_{model_name}_{date_str}.txt"
            generate_text_summary(feature_names, importance_values, model_name, txt_path)
            return 0

        print("[A8.1] Computing SHAP values via TreeExplainer…")
        try:
            explainer = shap.TreeExplainer(model)
        except Exception:
            # Not a tree model — try KernelExplainer with zeros background
            print("[A8.1] TreeExplainer failed, trying KernelExplainer…")
            try:
                def _predict(x):
                    if hasattr(model, "predict_proba"):
                        return model.predict_proba(x)[:, 1]
                    return model.predict(x)

                explainer = shap.KernelExplainer(_predict, background)
            except Exception as exc:
                print(f"[A8.1] KernelExplainer also failed ({exc}) — text fallback")
                importance_values = (
                    list(model.feature_importances_)
                    if hasattr(model, "feature_importances_")
                    else [0.0] * len(feature_names)
                )
                txt_path = REPORTS_DIR / f"shap_summary_{model_name}_{date_str}.txt"
                generate_text_summary(feature_names, importance_values, model_name, txt_path)
                return 0

        # Compute SHAP values on background (representative point)
        try:
            shap_values = explainer.shap_values(background)
        except Exception as exc:
            print(f"[A8.1] shap_values() failed ({exc}) — text fallback")
            importance_values = (
                list(model.feature_importances_)
                if hasattr(model, "feature_importances_")
                else [0.0] * len(feature_names)
            )
            txt_path = REPORTS_DIR / f"shap_summary_{model_name}_{date_str}.txt"
            generate_text_summary(feature_names, importance_values, model_name, txt_path)
            return 0

        # Handle multi-class output (take class-1 or average abs)
        if isinstance(shap_values, list):
            if len(shap_values) > 1:
                sv_arr = shap_values[1]  # positive class
            else:
                sv_arr = shap_values[0]
        else:
            sv_arr = shap_values

        mean_abs_shap = np.abs(sv_arr).mean(axis=0)

        # ── Try matplotlib plot ────────────────────────────────────────
        mpl = _try_import("matplotlib")
        plt = _try_import("matplotlib.pyplot")

        if mpl is None or plt is None:
            print("[A8.1] matplotlib not available — producing text summary")
            txt_path = REPORTS_DIR / f"shap_summary_{model_name}_{date_str}.txt"
            generate_text_summary(feature_names, list(mean_abs_shap), model_name, txt_path)
            return 0

        # Ensure non-interactive backend (no display required in CI)
        mpl.use("Agg")
        import matplotlib.pyplot as plt_mod  # re-import after backend set

        # Sort by importance descending
        sorted_pairs = sorted(
            zip(feature_names, mean_abs_shap), key=lambda x: x[1], reverse=True
        )
        sorted_names = [p[0] for p in sorted_pairs]
        sorted_vals = [float(p[1]) for p in sorted_pairs]

        fig, ax = plt_mod.subplots(figsize=(10, max(4, len(sorted_names) * 0.45)))
        y_pos = range(len(sorted_names))
        ax.barh(list(y_pos), sorted_vals[::-1], color="#2196F3", alpha=0.85)
        ax.set_yticks(list(y_pos))
        ax.set_yticklabels(sorted_names[::-1], fontsize=10)
        ax.set_xlabel("Mean |SHAP value|", fontsize=11)
        ax.set_title(
            f"SHAP Feature Importance — {model_name}\n"
            f"{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
            fontsize=12,
        )
        ax.grid(axis="x", alpha=0.3)
        plt_mod.tight_layout()

        png_path = REPORTS_DIR / f"shap_summary_{model_name}_{date_str}.png"
        plt_mod.savefig(str(png_path), dpi=150, bbox_inches="tight")
        plt_mod.close(fig)

        print(f"[A8.1] SHAP summary plot saved to {png_path}")

        # Also write a companion JSON for machine readability
        json_path = REPORTS_DIR / f"shap_summary_{model_name}_{date_str}.json"
        summary_data = {
            "model_name": model_name,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "feature_importances": [
                {"feature": name, "mean_abs_shap": round(float(val), 8)}
                for name, val in zip(sorted_names, sorted_vals)
            ],
        }
        json_path.write_text(json.dumps(summary_data, indent=2), encoding="utf-8")
        print(f"[A8.1] SHAP JSON summary saved to {json_path}")

        return 0

    except Exception:
        # Hard catch-all: print but never let CI fail
        print("[A8.1] Unexpected error during SHAP report generation (non-fatal):")
        traceback.print_exc()
        return 0


# ── CLI entry point ────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="A8.1 — Generate SHAP summary plot for a trained ML model"
    )
    parser.add_argument(
        "--model",
        required=True,
        help="Model name key (e.g. ml_consensus, signal_quality)",
    )
    parser.add_argument(
        "--model-path",
        default=None,
        help="Path to the .pkl model file (overrides default lookup)",
    )
    parser.add_argument(
        "--metadata",
        default=None,
        help="Path to model metadata JSON (overrides default lookup)",
    )
    args = parser.parse_args()

    exit_code = generate_shap_report(
        model_name=args.model,
        model_path=args.model_path,
        metadata_path=args.metadata,
    )
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
