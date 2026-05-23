"""Risk-parity capital allocator across asset classes.

Equal risk contribution: each asset class gets weight inversely proportional
to its realized volatility, so no single class dominates the portfolio's risk.

Standard hedge-fund tool. Implemented here without numpy/scipy so it runs in
any environment. Volatility = stdev of per-class daily (or per-pick) returns.

Why we need this
----------------
Our cycles-3-9 perf-reviews and the AutoHedge committee experiment (PR #298)
showed that crypto picks dominate both volume (~60-70% of closed picks) AND
losses (most negative cum-PnL). Equal-capital allocation is risk-concentrated
in the worst class.

Risk parity would:
  - Down-weight crypto (highest vol, most negative recent cum)
  - Up-weight equity/ETF (positive cum, moderate vol)
  - Balance forex / commodity / futures to their natural vol

Implementation is ONE-SIDED: we weight DOWN overweight high-vol losers.
We do NOT scale capital on positive strategies — that's a separate decision.

Usage:

    allocator = compute_risk_parity_weights(closed_picks, lookback_days=30)
    # returns dict[asset_class -> target_weight_pct]
"""
from __future__ import annotations

import statistics
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from typing import Any


def _f(v: Any, default: float = 0.0) -> float:
    if v is None:
        return default
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _parse_iso(ts: str | None) -> datetime | None:
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone(timezone.utc)
    except (ValueError, TypeError):
        return None


def per_class_returns(
    closed_picks: list[dict],
    lookback_days: int | None = None,
) -> dict[str, list[float]]:
    """Bucket per-trade returns (pnl_pct) by asset_class.

    If lookback_days is set, only include picks closed within that window.
    """
    cutoff = None
    if lookback_days is not None:
        cutoff = datetime.now(timezone.utc) - timedelta(days=lookback_days)

    out: dict[str, list[float]] = defaultdict(list)
    for p in closed_picks:
        if p.get("pnl_pct") is None:
            continue
        if cutoff:
            closed = _parse_iso(p.get("closed_at") or p.get("resolved_at") or p.get("timestamp"))
            if closed and closed < cutoff:
                continue
        ac = (p.get("asset_class") or "UNKNOWN").upper()
        out[ac].append(_f(p["pnl_pct"]))
    return dict(out)


def compute_risk_parity_weights(
    closed_picks: list[dict],
    lookback_days: int | None = None,
    min_n: int = 20,
    min_weight: float = 0.02,
    max_weight: float = 0.40,
) -> dict[str, dict]:
    """Inverse-volatility weighting with floor + cap.

    Returns dict[asset_class -> {n, stdev, raw_weight, target_weight_pct}].
    Classes with n < min_n get no capital (weight=0) — not enough data.
    """
    class_returns = per_class_returns(closed_picks, lookback_days=lookback_days)

    stats: dict[str, dict] = {}
    for ac, rs in class_returns.items():
        if len(rs) < 2:
            continue
        sd = statistics.stdev(rs) if len(rs) >= 2 else 0.0
        mean = sum(rs) / len(rs)
        stats[ac] = {
            "n": len(rs),
            "mean_pnl_pct": round(mean, 4),
            "stdev_pct": round(sd, 4),
            "excluded_reason": None if len(rs) >= min_n else f"n<{min_n}",
        }

    # Inverse-vol weights for eligible classes (n >= min_n AND stdev > 0)
    eligible = {ac: s for ac, s in stats.items()
                if s.get("excluded_reason") is None and s["stdev_pct"] > 0}
    if not eligible:
        return stats

    inv_vol = {ac: 1.0 / s["stdev_pct"] for ac, s in eligible.items()}
    total = sum(inv_vol.values())
    raw = {ac: iv / total for ac, iv in inv_vol.items()}

    # Floor + cap, then re-normalize
    capped = {ac: max(min_weight, min(max_weight, w)) for ac, w in raw.items()}
    total2 = sum(capped.values())
    final = {ac: w / total2 for ac, w in capped.items()}

    for ac, w in final.items():
        stats[ac]["raw_inv_vol_weight"] = round(raw[ac], 4)
        stats[ac]["target_weight_pct"] = round(w * 100, 2)

    # Eligible classes that got zero weight are explicitly marked
    for ac in stats:
        if "target_weight_pct" not in stats[ac]:
            stats[ac]["target_weight_pct"] = 0.0

    return stats


def summarize_allocation(weights: dict[str, dict]) -> dict:
    """Produce a human-readable summary: weights + drift vs equal-allocation."""
    n_classes = len([ac for ac, s in weights.items() if s.get("target_weight_pct", 0) > 0])
    if n_classes == 0:
        return {"error": "no eligible classes"}
    equal = 100.0 / n_classes

    rows = []
    for ac, s in sorted(weights.items(), key=lambda x: -x[1].get("target_weight_pct", 0)):
        if s.get("target_weight_pct", 0) > 0:
            rows.append({
                "asset_class": ac,
                "n": s["n"],
                "stdev_pct": s["stdev_pct"],
                "target_weight_pct": s["target_weight_pct"],
                "drift_vs_equal_pp": round(s["target_weight_pct"] - equal, 2),
            })
    return {
        "eligible_classes": n_classes,
        "equal_allocation_pct": round(equal, 2),
        "allocations": rows,
        "excluded": [{"asset_class": ac, "reason": s.get("excluded_reason", "no_stdev")}
                     for ac, s in weights.items() if s.get("target_weight_pct", 0) == 0],
    }


if __name__ == "__main__":
    import argparse
    import json

    ap = argparse.ArgumentParser(description="Risk-parity allocation across asset classes.")
    ap.add_argument("--dashboard", default="audit_trail/data/dashboard_payload.json")
    ap.add_argument("--lookback-days", type=int, default=None)
    ap.add_argument("--min-n", type=int, default=20)
    args = ap.parse_args()

    dp = json.load(open(args.dashboard, "r", encoding="utf-8"))
    closed = dp["picks"]["recent_closed"]
    weights = compute_risk_parity_weights(closed, lookback_days=args.lookback_days, min_n=args.min_n)
    summary = summarize_allocation(weights)
    print(json.dumps({"summary": summary, "detail": weights}, indent=2))
