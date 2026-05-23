#!/usr/bin/env python3
"""Alpha Decay Monitor — detect strategies whose edge is degrading.

For each strategy with >= 20 closed picks:
  1. Compute rolling 20-trade Sharpe ratio (using PnL % as returns)
  2. Compare current rolling Sharpe to historical peak Sharpe
  3. If current < peak - 2*std of rolling Sharpe history -> DECAYING
  4. If current < 0 for last 20 trades -> DEAD

Results are written to tools/alpha_decay_results.json and printed as summary.

Usage:
    python tools/alpha_decay_monitor.py                    # use default closed picks
    python tools/alpha_decay_monitor.py --input FILE.json  # specify closed picks file
"""

import json
import math
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# Resolve paths
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
OUTPUT_FILE = SCRIPT_DIR / "alpha_decay_results.json"

# Default closed picks locations (try multiple)
CLOSED_PICKS_CANDIDATES = [
    REPO_ROOT / "alpha_engine" / "data" / "closed_picks.json",
    REPO_ROOT / "alpha_engine" / "data" / "closed_picks_history.json",
    REPO_ROOT / "audit_trail" / "data" / "closed_picks.json",
    REPO_ROOT / "data" / "closed_picks.json",
]

# Minimum trades required per strategy for analysis
MIN_TRADES = 20
# Rolling window size for Sharpe calculation
ROLLING_WINDOW = 20
# Standard deviations below peak to flag as DECAYING
DECAY_SIGMA_THRESHOLD = 2.0


def load_closed_picks(filepath: Optional[str] = None) -> List[Dict[str, Any]]:
    """Load closed picks from file, trying multiple candidates if none specified."""
    if filepath:
        path = Path(filepath)
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, list) else data.get("picks", data.get("closed", []))

    for candidate in CLOSED_PICKS_CANDIDATES:
        if candidate.exists():
            try:
                with open(candidate, "r", encoding="utf-8") as f:
                    data = json.load(f)
                picks = data if isinstance(data, list) else data.get("picks", data.get("closed", []))
                if picks:
                    print(f"[INFO] Loaded {len(picks)} closed picks from {candidate}")
                    return picks
            except (json.JSONDecodeError, KeyError):
                continue

    print("[WARN] No closed picks file found. Checked:")
    for c in CLOSED_PICKS_CANDIDATES:
        print(f"  - {c}")
    return []


def _safe_float(val: Any) -> float:
    """Safely convert value to float."""
    try:
        return float(val or 0)
    except (ValueError, TypeError):
        return 0.0


def compute_rolling_sharpe(returns: List[float], window: int = ROLLING_WINDOW) -> List[float]:
    """Compute rolling Sharpe ratio over a window of returns.

    Sharpe = mean(returns) / std(returns) if std > 0, else 0.
    Returns a list of Sharpe values, one per window position.
    """
    if len(returns) < window:
        return []

    sharpe_values = []
    for i in range(len(returns) - window + 1):
        w = returns[i : i + window]
        mean_r = sum(w) / len(w)
        variance = sum((r - mean_r) ** 2 for r in w) / len(w)
        std_r = math.sqrt(variance) if variance > 0 else 0.0
        sharpe = mean_r / std_r if std_r > 1e-9 else 0.0
        sharpe_values.append(round(sharpe, 4))

    return sharpe_values


def analyze_strategy_decay(
    strategy_name: str, picks: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Analyze alpha decay for a single strategy.

    Returns:
        {
            "strategy": str,
            "n_trades": int,
            "status": "HEALTHY" | "DECAYING" | "DEAD",
            "current_sharpe": float,
            "peak_sharpe": float,
            "sharpe_std": float,
            "decay_threshold": float,
            "rolling_sharpe_history": [float, ...],
            "last_20_wr": float,
            "last_20_avg_pnl": float,
        }
    """
    returns = [_safe_float(p.get("pnl_pct", 0)) for p in picks]
    n = len(returns)

    result = {
        "strategy": strategy_name,
        "n_trades": n,
        "status": "HEALTHY",
        "current_sharpe": 0.0,
        "peak_sharpe": 0.0,
        "sharpe_std": 0.0,
        "decay_threshold": 0.0,
        "rolling_sharpe_history": [],
        "last_20_wr": 0.0,
        "last_20_avg_pnl": 0.0,
    }

    if n < MIN_TRADES:
        result["status"] = "INSUFFICIENT_DATA"
        return result

    # Compute rolling Sharpe series
    rolling = compute_rolling_sharpe(returns, ROLLING_WINDOW)
    result["rolling_sharpe_history"] = rolling

    if not rolling:
        result["status"] = "INSUFFICIENT_DATA"
        return result

    current_sharpe = rolling[-1]
    peak_sharpe = max(rolling)

    # Standard deviation of rolling Sharpe values
    mean_sharpe = sum(rolling) / len(rolling)
    variance = sum((s - mean_sharpe) ** 2 for s in rolling) / len(rolling)
    sharpe_std = math.sqrt(variance) if variance > 0 else 0.0

    decay_threshold = peak_sharpe - DECAY_SIGMA_THRESHOLD * sharpe_std

    result["current_sharpe"] = round(current_sharpe, 4)
    result["peak_sharpe"] = round(peak_sharpe, 4)
    result["sharpe_std"] = round(sharpe_std, 4)
    result["decay_threshold"] = round(decay_threshold, 4)

    # Last 20 trades stats
    last_20 = returns[-ROLLING_WINDOW:]
    wins = sum(1 for r in last_20 if r > 0)
    result["last_20_wr"] = round(wins / len(last_20) * 100, 1)
    result["last_20_avg_pnl"] = round(sum(last_20) / len(last_20), 3)

    # Classification
    if current_sharpe < 0:
        result["status"] = "DEAD"
    elif current_sharpe < decay_threshold:
        result["status"] = "DECAYING"
    else:
        result["status"] = "HEALTHY"

    return result


def run_alpha_decay_monitor(closed_picks: Optional[List[Dict[str, Any]]] = None,
                            input_file: Optional[str] = None) -> Dict[str, Any]:
    """Run the full alpha decay monitor.

    Args:
        closed_picks: Pre-loaded closed picks (optional).
        input_file: Path to closed picks JSON file (optional).

    Returns:
        Full results dict with per-strategy analysis and summary.
    """
    if closed_picks is None:
        closed_picks = load_closed_picks(input_file)

    if not closed_picks:
        print("[ERROR] No closed picks available for alpha decay analysis.")
        return {"strategies": [], "summary": {"total": 0}, "computed_at": ""}

    # Group by strategy
    strategy_map: Dict[str, list] = {}
    for p in closed_picks:
        strat = str(p.get("strategy", "") or "").strip()
        if strat:
            strategy_map.setdefault(strat, []).append(p)

    # Analyze each strategy
    results = []
    for strat_name, picks in sorted(strategy_map.items()):
        if len(picks) < MIN_TRADES:
            continue
        analysis = analyze_strategy_decay(strat_name, picks)
        results.append(analysis)

    # Summary counts
    healthy = sum(1 for r in results if r["status"] == "HEALTHY")
    decaying = sum(1 for r in results if r["status"] == "DECAYING")
    dead = sum(1 for r in results if r["status"] == "DEAD")
    insufficient = sum(1 for r in results if r["status"] == "INSUFFICIENT_DATA")

    summary = {
        "total_strategies_analyzed": len(results),
        "healthy": healthy,
        "decaying": decaying,
        "dead": dead,
        "insufficient_data": insufficient,
        "computed_at": datetime.now(timezone.utc).isoformat(),
    }

    # Sort: DEAD first, then DECAYING, then HEALTHY
    status_order = {"DEAD": 0, "DECAYING": 1, "HEALTHY": 2, "INSUFFICIENT_DATA": 3}
    results.sort(key=lambda r: (status_order.get(r["status"], 9), -r["n_trades"]))

    output = {
        "summary": summary,
        "strategies": results,
    }

    # Write results
    try:
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            # Strip rolling_sharpe_history from file output to keep it manageable
            slim_results = []
            for r in results:
                slim = dict(r)
                # Keep only last 5 rolling values for context
                if slim.get("rolling_sharpe_history"):
                    slim["rolling_sharpe_last5"] = slim["rolling_sharpe_history"][-5:]
                slim.pop("rolling_sharpe_history", None)
                slim_results.append(slim)
            json.dump(
                {"summary": summary, "strategies": slim_results},
                f, indent=2, ensure_ascii=False,
            )
        print(f"[INFO] Results written to {OUTPUT_FILE}")
    except OSError as e:
        print(f"[WARN] Could not write results: {e}")

    # Print summary
    print("\n" + "=" * 60)
    print("  ALPHA DECAY MONITOR RESULTS")
    print("=" * 60)
    print(f"  Strategies analyzed: {len(results)}")
    print(f"  HEALTHY:  {healthy}")
    print(f"  DECAYING: {decaying}")
    print(f"  DEAD:     {dead}")
    print(f"  (Insufficient data: {insufficient})")
    print("=" * 60)

    if dead > 0:
        print("\n  DEAD strategies (Sharpe < 0 on last 20 trades):")
        for r in results:
            if r["status"] == "DEAD":
                print(
                    f"    - {r['strategy']:<40s} "
                    f"Sharpe={r['current_sharpe']:+.3f}  "
                    f"WR={r['last_20_wr']:.0f}%  "
                    f"n={r['n_trades']}"
                )

    if decaying > 0:
        print("\n  DECAYING strategies (Sharpe dropped >2-sigma from peak):")
        for r in results:
            if r["status"] == "DECAYING":
                drop = r["peak_sharpe"] - r["current_sharpe"]
                print(
                    f"    - {r['strategy']:<40s} "
                    f"Sharpe={r['current_sharpe']:+.3f} (peak={r['peak_sharpe']:+.3f}, "
                    f"drop={drop:.3f})  "
                    f"WR={r['last_20_wr']:.0f}%  "
                    f"n={r['n_trades']}"
                )

    print()
    return output


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Alpha Decay Monitor")
    parser.add_argument("--input", "-i", help="Path to closed picks JSON file")
    args = parser.parse_args()

    run_alpha_decay_monitor(input_file=args.input)
