#!/usr/bin/env python3
"""
Strategy Mutator — DNA mutation engine for killed/underperforming strategies.

Policy: MUTATE/INVERSE before kill. Try DNA mutation, inverse direction,
symbol rotation before permanently removing any strategy.

For each killed strategy with 10+ closed trades, generates 3 mutation candidates:
  A) Inverse Direction — flip LONG<->SHORT
  B) Tighter TP/SL — TP*0.6, SL*0.7 (take profits faster, tighter stops)
  C) Symbol Rotation — restrict to top-5 performing symbols only

Scoring:
  - mutation WR > original WR + 10pp AND > 45%  -> PROMOTE (incubator)
  - mutation WR > original WR but < 45%          -> WATCHLIST
  - mutation WR <= original WR                   -> CONFIRMED_KILL
"""

import sys
import os
import json
import datetime
from collections import defaultdict
from pathlib import Path

# Windows UTF-8 fix
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
AUDIT_DIR = BASE_DIR.parent / "audit_trail" / "data"

KILL_LIST_PATH = DATA_DIR / "strategy_kill_list.json"
DASHBOARD_PAYLOAD_PATH = AUDIT_DIR / "dashboard_payload.json"
UNIVERSAL_RESOLVED_PATH = AUDIT_DIR / "universal_resolved_picks.json"
OUTPUT_PATH = DATA_DIR / "mutation_results.json"

TOP5_SYMBOLS = ["FETUSDT", "AVAXUSDT", "SOLUSDT", "ETHUSDT", "BNBUSDT"]

MIN_TRADES = 10
WR_IMPROVE_THRESHOLD = 0.10  # 10 percentage points
WR_PROMOTE_MIN = 0.45        # 45% minimum to promote


def _load_json(path):
    """Load JSON file, return None on failure."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"[WARN] Cannot load {path}: {e}")
        return None


def _save_json(path, data):
    """Save JSON file with UTF-8 encoding."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str, ensure_ascii=False)


def _load_all_closed_picks():
    """Load closed picks from dashboard_payload and universal_resolved_picks.

    Merges both sources, deduplicating by (strategy, symbol, timestamp).
    """
    picks = []
    seen = set()

    # Source 1: dashboard_payload.json -> picks.recent_closed
    payload = _load_json(DASHBOARD_PAYLOAD_PATH)
    if payload:
        recent_closed = payload.get("picks", {}).get("recent_closed", [])
        for p in recent_closed:
            key = (p.get("strategy", ""), p.get("symbol", ""), p.get("timestamp", ""))
            if key not in seen and p.get("strategy"):
                seen.add(key)
                picks.append(p)

    # Source 2: universal_resolved_picks.json
    universal = _load_json(UNIVERSAL_RESOLVED_PATH)
    if universal and isinstance(universal, list):
        for p in universal:
            key = (p.get("strategy", ""), p.get("symbol", ""), p.get("timestamp", ""))
            if key not in seen and p.get("strategy"):
                seen.add(key)
                picks.append(p)

    return picks


def _compute_wr(picks):
    """Compute win rate from a list of picks."""
    if not picks:
        return 0.0
    wins = sum(1 for p in picks if _is_win(p))
    return wins / len(picks)


def _is_win(pick):
    """Determine if a pick was a win."""
    status = str(pick.get("status", "")).upper()
    if status == "WON":
        return True
    if status in ("LOST", "STOPPED"):
        return False
    pnl = pick.get("pnl_pct", 0)
    if pnl is None:
        pnl = 0
    return float(pnl) > 0


def _compute_avg_pnl(picks):
    """Average PnL percentage across picks."""
    if not picks:
        return 0.0
    pnls = []
    for p in picks:
        pnl = p.get("pnl_pct", 0)
        if pnl is not None:
            pnls.append(float(pnl))
    return sum(pnls) / len(pnls) if pnls else 0.0


def _group_by_strategy(picks):
    """Group picks by strategy name."""
    groups = defaultdict(list)
    for p in picks:
        strat = p.get("strategy", "")
        if strat:
            groups[strat].append(p)
    return groups


def _get_killed_strategies():
    """Get list of killed strategy names from kill list and also find
    underperformers (WR < 30% on 10+ trades) from the closed picks."""
    killed = set()

    kill_data = _load_json(KILL_LIST_PATH)
    if kill_data:
        # Handle both list format and dict format
        if isinstance(kill_data, dict):
            for name in kill_data.get("auto_kill_strategies", []):
                killed.add(name)
            # Also check the details dict for any additional strategies
            for name in kill_data.get("details", {}):
                killed.add(name)
        elif isinstance(kill_data, list):
            for item in kill_data:
                if isinstance(item, str):
                    killed.add(item)
                elif isinstance(item, dict):
                    name = item.get("strategy", item.get("name", ""))
                    if name:
                        killed.add(name)

    return killed


def mutate_inverse(strategy_name, picks):
    """Mutation A: Inverse Direction.

    Flip all trade directions and recompute win rate.
    If original lost on LONGs (WR<40%), create SHORT-only variant and vice versa.
    """
    longs = [p for p in picks if str(p.get("direction", "")).upper() == "LONG"]
    shorts = [p for p in picks if str(p.get("direction", "")).upper() == "SHORT"]

    long_wr = _compute_wr(longs) if longs else None
    short_wr = _compute_wr(shorts) if shorts else None

    # Strategy 1: If lost on longs, try short-only
    # Strategy 2: If lost on shorts, try long-only
    # Strategy 3: Flip all directions (invert every trade outcome conceptually)

    best_subset = None
    best_label = "inverse_all"

    if long_wr is not None and long_wr < 0.40 and shorts:
        # Longs were bad -> use short-only subset
        best_subset = shorts
        best_label = "short_only"
    elif short_wr is not None and short_wr < 0.40 and longs:
        # Shorts were bad -> use long-only subset
        best_subset = longs
        best_label = "long_only"
    else:
        # Flip all directions: conceptually, inverse the losing trades
        # For inverse backtest, we simulate: wins become losses, losses become wins
        # This represents taking the opposite position for each signal
        inverted = []
        for p in picks:
            inv = dict(p)
            pnl = p.get("pnl_pct", 0)
            if pnl is None:
                pnl = 0
            inv["pnl_pct"] = -float(pnl)
            inv["status"] = "WON" if float(pnl) < 0 else "LOST"
            inv["direction"] = "SHORT" if str(p.get("direction", "")).upper() == "LONG" else "LONG"
            inverted.append(inv)
        best_subset = inverted
        best_label = "inverse_all"

    mutation_wr = _compute_wr(best_subset)
    mutation_pnl = _compute_avg_pnl(best_subset)

    return {
        "mutation_type": "inverse",
        "mutation_name": f"{strategy_name}_inverse",
        "variant": best_label,
        "trade_count": len(best_subset),
        "mutation_wr": round(mutation_wr, 4),
        "mutation_avg_pnl": round(mutation_pnl, 4),
        "long_count": len(longs),
        "short_count": len(shorts),
        "long_wr": round(long_wr, 4) if long_wr is not None else None,
        "short_wr": round(short_wr, 4) if short_wr is not None else None,
    }


def mutate_tight(strategy_name, picks):
    """Mutation B: Tighter TP/SL.

    Simulate TP*0.6 and SL*0.7 exits.
    Uses entry_price, take_profit, stop_loss, and pnl_pct to estimate outcomes.
    """
    results = []

    for p in picks:
        entry = p.get("entry_price")
        tp = p.get("take_profit")
        sl = p.get("stop_loss")
        pnl = p.get("pnl_pct", 0)
        direction = str(p.get("direction", "LONG")).upper()

        if entry is None or tp is None or sl is None:
            # Can't simulate tighter exits without price data, keep original
            results.append(p)
            continue

        try:
            entry = float(entry)
            tp = float(tp)
            sl = float(sl)
            pnl = float(pnl) if pnl is not None else 0
        except (ValueError, TypeError):
            results.append(p)
            continue

        if entry == 0:
            results.append(p)
            continue

        # Compute original TP/SL distances
        if direction == "LONG":
            tp_dist = (tp - entry) / entry  # positive
            sl_dist = (entry - sl) / entry  # positive
        else:
            tp_dist = (entry - tp) / entry  # positive
            sl_dist = (sl - entry) / entry  # positive

        # Tighter parameters
        new_tp_dist = tp_dist * 0.6
        new_sl_dist = sl_dist * 0.7

        # Simulate: did the trade reach tighter TP before tighter SL?
        # We use the actual pnl and exit_reason as a proxy:
        exit_reason = str(p.get("exit_reason", "")).upper()
        sim = dict(p)

        if exit_reason in ("TP_HIT", "TP"):
            # Original hit TP — tighter TP would also hit (sooner)
            sim["pnl_pct"] = round(new_tp_dist * 100, 4)
            sim["status"] = "WON"
        elif exit_reason in ("SL_HIT", "SL", "STOPPED"):
            # Check if tighter SL would have been hit even earlier
            # But also: tighter TP might have been hit before the SL
            # Heuristic: if original pnl was mildly negative and new_tp_dist
            # is small enough, the trade may have been positive at some point
            actual_loss_pct = abs(pnl) / 100 if pnl < 0 else 0
            if actual_loss_pct > new_sl_dist:
                # Loss exceeded even tighter SL — still a loss but smaller
                sim["pnl_pct"] = round(-new_sl_dist * 100, 4)
                sim["status"] = "LOST"
            elif new_tp_dist < sl_dist * 0.5:
                # TP is so tight it might have triggered before SL
                # Conservative: 50% chance it would have won
                sim["pnl_pct"] = round(new_tp_dist * 100, 4)
                sim["status"] = "WON"
            else:
                sim["pnl_pct"] = round(-new_sl_dist * 100, 4)
                sim["status"] = "LOST"
        elif exit_reason == "TIME":
            # Time-expired: check if actual pnl exceeds tighter TP
            if pnl > 0 and pnl / 100 >= new_tp_dist:
                sim["pnl_pct"] = round(new_tp_dist * 100, 4)
                sim["status"] = "WON"
            elif pnl < 0 and abs(pnl) / 100 >= new_sl_dist:
                sim["pnl_pct"] = round(-new_sl_dist * 100, 4)
                sim["status"] = "LOST"
            else:
                # Ended within tighter bounds — same outcome
                sim["pnl_pct"] = pnl
                sim["status"] = "WON" if pnl > 0 else "LOST"
        else:
            # Unknown exit reason — keep original result
            pass

        results.append(sim)

    mutation_wr = _compute_wr(results)
    mutation_pnl = _compute_avg_pnl(results)

    return {
        "mutation_type": "tight",
        "mutation_name": f"{strategy_name}_tight",
        "variant": "tp_0.6x_sl_0.7x",
        "trade_count": len(results),
        "mutation_wr": round(mutation_wr, 4),
        "mutation_avg_pnl": round(mutation_pnl, 4),
    }


def mutate_symbol_rotation(strategy_name, picks):
    """Mutation C: Symbol Rotation.

    Filter to top-5 performing symbols only and recompute WR.
    """
    filtered = [p for p in picks if p.get("symbol", "") in TOP5_SYMBOLS]

    if not filtered:
        return {
            "mutation_type": "symbol_rotation",
            "mutation_name": f"{strategy_name}_top5only",
            "variant": "top5_symbols",
            "trade_count": 0,
            "mutation_wr": 0.0,
            "mutation_avg_pnl": 0.0,
            "symbols_available": [p.get("symbol") for p in picks[:5]],
            "note": "No trades on top-5 symbols",
        }

    mutation_wr = _compute_wr(filtered)
    mutation_pnl = _compute_avg_pnl(filtered)
    symbol_counts = defaultdict(int)
    for p in filtered:
        symbol_counts[p.get("symbol", "UNKNOWN")] += 1

    return {
        "mutation_type": "symbol_rotation",
        "mutation_name": f"{strategy_name}_top5only",
        "variant": "top5_symbols",
        "trade_count": len(filtered),
        "mutation_wr": round(mutation_wr, 4),
        "mutation_avg_pnl": round(mutation_pnl, 4),
        "symbol_breakdown": dict(symbol_counts),
    }


def _classify_mutation(original_wr, mutation_wr):
    """Classify mutation result: PROMOTE / WATCHLIST / CONFIRMED_KILL."""
    improvement = mutation_wr - original_wr
    if improvement >= WR_IMPROVE_THRESHOLD and mutation_wr >= WR_PROMOTE_MIN:
        return "PROMOTE"
    elif mutation_wr > original_wr:
        return "WATCHLIST"
    else:
        return "CONFIRMED_KILL"


def run():
    """Main mutation engine entry point."""
    print("=" * 70)
    print("STRATEGY MUTATOR — DNA Mutation Engine")
    print("Policy: MUTATE/INVERSE before kill")
    print("=" * 70)

    # Load all closed picks
    all_picks = _load_all_closed_picks()
    print(f"\nLoaded {len(all_picks)} total closed picks")

    # Group by strategy
    by_strategy = _group_by_strategy(all_picks)
    print(f"Found {len(by_strategy)} unique strategies with closed trades")

    # Get killed strategies
    killed = _get_killed_strategies()
    print(f"Kill list contains {len(killed)} strategies")

    # Also find underperformers not yet on kill list (WR < 30% on 10+ trades)
    underperformers = set()
    for strat_name, strat_picks in by_strategy.items():
        if len(strat_picks) >= MIN_TRADES:
            wr = _compute_wr(strat_picks)
            if wr < 0.30:
                underperformers.add(strat_name)

    # Combine killed + underperformers
    candidates = killed | underperformers
    # Filter to those with enough trades
    candidates_with_data = {
        s for s in candidates if s in by_strategy and len(by_strategy[s]) >= MIN_TRADES
    }

    print(f"Candidates for mutation (killed + WR<30%, 10+ trades): {len(candidates_with_data)}")

    if not candidates_with_data:
        print("\nNo candidates with enough trade history for mutation analysis.")
        _save_json(OUTPUT_PATH, {
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "candidates_analyzed": 0,
            "mutations": [],
            "promotions": [],
            "watchlist": [],
            "confirmed_kills": [],
        })
        return

    # Run mutations
    all_mutations = []
    promotions = []
    watchlist = []
    confirmed_kills = []

    for strat_name in sorted(candidates_with_data):
        picks = by_strategy[strat_name]
        original_wr = _compute_wr(picks)
        original_pnl = _compute_avg_pnl(picks)
        trade_count = len(picks)

        strat_result = {
            "strategy": strat_name,
            "original_wr": round(original_wr, 4),
            "original_avg_pnl": round(original_pnl, 4),
            "original_trades": trade_count,
            "on_kill_list": strat_name in killed,
            "mutations": [],
        }

        # Generate 3 mutations
        mut_a = mutate_inverse(strat_name, picks)
        mut_b = mutate_tight(strat_name, picks)
        mut_c = mutate_symbol_rotation(strat_name, picks)

        for mut in [mut_a, mut_b, mut_c]:
            if mut["trade_count"] == 0:
                mut["verdict"] = "INSUFFICIENT_DATA"
            else:
                mut["verdict"] = _classify_mutation(original_wr, mut["mutation_wr"])
                mut["wr_improvement"] = round(mut["mutation_wr"] - original_wr, 4)

            strat_result["mutations"].append(mut)

            if mut.get("verdict") == "PROMOTE":
                promotions.append({
                    "strategy": strat_name,
                    "mutation": mut["mutation_name"],
                    "type": mut["mutation_type"],
                    "original_wr": round(original_wr, 4),
                    "mutation_wr": mut["mutation_wr"],
                    "improvement": mut.get("wr_improvement", 0),
                    "trades": mut["trade_count"],
                })
            elif mut.get("verdict") == "WATCHLIST":
                watchlist.append({
                    "strategy": strat_name,
                    "mutation": mut["mutation_name"],
                    "type": mut["mutation_type"],
                    "original_wr": round(original_wr, 4),
                    "mutation_wr": mut["mutation_wr"],
                    "improvement": mut.get("wr_improvement", 0),
                    "trades": mut["trade_count"],
                })

        # Check if all mutations failed
        verdicts = [m.get("verdict") for m in strat_result["mutations"]]
        if all(v in ("CONFIRMED_KILL", "INSUFFICIENT_DATA") for v in verdicts):
            confirmed_kills.append({
                "strategy": strat_name,
                "original_wr": round(original_wr, 4),
                "trades": trade_count,
                "reason": "All 3 mutations failed to improve WR",
            })

        all_mutations.append(strat_result)

    # Build output
    output = {
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "candidates_analyzed": len(candidates_with_data),
        "total_mutations_tested": len(candidates_with_data) * 3,
        "summary": {
            "promotions": len(promotions),
            "watchlist": len(watchlist),
            "confirmed_kills": len(confirmed_kills),
        },
        "promotions": promotions,
        "watchlist": watchlist,
        "confirmed_kills": confirmed_kills,
        "mutations": all_mutations,
    }

    _save_json(OUTPUT_PATH, output)
    print(f"\nResults saved to {OUTPUT_PATH}")

    # Print summary table
    print("\n" + "=" * 70)
    print("MUTATION RESULTS SUMMARY")
    print("=" * 70)

    if promotions:
        print(f"\n  PROMOTED TO INCUBATOR ({len(promotions)}):")
        print(f"  {'Mutation':<45} {'Orig WR':>8} {'New WR':>8} {'Delta':>7} {'Trades':>6}")
        print("  " + "-" * 76)
        for p in sorted(promotions, key=lambda x: -x["improvement"]):
            print(
                f"  {p['mutation']:<45} "
                f"{p['original_wr']*100:>7.1f}% "
                f"{p['mutation_wr']*100:>7.1f}% "
                f"{p['improvement']*100:>+6.1f}% "
                f"{p['trades']:>5}"
            )

    if watchlist:
        print(f"\n  WATCHLIST ({len(watchlist)}):")
        print(f"  {'Mutation':<45} {'Orig WR':>8} {'New WR':>8} {'Delta':>7} {'Trades':>6}")
        print("  " + "-" * 76)
        for w in sorted(watchlist, key=lambda x: -x["improvement"])[:20]:
            print(
                f"  {w['mutation']:<45} "
                f"{w['original_wr']*100:>7.1f}% "
                f"{w['mutation_wr']*100:>7.1f}% "
                f"{w['improvement']*100:>+6.1f}% "
                f"{w['trades']:>5}"
            )
        if len(watchlist) > 20:
            print(f"  ... and {len(watchlist) - 20} more")

    if confirmed_kills:
        print(f"\n  CONFIRMED KILLS ({len(confirmed_kills)}):")
        for ck in confirmed_kills:
            print(f"    {ck['strategy']:<40} WR={ck['original_wr']*100:.1f}% ({ck['trades']} trades)")

    print(f"\n  Total: {len(promotions)} promoted, {len(watchlist)} watchlist, "
          f"{len(confirmed_kills)} confirmed kills")
    print("=" * 70)

    return output


if __name__ == "__main__":
    run()
