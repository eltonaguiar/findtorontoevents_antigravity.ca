#!/usr/bin/env python3
"""
TL;DR What REALLY Would've Won — Hourly winner analysis report.

Analyzes closed picks across multiple time windows to find the optimal
filter combinations that would have maximized profits.

Output: alpha_engine/data/tldr_report.json
"""

import json
import os
import sys
from datetime import datetime, timezone
from itertools import combinations
from pathlib import Path

# Windows UTF-8 fix (guard against missing .buffer on redirected streams)
if sys.platform == "win32":
    import io
    try:
        if hasattr(sys.stdout, "buffer"):
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "buffer"):
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
    except (ValueError, AttributeError):
        pass  # Stream already wrapped or unavailable

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_DIR = SCRIPT_DIR.parent
PAYLOAD_PATH = ROOT_DIR / "audit_trail" / "data" / "dashboard_payload.json"
OUTPUT_PATH = SCRIPT_DIR / "data" / "tldr_report.json"


# ---------------------------------------------------------------------------
# Exit reason normalizer
# ---------------------------------------------------------------------------
def normalize_exit_reason(raw: str) -> str:
    """Collapse verbose exit reasons into canonical buckets."""
    if not raw:
        return "UNKNOWN"
    r = raw.upper()
    if "TAKE_PROFIT" in r or r in ("TP", "TP_HIT"):
        return "TP_HIT"
    if "STOP_LOSS" in r or r in ("SL", "SL_HIT"):
        return "SL_HIT"
    if "EXPIRED" in r or "STALE" in r:
        return "EXPIRED"
    if "TIME" in r:
        return "TIME_EXIT"
    if "PARTIAL" in r:
        return "PARTIAL_WIN"
    return "OTHER"


# ---------------------------------------------------------------------------
# Strategy family grouping
# ---------------------------------------------------------------------------
FAMILY_MAP = {
    "momentum": ["momentum", "rsi_momentum", "macd_momentum", "breakout"],
    "mean_reversion": ["mean_reversion", "bollinger", "rsi_oversold", "fear_greed_contrarian"],
    "trend_following": ["ema_cross", "sma_cross", "supertrend", "trend", "multi_timeframe_ema"],
    "ml_enhanced": ["ml_enhanced", "ml_crypto", "ml_signal", "ml_predictor", "catboost"],
    "copy_trader": ["copy_trader", "whale", "smart_money"],
    "on_chain": ["onchain", "exchange_netflow", "whale_accumulation"],
    "scalp": ["scalp", "micro", "quick"],
    "swing": ["swing", "position"],
    "volatility": ["atr", "volatility", "keltner", "squeeze"],
    "confluence": ["confluence", "multi_system", "agreement"],
    "sentiment": ["sentiment", "fear_greed", "social", "lunarcrush"],
    "forex": ["forex", "carry_trade", "london_breakout"],
    "equity": ["equity", "sector_rotation", "earnings"],
}


def get_strategy_family(strategy: str) -> str:
    """Map a strategy name to its family."""
    s = (strategy or "").lower()
    for family, keywords in FAMILY_MAP.items():
        for kw in keywords:
            if kw in s:
                return family
    return "other"


# ---------------------------------------------------------------------------
# Filter dimensions
# ---------------------------------------------------------------------------
def build_filter_dimensions(picks: list, exclude_outcome: bool = True) -> dict:
    """Build all filter dimensions to test against the pick set.

    If exclude_outcome=True, skip exit_reason filters since they're
    tautological (TP_HIT is always 100% WR by definition).
    """
    filters = {}

    # Direction
    filters["LONG"] = lambda p: p.get("direction") == "LONG"
    filters["SHORT"] = lambda p: p.get("direction") == "SHORT"

    # Asset class
    for ac in ("CRYPTO", "EQUITY", "FOREX"):
        filters[ac] = lambda p, _ac=ac: p.get("asset_class") == _ac

    # Score tiers
    for threshold in (30, 40, 50, 60, 70, 80):
        filters[f"score>={threshold}"] = lambda p, t=threshold: (p.get("score") or 0) >= t

    # Confidence tiers
    filters["conf>=0.50"] = lambda p: (p.get("confidence") or 0) >= 0.50
    filters["conf>=0.65"] = lambda p: (p.get("confidence") or 0) >= 0.65
    filters["conf_0.75-0.85"] = lambda p: 0.75 <= (p.get("confidence") or 0) <= 0.85
    filters["conf>=0.85"] = lambda p: (p.get("confidence") or 0) >= 0.85

    # Timeframe
    for tf in ("SCALP", "INTRADAY", "SWING", "POSITION"):
        filters[tf] = lambda p, _tf=tf: p.get("trade_timeframe") == _tf

    # Trust tier (may be empty in current data)
    for tier in ("PROVEN", "RELIABLE", "SANDBOX"):
        filters[f"trust={tier}"] = lambda p, _t=tier: (p.get("trust_tier") or "").upper() == _t

    # Exit reason (excluded from combo search by default — they're outcomes, not predictive)
    if not exclude_outcome:
        for er in ("TP_HIT", "SL_HIT", "EXPIRED", "TIME_EXIT"):
            filters[f"exit={er}"] = lambda p, _er=er: normalize_exit_reason(p.get("exit_reason", "")) == _er

    # Strategy families
    families_in_data = set(get_strategy_family(p.get("strategy", "")) for p in picks)
    for fam in families_in_data:
        if fam != "other":
            filters[f"family={fam}"] = lambda p, _f=fam: get_strategy_family(p.get("strategy", "")) == _f

    return filters


# ---------------------------------------------------------------------------
# Stats computation
# ---------------------------------------------------------------------------
def compute_stats(picks: list) -> dict:
    """Compute WR, PnL stats for a set of picks."""
    if not picks:
        return {"trades": 0, "wr": 0, "pnl": 0, "avg_pnl": 0, "wins": 0, "losses": 0}
    wins = sum(1 for p in picks if p.get("status") == "WON")
    losses = sum(1 for p in picks if p.get("status") == "LOST")
    total = wins + losses
    wr = (wins / total * 100) if total > 0 else 0
    pnl = sum(p.get("pnl_pct", 0) for p in picks)
    avg_pnl = pnl / len(picks) if picks else 0
    return {
        "trades": len(picks),
        "wr": round(wr, 1),
        "pnl": round(pnl, 2),
        "avg_pnl": round(avg_pnl, 4),
        "wins": wins,
        "losses": losses,
    }


# ---------------------------------------------------------------------------
# Time window slicer
# ---------------------------------------------------------------------------
def slice_by_hours(picks: list, max_hours: float | None) -> list:
    """Return picks within max_hours of the most recent timestamp."""
    if max_hours is None:
        return picks
    if not picks:
        return []
    now = datetime.now(timezone.utc)
    return [p for p in picks if p.get("age_hours", 9999) <= max_hours]


# ---------------------------------------------------------------------------
# Best filter combos
# ---------------------------------------------------------------------------
def find_best_filters(picks: list, filters: dict, combo_size: int, min_trades: int = 3) -> dict | None:
    """Find the best N-filter combination by total PnL."""
    # Pre-filter: only use filters that actually select something
    active_filters = {}
    for name, fn in filters.items():
        matching = [p for p in picks if fn(p)]
        if min_trades <= len(matching) < len(picks):
            active_filters[name] = fn

    if not active_filters:
        return None

    filter_names = list(active_filters.keys())

    # Limit combinatorial explosion
    if combo_size == 1:
        candidates = [(n,) for n in filter_names]
    elif combo_size == 2:
        candidates = list(combinations(filter_names, 2))
        if len(candidates) > 500:
            # Pre-screen: keep top 30 single filters by PnL
            singles = []
            for n in filter_names:
                subset = [p for p in picks if active_filters[n](p)]
                if len(subset) >= min_trades:
                    singles.append((n, compute_stats(subset)["pnl"]))
            singles.sort(key=lambda x: x[1], reverse=True)
            top_names = [s[0] for s in singles[:30]]
            candidates = list(combinations(top_names, 2))
    else:
        # For 3-combos, pre-screen top 20 singles
        singles = []
        for n in filter_names:
            subset = [p for p in picks if active_filters[n](p)]
            if len(subset) >= min_trades:
                singles.append((n, compute_stats(subset)["pnl"]))
        singles.sort(key=lambda x: x[1], reverse=True)
        top_names = [s[0] for s in singles[:20]]
        candidates = list(combinations(top_names, 3))

    best = None
    best_pnl = -float("inf")

    for combo in candidates:
        subset = picks
        for name in combo:
            subset = [p for p in subset if active_filters[name](p)]
        if len(subset) < min_trades:
            continue
        stats = compute_stats(subset)
        if stats["pnl"] > best_pnl:
            best_pnl = stats["pnl"]
            best = {
                "filters": list(combo) if combo_size > 1 else combo[0],
                **stats,
            }

    return best


# ---------------------------------------------------------------------------
# Winning / losing strategies and symbols
# ---------------------------------------------------------------------------
def rank_by_dimension(picks: list, key: str, top_n: int = 10) -> tuple:
    """Group picks by a dimension, return (winners, losers) sorted by PnL."""
    groups = {}
    for p in picks:
        val = p.get(key, "unknown") or "unknown"
        groups.setdefault(val, []).append(p)

    ranked = []
    for name, group in groups.items():
        stats = compute_stats(group)
        if stats["trades"] < 2:
            continue
        # Find best symbol within group
        sym_pnl = {}
        for p in group:
            s = p.get("symbol", "?")
            sym_pnl[s] = sym_pnl.get(s, 0) + p.get("pnl_pct", 0)
        best_sym = max(sym_pnl, key=sym_pnl.get) if sym_pnl else "?"
        ranked.append({"name": name, "best_symbol": best_sym, **stats})

    ranked.sort(key=lambda x: x["pnl"], reverse=True)
    winners = ranked[:top_n]
    losers = sorted(ranked, key=lambda x: x["pnl"])[:top_n]
    return winners, losers


# ---------------------------------------------------------------------------
# Additional filter suggestions
# ---------------------------------------------------------------------------
def suggest_additional_filters(picks: list, best_combo: dict | None, filters: dict) -> list:
    """Suggest additional filters that would've improved the best combo."""
    suggestions = []
    if not best_combo or not picks:
        return suggestions

    # Get the subset from the best combo
    combo_filters = best_combo.get("filters", [])
    if isinstance(combo_filters, str):
        combo_filters = [combo_filters]

    subset = picks
    for fname in combo_filters:
        if fname in filters:
            subset = [p for p in subset if filters[fname](p)]

    if len(subset) < 3:
        return suggestions

    base_stats = compute_stats(subset)

    # Try adding each unused filter
    for fname, fn in filters.items():
        if fname in combo_filters:
            continue
        enhanced = [p for p in subset if fn(p)]
        if len(enhanced) < 2 or len(enhanced) == len(subset):
            continue
        es = compute_stats(enhanced)
        if es["wr"] > base_stats["wr"] + 5 and es["trades"] >= 2:
            suggestions.append(
                f"Adding '{fname}' to best combo would boost WR from "
                f"{base_stats['wr']}% to {es['wr']}% ({es['trades']} trades, PnL {es['pnl']:+.1f}%)"
            )
        # Also check exclusion (inverse)
        excluded = [p for p in subset if not fn(p)]
        if len(excluded) < 2 or len(excluded) == len(subset):
            continue
        exs = compute_stats(excluded)
        removed_count = len(subset) - len(excluded)
        pnl_saved = exs["pnl"] - base_stats["pnl"]
        if exs["wr"] > base_stats["wr"] + 5 and pnl_saved > 0:
            suggestions.append(
                f"Excluding '{fname}' would remove {removed_count} trades and boost WR to "
                f"{exs['wr']}% (saving {pnl_saved:+.1f}% PnL)"
            )

    # Sort by impact and take top 5
    suggestions.sort(key=lambda s: float(s.split("to ")[-1].split("%")[0]) if "to " in s else 0, reverse=True)
    return suggestions[:5]


# ---------------------------------------------------------------------------
# Build TL;DR summary
# ---------------------------------------------------------------------------
def build_tldr_summary(window_name: str, stats: dict) -> str:
    """Generate a human-readable TL;DR for a time window."""
    parts = []

    total = stats.get("total_trades", 0)
    baseline = stats.get("baseline", {})
    parts.append(f"In {window_name}, {total} trades closed")

    if baseline.get("wr"):
        parts.append(f"(baseline WR {baseline['wr']}%, PnL {baseline['pnl']:+.1f}%).")
    else:
        parts.append(".")

    best1 = stats.get("best_single_filter")
    if best1:
        f = best1.get("filter", best1.get("filters", "?"))
        parts.append(
            f"Best single filter: {f} ({best1['wr']}% WR, {best1['pnl']:+.1f}% PnL, {best1['trades']} trades)."
        )

    best2 = stats.get("best_2_combo")
    if best2:
        f = " + ".join(best2["filters"]) if isinstance(best2.get("filters"), list) else str(best2.get("filters"))
        parts.append(f"Best 2-filter combo: {f} ({best2['wr']}% WR, {best2['pnl']:+.1f}%).")

    winners = stats.get("winning_strategies", [])
    if winners:
        top = winners[0]
        parts.append(
            f"Top strategy: {top['name']} ({top['wr']}% WR, {top['pnl']:+.1f}% on {top.get('best_symbol', '?')})."
        )

    avoid = stats.get("avoid", [])
    if avoid:
        worst = avoid[0]
        parts.append(f"AVOID: {worst['name']} ({worst['wr']}% WR, {worst['pnl']:+.1f}% PnL).")

    return " ".join(parts)


# ---------------------------------------------------------------------------
# Analyze one time window
# ---------------------------------------------------------------------------
def analyze_window(picks: list, window_name: str) -> dict:
    """Full analysis for one time window."""
    if not picks:
        return {
            "total_trades": 0,
            "baseline": {"wr": 0, "pnl": 0, "avg_pnl": 0},
            "best_single_filter": None,
            "best_2_combo": None,
            "best_3_combo": None,
            "winning_strategies": [],
            "winning_symbols": [],
            "avoid": [],
            "additional_filters": [],
            "tldr_summary": f"No closed trades in {window_name}.",
        }

    filters = build_filter_dimensions(picks, exclude_outcome=True)
    baseline = compute_stats(picks)

    # Best single filter
    best1 = find_best_filters(picks, filters, combo_size=1, min_trades=max(2, len(picks) // 20))
    if best1:
        improvement = best1["pnl"] - baseline["pnl"]
        best1["improvement"] = f"{improvement:+.1f}% PnL vs baseline"
        best1 = {"filter": best1.pop("filters", "?"), **best1}

    # Best 2-filter combo
    best2 = find_best_filters(picks, filters, combo_size=2, min_trades=max(2, len(picks) // 20))

    # Best 3-filter combo
    best3 = find_best_filters(picks, filters, combo_size=3, min_trades=max(2, len(picks) // 30))

    # Winning/losing strategies
    strat_winners, strat_losers = rank_by_dimension(picks, "strategy", top_n=10)

    # Winning/losing symbols
    sym_winners, sym_losers = rank_by_dimension(picks, "symbol", top_n=10)

    # Build avoid list
    avoid = []
    for loser in strat_losers[:5]:
        if loser["pnl"] < 0:
            avoid.append({**loser, "reason": "consistently losing strategy"})
    for loser in sym_losers[:3]:
        if loser["pnl"] < 0 and loser not in avoid:
            avoid.append({**loser, "reason": "worst performing symbol"})

    # Check worst filters
    for fname, fn in filters.items():
        subset = [p for p in picks if fn(p)]
        if len(subset) >= 3:
            s = compute_stats(subset)
            if s["pnl"] < -5 and s["wr"] < baseline["wr"] - 10:
                avoid.append({"name": fname, "filter": fname, **s, "reason": f"worst filter ({s['wr']}% WR)"})

    avoid.sort(key=lambda x: x.get("pnl", 0))
    avoid = avoid[:8]

    # Additional filter suggestions
    additional = suggest_additional_filters(picks, best2 or best1, filters)

    result = {
        "total_trades": len(picks),
        "baseline": {
            "wr": baseline["wr"],
            "pnl": baseline["pnl"],
            "avg_pnl": baseline["avg_pnl"],
        },
        "best_single_filter": best1,
        "best_2_combo": best2,
        "best_3_combo": best3,
        "winning_strategies": strat_winners[:10],
        "winning_symbols": sym_winners[:10],
        "avoid": avoid,
        "additional_filters": additional,
    }
    result["tldr_summary"] = build_tldr_summary(window_name, result)
    return result


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    print("=" * 60)
    print("  TL;DR What REALLY Would've Won")
    print(f"  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 60)

    if not PAYLOAD_PATH.exists():
        print(f"ERROR: {PAYLOAD_PATH} not found")
        sys.exit(1)

    with open(PAYLOAD_PATH, "r", encoding="utf-8") as f:
        payload = json.load(f)

    closed_picks = payload.get("picks", {}).get("recent_closed", [])
    print(f"Loaded {len(closed_picks)} closed picks")

    if not closed_picks:
        print("No closed picks to analyze")
        report = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "time_windows": {},
            "error": "No closed picks available",
        }
        OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
        return

    # Time windows
    windows = {
        "last_1h": 1,
        "last_4h": 4,
        "last_24h": 24,
        "last_48h": 48,
        "all_time": None,
    }

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_closed_analyzed": len(closed_picks),
        "time_windows": {},
    }

    for window_name, max_hours in windows.items():
        subset = slice_by_hours(closed_picks, max_hours)
        print(f"\n--- {window_name}: {len(subset)} picks ---")
        analysis = analyze_window(subset, window_name)
        report["time_windows"][window_name] = analysis
        print(f"  Baseline: WR={analysis['baseline']['wr']}%, PnL={analysis['baseline']['pnl']:+.1f}%")
        if analysis.get("best_single_filter"):
            bf = analysis["best_single_filter"]
            print(f"  Best filter: {bf.get('filter','?')} -> WR={bf['wr']}%, PnL={bf['pnl']:+.1f}%")
        if analysis.get("best_2_combo"):
            bc = analysis["best_2_combo"]
            print(f"  Best 2-combo: {bc.get('filters','?')} -> WR={bc['wr']}%, PnL={bc['pnl']:+.1f}%")
        print(f"  TL;DR: {analysis['tldr_summary'][:120]}...")

    # Save report
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print(f"\nReport saved to {OUTPUT_PATH}")
    print("Done.")


if __name__ == "__main__":
    main()
