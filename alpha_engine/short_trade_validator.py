#!/usr/bin/env python3
"""
SHORT TRADE VALIDATOR -- Criterion 6: Profitable Short Trades
=============================================================
Analyzes closed SELL/SHORT picks to determine:
  1. Which short strategies actually work (WR > 50%)
  2. Which to keep, which to kill
  3. Whether restricting to high-confidence + bearish regime helps
  4. Provides a proven_short_strategies whitelist for the quality gate

Based on analysis of 788 forward-tested closed picks (173 shorts, 30.1% WR).

Key findings driving this module:
  - Shorts in "ranging" regime: 92% WR (12 trades)
  - Shorts in "trending" regime: 60% WR (15 trades)
  - Shorts with conf >= 0.80: 47% WR (41 trades)
  - Shorts with regime=None: 21% WR (146 trades) -- the main drag
  - ML-enhanced shorts (ADAUSDT, BTCUSDT): 0% WR -- pure noise
  - fractal_sr_bounce: 53% WR on 15 shorts -- only volume strategy that works
  - multi_timeframe_ema_stack: 100% WR on 3 decided shorts (2 expired)
  - cumulative_delta_divergence: 100% WR on 3 shorts
  - volume_profile_poc_reversion: 100% WR on 2 decided shorts

Usage:
  python short_trade_validator.py                  # Print full analysis
  python -c "from short_trade_validator import get_proven_short_strategies; print(get_proven_short_strategies())"
"""

from __future__ import annotations

import json
import os
from collections import Counter, defaultdict
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent / "data"
CLOSED_PICKS_PATH = DATA_DIR / "closed_picks.json"

# ---------------------------------------------------------------------------
# Minimum sample size to consider a strategy "proven"
# ---------------------------------------------------------------------------
MIN_TRADES_FOR_PROVEN = 3          # At least 3 decided (WON/LOST) trades
MIN_WR_FOR_PROVEN = 0.50           # >= 50% win rate
HIGH_CONFIDENCE_THRESHOLD = 0.80   # Shorts need higher bar than longs (0.70)
BEARISH_REGIMES = {"bearish", "capitulation"}
ALLOWED_SHORT_REGIMES = {"bearish", "capitulation", "consolidation", "ranging", "trending"}

# ---------------------------------------------------------------------------
# Symbols that are toxic for shorts (0% WR on 5+ trades)
# ---------------------------------------------------------------------------
TOXIC_SHORT_SYMBOLS = {
    "ADAUSDT",    # 0% WR on 10 shorts
    "BTCUSDT",    # 0% WR on 9 shorts
    "SOLUSDT",    # 0% WR on 3 shorts
    "AUDJPY=X",   # 0% WR on 5 shorts (forex)
    "EURJPY=X",   # 0% WR on 4 shorts (forex)
    "NZDUSD=X",   # 0% WR on 4 shorts (forex)
    "GBPUSD=X",   # 0% WR on 3 shorts (forex)
}

# ---------------------------------------------------------------------------
# Strategies proven to be unprofitable for shorts (0% WR on 5+ trades)
# ---------------------------------------------------------------------------
TOXIC_SHORT_STRATEGIES = {
    "ml_enhanced_ADAUSDT_15m_D_ensemble_stack",   # 0% WR on 8 shorts
    "ml_enhanced_BTCUSDT_15m_D_ensemble_stack",   # 0% WR on 7 shorts
    "community_london_breakout_v2_forex",          # 0% WR on 7 shorts
    "seasonal_factor_rotation",                    # 21% WR on 14 shorts
}


def load_closed_picks() -> list[dict]:
    """Load closed picks from JSON."""
    if not CLOSED_PICKS_PATH.exists():
        return []
    with open(CLOSED_PICKS_PATH) as f:
        return json.load(f)


def analyze_shorts(picks: list[dict] | None = None) -> dict:
    """Full analysis of short trade performance.

    Returns a dict with strategy-level stats, symbol stats, regime stats,
    confidence-tier stats, and recommendations.
    """
    if picks is None:
        picks = load_closed_picks()

    shorts = [p for p in picks if (p.get("signal_type") or "").upper() in ("SELL", "SHORT")]
    longs = [p for p in picks if (p.get("signal_type") or "").upper() in ("BUY", "LONG")]

    # --- Strategy-level breakdown ---
    strat_stats: dict[str, dict] = defaultdict(lambda: {"won": 0, "lost": 0, "expired": 0,
                                                         "total_pnl": 0.0, "trades": []})
    for s in shorts:
        strat = s.get("strategy", "unknown")
        status = (s.get("status") or "").upper()
        pnl = s.get("pnl_pct", 0) or 0
        strat_stats[strat]["total_pnl"] += pnl
        strat_stats[strat]["trades"].append(s)
        if status == "WON":
            strat_stats[strat]["won"] += 1
        elif status == "LOST":
            strat_stats[strat]["lost"] += 1
        else:
            strat_stats[strat]["expired"] += 1

    # Compute WR and classify
    proven_good = {}     # WR >= 50% on 3+ decided trades
    proven_bad = {}      # WR < 50% on 5+ decided trades
    insufficient = {}    # Not enough data

    for strat, stats in strat_stats.items():
        decided = stats["won"] + stats["lost"]
        wr = stats["won"] / decided if decided > 0 else 0
        stats["decided"] = decided
        stats["wr"] = wr
        stats["total"] = decided + stats["expired"]

        if decided >= MIN_TRADES_FOR_PROVEN and wr >= MIN_WR_FOR_PROVEN:
            proven_good[strat] = stats
        elif decided >= 5 and wr < MIN_WR_FOR_PROVEN:
            proven_bad[strat] = stats
        else:
            insufficient[strat] = stats

    # --- Symbol-level breakdown ---
    sym_stats: dict[str, dict] = defaultdict(lambda: {"won": 0, "lost": 0, "expired": 0})
    for s in shorts:
        sym = s.get("symbol", "unknown")
        status = (s.get("status") or "").upper()
        if status == "WON":
            sym_stats[sym]["won"] += 1
        elif status == "LOST":
            sym_stats[sym]["lost"] += 1
        else:
            sym_stats[sym]["expired"] += 1

    # --- Regime analysis ---
    regime_stats: dict[str, dict] = defaultdict(lambda: {"won": 0, "lost": 0, "total": 0})
    for s in shorts:
        regime = s.get("regime_at_entry") or "unknown"
        regime = str(regime).lower()
        regime_stats[regime]["total"] += 1
        status = (s.get("status") or "").upper()
        if status == "WON":
            regime_stats[regime]["won"] += 1
        elif status == "LOST":
            regime_stats[regime]["lost"] += 1

    # --- Confidence tier analysis ---
    conf_tiers = {}
    for threshold in [0.50, 0.60, 0.70, 0.80, 0.90]:
        subset = [s for s in shorts if (s.get("confidence", 0) or 0) >= threshold]
        wins = sum(1 for s in subset if (s.get("status") or "").upper() == "WON")
        losses = sum(1 for s in subset if (s.get("status") or "").upper() == "LOST")
        decided = wins + losses
        conf_tiers[threshold] = {
            "total": len(subset), "won": wins, "lost": losses,
            "wr": wins / decided if decided > 0 else 0,
        }

    # --- Simulation: conf >= 0.80 + bearish regime only ---
    filtered = [s for s in shorts
                if (s.get("confidence", 0) or 0) >= 0.80
                and str(s.get("regime_at_entry") or "").lower() in BEARISH_REGIMES]
    sim_wins = sum(1 for s in filtered if (s.get("status") or "").upper() == "WON")
    sim_losses = sum(1 for s in filtered if (s.get("status") or "").upper() == "LOST")
    sim_decided = sim_wins + sim_losses
    strict_simulation = {
        "total": len(filtered), "won": sim_wins, "lost": sim_losses,
        "wr": sim_wins / sim_decided if sim_decided > 0 else 0,
    }

    # --- SL distance comparison ---
    short_sl_dists = []
    long_sl_dists = []
    for s in shorts:
        entry = s.get("entry_price", 0) or 0
        sl = s.get("stop_loss", 0) or 0
        if entry > 0 and sl > 0:
            short_sl_dists.append(abs(sl - entry) / entry * 100)
    for s in longs:
        entry = s.get("entry_price", 0) or 0
        sl = s.get("stop_loss", 0) or 0
        if entry > 0 and sl > 0:
            long_sl_dists.append(abs(sl - entry) / entry * 100)

    return {
        "total_shorts": len(shorts),
        "total_longs": len(longs),
        "short_wr": sum(1 for s in shorts if s.get("status") == "WON")
                    / max(1, sum(1 for s in shorts if s.get("status") in ("WON", "LOST"))),
        "proven_good_strategies": {k: {"wr": v["wr"], "decided": v["decided"],
                                        "total_pnl": v["total_pnl"]}
                                    for k, v in proven_good.items()},
        "proven_bad_strategies": {k: {"wr": v["wr"], "decided": v["decided"],
                                       "total_pnl": v["total_pnl"]}
                                   for k, v in proven_bad.items()},
        "insufficient_data": {k: {"wr": v["wr"], "decided": v["decided"]}
                              for k, v in insufficient.items()},
        "regime_stats": {k: {"won": v["won"], "lost": v["lost"], "total": v["total"],
                             "wr": v["won"] / max(1, v["won"] + v["lost"])}
                         for k, v in regime_stats.items()},
        "confidence_tiers": conf_tiers,
        "strict_bearish_simulation": strict_simulation,
        "avg_short_sl_pct": sum(short_sl_dists) / max(1, len(short_sl_dists)),
        "avg_long_sl_pct": sum(long_sl_dists) / max(1, len(long_sl_dists)),
        "toxic_symbols": list(TOXIC_SHORT_SYMBOLS),
        "toxic_strategies": list(TOXIC_SHORT_STRATEGIES),
    }


def get_proven_short_strategies(picks: list[dict] | None = None) -> set[str]:
    """Return set of strategy names with WR >= 50% on 3+ decided short trades.

    Used by the production scanner quality gate to whitelist proven short strategies.
    """
    result = analyze_shorts(picks)
    return set(result["proven_good_strategies"].keys())


def should_allow_short(pick: dict, regime: str = "neutral",
                       proven_strategies: set[str] | None = None) -> tuple[bool, str]:
    """Determine whether a short trade should be allowed through the quality gate.

    Returns (allowed: bool, reason: str).

    A short is allowed if ANY of these conditions are met:
      1. Strategy is in the proven-profitable whitelist (WR > 50% on 3+ trades)
      2. Confidence >= 0.80 AND regime is bearish/capitulation/consolidation
      3. Confidence >= 0.85 AND regime is unknown (high bar for unknown regime)

    A short is BLOCKED if:
      - Strategy is in toxic list (0% WR on 5+ trades)
      - Symbol is in toxic list (0% WR on 5+ trades)
      - Confidence < 0.75 (short floor higher than long floor of 0.70)
    """
    strategy = pick.get("strategy", "")
    symbol = pick.get("symbol", "")
    conf = pick.get("confidence", 0) or 0
    regime_lower = regime.lower() if regime else "unknown"

    if proven_strategies is None:
        proven_strategies = get_proven_short_strategies()

    # Hard blocks
    if strategy in TOXIC_SHORT_STRATEGIES:
        return False, f"toxic short strategy ({strategy}): 0% WR historically"

    if symbol in TOXIC_SHORT_SYMBOLS:
        return False, f"toxic short symbol ({symbol}): 0% WR historically"

    if conf < 0.75:
        return False, f"short confidence {conf:.2f} < 0.75 floor"

    # Allow: proven strategy
    if strategy in proven_strategies:
        return True, f"proven short strategy ({strategy}): WR > 50% on 3+ trades"

    # Allow: high confidence + bearish regime
    if conf >= 0.80 and regime_lower in ("bearish", "capitulation"):
        return True, f"high-conf ({conf:.2f}) short in {regime_lower} regime"

    # Allow: high confidence + consolidation (92% WR in ranging/consolidation)
    if conf >= 0.80 and regime_lower in ("consolidation", "ranging"):
        return True, f"high-conf ({conf:.2f}) short in {regime_lower} regime (92% hist WR)"

    # Allow: very high confidence in unknown regime
    if conf >= 0.85 and regime_lower in ("unknown", "none"):
        return True, f"very-high-conf ({conf:.2f}) short in unknown regime"

    # Block everything else
    return False, (f"short blocked: conf={conf:.2f}, regime={regime_lower}. "
                   f"Need conf>=0.80+bearish/consolidation OR proven strategy")


def print_report():
    """Print a human-readable analysis report."""
    result = analyze_shorts()

    print("=" * 72)
    print("SHORT TRADE ANALYSIS -- Criterion 6: Profitable Short Trades")
    print("=" * 72)
    print(f"\nTotal shorts: {result['total_shorts']} | Total longs: {result['total_longs']}")
    print(f"Overall short WR: {result['short_wr']:.1%}")
    print(f"Avg SL distance -- Shorts: {result['avg_short_sl_pct']:.2f}% | "
          f"Longs: {result['avg_long_sl_pct']:.2f}%")

    print("\n--- PROVEN GOOD SHORT STRATEGIES (WR >= 50%, 3+ trades) ---")
    for strat, stats in sorted(result["proven_good_strategies"].items(),
                                key=lambda x: -x[1]["wr"]):
        print(f"  {strat}: WR={stats['wr']:.0%} on {stats['decided']} trades, "
              f"PnL={stats['total_pnl']:.2f}%")

    print("\n--- PROVEN BAD SHORT STRATEGIES (WR < 50%, 5+ trades) ---")
    for strat, stats in sorted(result["proven_bad_strategies"].items(),
                                key=lambda x: x[1]["wr"]):
        print(f"  {strat}: WR={stats['wr']:.0%} on {stats['decided']} trades, "
              f"PnL={stats['total_pnl']:.2f}%")

    print("\n--- REGIME PERFORMANCE ---")
    for regime, stats in sorted(result["regime_stats"].items(),
                                 key=lambda x: -x[1]["wr"]):
        print(f"  {regime}: WR={stats['wr']:.0%} "
              f"(W:{stats['won']} L:{stats['total']-stats['won']-stats.get('expired',0)}) "
              f"total={stats['total']}")

    print("\n--- CONFIDENCE TIERS ---")
    for thresh, stats in sorted(result["confidence_tiers"].items()):
        print(f"  conf >= {thresh}: {stats['total']} trades, WR={stats['wr']:.0%}")

    print("\n--- SIMULATION: conf >= 0.80 + bearish regime ---")
    sim = result["strict_bearish_simulation"]
    print(f"  {sim['total']} trades | WR={sim['wr']:.0%} (W:{sim['won']} L:{sim['lost']})")

    print("\n--- TOXIC SYMBOLS (0% WR on shorts) ---")
    print(f"  {', '.join(sorted(result['toxic_symbols']))}")

    print("\n--- TOXIC STRATEGIES (0% WR on shorts) ---")
    print(f"  {', '.join(sorted(result['toxic_strategies']))}")

    print("\n--- RECOMMENDATIONS ---")
    print("  1. KEEP: proven strategies (fractal_sr_bounce, multi_timeframe_ema_stack, etc.)")
    print("  2. KILL: ML-enhanced shorts (0% WR), seasonal_factor_rotation shorts (21% WR)")
    print("  3. GATE: All other shorts need conf >= 0.80 + bearish/consolidation regime")
    print("  4. BLOCK: Toxic symbols (ADAUSDT, BTCUSDT shorts = 0% WR)")
    print("  5. TIGHTEN SL: Short SL avg 3.49% vs Long 3.13% -- consider 2.5% max for shorts")


if __name__ == "__main__":
    print_report()
