"""
Portfolio Tracker — Merges closed picks from ALL trading systems
and computes portfolio-level metrics.

Usage:
    python -m portfolio_tracker.tracker
"""

import json
import math
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parent.parent

SYSTEM_CLOSED_PATHS = {
    "mercury2": "mercury2/data/closed_picks.json",
    "alpha_engine": "alpha_engine/data/closed_picks.json",
    "kimi": "KIMI_RISEOFTHECLAW/data/signal_tracking.json",
    "signal_engine": "crypto_signal_engine/data/closed_picks.json",
    "ml_bg_a": "ml_battleground/system_a_filter/data/closed_picks.json",
    "ml_bg_b": "ml_battleground/system_b_regime/data/closed_picks.json",
    "breakout_c": "breakout_arena/approach_c_spike_reverse/data/closed_picks.json",
    "claude_gainer": "claude_gainer_ml/tracker/claude_performance.json",
}


# ---------------------------------------------------------------------------
# Normalizers — each returns a list of unified dicts
# ---------------------------------------------------------------------------

def _extract_pnl(record: dict) -> float | None:
    """Try common pnl field names in priority order."""
    for key in ("pnl_pct", "net_pnl_pct", "realized_pnl_pct"):
        val = record.get(key)
        if val is not None:
            try:
                return float(val)
            except (TypeError, ValueError):
                pass
    return None


def _extract_exit_time(record: dict) -> str:
    """Try common exit-time field names."""
    for key in ("exit_time", "closed_at", "close_time", "exit_date"):
        val = record.get(key)
        if val:
            return str(val)
    return ""


def _is_win(record: dict) -> bool | None:
    """Determine win/loss from status-like fields."""
    for key in ("status", "result", "outcome"):
        val = str(record.get(key, "")).upper()
        if val in ("WON", "TP", "WIN", "PROFIT"):
            return True
        if val in ("LOST", "SL", "LOSS", "STOPPED"):
            return False
    return None


def _normalize_mercury2(records: list[dict]) -> list[dict]:
    out = []
    for r in records:
        pnl = r.get("pnl_pct")
        if pnl is None:
            continue
        out.append({
            "symbol": r.get("symbol", "UNKNOWN"),
            "direction": r.get("direction", r.get("side", "LONG")).upper(),
            "entry_price": r.get("entry_price", 0),
            "exit_price": r.get("exit_price", 0),
            "pnl_pct": float(pnl),
            "exit_time": r.get("exit_time", ""),
            "system": "mercury2",
            "strategy": r.get("strategy", "mercury2"),
        })
    return out


def _normalize_alpha_engine(records: list[dict]) -> list[dict]:
    out = []
    for r in records:
        pnl = r.get("net_pnl_pct")
        if pnl is None:
            pnl = r.get("pnl_pct")
        if pnl is None:
            continue
        out.append({
            "symbol": r.get("symbol", "UNKNOWN"),
            "direction": r.get("direction", r.get("side", "LONG")).upper(),
            "entry_price": r.get("entry_price", 0),
            "exit_price": r.get("exit_price", 0),
            "pnl_pct": float(pnl),
            "exit_time": r.get("closed_at", r.get("exit_time", "")),
            "system": "alpha_engine",
            "strategy": r.get("strategy", "alpha_engine"),
        })
    return out


def _normalize_kimi(records: list[dict]) -> list[dict]:
    out = []
    for r in records:
        pnl = r.get("realized_pnl_pct")
        if pnl is None:
            pnl = _extract_pnl(r)
        if pnl is None:
            continue
        out.append({
            "symbol": r.get("symbol", r.get("pair", "UNKNOWN")),
            "direction": r.get("direction", r.get("side", "LONG")).upper(),
            "entry_price": r.get("entry_price", r.get("entry", 0)),
            "exit_price": r.get("exit_price", r.get("exit", 0)),
            "pnl_pct": float(pnl),
            "exit_time": r.get("closed_at", r.get("exit_time", "")),
            "system": "kimi",
            "strategy": r.get("strategy", r.get("algorithm", "kimi")),
        })
    return out


def _normalize_generic(records: list[dict], system_name: str) -> list[dict]:
    """Fallback normalizer for ml_battleground, signal_engine, etc."""
    out = []
    for r in records:
        pnl = _extract_pnl(r)
        if pnl is None:
            continue
        out.append({
            "symbol": r.get("symbol", r.get("pair", "UNKNOWN")),
            "direction": r.get("direction", r.get("side", "LONG")).upper(),
            "entry_price": r.get("entry_price", 0),
            "exit_price": r.get("exit_price", 0),
            "pnl_pct": float(pnl),
            "exit_time": _extract_exit_time(r),
            "system": system_name,
            "strategy": r.get("strategy", system_name),
        })
    return out


NORMALIZERS = {
    "mercury2": _normalize_mercury2,
    "alpha_engine": _normalize_alpha_engine,
    "kimi": _normalize_kimi,
}


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------

def load_all_closed_picks() -> list[dict]:
    """Load and normalize closed picks from every system."""
    all_trades: list[dict] = []

    for system, rel_path in SYSTEM_CLOSED_PATHS.items():
        fpath = ROOT / rel_path
        if not fpath.exists():
            print(f"  [SKIP] {system}: {fpath} not found", file=sys.stderr)
            continue

        try:
            with open(fpath, "r", encoding="utf-8") as f:
                raw = json.load(f)
        except (json.JSONDecodeError, OSError) as exc:
            print(f"  [WARN] {system}: failed to read {fpath}: {exc}", file=sys.stderr)
            continue

        # Handle both list-of-records and dict-with-list patterns
        records: list[dict] = []
        if isinstance(raw, list):
            records = raw
        elif isinstance(raw, dict):
            # Try common wrapper keys
            for key in ("closed", "closed_picks", "trades", "signals", "picks", "data"):
                if key in raw and isinstance(raw[key], list):
                    records = raw[key]
                    break
            if not records:
                # Maybe the dict itself wraps a flat list at top level
                records = [raw] if _extract_pnl(raw) is not None else []

        normalizer = NORMALIZERS.get(system, lambda recs: _normalize_generic(recs, system))
        normalized = normalizer(records)
        print(f"  [{system}] loaded {len(normalized)} closed picks from {fpath.name}")
        all_trades.extend(normalized)

    return all_trades


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------

def compute_sharpe(returns: list[float], annualize: float = 252.0) -> float:
    """Sharpe ratio from a list of per-trade returns (as decimals, e.g. 0.05 = 5%)."""
    if len(returns) < 2:
        return 0.0
    arr = np.array(returns, dtype=np.float64)
    std = np.std(arr, ddof=0)
    if std == 0:
        return 0.0
    return float(np.mean(arr) / std * np.sqrt(annualize))


def compute_max_drawdown(pnl_series: list[float]) -> float:
    """Max drawdown (negative %) from a cumulative P&L series."""
    if not pnl_series:
        return 0.0
    cum = np.cumsum(pnl_series)
    peak = np.maximum.accumulate(cum)
    drawdowns = cum - peak
    return float(np.min(drawdowns)) if len(drawdowns) > 0 else 0.0


def compute_calmar(total_return_pct: float, max_dd_pct: float) -> float:
    """Calmar ratio = annualized return / |max drawdown|."""
    if max_dd_pct == 0:
        return 0.0
    return round(total_return_pct / abs(max_dd_pct), 2)


def compute_system_weights(system_sharpes: dict[str, float]) -> dict[str, float]:
    """Softmax over Sharpe ratios clipped at 0."""
    clipped = {sys: max(0.0, s) for sys, s in system_sharpes.items()}
    exp_vals = {sys: math.exp(s) for sys, s in clipped.items()}
    total = sum(exp_vals.values())
    if total == 0:
        n = len(clipped)
        return {sys: round(1.0 / n, 3) if n > 0 else 0.0 for sys in clipped}
    return {sys: round(v / total, 3) for sys, v in exp_vals.items()}


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def build_portfolio_metrics(trades: list[dict]) -> dict[str, Any]:
    """Compute all portfolio metrics from unified trade list."""

    # Sort by exit_time where available
    def sort_key(t: dict):
        et = t.get("exit_time", "")
        return et if et else "9999"

    sorted_trades = sorted(trades, key=sort_key)

    # Per-trade returns as decimals
    returns = [t["pnl_pct"] / 100.0 for t in sorted_trades]

    # Overall metrics
    all_sharpe = compute_sharpe(returns)
    rolling_30 = compute_sharpe(returns[-30:]) if len(returns) >= 5 else all_sharpe
    max_dd = compute_max_drawdown([t["pnl_pct"] for t in sorted_trades])
    total_pnl = sum(t["pnl_pct"] for t in sorted_trades)
    wins = sum(1 for t in sorted_trades if t["pnl_pct"] > 0)
    losses = sum(1 for t in sorted_trades if t["pnl_pct"] <= 0)
    win_rate = wins / len(sorted_trades) if sorted_trades else 0.0
    calmar = compute_calmar(total_pnl, max_dd)

    # Equity curve (cumulative P&L %)
    equity_curve = []
    cum = 0.0
    for t in sorted_trades:
        cum += t["pnl_pct"]
        equity_curve.append(round(cum, 2))

    # Per-system breakdown
    by_system: dict[str, list[dict]] = {}
    for t in sorted_trades:
        by_system.setdefault(t["system"], []).append(t)

    per_system = {}
    system_sharpes = {}
    for sys, sys_trades in by_system.items():
        sys_returns = [t["pnl_pct"] / 100.0 for t in sys_trades]
        s = compute_sharpe(sys_returns)
        system_sharpes[sys] = s
        sys_wins = sum(1 for t in sys_trades if t["pnl_pct"] > 0)
        sys_pnl = sum(t["pnl_pct"] for t in sys_trades)
        per_system[sys] = {
            "sharpe": round(s, 2),
            "win_rate": round(sys_wins / len(sys_trades), 3) if sys_trades else 0.0,
            "closed": len(sys_trades),
            "pnl_pct": round(sys_pnl, 2),
            "weight": 0.0,  # filled below
        }

    weights = compute_system_weights(system_sharpes)
    for sys, w in weights.items():
        if sys in per_system:
            per_system[sys]["weight"] = w

    return {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "total_closed_picks": len(sorted_trades),
        "overall": {
            "sharpe": round(all_sharpe, 2),
            "rolling_sharpe_30": round(rolling_30, 2),
            "max_drawdown_pct": round(max_dd, 2),
            "calmar_ratio": calmar,
            "win_rate": round(win_rate, 3),
            "total_pnl_pct": round(total_pnl, 2),
            "total_wins": wins,
            "total_losses": losses,
        },
        "per_system": per_system,
        "system_weights": weights,
        "equity_curve": equity_curve,
    }


def main():
    print("=== Portfolio Tracker ===")
    print(f"Root: {ROOT}\n")

    print("Loading closed picks from all systems...")
    trades = load_all_closed_picks()

    if not trades:
        print("\nNo closed picks found across any system. Nothing to compute.")
        sys.exit(0)

    print(f"\nTotal unified trades: {len(trades)}")

    metrics = build_portfolio_metrics(trades)

    # Write output
    out_dir = ROOT / "data"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "portfolio_metrics.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)
    print(f"\nMetrics written to: {out_path}")

    # Print summary
    o = metrics["overall"]
    print(f"\n--- Portfolio Summary ---")
    print(f"  Total Picks:       {metrics['total_closed_picks']}")
    print(f"  Win Rate:          {o['win_rate']:.1%} ({o['total_wins']}W / {o['total_losses']}L)")
    print(f"  Total P&L:         {o['total_pnl_pct']:+.2f}%")
    print(f"  Sharpe (all-time): {o['sharpe']:.2f}")
    print(f"  Sharpe (last 30):  {o['rolling_sharpe_30']:.2f}")
    print(f"  Max Drawdown:      {o['max_drawdown_pct']:.2f}%")
    print(f"  Calmar Ratio:      {o['calmar_ratio']:.2f}")

    print(f"\n--- System Weights ---")
    for sys, w in sorted(metrics["system_weights"].items(), key=lambda x: -x[1]):
        info = metrics["per_system"].get(sys, {})
        print(f"  {sys:20s}  weight={w:.3f}  sharpe={info.get('sharpe', 0):.2f}  "
              f"WR={info.get('win_rate', 0):.1%}  closed={info.get('closed', 0)}  "
              f"pnl={info.get('pnl_pct', 0):+.2f}%")


if __name__ == "__main__":
    main()
