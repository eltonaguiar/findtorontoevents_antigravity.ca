#!/usr/bin/env python3
"""
ALPHA_ENGINE -- Adaptive Trust Tuner
=====================================
Automatically adjusts strategy trust weights based on forward performance.
Strategies that consistently hit TP get higher confidence; strategies that
consistently hit SL get lower confidence.

Standalone:  python adaptive_trust_tuner.py          # prints report + writes JSON
Imported:    from adaptive_trust_tuner import apply_trust_adjustments

Output:      data/trust_adjustments.json

Respects the "mutate before kill" rule -- NEVER deletes strategies, only adjusts
confidence within a bounded range.
"""

from __future__ import annotations

import json
import os
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ENGINE_DIR = Path(__file__).resolve().parent
DATA_DIR = ENGINE_DIR / "data"
CLOSED_PICKS_PATH = DATA_DIR / "closed_picks.json"
TRUST_ADJ_PATH = DATA_DIR / "trust_adjustments.json"

# ---------------------------------------------------------------------------
# Cache for apply_trust_adjustments (avoids re-reading JSON on every pick)
# ---------------------------------------------------------------------------
_adj_cache: dict | None = None
_adj_cache_ts: float = 0.0
_ADJ_CACHE_TTL = 3600  # 1 hour


# ---------------------------------------------------------------------------
# Core: compute adjustments from closed picks
# ---------------------------------------------------------------------------

def load_closed_picks() -> list[dict]:
    """Load closed picks from JSON file."""
    if not CLOSED_PICKS_PATH.exists():
        return []
    try:
        with open(CLOSED_PICKS_PATH, "r") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def _compute_rolling_metrics(trades: list[dict]) -> dict:
    """Compute rolling win-rate and profit-factor metrics for a list of trades.

    Trades should be sorted chronologically (oldest first).
    """
    total = len(trades)
    if total == 0:
        return {
            "total_trades": 0,
            "wr_last10": None,
            "wr_last20": None,
            "wr_last50": None,
            "profit_factor_last20": None,
            "avg_pnl": None,
        }

    def _win_rate(subset: list[dict]) -> float | None:
        if not subset:
            return None
        wins = sum(1 for t in subset if t.get("status") == "WON")
        return round(wins / len(subset), 4)

    def _profit_factor(subset: list[dict]) -> float | None:
        if not subset:
            return None
        gross_wins = sum(abs(t.get("pnl_pct") or 0) for t in subset if t.get("status") == "WON")
        gross_losses = sum(abs(t.get("pnl_pct") or 0) for t in subset if t.get("status") == "LOST")
        if gross_losses == 0:
            return 99.0 if gross_wins > 0 else 1.0
        return round(gross_wins / gross_losses, 2)

    def _avg_pnl(subset: list[dict]) -> float | None:
        if not subset:
            return None
        return round(sum((t.get("pnl_pct") or 0) for t in subset) / len(subset), 4)

    last10 = trades[-10:] if total >= 5 else trades
    last20 = trades[-20:] if total >= 10 else trades
    last50 = trades[-50:] if total >= 20 else trades

    return {
        "total_trades": total,
        "wr_last10": _win_rate(last10),
        "wr_last20": _win_rate(last20),
        "wr_last50": _win_rate(last50) if total >= 20 else None,
        "profit_factor_last20": _profit_factor(last20),
        "avg_pnl": _avg_pnl(trades),
    }


def _strategy_boost(metrics: dict) -> tuple[float, str]:
    """Compute trust boost for a strategy based on rolling metrics.

    Returns (boost_value, human_reason).
    """
    total = metrics["total_trades"]
    wr10 = metrics["wr_last10"]

    if wr10 is None or total < 5:
        return 0.0, f"insufficient data ({total} trades)"

    # Use the most recent window (last 10) for responsiveness
    pf = metrics.get("profit_factor_last20")
    avg_pnl = metrics.get("avg_pnl")

    # Fix 6: If WR looks decent but profit_factor < 1.0 AND avg_pnl < 0,
    # the strategy is winning often but losing MORE per loss (bad R:R).
    # Boost should be NEGATIVE regardless of recent WR.
    if (pf is not None and pf < 1.0
            and avg_pnl is not None and avg_pnl < 0
            and wr10 >= 0.50):
        return -0.05, (f"{wr10*100:.0f}% WR but PF={pf:.2f} < 1.0, "
                        f"avg_pnl={avg_pnl:.2f}% (losing money despite wins)")

    if wr10 >= 0.70 and total >= 10:
        return +0.15, f"{wr10*100:.0f}% WR over last {min(total,10)} trades"
    if wr10 >= 0.60 and total >= 10:
        return +0.10, f"{wr10*100:.0f}% WR over last {min(total,10)} trades"
    if wr10 >= 0.50 and total >= 5:
        return +0.05, f"{wr10*100:.0f}% WR over last {min(total,10)} trades"
    if wr10 < 0.30 and total >= 10:
        return -0.15, f"{wr10*100:.0f}% WR over last {min(total,10)} trades"
    if wr10 < 0.40 and total >= 10:
        return -0.10, f"{wr10*100:.0f}% WR over last {min(total,10)} trades"

    return 0.0, f"{wr10*100:.0f}% WR ({total} trades, neutral)"


def _symbol_boost(trades: list[dict]) -> tuple[float, str]:
    """Compute trust boost for a specific strategy+symbol combo.

    Returns (boost_value, human_reason).
    """
    total = len(trades)
    if total < 5:
        return 0.0, f"insufficient data ({total} trades)"

    wins = sum(1 for t in trades if t.get("status") == "WON")
    wr = wins / total

    if wr >= 0.70:
        return +0.08, f"{wr*100:.0f}% WR ({total} trades)"
    if wr < 0.30:
        return -0.10, f"{wr*100:.0f}% WR ({total} trades)"

    return 0.0, f"{wr*100:.0f}% WR ({total} trades, neutral)"


def compute_trust_adjustments() -> dict:
    """Analyze all closed picks and produce trust adjustment recommendations.

    Returns the full adjustments dict (also written to trust_adjustments.json).
    """
    closed = load_closed_picks()

    # Filter to only completed trades (WON or LOST)
    completed = [
        p for p in closed
        if p.get("status") in ("WON", "LOST")
    ]

    if not completed:
        print("[TRUST TUNER] No completed trades found, writing empty adjustments")
        result = {
            "strategy_adjustments": {},
            "symbol_adjustments": {},
            "meta": {
                "total_closed_analyzed": 0,
                "strategies_analyzed": 0,
                "strategies_boosted": 0,
                "strategies_penalized": 0,
            },
            "last_updated": datetime.now(timezone.utc).isoformat(),
        }
        _write_adjustments(result)
        return result

    # Sort by exit_date for chronological ordering
    completed.sort(key=lambda p: p.get("exit_date", "") or "")

    # --- Group by strategy ---
    by_strategy: dict[str, list[dict]] = defaultdict(list)
    for p in completed:
        strat = p.get("strategy", "unknown")
        by_strategy[strat].append(p)

    # --- Group by strategy + symbol ---
    by_strat_sym: dict[str, dict[str, list[dict]]] = defaultdict(lambda: defaultdict(list))
    for p in completed:
        strat = p.get("strategy", "unknown")
        sym = p.get("symbol", "UNKNOWN")
        by_strat_sym[strat][sym].append(p)

    # --- Compute strategy-level adjustments ---
    strategy_adj: dict[str, dict] = {}
    boosted = 0
    penalized = 0

    for strat, trades in by_strategy.items():
        metrics = _compute_rolling_metrics(trades)
        boost, reason = _strategy_boost(metrics)
        if boost != 0.0:
            strategy_adj[strat] = {
                "boost": boost,
                "reason": reason,
                "total_trades": metrics["total_trades"],
                "wr_last10": metrics["wr_last10"],
                "wr_last20": metrics["wr_last20"],
                "profit_factor": metrics["profit_factor_last20"],
                "avg_pnl": metrics["avg_pnl"],
            }
            if boost > 0:
                boosted += 1
            else:
                penalized += 1

    # --- Compute symbol-level adjustments ---
    symbol_adj: dict[str, dict] = {}

    for strat, sym_map in by_strat_sym.items():
        for sym, trades in sym_map.items():
            boost, reason = _symbol_boost(trades)
            if boost != 0.0:
                if strat not in symbol_adj:
                    symbol_adj[strat] = {}
                symbol_adj[strat][sym] = {
                    "boost": boost,
                    "reason": reason,
                }

    result = {
        "strategy_adjustments": strategy_adj,
        "symbol_adjustments": symbol_adj,
        "meta": {
            "total_closed_analyzed": len(completed),
            "strategies_analyzed": len(by_strategy),
            "strategies_boosted": boosted,
            "strategies_penalized": penalized,
        },
        "last_updated": datetime.now(timezone.utc).isoformat(),
    }

    _write_adjustments(result)
    return result


def _write_adjustments(data: dict) -> None:
    """Write trust_adjustments.json atomically."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    tmp = TRUST_ADJ_PATH.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    tmp.replace(TRUST_ADJ_PATH)


# ---------------------------------------------------------------------------
# Integration: apply adjustments to a pick
# ---------------------------------------------------------------------------

def _load_adjustments() -> dict:
    """Load trust_adjustments.json with 1-hour in-memory cache."""
    global _adj_cache, _adj_cache_ts
    now = time.time()
    if _adj_cache is not None and (now - _adj_cache_ts) < _ADJ_CACHE_TTL:
        return _adj_cache
    if not TRUST_ADJ_PATH.exists():
        _adj_cache = {"strategy_adjustments": {}, "symbol_adjustments": {}}
        _adj_cache_ts = now
        return _adj_cache
    try:
        with open(TRUST_ADJ_PATH, "r") as f:
            _adj_cache = json.load(f)
        _adj_cache_ts = now
    except (json.JSONDecodeError, OSError):
        _adj_cache = {"strategy_adjustments": {}, "symbol_adjustments": {}}
        _adj_cache_ts = now
    return _adj_cache


def apply_trust_adjustments(pick: dict) -> float:
    """Look up trust adjustments for a pick and return the total adjustment.

    Args:
        pick: A signal dict with at least "strategy" and "symbol" keys.

    Returns:
        Total confidence adjustment, capped to [-0.20, +0.20].
    """
    adj = _load_adjustments()
    strategy = pick.get("strategy", "")
    symbol = pick.get("symbol", "")

    # Strategy-level boost
    strat_info = adj.get("strategy_adjustments", {}).get(strategy, {})
    strat_boost = strat_info.get("boost", 0.0) if strat_info else 0.0

    # Symbol-level boost
    sym_info = adj.get("symbol_adjustments", {}).get(strategy, {}).get(symbol, {})
    sym_boost = sym_info.get("boost", 0.0) if sym_info else 0.0

    total = strat_boost + sym_boost
    # Hard cap: never adjust more than +/- 0.20
    return max(-0.20, min(0.20, total))


def get_adjustment_reason(pick: dict) -> str:
    """Return a human-readable reason string for the adjustment on a pick."""
    adj = _load_adjustments()
    strategy = pick.get("strategy", "")
    symbol = pick.get("symbol", "")

    parts = []
    strat_info = adj.get("strategy_adjustments", {}).get(strategy, {})
    if strat_info and strat_info.get("boost", 0) != 0:
        parts.append(f"strategy {strat_info['boost']:+.2f} ({strat_info.get('reason', '')})")

    sym_info = adj.get("symbol_adjustments", {}).get(strategy, {}).get(symbol, {})
    if sym_info and sym_info.get("boost", 0) != 0:
        parts.append(f"symbol {sym_info['boost']:+.2f} ({sym_info.get('reason', '')})")

    return "; ".join(parts) if parts else "no adjustment"


# ---------------------------------------------------------------------------
# Standalone: report + write
# ---------------------------------------------------------------------------

def print_report(result: dict) -> None:
    """Print a human-readable trust tuner report."""
    meta = result.get("meta", {})
    strat_adj = result.get("strategy_adjustments", {})
    sym_adj = result.get("symbol_adjustments", {})

    print("\n" + "=" * 70)
    print("  ADAPTIVE TRUST TUNER -- Forward Performance Report")
    print("=" * 70)
    print(f"  Closed trades analyzed: {meta.get('total_closed_analyzed', 0)}")
    print(f"  Strategies analyzed:    {meta.get('strategies_analyzed', 0)}")
    print(f"  Strategies boosted:     {meta.get('strategies_boosted', 0)}")
    print(f"  Strategies penalized:   {meta.get('strategies_penalized', 0)}")

    if strat_adj:
        # Sort by boost descending
        sorted_strats = sorted(strat_adj.items(), key=lambda x: x[1].get("boost", 0), reverse=True)

        print(f"\n  --- Strategy Adjustments ({len(sorted_strats)}) ---")
        print(f"  {'Strategy':<40} {'Boost':>7} {'WR10':>6} {'WR20':>6} {'PF':>6} {'Trades':>7}")
        print(f"  {'-'*40} {'-'*7} {'-'*6} {'-'*6} {'-'*6} {'-'*7}")

        for strat, info in sorted_strats:
            boost = info.get("boost", 0)
            wr10 = info.get("wr_last10")
            wr20 = info.get("wr_last20")
            pf = info.get("profit_factor")
            total = info.get("total_trades", 0)
            wr10_s = f"{wr10*100:.0f}%" if wr10 is not None else "N/A"
            wr20_s = f"{wr20*100:.0f}%" if wr20 is not None else "N/A"
            pf_s = f"{pf:.1f}" if pf is not None else "N/A"
            marker = "+" if boost > 0 else ""
            print(f"  {strat:<40} {marker}{boost:.2f}  {wr10_s:>5} {wr20_s:>5} {pf_s:>5}  {total:>6}")

    if sym_adj:
        total_sym = sum(len(v) for v in sym_adj.values())
        print(f"\n  --- Symbol-Specific Adjustments ({total_sym}) ---")
        for strat, sym_map in sorted(sym_adj.items()):
            for sym, info in sorted(sym_map.items()):
                boost = info.get("boost", 0)
                reason = info.get("reason", "")
                marker = "+" if boost > 0 else ""
                print(f"  {strat:<30} {sym:<12} {marker}{boost:.2f}  ({reason})")

    print(f"\n  Written to: {TRUST_ADJ_PATH}")
    print(f"  Last updated: {result.get('last_updated', 'N/A')}")
    print("=" * 70)


if __name__ == "__main__":
    print("[TRUST TUNER] Computing adaptive trust adjustments...")
    result = compute_trust_adjustments()
    print_report(result)
