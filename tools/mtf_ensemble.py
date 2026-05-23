"""Multi-timeframe (MTF) signal ensemble aggregator.

Pattern lifted from `51bitquant/ai-hedge-fund-crypto` (571 ⭐, LangGraph DAG):
run the same strategy on multiple timeframes in parallel, then weight-combine
the per-TF signals into a single ensemble verdict.

Current state: our picks have `htf_confirmation` as a boolean-ish field but
no formal ensemble logic. This module provides the math for properly
weighting signals across timeframes using performance-weighted or
inverse-noise-weighted aggregation.

Signal shape (per-timeframe):
  {"direction": "LONG" | "SHORT" | "FLAT",
   "strength": float in [-1, +1]  (-1 = strong short, +1 = strong long),
   "confidence": float in [0, 1]}

Aggregation modes:
  - equal_weight           : naive
  - inverse_noise          : weight by inverse of TF's realized volatility
  - performance_weighted   : weight by TF's historical WR on this strategy

Output: aggregate signal + per-TF attribution. Pick is ACTED ON only when
aggregate_strength exceeds a configurable threshold (default 0.4).

Reference: https://github.com/51bitquant/ai-hedge-fund-crypto — multi-timeframe
DAG architecture; our ensemble is the aggregation math without the LangGraph
orchestration overhead.
"""
from __future__ import annotations

from typing import Any


def _f(v: Any, default: float = 0.0) -> float:
    if v is None:
        return default
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


STANDARD_TIMEFRAMES = ["5m", "15m", "30m", "1h", "4h", "1d"]


def signal_from_fields(
    direction: str | None,
    strength_0_100: float | None = None,
    confidence_0_1: float | None = None,
) -> dict:
    """Normalize a signal record. strength_0_100 is optional; defaults to 50."""
    d = (direction or "").upper()
    if d not in ("LONG", "SHORT", "FLAT", "BUY", "SELL"):
        d = "FLAT"
    if d == "BUY":
        d = "LONG"
    if d == "SELL":
        d = "SHORT"

    s01 = max(0.0, min(100.0, _f(strength_0_100, 50.0))) / 50.0 - 1.0  # map to [-1, 1]
    if d == "LONG":
        strength = abs(s01)
    elif d == "SHORT":
        strength = -abs(s01)
    else:
        strength = 0.0
    return {
        "direction": d,
        "strength": round(strength, 4),
        "confidence": max(0.0, min(1.0, _f(confidence_0_1, 0.5))),
    }


def equal_weight_ensemble(signals: dict[str, dict]) -> dict:
    """Plain average of signal strengths across timeframes."""
    if not signals:
        return {"direction": "FLAT", "strength": 0.0, "confidence": 0.0, "agreement_pct": 0.0}
    strengths = [s["strength"] for s in signals.values()]
    agg = sum(strengths) / len(strengths)
    # Direction-agreement: fraction of signals agreeing with the majority sign
    n_pos = sum(1 for s in strengths if s > 0.05)
    n_neg = sum(1 for s in strengths if s < -0.05)
    majority = max(n_pos, n_neg)
    agreement = majority / len(strengths) if strengths else 0.0
    direction = "LONG" if agg > 0.05 else "SHORT" if agg < -0.05 else "FLAT"
    conf_avg = sum(s["confidence"] for s in signals.values()) / len(signals)
    return {
        "direction": direction,
        "strength": round(agg, 4),
        "confidence": round(conf_avg * agreement, 4),
        "agreement_pct": round(agreement * 100, 2),
        "n_timeframes": len(signals),
    }


def performance_weighted_ensemble(
    signals: dict[str, dict],
    tf_weights: dict[str, float],
) -> dict:
    """Weight signals by tf_weights (e.g., derived from each TF's historical WR)."""
    if not signals:
        return {"direction": "FLAT", "strength": 0.0, "confidence": 0.0, "n_timeframes": 0}
    used = {tf: s for tf, s in signals.items() if tf in tf_weights and tf_weights[tf] > 0}
    if not used:
        return equal_weight_ensemble(signals)
    total_w = sum(tf_weights[tf] for tf in used)
    if total_w == 0:
        return equal_weight_ensemble(signals)
    agg = sum(used[tf]["strength"] * tf_weights[tf] for tf in used) / total_w
    conf = sum(used[tf]["confidence"] * tf_weights[tf] for tf in used) / total_w
    direction = "LONG" if agg > 0.05 else "SHORT" if agg < -0.05 else "FLAT"
    return {
        "direction": direction,
        "strength": round(agg, 4),
        "confidence": round(conf, 4),
        "n_timeframes": len(used),
        "weights_applied": {tf: round(tf_weights[tf] / total_w, 4) for tf in used},
    }


def inverse_noise_weights(realized_vol_by_tf: dict[str, float]) -> dict[str, float]:
    """Convert realized per-TF volatility into weights. Lower-vol TFs get more weight."""
    inv = {tf: 1.0 / v if v > 0 else 0.0 for tf, v in realized_vol_by_tf.items()}
    total = sum(inv.values())
    if total == 0:
        return {tf: 1.0 / len(realized_vol_by_tf) for tf in realized_vol_by_tf}
    return {tf: inv[tf] / total for tf in inv}


def passes_mtf_threshold(
    ensemble: dict,
    min_strength: float = 0.4,
    min_agreement_pct: float = 60.0,
    min_n_tf: int = 3,
) -> dict:
    """Gate: pick must meet MTF ensemble thresholds to be acted on."""
    reasons = []
    if ensemble.get("n_timeframes", 0) < min_n_tf:
        reasons.append(f"too_few_tfs({ensemble.get('n_timeframes', 0)} < {min_n_tf})")
    if abs(ensemble.get("strength", 0.0)) < min_strength:
        reasons.append(f"weak_strength(|{ensemble.get('strength')}| < {min_strength})")
    if ensemble.get("agreement_pct", 100) < min_agreement_pct:
        # Only applies to equal_weight ensembles that emit agreement_pct
        reasons.append(f"low_agreement({ensemble.get('agreement_pct')}% < {min_agreement_pct}%)")
    return {"passed": len(reasons) == 0, "reject_reasons": reasons}


if __name__ == "__main__":
    import argparse
    import json

    ap = argparse.ArgumentParser(description="MTF ensemble demo.")
    args = ap.parse_args()

    # Synthetic example: 4 TFs, 3 agree long, 1 weak short
    signals = {
        "5m":  signal_from_fields("LONG", strength_0_100=65, confidence_0_1=0.7),
        "15m": signal_from_fields("LONG", strength_0_100=70, confidence_0_1=0.8),
        "1h":  signal_from_fields("SHORT", strength_0_100=55, confidence_0_1=0.4),
        "4h":  signal_from_fields("LONG", strength_0_100=75, confidence_0_1=0.85),
    }
    eq = equal_weight_ensemble(signals)
    # Higher TFs have lower vol -> higher weight
    perf_weights = {"5m": 0.1, "15m": 0.2, "1h": 0.3, "4h": 0.4}
    perf = performance_weighted_ensemble(signals, perf_weights)
    gate = passes_mtf_threshold(eq, min_strength=0.2)
    print(json.dumps({
        "signals": signals,
        "equal_weight_ensemble": eq,
        "performance_weighted_ensemble": perf,
        "gate_result": gate,
    }, indent=2))
