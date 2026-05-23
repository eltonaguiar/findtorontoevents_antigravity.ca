#!C:/Users/zerou/AppData/Local/Programs/Python/Python310/python.exe
"""
$1000 INVESTMENT SIMULATION ACROSS ALL TRADING SYSTEMS
======================================================
Loads every data file from every system, calculates PnL,
ranks by return, and provides tier analysis + verdict.
"""

import json
import os
import sys
from pathlib import Path

BASE = Path(r"e:\findtorontoevents_antigravity.ca")
INITIAL_CAPITAL = 1000.0

# PnL field names to try, in priority order
PNL_FIELDS = [
    "pnl_pct", "unrealized_pnl_pct", "pnl", "unrealized_pnl",
    "return_pct", "profit_pct", "gain_pct", "performance",
    "actual_pnl_pct", "pnl_percent"
]


def load_json(filepath):
    """Load JSON file, return list of picks."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        return None, str(e)

    # Normalize to list of picks
    if isinstance(data, list):
        return data, None
    elif isinstance(data, dict):
        # Try common wrapper keys
        for key in ["picks", "active_picks", "signals", "closed_picks", "data"]:
            if key in data and isinstance(data[key], list):
                return data[key], None
        # Single pick dict? Wrap it
        if "symbol" in data or "ticker" in data:
            return [data], None
        return [], "dict with no recognized list key"
    return [], "unknown format"


def extract_pnl(pick):
    """Extract PnL percentage from a pick using multiple field names."""
    for field in PNL_FIELDS:
        val = pick.get(field)
        if val is not None:
            try:
                pnl = float(val)
                # Some systems store as decimal (0.05 = 5%), some as percent (5.0 = 5%)
                # Heuristic: if abs(val) < 1 and it's not obviously a percentage field name
                # with "pct" or "percent", treat as decimal and convert
                # Actually most systems here store as percentage already (e.g. 2.0 = 2%)
                # The unrealized_pnl_pct from alpha_engine stores as decimal (0.01 = 1%)
                if field in ("unrealized_pnl_pct", "unrealized_pnl") and abs(pnl) < 1:
                    pnl *= 100  # convert 0.05 -> 5%
                return pnl, field
            except (ValueError, TypeError):
                continue

    # Try to calculate from entry/exit prices
    entry = pick.get("entry_price") or pick.get("entry")
    exit_p = pick.get("exit_price") or pick.get("close_price") or pick.get("current_price")
    if entry and exit_p:
        try:
            entry_f = float(entry)
            exit_f = float(exit_p)
            if entry_f > 0:
                direction = pick.get("direction", "LONG").upper()
                if direction in ("SHORT", "SELL"):
                    pnl = ((entry_f - exit_f) / entry_f) * 100
                else:
                    pnl = ((exit_f - entry_f) / entry_f) * 100
                return pnl, "calculated"
        except (ValueError, TypeError):
            pass

    return None, None


def analyze_system(name, filepath, category="closed"):
    """Analyze a single system's data file."""
    picks, err = load_json(filepath)
    if picks is None:
        return {"name": name, "error": err, "category": category}

    pnls = []
    for pick in picks:
        pnl, field = extract_pnl(pick)
        if pnl is not None:
            pnls.append(pnl)

    if not pnls:
        return {
            "name": name,
            "total_picks": len(picks),
            "picks_with_pnl": 0,
            "category": category,
            "error": "no PnL data found"
        }

    wins = sum(1 for p in pnls if p > 0)
    losses = sum(1 for p in pnls if p < 0)
    flat = sum(1 for p in pnls if p == 0)
    avg_pnl = sum(pnls) / len(pnls)
    total_return_pct = sum(pnls)

    # $1000 simulation: compound each trade
    capital = INITIAL_CAPITAL
    for pnl in pnls:
        capital *= (1 + pnl / 100)

    # Also do equal-weight (invest $1000/n per trade)
    simple_return = INITIAL_CAPITAL * (1 + avg_pnl * len(pnls) / 100)

    best_trade = max(pnls)
    worst_trade = min(pnls)

    return {
        "name": name,
        "total_picks": len(picks),
        "picks_with_pnl": len(pnls),
        "wins": wins,
        "losses": losses,
        "flat": flat,
        "win_rate": (wins / len(pnls) * 100) if pnls else 0,
        "avg_pnl": avg_pnl,
        "total_return_pct": total_return_pct,
        "compounded_capital": capital,
        "compounded_return_pct": (capital - INITIAL_CAPITAL) / INITIAL_CAPITAL * 100,
        "best_trade": best_trade,
        "worst_trade": worst_trade,
        "category": category,
        "error": None
    }


def tier_rank(result):
    """Assign tier based on picks count and performance."""
    if result.get("error"):
        return "N/A"
    picks = result.get("picks_with_pnl", 0)
    avg = result.get("avg_pnl", 0)
    wr = result.get("win_rate", 0)
    ret = result.get("compounded_return_pct", 0)

    if picks >= 30 and avg > 0 and wr >= 50:
        return "PROVEN"
    elif picks >= 30 and avg > 0:
        return "PROMISING"
    elif picks >= 10 and avg > 0:
        return "PROMISING"
    elif picks >= 10 and avg <= 0 and wr >= 45:
        return "EXPERIMENTAL"
    elif picks >= 5 and avg > 0:
        return "EXPERIMENTAL"
    elif picks < 5:
        return "EXPERIMENTAL"
    else:
        return "DEAD WEIGHT"


def fmt_money(val):
    """Format as dollar amount."""
    if val >= 0:
        return "$%.2f" % val
    else:
        return "-$%.2f" % abs(val)


def fmt_pct(val):
    """Format as percentage."""
    if val >= 0:
        return "+%.2f%%" % val
    else:
        return "%.2f%%" % val


def print_separator(char="=", width=100):
    print(char * width)


def print_header(title, width=100):
    print()
    print_separator("=", width)
    print("  %s" % title)
    print_separator("=", width)


def main():
    # =========================================================================
    # DEFINE ALL SYSTEMS
    # =========================================================================

    closed_systems = [
        ("Battleground", "battleground/data/closed_picks.json"),
        ("ML Claws of Doom (F)", "ml_battleground/system_f_clawsofdoom/data/closed_picks.json"),
        ("Mercury 2", "mercury2/data/closed_picks.json"),
        ("Paper Trading", "paper_trading/data/closed_picks.json"),
        ("Alpha Engine", "alpha_engine/data/closed_picks.json"),
        ("ML Filter (A)", "ml_battleground/system_a_filter/data/closed_picks.json"),
        ("ML Regime (B)", "ml_battleground/system_b_regime/data/closed_picks.json"),
        ("ML Ensemble", "ml_battleground/ensemble_data/closed_picks.json"),
        ("ML DeepLearn (C)", "ml_battleground/system_c_deeplearn/data/closed_picks.json"),
        ("ML Crypto Predictor (archive)", "ml_crypto_predictor/enhanced_models/live_picks/archive_v1.2/closed_picks.json"),
        ("KIMI Rise of the Claw", "KIMI_RISEOFTHECLAW/data/closed_picks.json"),
        ("Crypto Signal Engine", "crypto_signal_engine/data/closed_picks.json"),
        ("Breakout Arena Spike Rev (C)", "breakout_arena/approach_c_spike_reverse/data/closed_picks.json"),
    ]

    active_systems = [
        ("Alpha Engine (active)", "alpha_engine/data/active_picks.json"),
        ("KIMI (active)", "KIMI_RISEOFTHECLAW/data/active_picks.json"),
        ("Battleground (active)", "battleground/data/active_picks.json"),
        ("Paper Trading (active)", "paper_trading/data/active_picks.json"),
        ("Multi-Asset (active)", "multi_asset/data/active_picks.json"),
        ("Crypto ML Edge (active)", "crypto_ml_edge/data/active_picks.json"),
        ("Claws of Doom (active)", "ml_battleground/system_f_clawsofdoom/data/active_picks.json"),
        ("Mercury 2 (active)", "mercury2/data/active_picks.json"),
        ("Rapid Fire (active)", "rapid_fire_data/active_picks.json"),
        ("ML Crypto Predictor (active)", "ml_crypto_predictor/enhanced_models/live_picks/active_picks.json"),
        ("Breakout ML (active)", "breakout_arena/approach_b_ml_breakout/data/active_picks.json"),
        ("CoinGlass (active)", "coinglass_strategies/data/active_picks.json"),
        ("QuanEngine (active)", "quan_engine/data/active_signals.json"),
        ("Regime Terminal (active)", "regime_terminal/data/active_signals.json"),
        ("RL Agent (active)", "rl_agent/data/active_picks.json"),
        ("Genome DNA (active)", "genome/active_picks.json"),
        ("KIMI Research Feb16 (active)", "KIMI_CLAW_RESEARCH_FEB162026/data/active_picks.json"),
        ("Multi-Asset Institutional", "multi_asset/data/institutional_picks.json"),
    ]

    archive_systems = [
        ("ML Crypto Predictor (full log)", "ml_crypto_predictor/enhanced_models/live_picks/all_picks_log.json"),
        ("Rapid Fire (all history)", "rapid_fire_data/now_picks.json"),
        ("Claws of Doom (full history)", "ml_battleground/system_f_clawsofdoom/data/picks_history.json"),
    ]

    aggregator_systems = [
        ("Signal Aggregator", "signal_aggregator/data/master_picks_tracker.json"),
        ("FC Crypto Pro", "data/fc_crypto_pro_picks.json"),
        ("Aggregated Picks", "data/aggregated_picks.json"),
    ]

    # =========================================================================
    # RUN ANALYSIS
    # =========================================================================

    all_results = []

    # Closed picks (proven track record)
    closed_results = []
    for name, path in closed_systems:
        full = BASE / path
        r = analyze_system(name, full, "closed")
        closed_results.append(r)
        all_results.append(r)

    # Active picks (current snapshot)
    active_results = []
    for name, path in active_systems:
        full = BASE / path
        r = analyze_system(name, full, "active")
        active_results.append(r)
        all_results.append(r)

    # Archives
    archive_results = []
    for name, path in archive_systems:
        full = BASE / path
        r = analyze_system(name, full, "archive")
        archive_results.append(r)

    # Aggregators
    agg_results = []
    for name, path in aggregator_systems:
        full = BASE / path
        if not (BASE / path).exists():
            continue
        r = analyze_system(name, full, "aggregator")
        agg_results.append(r)

    # =========================================================================
    # SECTION 1: $1000 SIMULATION - ALL SYSTEMS
    # =========================================================================

    print_header("$1000 SIMULATION - ALL TRADING SYSTEMS (ranked by return)")

    # Combine closed + active, sort by compounded return
    valid_results = [r for r in all_results if not r.get("error")]
    valid_results.sort(key=lambda x: x.get("compounded_return_pct", -9999), reverse=True)

    # Print header row
    print()
    print("%-36s %5s %5s %6s %8s %10s %10s %9s %9s" % (
        "SYSTEM", "PICKS", "W/L", "WR%", "AVG PnL", "$1000 NOW", "RETURN%", "BEST", "WORST"
    ))
    print("-" * 100)

    for r in valid_results:
        wl = "%d/%d" % (r["wins"], r["losses"])
        tag = ""
        if r["category"] == "active":
            tag = " [LIVE]"
        print("%-36s %5d %5s %5.1f%% %7s %10s %9s %8s %8s" % (
            (r["name"] + tag)[:36],
            r["picks_with_pnl"],
            wl,
            r["win_rate"],
            fmt_pct(r["avg_pnl"]),
            fmt_money(r["compounded_capital"]),
            fmt_pct(r["compounded_return_pct"]),
            fmt_pct(r["best_trade"]),
            fmt_pct(r["worst_trade"]),
        ))

    # Show errored systems
    errored = [r for r in all_results if r.get("error")]
    if errored:
        print()
        print("  Systems with no usable PnL data:")
        for r in errored:
            picks_info = ""
            if "total_picks" in r:
                picks_info = " (%d picks loaded)" % r["total_picks"]
            print("    - %s: %s%s" % (r["name"], r["error"], picks_info))

    # =========================================================================
    # SECTION 2: TIER RANKING
    # =========================================================================

    print_header("TIER RANKING")

    tiers = {"PROVEN": [], "PROMISING": [], "EXPERIMENTAL": [], "DEAD WEIGHT": [], "N/A": []}
    for r in all_results:
        t = tier_rank(r)
        r["tier"] = t
        tiers[t].append(r)

    tier_labels = {
        "PROVEN": "*** TIER 1: PROVEN (30+ picks, positive avg, 50%+ WR) ***",
        "PROMISING": "** TIER 2: PROMISING (10+ picks, positive avg) **",
        "EXPERIMENTAL": "* TIER 3: EXPERIMENTAL (few picks or positive edge) *",
        "DEAD WEIGHT": "TIER 4: DEAD WEIGHT (negative returns, enough data to judge)",
    }

    for tier_name in ["PROVEN", "PROMISING", "EXPERIMENTAL", "DEAD WEIGHT"]:
        systems = tiers[tier_name]
        print()
        print(tier_labels[tier_name])
        print("-" * 70)
        if not systems:
            print("  (none)")
            continue
        systems.sort(key=lambda x: x.get("compounded_return_pct", -9999), reverse=True)
        for r in systems:
            if r.get("error"):
                print("  %-35s -- no data --" % r["name"])
            else:
                print("  %-35s %3d picks | WR %.1f%% | Avg %s | $1000 -> %s (%s)" % (
                    r["name"],
                    r["picks_with_pnl"],
                    r["win_rate"],
                    fmt_pct(r["avg_pnl"]),
                    fmt_money(r["compounded_capital"]),
                    fmt_pct(r["compounded_return_pct"]),
                ))

    # =========================================================================
    # SECTION 3: HISTORICAL ARCHIVES
    # =========================================================================

    print_header("HISTORICAL ARCHIVES (large datasets)")

    print()
    print("%-40s %5s %5s %6s %8s %10s %10s" % (
        "ARCHIVE", "PICKS", "W/L", "WR%", "AVG PnL", "$1000 NOW", "RETURN%"
    ))
    print("-" * 85)

    for r in archive_results:
        if r.get("error"):
            print("%-40s -- %s --" % (r["name"], r["error"]))
        else:
            wl = "%d/%d" % (r["wins"], r["losses"])
            print("%-40s %5d %5s %5.1f%% %7s %10s %9s" % (
                r["name"],
                r["picks_with_pnl"],
                wl,
                r["win_rate"],
                fmt_pct(r["avg_pnl"]),
                fmt_money(r["compounded_capital"]),
                fmt_pct(r["compounded_return_pct"]),
            ))

    # Aggregators
    if agg_results:
        print()
        print("AGGREGATOR / CONSENSUS SYSTEMS:")
        print("-" * 60)
        for r in agg_results:
            if r.get("error"):
                picks_info = ""
                if "total_picks" in r:
                    picks_info = " (%d picks)" % r["total_picks"]
                print("  %-35s -- %s%s --" % (r["name"], r["error"], picks_info))
            else:
                print("  %-35s %3d picks | WR %.1f%% | Avg %s | $1000 -> %s" % (
                    r["name"],
                    r["picks_with_pnl"],
                    r["win_rate"],
                    fmt_pct(r["avg_pnl"]),
                    fmt_money(r["compounded_capital"]),
                ))

    # =========================================================================
    # SECTION 4: VERDICT
    # =========================================================================

    print_header("VERDICT: WHICH SYSTEMS TO BET ON vs KILL")

    proven = [r for r in tiers["PROVEN"] if not r.get("error")]
    promising = [r for r in tiers["PROMISING"] if not r.get("error")]
    dead = [r for r in tiers["DEAD WEIGHT"] if not r.get("error")]

    print()
    print("BET ON THESE (Tier 1 + Tier 2 with positive edge):")
    print("-" * 60)
    bet_on = proven + [r for r in promising if r.get("compounded_return_pct", 0) > 0]
    if bet_on:
        for r in sorted(bet_on, key=lambda x: x["compounded_return_pct"], reverse=True):
            print("  [+] %-30s $1000 -> %s (%s) | %d trades" % (
                r["name"],
                fmt_money(r["compounded_capital"]),
                fmt_pct(r["compounded_return_pct"]),
                r["picks_with_pnl"],
            ))
    else:
        print("  (none qualified)")

    print()
    print("KILL THESE (negative returns with enough data):")
    print("-" * 60)
    if dead:
        for r in sorted(dead, key=lambda x: x["compounded_return_pct"]):
            print("  [X] %-30s $1000 -> %s (%s) | %d trades" % (
                r["name"],
                fmt_money(r["compounded_capital"]),
                fmt_pct(r["compounded_return_pct"]),
                r["picks_with_pnl"],
            ))
    else:
        print("  (none - all systems have positive or insufficient data)")

    print()
    print("WATCH LIST (experimental, not enough data yet):")
    print("-" * 60)
    experimental = [r for r in tiers["EXPERIMENTAL"] if not r.get("error")]
    if experimental:
        for r in sorted(experimental, key=lambda x: x["compounded_return_pct"], reverse=True):
            print("  [?] %-30s $1000 -> %s (%s) | %d trades" % (
                r["name"],
                fmt_money(r["compounded_capital"]),
                fmt_pct(r["compounded_return_pct"]),
                r["picks_with_pnl"],
            ))
    else:
        print("  (none)")

    # =========================================================================
    # SECTION 5: COMBINED PORTFOLIO
    # =========================================================================

    print_header("COMBINED PORTFOLIO: $1000 SPLIT ACROSS TIER 1 SYSTEMS")

    tier1 = [r for r in tiers["PROVEN"] if not r.get("error")]

    if not tier1:
        # Fall back to top performers from any tier
        print()
        print("  No Tier 1 (Proven) systems found. Using top 5 performers instead.")
        tier1 = sorted(
            [r for r in valid_results if r.get("compounded_return_pct", 0) > 0],
            key=lambda x: x["compounded_return_pct"],
            reverse=True
        )[:5]

    if tier1:
        per_system = INITIAL_CAPITAL / len(tier1)
        total_final = 0

        print()
        print("  Allocating %s per system across %d systems:" % (
            fmt_money(per_system), len(tier1)
        ))
        print()
        print("  %-35s %10s %10s %10s" % ("SYSTEM", "INVESTED", "FINAL", "P/L"))
        print("  " + "-" * 70)

        for r in sorted(tier1, key=lambda x: x["compounded_return_pct"], reverse=True):
            ret_pct = r["compounded_return_pct"]
            final = per_system * (1 + ret_pct / 100)
            pl = final - per_system
            total_final += final
            print("  %-35s %10s %10s %10s" % (
                r["name"],
                fmt_money(per_system),
                fmt_money(final),
                fmt_money(pl),
            ))

        total_pl = total_final - INITIAL_CAPITAL
        total_ret = (total_final - INITIAL_CAPITAL) / INITIAL_CAPITAL * 100

        print("  " + "-" * 70)
        print("  %-35s %10s %10s %10s" % (
            "TOTAL PORTFOLIO",
            fmt_money(INITIAL_CAPITAL),
            fmt_money(total_final),
            fmt_money(total_pl),
        ))
        print()
        print("  PORTFOLIO RETURN: %s" % fmt_pct(total_ret))
        print("  $1000 BECAME: %s" % fmt_money(total_final))
    else:
        print()
        print("  No systems with positive returns found.")

    # =========================================================================
    # SUMMARY STATS
    # =========================================================================

    print_header("SUMMARY STATISTICS")

    total_systems = len(all_results)
    total_valid = len(valid_results)
    total_picks_all = sum(r.get("picks_with_pnl", 0) for r in valid_results)
    positive_systems = sum(1 for r in valid_results if r.get("compounded_return_pct", 0) > 0)
    negative_systems = sum(1 for r in valid_results if r.get("compounded_return_pct", 0) < 0)

    print()
    print("  Total systems analyzed:    %d" % total_systems)
    print("  Systems with PnL data:     %d" % total_valid)
    print("  Total trades analyzed:     %d" % total_picks_all)
    print("  Profitable systems:        %d" % positive_systems)
    print("  Losing systems:            %d" % negative_systems)
    print("  Tier 1 (Proven):           %d" % len(tiers["PROVEN"]))
    print("  Tier 2 (Promising):        %d" % len(tiers["PROMISING"]))
    print("  Tier 3 (Experimental):     %d" % len(tiers["EXPERIMENTAL"]))
    print("  Tier 4 (Dead Weight):      %d" % len(tiers["DEAD WEIGHT"]))

    # Best and worst overall
    if valid_results:
        best = max(valid_results, key=lambda x: x.get("compounded_return_pct", -9999))
        worst = min(valid_results, key=lambda x: x.get("compounded_return_pct", 9999))
        print()
        print("  BEST SYSTEM:  %-25s -> %s (%s)" % (
            best["name"], fmt_money(best["compounded_capital"]),
            fmt_pct(best["compounded_return_pct"])
        ))
        print("  WORST SYSTEM: %-25s -> %s (%s)" % (
            worst["name"], fmt_money(worst["compounded_capital"]),
            fmt_pct(worst["compounded_return_pct"])
        ))

    print()
    print_separator("=")
    print("  Simulation complete. All values based on historical/current PnL data.")
    print("  Past performance does not guarantee future results.")
    print_separator("=")
    print()


if __name__ == "__main__":
    main()
