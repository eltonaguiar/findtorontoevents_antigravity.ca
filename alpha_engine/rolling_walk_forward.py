#!/usr/bin/env python3
"""
ALPHA_ENGINE -- 30-Day Rolling Walk-Forward Validation
=======================================================
Hedge Fund Scorecard Gap 3: checks whether system performance is STABLE
across rolling 30-day windows, not just good in aggregate.

For each 30-day window of closed picks:
  - Win Rate (WR)
  - Profit Factor (PF)
  - Sharpe ratio (per-window)
  - Sortino ratio (per-window)

Flags any window where WR < 40% or PF < 1.0 as a "weak window".

Output:
  - alpha_engine/data/walk_forward_rolling_report.json

Usage:
    python rolling_walk_forward.py
    python rolling_walk_forward.py --window-days 14
"""

from __future__ import annotations

import json
import math
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# ── Windows UTF-8 fix ────────────────────────────────────────────────────────
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = Path(__file__).resolve().parent / "data"

# ── Thresholds for flagging weak windows ─────────────────────────────────────
WEAK_WR_THRESHOLD = 0.40     # Flag if win rate < 40%
WEAK_PF_THRESHOLD = 1.0      # Flag if profit factor < 1.0
MIN_PICKS_PER_WINDOW = 5     # Skip windows with fewer picks


# ── Data Loading ─────────────────────────────────────────────────────────────

def _load_closed_picks() -> list[dict]:
    """Load closed picks with timestamps, sorted chronologically."""
    picks = []

    # Primary: dashboard_payload.json
    payload_path = ROOT / "audit_trail" / "data" / "dashboard_payload.json"
    if payload_path.exists():
        try:
            with open(payload_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            closed = data.get("picks", {}).get("recent_closed", [])
            picks = [
                p for p in closed
                if p.get("pnl_pct") is not None
                and not p.get("_auto_expired", False)
            ]
        except Exception:
            pass

    # Fallback: closed_picks.json
    if not picks:
        fallback_path = DATA_DIR / "closed_picks.json"
        if fallback_path.exists():
            try:
                with open(fallback_path, "r", encoding="utf-8") as f:
                    raw = json.load(f)
                picks = [p for p in raw if p.get("pnl_pct") is not None]
            except Exception:
                pass

    # Parse timestamps and sort
    for p in picks:
        p["_ts"] = _parse_timestamp(p)

    picks = [p for p in picks if p["_ts"] is not None]
    picks.sort(key=lambda p: p["_ts"])
    return picks


def _parse_timestamp(pick: dict) -> datetime | None:
    """Extract a datetime from a pick dict."""
    for field in ("closed_at", "exit_date", "entry_date", "timestamp", "created_at", "generated_at"):
        val = pick.get(field)
        if not val:
            # Check inside extra_json
            extra = pick.get("extra_json", "")
            if isinstance(extra, str) and extra:
                try:
                    extra_data = json.loads(extra)
                    val = extra_data.get(field)
                except (json.JSONDecodeError, TypeError):
                    pass
        if val:
            try:
                if isinstance(val, datetime):
                    return val if val.tzinfo else val.replace(tzinfo=timezone.utc)
                # Handle date-only strings
                s = str(val).strip()
                if len(s) == 10:  # YYYY-MM-DD
                    return datetime.strptime(s, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
                return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
            except (ValueError, TypeError):
                continue
    return None


# ── Metric Computations (stdlib only) ────────────────────────────────────────

def _compute_window_metrics(pnl_values: list[float]) -> dict:
    """Compute WR, PF, Sharpe, Sortino for a single window of PnL values."""
    n = len(pnl_values)
    if n == 0:
        return {"n_picks": 0, "wr": 0.0, "pf": 0.0, "sharpe": 0.0, "sortino": 0.0}

    wins = [p for p in pnl_values if p > 0]
    losses = [p for p in pnl_values if p <= 0]
    wr = len(wins) / n if n > 0 else 0.0

    # Profit Factor
    sum_wins = sum(wins) if wins else 0.0
    sum_losses = abs(sum(losses)) if losses else 0.0
    pf = sum_wins / sum_losses if sum_losses > 0 else (float("inf") if sum_wins > 0 else 0.0)

    # Sharpe
    mean_ret = sum(pnl_values) / n
    if n >= 2:
        variance = sum((r - mean_ret) ** 2 for r in pnl_values) / (n - 1)
        std_dev = math.sqrt(variance)
        sharpe = mean_ret / std_dev if std_dev > 0 else 0.0
    else:
        sharpe = 0.0

    # Sortino (target = 0)
    downside_sq = [(r ** 2) for r in pnl_values if r < 0]
    if downside_sq:
        downside_dev = math.sqrt(sum(downside_sq) / len(downside_sq))
        sortino = mean_ret / downside_dev if downside_dev > 0 else 0.0
    else:
        sortino = float("inf") if mean_ret > 0 else 0.0

    return {
        "n_picks": n,
        "total_pnl_pct": round(sum(pnl_values), 4),
        "mean_pnl_pct": round(mean_ret, 6),
        "wr": round(wr, 4),
        "pf": round(pf, 4) if math.isfinite(pf) else "inf",
        "sharpe": round(sharpe, 4),
        "sortino": round(sortino, 4) if math.isfinite(sortino) else "inf",
    }


# ── Main Runner ──────────────────────────────────────────────────────────────

def run(window_days: int = 30) -> dict:
    """Run 30-day rolling walk-forward validation.

    Splits closed picks into non-overlapping windows of `window_days` days,
    computes per-window metrics, and flags weak windows.

    Returns the full report dict.
    """
    picks = _load_closed_picks()
    if len(picks) < MIN_PICKS_PER_WINDOW:
        msg = f"Insufficient closed picks ({len(picks)}) for rolling walk-forward."
        print(f"[rolling_wf] {msg}")
        return {"status": "insufficient_data", "message": msg, "windows": []}

    print(f"[rolling_wf] Loaded {len(picks)} closed picks")

    # Determine date range
    first_ts = picks[0]["_ts"]
    last_ts = picks[-1]["_ts"]
    total_days = (last_ts - first_ts).days
    print(f"[rolling_wf] Date range: {first_ts.date()} to {last_ts.date()} ({total_days} days)")

    # Build windows
    windows = []
    window_start = first_ts
    window_delta = timedelta(days=window_days)

    while window_start < last_ts:
        window_end = window_start + window_delta
        window_picks = [
            p for p in picks
            if window_start <= p["_ts"] < window_end
        ]

        pnl_values = [float(p.get("pnl_pct", 0) or 0) for p in window_picks]

        if len(pnl_values) >= MIN_PICKS_PER_WINDOW:
            metrics = _compute_window_metrics(pnl_values)
            is_weak = (
                metrics["wr"] < WEAK_WR_THRESHOLD
                or (isinstance(metrics["pf"], (int, float)) and metrics["pf"] < WEAK_PF_THRESHOLD)
            )
            window_info = {
                "window_start": window_start.strftime("%Y-%m-%d"),
                "window_end": window_end.strftime("%Y-%m-%d"),
                "is_weak": is_weak,
                **metrics,
            }
            windows.append(window_info)

        window_start = window_end

    if not windows:
        msg = "No windows had enough picks for analysis."
        print(f"[rolling_wf] {msg}")
        return {"status": "no_valid_windows", "message": msg, "windows": []}

    # Aggregate statistics across windows
    wrs = [w["wr"] for w in windows]
    pfs = [w["pf"] for w in windows if isinstance(w["pf"], (int, float))]
    sharpes = [w["sharpe"] for w in windows]
    sortinos = [w["sortino"] for w in windows if isinstance(w["sortino"], (int, float))]
    weak_windows = [w for w in windows if w["is_weak"]]

    def _safe_std(vals: list[float]) -> float:
        if len(vals) < 2:
            return 0.0
        mean = sum(vals) / len(vals)
        return math.sqrt(sum((v - mean) ** 2 for v in vals) / (len(vals) - 1))

    aggregate = {
        "total_windows": len(windows),
        "weak_windows": len(weak_windows),
        "stability_pct": round(100.0 * (1 - len(weak_windows) / len(windows)), 2),
        "wr_mean": round(sum(wrs) / len(wrs), 4),
        "wr_std": round(_safe_std(wrs), 4),
        "wr_min": round(min(wrs), 4),
        "wr_max": round(max(wrs), 4),
        "pf_mean": round(sum(pfs) / len(pfs), 4) if pfs else 0.0,
        "pf_std": round(_safe_std(pfs), 4) if pfs else 0.0,
        "sharpe_mean": round(sum(sharpes) / len(sharpes), 4),
        "sharpe_std": round(_safe_std(sharpes), 4),
        "sortino_mean": round(sum(sortinos) / len(sortinos), 4) if sortinos else 0.0,
    }

    # Overall stability assessment
    if aggregate["stability_pct"] >= 80:
        verdict = "STABLE: >= 80% of windows are above thresholds"
    elif aggregate["stability_pct"] >= 60:
        verdict = "MODERATE: 60-80% of windows pass -- some regime sensitivity"
    else:
        verdict = "UNSTABLE: < 60% of windows pass -- performance is not consistent"

    report = {
        "status": "complete",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "parameters": {
            "window_days": window_days,
            "weak_wr_threshold": WEAK_WR_THRESHOLD,
            "weak_pf_threshold": WEAK_PF_THRESHOLD,
            "min_picks_per_window": MIN_PICKS_PER_WINDOW,
        },
        "total_closed_picks": len(picks),
        "date_range": {
            "start": first_ts.strftime("%Y-%m-%d"),
            "end": last_ts.strftime("%Y-%m-%d"),
            "total_days": total_days,
        },
        "aggregate": aggregate,
        "verdict": verdict,
        "windows": windows,
        "weak_window_details": weak_windows,
    }

    # ── Save ─────────────────────────────────────────────────────────────────
    os.makedirs(DATA_DIR, exist_ok=True)
    out_path = DATA_DIR / "walk_forward_rolling_report.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print(f"[rolling_wf] Saved to {out_path}")

    # ── Console summary ──────────────────────────────────────────────────────
    print()
    print("=" * 65)
    print("  30-DAY ROLLING WALK-FORWARD VALIDATION")
    print("=" * 65)
    print(f"  Total windows         : {aggregate['total_windows']}")
    print(f"  Weak windows          : {aggregate['weak_windows']}")
    print(f"  Stability             : {aggregate['stability_pct']:.1f}%")
    print(f"  Verdict               : {verdict}")
    print("-" * 65)
    print(f"  WR  (mean +/- std)    : {aggregate['wr_mean']:.4f} +/- {aggregate['wr_std']:.4f}")
    print(f"  WR  (min / max)       : {aggregate['wr_min']:.4f} / {aggregate['wr_max']:.4f}")
    print(f"  PF  (mean +/- std)    : {aggregate['pf_mean']:.4f} +/- {aggregate['pf_std']:.4f}")
    print(f"  Sharpe (mean +/- std) : {aggregate['sharpe_mean']:.4f} +/- {aggregate['sharpe_std']:.4f}")
    print(f"  Sortino (mean)        : {aggregate['sortino_mean']:.4f}")
    print("-" * 65)

    if weak_windows:
        print("  FLAGGED WEAK WINDOWS:")
        for w in weak_windows[:10]:
            pf_str = f"{w['pf']:.2f}" if isinstance(w["pf"], (int, float)) else str(w["pf"])
            print(f"    {w['window_start']} to {w['window_end']}: "
                  f"WR={w['wr']:.1%}, PF={pf_str}, "
                  f"n={w['n_picks']}")
        if len(weak_windows) > 10:
            print(f"    ... and {len(weak_windows) - 10} more")
    else:
        print("  No weak windows detected -- performance is consistent!")

    print("=" * 65)

    return report


# ── CLI ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="30-day rolling walk-forward validation")
    parser.add_argument("--window-days", type=int, default=30,
                        help="Window size in days (default: 30)")
    args = parser.parse_args()
    run(window_days=args.window_days)
