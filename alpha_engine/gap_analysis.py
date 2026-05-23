#!/usr/bin/env python3
"""
Gap Analysis System — identifies WHERE we're missing winning trades.

Segments by: hour-of-day, asset class, direction, strategy system, score tier.
Finds the top gaps (worst WR vs average) and suggests gate/filter fixes.

Stdlib only. Windows UTF-8 safe.
"""

import sys
import os
import io
import json
import math
from collections import defaultdict
from datetime import datetime, timezone

# ── Windows UTF-8 fix ──────────────────────────────────────────────
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

# ── Data sources ───────────────────────────────────────────────────
DASHBOARD_PAYLOAD = os.path.join(ROOT, "audit_trail", "data", "dashboard_payload.json")
UNIVERSAL_RESOLVED = os.path.join(ROOT, "audit_trail", "data", "universal_resolved_picks.json")
CLOSED_PICKS = os.path.join(DATA_DIR, "closed_picks.json")
OUTPUT_FILE = os.path.join(DATA_DIR, "gap_analysis.json")


def _load_json(path):
    """Load JSON file, return None on failure."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"  [WARN] Could not load {os.path.basename(path)}: {e}")
        return None


def _classify_asset(symbol, category=None, asset_class=None):
    """Determine asset class from symbol name / explicit fields."""
    if asset_class:
        ac = asset_class.upper()
        if ac in ("CRYPTO", "FOREX", "EQUITY", "FUTURES", "COMMODITY"):
            # Normalize FUTURES/COMMODITY -> closest bucket
            if ac == "FUTURES":
                return "CRYPTO"  # most futures in this system are crypto perps
            if ac == "COMMODITY":
                return "EQUITY"
            return ac
    if category:
        cat = category.lower()
        if cat in ("crypto", "cryptocurrency"):
            return "CRYPTO"
        if cat in ("forex", "fx"):
            return "FOREX"
        if cat in ("equity", "stock", "stocks"):
            return "EQUITY"
    # Heuristic from symbol
    s = (symbol or "").upper()
    forex_tokens = ("USD", "EUR", "GBP", "JPY", "CHF", "AUD", "NZD", "CAD")
    if any(s == a + b or s == a + b + ".FX" for a in forex_tokens for b in forex_tokens if a != b):
        return "FOREX"
    if s.endswith("USDT") or s.endswith("USD") or s.endswith("BTC") or s.endswith("ETH"):
        return "CRYPTO"
    equity_hints = ("SPY", "QQQ", "AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "NVDA",
                    "META", "AMD", "NFLX", "DIA", "IWM", "XLF", "XLE", "GLD", "SLV")
    if s in equity_hints:
        return "EQUITY"
    return "CRYPTO"  # default for this system


def _parse_hour(timestamp_str):
    """Extract UTC hour from ISO timestamp string."""
    if not timestamp_str:
        return None
    try:
        # Handle various formats
        ts = timestamp_str.replace("Z", "+00:00")
        if "T" in ts:
            dt = datetime.fromisoformat(ts)
            return dt.hour
        # Date-only format like "2026-03-18"
        return None
    except Exception:
        return None


def _confidence_to_tier(confidence):
    """Map confidence/score to letter tier."""
    if confidence is None:
        return "UNKNOWN"
    try:
        c = float(confidence)
    except (ValueError, TypeError):
        return "UNKNOWN"
    if c >= 0.9:
        return "S"
    if c >= 0.8:
        return "A"
    if c >= 0.7:
        return "B"
    if c >= 0.6:
        return "C"
    if c >= 0.5:
        return "D"
    return "F"


def _determine_direction(pick):
    """Get LONG/SHORT from pick data."""
    d = pick.get("direction") or pick.get("signal_type") or ""
    d = d.upper()
    if d in ("LONG", "BUY"):
        return "LONG"
    if d in ("SHORT", "SELL"):
        return "SHORT"
    return "UNKNOWN"


def _is_win(pick):
    """Determine if a pick was a winner."""
    status = (pick.get("status") or "").upper()
    if status == "WON":
        return True
    if status == "LOST":
        return False
    exit_reason = (pick.get("exit_reason") or "").upper()
    if "TP" in exit_reason:
        return True
    if "SL" in exit_reason:
        return False
    pnl = pick.get("pnl_pct")
    if pnl is not None:
        try:
            return float(pnl) > 0
        except (ValueError, TypeError):
            pass
    return False


def _extract_source_system(pick):
    """Get the source system (alpha_engine, kimi, copy_trader, etc.)."""
    ss = pick.get("source_system") or ""
    if ss:
        # Normalize common prefixes
        sl = ss.lower()
        if "copy_trader" in sl:
            return "copy_trader"
        if "kimi" in sl:
            return "kimi"
        if "alpha" in sl or "incubator" in sl or "dna" in sl:
            return "alpha_engine"
        if "rapid" in sl:
            return "rapid_fire"
        if "ai_challenge" in sl or "claude" in sl:
            return "ai_challenge"
        if "gainer" in sl:
            return "alpha_engine"
        return sl
    # Fallback: infer from strategy name
    strat = (pick.get("strategy") or "").lower()
    if "copy" in strat:
        return "copy_trader"
    if "kimi" in strat or "claw" in strat:
        return "kimi"
    if "rapid" in strat:
        return "rapid_fire"
    if "gainer" in strat or "dna" in strat or "incubator" in strat:
        return "alpha_engine"
    return "alpha_engine"


def load_all_closed_picks():
    """Load closed picks from all available sources, deduplicate."""
    all_picks = []
    seen_ids = set()

    def _pick_id(p):
        return (
            p.get("symbol", ""),
            p.get("strategy", ""),
            str(p.get("timestamp", "")),
            str(p.get("entry_price", "")),
        )

    # Source 1: universal_resolved_picks.json (highest quality — has source_system)
    data = _load_json(UNIVERSAL_RESOLVED)
    if isinstance(data, list):
        for p in data:
            pid = _pick_id(p)
            if pid not in seen_ids:
                seen_ids.add(pid)
                all_picks.append(p)
        print(f"  Loaded {len(data)} from universal_resolved_picks.json")

    # Source 2: closed_picks.json (alpha_engine)
    data = _load_json(CLOSED_PICKS)
    if isinstance(data, list):
        added = 0
        for p in data:
            pid = _pick_id(p)
            if pid not in seen_ids:
                seen_ids.add(pid)
                all_picks.append(p)
                added += 1
        print(f"  Loaded {added} new from closed_picks.json (skipped {len(data) - added} dupes)")

    # Source 3: dashboard_payload.json picks (only if it has a closed array)
    data = _load_json(DASHBOARD_PAYLOAD)
    if isinstance(data, dict):
        picks_section = data.get("picks", {})
        closed_list = picks_section.get("closed", [])
        if isinstance(closed_list, list) and closed_list:
            added = 0
            for p in closed_list:
                pid = _pick_id(p)
                if pid not in seen_ids:
                    seen_ids.add(pid)
                    all_picks.append(p)
                    added += 1
            print(f"  Loaded {added} new from dashboard_payload.json picks.closed")

    print(f"  Total unique closed picks: {len(all_picks)}")
    return all_picks


def normalize_pick(pick):
    """Extract standardized fields from a pick."""
    return {
        "symbol": (pick.get("symbol") or "UNKNOWN").upper(),
        "direction": _determine_direction(pick),
        "pnl_pct": pick.get("pnl_pct"),
        "strategy": pick.get("strategy") or "unknown",
        "timestamp": pick.get("timestamp") or pick.get("entry_date") or "",
        "asset_class": _classify_asset(
            pick.get("symbol"),
            pick.get("category"),
            pick.get("asset_class"),
        ),
        "source_system": _extract_source_system(pick),
        "confidence": pick.get("confidence") or pick.get("ml_score"),
        "score_tier": _confidence_to_tier(pick.get("confidence") or pick.get("ml_score")),
        "hour_utc": _parse_hour(pick.get("timestamp") or pick.get("entry_date")),
        "exit_reason": pick.get("exit_reason") or "",
        "is_win": _is_win(pick),
    }


def compute_segment_stats(picks, key_fn, label):
    """Group picks by key_fn, compute WR stats for each segment."""
    buckets = defaultdict(lambda: {"wins": 0, "losses": 0, "total_pnl": 0.0, "picks": []})
    for p in picks:
        k = key_fn(p)
        if k is None:
            continue
        b = buckets[k]
        if p["is_win"]:
            b["wins"] += 1
        else:
            b["losses"] += 1
        try:
            b["total_pnl"] += float(p["pnl_pct"] or 0)
        except (ValueError, TypeError):
            pass

    results = {}
    for k, b in sorted(buckets.items(), key=lambda x: str(x[0])):
        total = b["wins"] + b["losses"]
        if total == 0:
            continue
        wr = round(100.0 * b["wins"] / total, 1)
        results[str(k)] = {
            "win_rate": wr,
            "wins": b["wins"],
            "losses": b["losses"],
            "total": total,
            "total_pnl": round(b["total_pnl"], 2),
            "avg_pnl": round(b["total_pnl"] / total, 3),
        }
    return results


def find_gaps(segment_results, overall_wr, min_trades=10):
    """Find segments performing worst vs the overall average."""
    gaps = []
    for seg_name, stats in segment_results.items():
        if stats["total"] < min_trades:
            continue
        delta = stats["win_rate"] - overall_wr
        gaps.append({
            "segment": seg_name,
            "win_rate": stats["win_rate"],
            "overall_wr": overall_wr,
            "delta": round(delta, 1),
            "trades": stats["total"],
            "total_pnl": stats["total_pnl"],
            "avg_pnl": stats["avg_pnl"],
        })
    gaps.sort(key=lambda g: g["delta"])
    return gaps


# ── Gate/filter suggestions per dimension ──────────────────────────
SUGGESTIONS = {
    "hour_of_day": {
        "default": "Add hour-of-day filter gate: skip signals generated during hour {segment} UTC",
        "detail": "Asian session (0-8 UTC) or late US session (21-23 UTC) often has low liquidity → wider spreads → more SL hits",
    },
    "asset_class": {
        "FOREX": "Tighten forex entry: require ATR > 1.5x median + RSI confirmation. Forex has thinner margins.",
        "EQUITY": "Add equity market-hours gate: only trade during NYSE 14:30-20:00 UTC. Filter pre/post-market noise.",
        "CRYPTO": "Add volume-ratio gate: require 24h volume > 2x 7d average before entry.",
        "default": "Review asset class {segment}: may need class-specific TP/SL ratios.",
    },
    "direction": {
        "LONG": "Add trend-confirmation gate for longs: require price > EMA-50 on 4H timeframe.",
        "SHORT": "Add trend-confirmation gate for shorts: require price < EMA-50 on 4H + negative funding rate.",
        "default": "Review direction bias: system may be over-generating {segment} signals in wrong regime.",
    },
    "source_system": {
        "copy_trader": "Increase copy_trader minimum whale PnL threshold. Filter whales with < 55% WR.",
        "kimi": "Tighten KIMI confidence threshold from 0.6 to 0.7. Add regime filter.",
        "rapid_fire": "Rapid fire signals need cooldown gate: max 1 signal per symbol per 4 hours.",
        "ai_challenge": "AI challenge strategies need longer backtest validation before promotion.",
        "default": "Review {segment} system: may need strategy-level WR gating (kill < 40% WR strats).",
    },
    "score_tier": {
        "F": "GATE: Block all F-tier signals (confidence < 0.5). These destroy edge.",
        "D": "GATE: Require D-tier signals to have 2+ system consensus before entry.",
        "C": "Reduce position size for C-tier by 50%. Marginal confidence = marginal sizing.",
        "default": "Review tier {segment}: consider raising minimum confidence threshold.",
    },
}


def suggest_fix(dimension, segment):
    """Return a suggested gate/filter fix for a gap."""
    dim_suggestions = SUGGESTIONS.get(dimension, {})
    suggestion = dim_suggestions.get(segment, dim_suggestions.get("default", ""))
    return suggestion.format(segment=segment)


def format_table(title, stats, overall_wr):
    """Print a formatted ASCII table for a segment dimension."""
    if not stats:
        return
    print(f"\n{'=' * 70}")
    print(f"  {title}")
    print(f"{'=' * 70}")
    print(f"  {'Segment':<22} {'WR%':>6} {'Delta':>7} {'Wins':>6} {'Losses':>7} {'Total':>6} {'AvgPnL':>8}")
    print(f"  {'-' * 22} {'-' * 6} {'-' * 7} {'-' * 6} {'-' * 7} {'-' * 6} {'-' * 8}")
    for seg, s in sorted(stats.items(), key=lambda x: x[1]["win_rate"]):
        delta = s["win_rate"] - overall_wr
        flag = " **" if delta < -5 else ""
        print(f"  {seg:<22} {s['win_rate']:>5.1f}% {delta:>+6.1f}% {s['wins']:>6} {s['losses']:>7} {s['total']:>6} {s['avg_pnl']:>+7.3f}{flag}")
    print(f"  {'OVERALL':<22} {overall_wr:>5.1f}%")


def run():
    """Main entry point for workflow integration."""
    print("\n" + "=" * 70)
    print("  GAP ANALYSIS — Where are we missing winning trades?")
    print("=" * 70)

    # Load data
    print("\n[1/5] Loading closed picks...")
    raw_picks = load_all_closed_picks()
    if not raw_picks:
        print("  ERROR: No closed picks found. Nothing to analyze.")
        return {"error": "no_data"}

    # Normalize
    print("[2/5] Normalizing picks...")
    picks = [normalize_pick(p) for p in raw_picks]
    total_wins = sum(1 for p in picks if p["is_win"])
    total_losses = sum(1 for p in picks if not p["is_win"])
    total = total_wins + total_losses
    overall_wr = round(100.0 * total_wins / total, 1) if total > 0 else 0.0
    print(f"  {total} picks | {total_wins} wins | {total_losses} losses | WR: {overall_wr}%")

    # Compute segments
    print("[3/5] Computing segment breakdowns...")

    hour_stats = compute_segment_stats(
        picks, lambda p: f"{p['hour_utc']:02d}:00" if p["hour_utc"] is not None else None, "hour"
    )
    asset_stats = compute_segment_stats(picks, lambda p: p["asset_class"], "asset_class")
    direction_stats = compute_segment_stats(picks, lambda p: p["direction"], "direction")
    system_stats = compute_segment_stats(picks, lambda p: p["source_system"], "source_system")
    tier_stats = compute_segment_stats(picks, lambda p: p["score_tier"], "score_tier")

    # Print tables
    format_table("WIN RATE BY HOUR OF DAY (UTC)", hour_stats, overall_wr)
    format_table("WIN RATE BY ASSET CLASS", asset_stats, overall_wr)
    format_table("WIN RATE BY DIRECTION", direction_stats, overall_wr)
    format_table("WIN RATE BY SOURCE SYSTEM", system_stats, overall_wr)
    format_table("WIN RATE BY SCORE TIER", tier_stats, overall_wr)

    # Find top gaps across all dimensions
    print("\n[4/5] Identifying top gaps...")
    all_gaps = []

    for dim_name, dim_stats in [
        ("hour_of_day", hour_stats),
        ("asset_class", asset_stats),
        ("direction", direction_stats),
        ("source_system", system_stats),
        ("score_tier", tier_stats),
    ]:
        gaps = find_gaps(dim_stats, overall_wr, min_trades=10)
        for g in gaps:
            g["dimension"] = dim_name
            g["suggestion"] = suggest_fix(dim_name, g["segment"])
        all_gaps.extend(gaps)

    # Sort by worst delta (most negative = biggest gap)
    all_gaps.sort(key=lambda g: g["delta"])
    top_gaps = all_gaps[:5]

    print(f"\n{'=' * 70}")
    print("  TOP 5 PERFORMANCE GAPS (worst WR vs overall average)")
    print(f"{'=' * 70}")
    for i, g in enumerate(top_gaps, 1):
        print(f"\n  #{i}  [{g['dimension']}] {g['segment']}")
        print(f"      WR: {g['win_rate']}% vs {g['overall_wr']}% overall ({g['delta']:+.1f}%)")
        print(f"      Trades: {g['trades']} | Avg PnL: {g['avg_pnl']:+.3f}%")
        print(f"      FIX: {g['suggestion']}")

    # Build output
    print("\n[5/5] Saving results...")
    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_picks_analyzed": total,
        "overall_win_rate": overall_wr,
        "overall_wins": total_wins,
        "overall_losses": total_losses,
        "segments": {
            "hour_of_day": hour_stats,
            "asset_class": asset_stats,
            "direction": direction_stats,
            "source_system": system_stats,
            "score_tier": tier_stats,
        },
        "top_gaps": top_gaps,
        "all_gaps_sorted": all_gaps,
    }

    os.makedirs(DATA_DIR, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print(f"  Saved to {OUTPUT_FILE}")

    print(f"\n{'=' * 70}")
    print(f"  Gap analysis complete. {len(top_gaps)} actionable gaps identified.")
    print(f"{'=' * 70}\n")

    return result


if __name__ == "__main__":
    run()
