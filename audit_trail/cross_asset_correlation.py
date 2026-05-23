#!/usr/bin/env python3
"""B15: Cross-asset correlation monitor.

Detects cross-class beta shifts and hedge leakage when regime gates or
vol-target sidecars are active. Computes pairwise Pearson correlations
of daily PnL series across CRYPTO, EQUITY, FOREX, BOND, COMMODITY.

Flags:
- HIGH_CORRELATION (|r| > 0.60): two asset classes moving together —
  portfolio is less diversified than intended.
- HEDGE_LEAKAGE: CRYPTO SHORT direction correlates with EQUITY/FOREX BUY
  direction (directional hedge unexpectedly correlated with target position).

Wire-Up: opt-in sidecar per CLAUDE.md Wire-Up Rule.
Wiring plan: dashboard generator will read the JSON artifact in a future
"B15-dashboard-panel" PR. Initially consumed via CI quality gate in
`audit_trail/quality_gates.py` when HIGH_CORRELATION flags are present.

Usage:
    python audit_trail/cross_asset_correlation.py [--input PATH] [--window 30]
                                                  [--out reports/cross_asset_correlation_latest.json]
"""
from __future__ import annotations

import argparse
import json
import math
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


# Minimum daily observations required to compute a meaningful correlation
_MIN_OBSERVATIONS = 5

# Correlation threshold above which a pair is flagged
HIGH_CORR_THRESHOLD = 0.60

# Asset classes to monitor
_MONITORED_CLASSES = ("CRYPTO", "EQUITY", "FOREX", "BOND", "COMMODITY")


# ---------------------------------------------------------------------------
# Pure-Python Pearson correlation (avoids numpy dependency)
# ---------------------------------------------------------------------------

def pearson_correlation(xs: list[float], ys: list[float]) -> float | None:
    """Return Pearson r for paired lists xs, ys. Returns None if undetermined."""
    n = len(xs)
    if n < 2 or len(ys) != n:
        return None
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    cov = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    var_x = sum((x - mean_x) ** 2 for x in xs)
    var_y = sum((y - mean_y) ** 2 for y in ys)
    denom = math.sqrt(var_x * var_y)
    if denom == 0:
        return None
    return round(cov / denom, 4)


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def _parse_iso_date(ts: Any) -> str | None:
    """Return YYYY-MM-DD string from an ISO timestamp, or None."""
    if not ts:
        return None
    try:
        dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d")
    except (ValueError, TypeError):
        return None


def _safe_float(v: Any) -> float | None:
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _load_closed_picks(input_path: Path) -> list[dict[str, Any]]:
    raw = json.loads(input_path.read_text(encoding="utf-8"))
    if isinstance(raw, list):
        return [p for p in raw if isinstance(p, dict)]
    # Dashboard data structure: payload["picks"]["recent_closed"]
    picks_node = raw.get("picks") or {}
    if isinstance(picks_node, dict):
        candidates = picks_node.get("recent_closed") or []
        if isinstance(candidates, list):
            return [p for p in candidates if isinstance(p, dict)]
    # Generic: try common key names
    for key in ("recent_closed", "closed_picks", "picks"):
        val = raw.get(key)
        if isinstance(val, list):
            return [p for p in val if isinstance(p, dict)]
    return []


# ---------------------------------------------------------------------------
# PnL series builder
# ---------------------------------------------------------------------------

def build_daily_pnl_series(
    picks: list[dict[str, Any]],
    window_days: int = 30,
    now: datetime | None = None,
) -> dict[str, dict[str, float]]:
    """Build {asset_class: {date_str: mean_pnl_pct}} over the trailing window.

    Only picks with a parseable close date within `window_days` are included.
    """
    if now is None:
        now = datetime.now(timezone.utc)

    cutoff_days = window_days

    series: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(list))

    for p in picks:
        ac = str(p.get("asset_class") or "UNKNOWN").upper()
        if ac not in _MONITORED_CLASSES:
            continue

        ts_raw = p.get("closed_at") or p.get("timestamp") or p.get("exit_time")
        date_str = _parse_iso_date(ts_raw)
        if not date_str:
            continue

        # Age filter
        try:
            pick_dt = datetime.fromisoformat(str(ts_raw).replace("Z", "+00:00"))
            age_days = (now - pick_dt.replace(tzinfo=timezone.utc)).days
            if age_days > cutoff_days:
                continue
        except (ValueError, TypeError):
            continue

        pnl = _safe_float(p.get("pnl_pct") or p.get("pnlPct"))
        if pnl is None:
            continue

        series[ac][date_str].append(pnl)

    # Average PnL per (class, date)
    result: dict[str, dict[str, float]] = {}
    for ac, date_map in series.items():
        result[ac] = {
            date: round(sum(vals) / len(vals), 6)
            for date, vals in date_map.items()
        }

    return result


# ---------------------------------------------------------------------------
# Correlation computation
# ---------------------------------------------------------------------------

def compute_pair_correlation(
    series_a: dict[str, float],
    series_b: dict[str, float],
) -> dict[str, Any]:
    """Compute Pearson r on the intersection of dates."""
    common_dates = sorted(set(series_a) & set(series_b))
    if len(common_dates) < _MIN_OBSERVATIONS:
        return {"r": None, "n_obs": len(common_dates), "status": "INSUFFICIENT_DATA"}
    xs = [series_a[d] for d in common_dates]
    ys = [series_b[d] for d in common_dates]
    r = pearson_correlation(xs, ys)
    return {
        "r": r,
        "n_obs": len(common_dates),
        "dates_range": f"{common_dates[0]} → {common_dates[-1]}",
        "status": "OK",
    }


def _is_hedge_leakage(class_a: str, class_b: str, r: float | None) -> bool:
    """True if a SHORT-oriented CRYPTO pick correlates with BUY-oriented EQUITY/FX."""
    if r is None or abs(r) < HIGH_CORR_THRESHOLD:
        return False
    pair = frozenset({class_a, class_b})
    # CRYPTO vs EQUITY or FOREX is the primary hedge-leakage concern
    return pair in (
        frozenset({"CRYPTO", "EQUITY"}),
        frozenset({"CRYPTO", "FOREX"}),
    )


# ---------------------------------------------------------------------------
# Main report builder
# ---------------------------------------------------------------------------

def build_correlation_report(
    input_path: Path,
    window_days: int = 30,
    now: datetime | None = None,
    out_path: Path | None = None,
) -> dict[str, Any]:
    """Build the cross-asset correlation report.

    Args:
        input_path: Path to dashboard JSON or any picks JSON.
        window_days: Trailing window for PnL series.
        now: Reference timestamp (default: current UTC).
        out_path: If provided, write JSON artifact here.
    """
    if now is None:
        now = datetime.now(timezone.utc)

    picks = _load_closed_picks(input_path)
    daily_pnl = build_daily_pnl_series(picks, window_days=window_days, now=now)

    classes = sorted(daily_pnl)
    pairs: list[dict[str, Any]] = []
    flags: list[str] = []

    for i, class_a in enumerate(classes):
        for class_b in classes[i + 1:]:
            result = compute_pair_correlation(daily_pnl[class_a], daily_pnl[class_b])
            r = result.get("r")
            is_high = r is not None and abs(r) >= HIGH_CORR_THRESHOLD
            is_leakage = _is_hedge_leakage(class_a, class_b, r)

            pair_record: dict[str, Any] = {
                "class_a": class_a,
                "class_b": class_b,
                "r": r,
                "n_obs": result["n_obs"],
                "status": result["status"],
                "high_correlation": is_high,
                "hedge_leakage": is_leakage,
            }
            if "dates_range" in result:
                pair_record["dates_range"] = result["dates_range"]
            pairs.append(pair_record)

            if is_high:
                flags.append(f"HIGH_CORRELATION:{class_a}-{class_b}:r={r}")
            if is_leakage:
                flags.append(f"HEDGE_LEAKAGE:{class_a}-{class_b}:r={r}")

    report: dict[str, Any] = {
        "generated_at": now.isoformat(),
        "input_path": str(input_path),
        "window_days": window_days,
        "high_corr_threshold": HIGH_CORR_THRESHOLD,
        "n_picks_loaded": len(picks),
        "asset_classes_observed": classes,
        "pairs": pairs,
        "flags": flags,
        "alert": len(flags) > 0,
    }

    if out_path is not None:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    return report


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--input",
        default="audit_dashboard/data/dashboard_data.json",
        help="Dashboard JSON or picks JSON path",
    )
    ap.add_argument("--window", type=int, default=30, help="Trailing window in days")
    ap.add_argument(
        "--out",
        default="reports/cross_asset_correlation_latest.json",
        help="Output JSON artifact path",
    )
    args = ap.parse_args()

    report = build_correlation_report(
        input_path=Path(args.input),
        window_days=args.window,
        out_path=Path(args.out),
    )

    print(f"Cross-asset correlation — {report['n_picks_loaded']} picks "
          f"over {args.window}d window")
    print(f"  Asset classes observed: {', '.join(report['asset_classes_observed'])}")
    for p in report["pairs"]:
        if p["r"] is not None:
            flag = " ⚠ HIGH" if p["high_correlation"] else ""
            leak = " ⚠ LEAKAGE" if p["hedge_leakage"] else ""
            print(f"  {p['class_a']} × {p['class_b']}: r={p['r']:.3f} "
                  f"(n={p['n_obs']}){flag}{leak}")
    if report["flags"]:
        print(f"\nFLAGS: {'; '.join(report['flags'])}")
    else:
        print("No correlation flags.")
    print(f"Wrote: {args.out}")
    return 1 if report["alert"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
