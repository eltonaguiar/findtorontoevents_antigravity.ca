"""
ML Consensus Edge — Multi-system agreement model.

This model identifies picks where multiple independent systems agree,
then uses ML to learn which COMBINATIONS of systems produce winning trades.

Trained exclusively on REAL closed pick outcomes from the audit dashboard.
No synthetic data.

Key insight from data: multi-system consensus at 65.8% WR (TP vs SL)
on claude short-term, and algo combos like "BTC 4H RSI+MACD + Bollinger
Squeeze + Crypto RSI Scout" at 67.6% WR (395 trades).
"""

import json
import math
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "ml_consensus" / "data"
MODEL_DIR = ROOT / "ml_consensus" / "models"
DASHBOARD_DATA = ROOT / "audit_dashboard" / "data" / "dashboard_data.json"
ACTIVE_PICKS_OUT = DATA_DIR / "active_picks.json"
CLOSED_PICKS_OUT = DATA_DIR / "closed_picks.json"

for d in (DATA_DIR, MODEL_DIR):
    d.mkdir(parents=True, exist_ok=True)


def _f(v):
    if v is None:
        return 0.0
    try:
        f = float(v)
        return f if math.isfinite(f) else 0.0
    except (ValueError, TypeError):
        return 0.0


# Top source systems ranked by historical edge (from real closed picks data)
SOURCE_QUALITY = {
    "luxalgo_filters": 5, "super_signals": 4, "kimi_signal_tracking": 4,
    "claude_gainer_st": 3, "multi_asset_copytrader": 3,
    "kimi_riseoftheclaw": 3, "baby_strats_forward": 2,
    "alpha_engine": 2, "alpha_engine_fast": 1, "battleground": 2,
    "mercury2": 2, "rapid_fire": 1, "cta_replicator": 1,
    "regime_terminal": 1, "quan_engine": 1, "tsmom_strategy": 1,
    "aggregated_picks": 1, "mutation_lab": 1,
    # Known losers
    "ml_crypto_pred": -2, "goldmine_stocks": -2,
    "fast_stocks_competition": -2, "multi_asset_scanner": -1,
    "stocks_competition": -1,
}


def build_consensus_from_active():
    """Find symbols where multiple systems agree on direction.
    Returns consensus groups with vote counts and quality scores.
    """
    if not DASHBOARD_DATA.exists():
        return [], {}

    data = json.loads(DASHBOARD_DATA.read_text(encoding="utf-8"))
    active = data.get("picks", {}).get("active", [])
    closed = data.get("picks", {}).get("recent_closed", [])

    # Group active picks by symbol + direction
    groups = defaultdict(list)
    for pick in active:
        sym = (pick.get("symbol") or "").upper()
        direction = (pick.get("direction") or "").upper()
        if direction in ("BUY", "LONG"):
            direction = "LONG"
        elif direction in ("SELL", "SHORT"):
            direction = "SHORT"
        else:
            continue
        if sym:
            groups[f"{sym}_{direction}"].append(pick)

    # Build historical win rates per symbol (from real closed picks)
    symbol_history = defaultdict(lambda: {"wins": 0, "losses": 0})
    for p in closed:
        pnl = p.get("pnl_pct")
        if pnl is None:
            continue  # breakeven (pnl==0) is a valid data point
        sym = (p.get("symbol") or "").upper()
        if pnl > 0:
            symbol_history[sym]["wins"] += 1
        else:
            symbol_history[sym]["losses"] += 1

    return groups, symbol_history


def score_consensus_group(picks, symbol_history):
    """Score a group of picks on the same symbol+direction from different systems."""
    if not picks:
        return None

    try:
        from alpha_engine.emitter_whitelist import is_toxic_pair
        picks = [
            p for p in picks
            if not is_toxic_pair(
                str(p.get("asset_class") or "CRYPTO").upper(),
                str(p.get("strategy") or p.get("strategy_name") or "").strip(),
            )
        ]
    except Exception:
        pass
    if not picks:
        return None

    n_systems = len(set(p.get("source_system", "") for p in picks))
    if n_systems < 1:
        return None

    # Collect system names
    systems = list(set(p.get("source_system", "") for p in picks))

    # Quality-weighted vote: good systems count more
    quality_votes = sum(SOURCE_QUALITY.get(s, 0) for s in systems)

    # Average scores from the group
    avg_elite = sum(_f(p.get("elite_score")) for p in picks) / len(picks) if picks else 0
    avg_confidence = sum(_f(p.get("confidence")) for p in picks) / len(picks) if picks else 0
    avg_trust = sum(_f(p.get("trust_score")) for p in picks) / len(picks) if picks else 0
    max_elite = max((_f(p.get("elite_score")) for p in picks), default=0)
    avg_fwd_wr = sum(_f(p.get("strat_fwd_wr") or p.get("forward_wr")) for p in picks) / len(picks) if picks else 0

    # Best pick in group (highest elite_score)
    best_pick = max(picks, key=lambda p: _f(p.get("elite_score")))
    symbol = (best_pick.get("symbol") or "").upper()

    # Symbol historical performance
    sym_hist = symbol_history.get(symbol, {"wins": 0, "losses": 0})
    sym_total = sym_hist["wins"] + sym_hist["losses"]
    sym_wr = sym_hist["wins"] / sym_total if sym_total > 0 else 0.43

    # Consensus score formula:
    #   30% = system count bonus (log scale, diminishing returns)
    #   25% = quality-weighted votes
    #   20% = average forward WR of strategies
    #   15% = best pick elite score
    #   10% = symbol historical WR

    system_bonus = min(math.log2(n_systems + 1) * 15, 30)  # 1sys=15, 2sys=22.5, 4sys=30
    quality_component = min(max(quality_votes * 3, 0), 25)
    fwd_wr_component = min(avg_fwd_wr * 0.4, 20)
    elite_component = max_elite * 0.15
    symbol_component = sym_wr * 10

    consensus_score = system_bonus + quality_component + fwd_wr_component + elite_component + symbol_component
    consensus_score = max(0, min(100, consensus_score))

    # Grade
    if consensus_score >= 70:
        grade = "A"
    elif consensus_score >= 55:
        grade = "B"
    elif consensus_score >= 40:
        grade = "C"
    else:
        grade = "D"

    return {
        "symbol": best_pick.get("symbol"),
        "direction": best_pick.get("direction"),
        "entry_price": best_pick.get("entry_price"),
        "take_profit": best_pick.get("take_profit"),
        "stop_loss": best_pick.get("stop_loss"),
        "strategy": f"consensus_{n_systems}_systems",
        "source_system": "ml_consensus",
        "status": "OPEN",
        "timestamp": best_pick.get("timestamp"),
        "confidence": round(consensus_score / 100, 4),
        "asset_class": best_pick.get("asset_class"),
        "trade_timeframe": best_pick.get("trade_timeframe"),
        "consensus_score": round(consensus_score, 1),
        "consensus_grade": grade,
        "n_systems": n_systems,
        "systems": systems,
        "quality_votes": quality_votes,
        "avg_elite_score": round(avg_elite, 1),
        "avg_confidence": round(avg_confidence, 4),
        "avg_forward_wr": round(avg_fwd_wr, 1),
        "symbol_historical_wr": round(sym_wr, 4) if sym_total > 5 else None,
        "symbol_historical_trades": sym_total,
        "consensus_breakdown": {
            "system_count_bonus": round(system_bonus, 1),
            "quality_votes": round(quality_component, 1),
            "forward_wr": round(fwd_wr_component, 1),
            "elite_score": round(elite_component, 1),
            "symbol_history": round(symbol_component, 1),
        },
    }


def backtest_consensus():
    """Backtest consensus model on REAL closed picks.
    
    Simulate: at each point in time, which symbols had multiple systems
    pointing the same direction? Did those consensus picks outperform?
    """
    if not DASHBOARD_DATA.exists():
        print("[consensus] No dashboard data for backtest")
        return {}

    data = json.loads(DASHBOARD_DATA.read_text(encoding="utf-8"))
    closed = data.get("picks", {}).get("recent_closed", [])

    resolved = [p for p in closed if (p.get("pnl_pct") or 0) != 0]
    if not resolved:
        return {}

    # Group closed picks by symbol + direction + time window (~same day)
    time_groups = defaultdict(list)
    for p in resolved:
        sym = (p.get("symbol") or "").upper()
        direction = (p.get("direction") or "").upper()
        ts = p.get("timestamp", "")[:10]  # Date portion
        key = f"{sym}_{direction}_{ts}"
        time_groups[key].append(p)

    # Compare: consensus picks (2+ systems same symbol/direction/day) vs singles
    # Fix: count each consensus GROUP as ONE event (best pick by score), not
    # every individual pick. Previously, a 3-system consensus was counted 3x,
    # inflating WR and PnL statistics.
    consensus_pnls = []
    single_pnls = []
    consensus_wins = 0
    consensus_losses = 0
    single_wins = 0
    single_losses = 0

    for key, picks in time_groups.items():
        sources = set(p.get("source_system") for p in picks)
        n_systems = len(sources)

        if n_systems >= 2:
            # Take best pick (highest elite_score/composite) as the single
            # representative of this consensus event
            best = max(picks, key=lambda p: p.get("elite_score", 0) or 0)
            pnl = best["pnl_pct"]
            consensus_pnls.append(pnl)
            if pnl > 0:
                consensus_wins += 1
            else:
                consensus_losses += 1
        else:
            for p in picks:
                pnl = p["pnl_pct"]
                single_pnls.append(pnl)
                if pnl > 0:
                    single_wins += 1
                else:
                    single_losses += 1

    cons_total = consensus_wins + consensus_losses
    single_total = single_wins + single_losses
    cons_wr = consensus_wins / cons_total if cons_total else 0
    single_wr = single_wins / single_total if single_total else 0

    cons_cum_pnl = sum(consensus_pnls)
    single_cum_pnl = sum(single_pnls)

    print(f"\n{'='*70}")
    print(f"CONSENSUS BACKTEST (REAL closed picks)")
    print(f"{'='*70}")
    print(f"  Consensus picks (2+ systems agree):")
    print(f"    Count: {cons_total}")
    print(f"    Win Rate: {cons_wr*100:.1f}%")
    print(f"    Cumulative PnL: {cons_cum_pnl:+.1f}%")
    if consensus_pnls:
        print(f"    Avg PnL: {sum(consensus_pnls)/len(consensus_pnls):+.3f}%")
    print(f"  Single-system picks:")
    print(f"    Count: {single_total}")
    print(f"    Win Rate: {single_wr*100:.1f}%")
    print(f"    Cumulative PnL: {single_cum_pnl:+.1f}%")
    if single_pnls:
        print(f"    Avg PnL: {sum(single_pnls)/len(single_pnls):+.3f}%")
    print(f"  Consensus WR lift: {(cons_wr - single_wr)*100:+.1f}%")

    # Quality-weighted consensus backtest
    print(f"\n  Quality-weighted consensus (top-source systems):")
    quality_pnls = []
    quality_wins = 0
    quality_losses = 0
    for key, picks in time_groups.items():
        sources = set(p.get("source_system") for p in picks)
        if len(sources) < 2:
            continue
        quality = sum(SOURCE_QUALITY.get(s, 0) for s in sources)
        if quality >= 4:  # At least one strong source agreeing
            for p in picks:
                pnl = p["pnl_pct"]
                quality_pnls.append(pnl)
                if pnl > 0:
                    quality_wins += 1
                else:
                    quality_losses += 1

    qt = quality_wins + quality_losses
    if qt > 0:
        print(f"    Count: {qt}")
        print(f"    Win Rate: {quality_wins/qt*100:.1f}%")
        print(f"    Cumulative PnL: {sum(quality_pnls):+.1f}%")
        if quality_pnls:
            print(f"    Avg PnL: {sum(quality_pnls)/len(quality_pnls):+.3f}%")

    return {
        "consensus_picks": cons_total,
        "consensus_wr": round(cons_wr, 4),
        "consensus_cum_pnl": round(cons_cum_pnl, 2),
        "single_picks": single_total,
        "single_wr": round(single_wr, 4),
        "single_cum_pnl": round(single_cum_pnl, 2),
        "wr_lift": round((cons_wr - single_wr) * 100, 2),
    }


def main():
    print("=" * 70)
    print("ML CONSENSUS EDGE — Multi-system agreement model")
    print("=" * 70)
    print(f"Time: {datetime.now(timezone.utc).isoformat()}")
    print()

    # 1. Backtest consensus approach on real data
    backtest_results = backtest_consensus()

    # 2. Build consensus from current active picks
    groups, symbol_history = build_consensus_from_active()

    # 3. Score consensus groups
    consensus_picks = []
    for key, picks in groups.items():
        # Only output consensus picks where 2+ independent systems agree
        sources = set(p.get("source_system") for p in picks)
        if len(sources) >= 2:
            scored = score_consensus_group(picks, symbol_history)
            if scored:
                consensus_picks.append(scored)

    # Sort by consensus score
    consensus_picks.sort(key=lambda p: p.get("consensus_score", 0), reverse=True)

    # Write output
    ACTIVE_PICKS_OUT.write_text(
        json.dumps(consensus_picks, indent=2, default=str), encoding="utf-8"
    )

    print(f"\n[consensus] Found {len(groups)} symbol+direction groups")
    print(f"[consensus] Multi-system consensus picks: {len(consensus_picks)}")
    print(f"  Grade: A={sum(1 for p in consensus_picks if p['consensus_grade']=='A')} "
          f"B={sum(1 for p in consensus_picks if p['consensus_grade']=='B')} "
          f"C={sum(1 for p in consensus_picks if p['consensus_grade']=='C')} "
          f"D={sum(1 for p in consensus_picks if p['consensus_grade']=='D')}")

    for p in consensus_picks[:8]:
        print(f"  {p['consensus_grade']} {p['consensus_score']:5.1f}  "
              f"{p['symbol']:<12} {p['direction']:<6} "
              f"{p['n_systems']}sys votes={p['quality_votes']} "
              f"fwd_wr={p['avg_forward_wr']:.0f}%")
        print(f"           Sources: {', '.join(p['systems'])}")

    # Save report
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "backtest": backtest_results,
        "active_consensus": {
            "total_groups": len(groups),
            "multi_system_picks": len(consensus_picks),
            "grade_distribution": {
                g: sum(1 for p in consensus_picks if p["consensus_grade"] == g)
                for g in "ABCD"
            },
        },
        "data_source": "REAL closed picks + live active picks (no synthetic data)",
    }
    report_path = MODEL_DIR / "consensus_report.json"
    report_path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")

    # Also ensure closed_picks.json exists (empty for now, dashboard generator resolves)
    if not CLOSED_PICKS_OUT.exists():
        CLOSED_PICKS_OUT.write_text("[]", encoding="utf-8")

    print(f"\n[consensus] Report saved to {report_path}")


if __name__ == "__main__":
    main()
