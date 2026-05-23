#!/usr/bin/env python3
"""
Optimal Entry Finder — Permutation analysis of entry conditions.

Finds which combinations of entry conditions would have been most profitable
today and this week by testing permutations against closed pick history.

Usage:
    python alpha_engine/optimal_entry_finder.py
"""

import json
import os
import sys
import itertools
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path
from collections import defaultdict

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
CLOSED_PICKS_PATH = DATA_DIR / "closed_picks.json"
ACTIVE_PICKS_PATH = DATA_DIR / "active_picks.json"
OUTPUT_PATH = DATA_DIR / "optimal_entry_analysis.json"

# ---------------------------------------------------------------------------
# Entry condition variable space
# ---------------------------------------------------------------------------
ENTRY_CONDITIONS = {
    "confidence_min": [0.60, 0.65, 0.70, 0.75, 0.80],
    "rsi_range": [(20, 80), (25, 75), (30, 70), (35, 65)],
    "volume_ratio_min": [1.0, 1.2, 1.5, 2.0, 3.0],
    "direction": ["BUY_ONLY", "SELL_ONLY", "BOTH"],
    "regime": ["all", "trending", "ranging", "bearish"],
    "risk_reward_min": [1.0, 1.5, 2.0, 2.5, 3.0],
    "tp_pct": [3, 5, 6, 8, 10, 12],
    "sl_pct": [2, 3, 4, 5, 6],
    "max_hold_days": [1, 2, 3, 5, 7, 14],
    "hour_utc_range": [(0, 24), (7, 16), (13, 17), (0, 8)],
    "category": ["all", "crypto", "stock"],
    "source_system_tier": ["all", "PROVEN", "RELIABLE", "PROVEN+RELIABLE"],
}

# Current default settings (baseline for comparison)
CURRENT_DEFAULTS = {
    "confidence_min": 0.70,
    "rsi_range": (20, 80),
    "volume_ratio_min": 1.0,
    "direction": "BOTH",
    "regime": "all",
    "risk_reward_min": 1.0,
    "tp_pct": 6,
    "sl_pct": 3,
    "max_hold_days": 14,
    "hour_utc_range": (0, 24),
    "category": "all",
    "source_system_tier": "all",
}

# Strategy tiers based on known forward WR
PROVEN_STRATEGIES = {
    "winner_pattern_precursor", "momentum_catcher", "beaten_majors",
    "rsi_capitulation", "relative_strength", "altcoin_season",
}
RELIABLE_STRATEGIES = {
    "volume_spike_backfill", "ema_crossover_backfill", "rsi_bounce_backfill",
    "ml_enhanced",
}


def _is_reliable_strategy(strategy_name: str) -> bool:
    """Check if strategy matches any RELIABLE prefix."""
    for s in RELIABLE_STRATEGIES:
        if strategy_name and strategy_name.startswith(s):
            return True
    return False


def _is_proven_strategy(strategy_name: str) -> bool:
    """Check if strategy matches any PROVEN prefix."""
    for s in PROVEN_STRATEGIES:
        if strategy_name and strategy_name.startswith(s):
            return True
    return False


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_picks(path: Path) -> list:
    """Load picks from JSON file, return empty list if missing."""
    if not path.exists():
        print(f"  [WARN] {path} not found — returning empty list")
        return []
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, list):
        return data
    if isinstance(data, dict) and "picks" in data:
        return data["picks"]
    return []


def parse_date(d) -> datetime:
    """Parse a date string to datetime (UTC)."""
    if not d:
        return datetime.min.replace(tzinfo=timezone.utc)
    if isinstance(d, datetime):
        return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%SZ",
                "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S.%f%z",
                "%Y-%m-%dT%H:%M:%S.%fZ"):
        try:
            dt = datetime.strptime(d, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except (ValueError, TypeError):
            continue
    return datetime.min.replace(tzinfo=timezone.utc)


def compute_pick_tp_sl_pct(pick: dict):
    """Compute actual TP% and SL% from the pick's prices."""
    entry = pick.get("entry_price", 0)
    tp = pick.get("take_profit", 0)
    sl = pick.get("stop_loss", 0)
    if not entry or entry <= 0:
        return None, None
    tp_pct = abs(tp - entry) / entry * 100 if tp else None
    sl_pct = abs(entry - sl) / entry * 100 if sl else None
    return tp_pct, sl_pct


def compute_risk_reward(pick: dict):
    """Compute risk-reward ratio from TP/SL distances."""
    tp_pct, sl_pct = compute_pick_tp_sl_pct(pick)
    if tp_pct and sl_pct and sl_pct > 0:
        return tp_pct / sl_pct
    return pick.get("risk_reward")


def get_entry_hour(pick: dict):
    """Extract UTC hour of entry from scan_timestamp or entry_date."""
    ts = pick.get("scan_timestamp") or pick.get("entry_date")
    if not ts:
        return None
    dt = parse_date(ts)
    if dt == datetime.min.replace(tzinfo=timezone.utc):
        return None
    # If only date (no time), return None
    if isinstance(ts, str) and len(ts) <= 10:
        return None
    return dt.hour


# ---------------------------------------------------------------------------
# Filter engine
# ---------------------------------------------------------------------------

def pick_matches_conditions(pick: dict, conditions: dict) -> bool:
    """Check if a pick satisfies all entry conditions."""
    # Confidence
    conf = pick.get("confidence")
    if conf is not None:
        # Normalize: some picks have confidence > 1 (percentage)
        if conf > 1:
            conf = conf / 100.0
        if conf < conditions["confidence_min"]:
            return False

    # RSI range (for BUY: RSI should be in low range; we filter by range)
    rsi = pick.get("rsi_at_entry") or pick.get("rsi")
    rsi_min, rsi_max = conditions["rsi_range"]
    if rsi is not None:
        signal = pick.get("signal_type") or pick.get("direction", "")
        if signal in ("BUY", "LONG"):
            # For buys, RSI should be below rsi_max (not overbought)
            if rsi > rsi_max:
                return False
        elif signal in ("SELL", "SHORT"):
            # For sells, RSI should be above rsi_min (not oversold)
            if rsi < rsi_min:
                return False

    # Volume ratio
    vol = pick.get("volume_ratio")
    if vol is not None and conditions["volume_ratio_min"] > 1.0:
        if vol < conditions["volume_ratio_min"]:
            return False

    # Direction filter
    direction = conditions["direction"]
    signal = pick.get("signal_type") or pick.get("direction", "")
    if direction == "BUY_ONLY" and signal in ("SELL", "SHORT"):
        return False
    if direction == "SELL_ONLY" and signal in ("BUY", "LONG"):
        return False

    # Regime filter
    regime_cond = conditions["regime"]
    if regime_cond != "all":
        regime = (pick.get("regime_at_entry") or pick.get("regime_at_signal") or "").lower()
        if regime_cond == "trending" and regime not in ("trending", "momentum", "bullish"):
            return False
        if regime_cond == "ranging" and regime not in ("ranging", "transitional"):
            return False
        if regime_cond == "bearish" and regime not in ("bearish",):
            return False

    # Risk-reward minimum
    rr = compute_risk_reward(pick)
    if rr is not None and rr < conditions["risk_reward_min"]:
        return False

    # TP% filter — only include picks with TP distance close to condition
    tp_pct_actual, sl_pct_actual = compute_pick_tp_sl_pct(pick)
    cond_tp = conditions["tp_pct"]
    if tp_pct_actual is not None:
        # Accept picks within ±50% of target TP (or above)
        if tp_pct_actual < cond_tp * 0.5:
            return False

    # SL% filter — only include picks with SL distance close to condition
    cond_sl = conditions["sl_pct"]
    if sl_pct_actual is not None:
        # Reject picks with SL wider than condition allows
        if sl_pct_actual > cond_sl * 1.5:
            return False

    # Max hold days
    hold = pick.get("hold_days")
    if hold is not None and hold > conditions["max_hold_days"]:
        return False

    # Hour UTC range
    h_min, h_max = conditions["hour_utc_range"]
    if h_min != 0 or h_max != 24:
        hour = get_entry_hour(pick)
        if hour is not None:
            if h_min <= h_max:
                if not (h_min <= hour < h_max):
                    return False
            else:  # wraps midnight
                if not (hour >= h_min or hour < h_max):
                    return False

    # Category
    cat_cond = conditions["category"]
    if cat_cond != "all":
        cat = (pick.get("category") or "").lower()
        if cat != cat_cond:
            return False

    # Source system tier
    tier = conditions["source_system_tier"]
    if tier != "all":
        strat = pick.get("strategy") or ""
        is_proven = _is_proven_strategy(strat)
        is_reliable = _is_reliable_strategy(strat)
        if tier == "PROVEN" and not is_proven:
            return False
        if tier == "RELIABLE" and not is_reliable:
            return False
        if tier == "PROVEN+RELIABLE" and not (is_proven or is_reliable):
            return False

    return True


# ---------------------------------------------------------------------------
# Metrics computation
# ---------------------------------------------------------------------------

def compute_metrics(filtered_picks: list) -> dict:
    """Compute trading metrics for a set of filtered picks."""
    if not filtered_picks:
        return {
            "trade_count": 0, "win_rate": 0, "avg_pnl": 0,
            "avg_win": 0, "avg_loss": 0, "expectancy": 0,
            "profit_factor": 0, "total_pnl": 0,
        }

    wins = [p for p in filtered_picks if p.get("status") == "WON"]
    losses = [p for p in filtered_picks if p.get("status") == "LOST"]
    expired = [p for p in filtered_picks if p.get("status") == "EXPIRED"]

    n_decided = len(wins) + len(losses)
    win_rate = len(wins) / n_decided if n_decided > 0 else 0

    pnls = [p.get("pnl_pct", 0) or 0 for p in filtered_picks]
    avg_pnl = sum(pnls) / len(pnls) if pnls else 0

    win_pnls = [p.get("pnl_pct", 0) or 0 for p in wins]
    loss_pnls = [abs(p.get("pnl_pct", 0) or 0) for p in losses]

    avg_win = sum(win_pnls) / len(win_pnls) if win_pnls else 0
    avg_loss = sum(loss_pnls) / len(loss_pnls) if loss_pnls else 0

    # Expectancy = (WR * avg_win) - (LR * avg_loss)
    loss_rate = 1 - win_rate
    expectancy = (win_rate * avg_win) - (loss_rate * avg_loss)

    # Profit factor = gross_wins / gross_losses
    gross_wins = sum(win_pnls) if win_pnls else 0
    gross_losses = sum(loss_pnls) if loss_pnls else 0
    profit_factor = gross_wins / gross_losses if gross_losses > 0 else (
        float("inf") if gross_wins > 0 else 0
    )

    total_pnl = sum(pnls)

    return {
        "trade_count": len(filtered_picks),
        "wins": len(wins),
        "losses": len(losses),
        "expired": len(expired),
        "win_rate": round(win_rate, 4),
        "avg_pnl": round(avg_pnl, 6),
        "avg_win": round(avg_win, 6),
        "avg_loss": round(avg_loss, 6),
        "expectancy": round(expectancy, 6),
        "profit_factor": round(profit_factor, 3),
        "total_pnl": round(total_pnl, 6),
    }


# ---------------------------------------------------------------------------
# Permutation generator — smart sampling
# ---------------------------------------------------------------------------

def generate_permutations(max_combos: int = 2500) -> list:
    """Generate smart-sampled permutations of entry conditions.

    Focus on the most impactful variables:
    confidence_min x direction x risk_reward_min x tp_pct x sl_pct
    Plus a random sample from the full space.
    """
    combos = []

    # --- Tier 1: Core permutations (most impactful) ---
    # confidence x direction x risk_reward x tp x sl
    core_keys = ["confidence_min", "direction", "risk_reward_min", "tp_pct", "sl_pct"]
    core_values = [ENTRY_CONDITIONS[k] for k in core_keys]
    other_keys = [k for k in ENTRY_CONDITIONS if k not in core_keys]

    for combo in itertools.product(*core_values):
        conditions = dict(CURRENT_DEFAULTS)  # start from defaults
        for k, v in zip(core_keys, combo):
            conditions[k] = v
        combos.append(dict(conditions))

    # --- Tier 2: Regime + category variations on top defaults ---
    for regime in ENTRY_CONDITIONS["regime"]:
        for cat in ENTRY_CONDITIONS["category"]:
            for tier in ENTRY_CONDITIONS["source_system_tier"]:
                conditions = dict(CURRENT_DEFAULTS)
                conditions["regime"] = regime
                conditions["category"] = cat
                conditions["source_system_tier"] = tier
                combos.append(dict(conditions))

    # --- Tier 3: RSI + volume + hour variations ---
    for rsi in ENTRY_CONDITIONS["rsi_range"]:
        for vol in ENTRY_CONDITIONS["volume_ratio_min"]:
            for hour in ENTRY_CONDITIONS["hour_utc_range"]:
                conditions = dict(CURRENT_DEFAULTS)
                conditions["rsi_range"] = rsi
                conditions["volume_ratio_min"] = vol
                conditions["hour_utc_range"] = hour
                combos.append(dict(conditions))

    # --- Tier 4: Random full-space samples ---
    all_keys = list(ENTRY_CONDITIONS.keys())
    all_values = [ENTRY_CONDITIONS[k] for k in all_keys]
    remaining = max(0, max_combos - len(combos))
    if remaining > 0:
        seen = set()
        attempts = 0
        while len(seen) < remaining and attempts < remaining * 5:
            sample = tuple(random.choice(vals) for vals in all_values)
            key = str(sample)
            if key not in seen:
                seen.add(key)
                conditions = {}
                for k, v in zip(all_keys, sample):
                    conditions[k] = v
                combos.append(conditions)
            attempts += 1

    # Deduplicate
    unique = {}
    for c in combos:
        key = str(sorted(c.items()))
        if key not in unique:
            unique[key] = c

    result = list(unique.values())
    if len(result) > max_combos:
        # Keep all core combos, sample the rest
        result = result[:max_combos]
    return result


# ---------------------------------------------------------------------------
# Condition serializer (for JSON output)
# ---------------------------------------------------------------------------

def serialize_conditions(cond: dict) -> dict:
    """Convert tuples to lists for JSON serialization."""
    out = {}
    for k, v in cond.items():
        if isinstance(v, tuple):
            out[k] = list(v)
        else:
            out[k] = v
    return out


def format_conditions_short(cond: dict) -> str:
    """One-line human-readable condition summary."""
    parts = []
    parts.append(f"conf>={cond['confidence_min']:.0%}")
    rr = cond.get("risk_reward_min", 1.0)
    parts.append(f"R:R>={rr:.1f}")
    parts.append(f"TP {cond['tp_pct']}%")
    parts.append(f"SL {cond['sl_pct']}%")
    d = cond.get("direction", "BOTH")
    if d != "BOTH":
        parts.append(d)
    r = cond.get("regime", "all")
    if r != "all":
        parts.append(f"regime={r}")
    cat = cond.get("category", "all")
    if cat != "all":
        parts.append(cat)
    rsi = cond.get("rsi_range", (20, 80))
    if rsi != (20, 80):
        parts.append(f"RSI({rsi[0]}-{rsi[1]})")
    vol = cond.get("volume_ratio_min", 1.0)
    if vol > 1.0:
        parts.append(f"vol>={vol}x")
    hold = cond.get("max_hold_days", 14)
    if hold < 14:
        parts.append(f"hold<={hold}d")
    hour = cond.get("hour_utc_range", (0, 24))
    if hour != (0, 24):
        session_names = {(7, 16): "London", (13, 17): "NY", (0, 8): "Asia"}
        name = session_names.get(tuple(hour), f"{hour[0]}-{hour[1]}UTC")
        parts.append(name)
    tier = cond.get("source_system_tier", "all")
    if tier != "all":
        parts.append(f"tier={tier}")
    return ", ".join(parts)


# ---------------------------------------------------------------------------
# "Today" analysis — best single filter improvement
# ---------------------------------------------------------------------------

def analyze_today(today_picks: list, all_conditions: dict) -> dict:
    """Find the single best filter change for today's picks."""
    if not today_picks:
        return {"message": "No picks opened today to analyze."}

    baseline_metrics = compute_metrics(today_picks)
    best_improvement = None
    best_improvement_score = 0

    # Test each single dimension independently
    for dim_key, dim_values in ENTRY_CONDITIONS.items():
        for val in dim_values:
            test_cond = dict(CURRENT_DEFAULTS)
            test_cond[dim_key] = val
            # Skip if same as default
            if test_cond[dim_key] == CURRENT_DEFAULTS[dim_key]:
                continue
            filtered = [p for p in today_picks if pick_matches_conditions(p, test_cond)]
            if len(filtered) < 1:
                continue
            m = compute_metrics(filtered)
            # Score = expectancy improvement
            improvement = m["expectancy"] - baseline_metrics["expectancy"]
            if improvement > best_improvement_score and m["trade_count"] >= 2:
                best_improvement_score = improvement
                best_improvement = {
                    "dimension": dim_key,
                    "value": val if not isinstance(val, tuple) else list(val),
                    "metrics": m,
                    "improvement_expectancy": round(improvement, 6),
                    "trades_kept": m["trade_count"],
                    "trades_dropped": len(today_picks) - m["trade_count"],
                }

    winners_today = [p for p in today_picks if p.get("status") == "WON"]
    losers_today = [p for p in today_picks if p.get("status") == "LOST"]

    # Which losers would have been avoided?
    avoided_losers = []
    if best_improvement and best_improvement.get("dimension"):
        test_cond = dict(CURRENT_DEFAULTS)
        test_cond[best_improvement["dimension"]] = (
            tuple(best_improvement["value"])
            if isinstance(best_improvement["value"], list)
            else best_improvement["value"]
        )
        for p in losers_today:
            if not pick_matches_conditions(p, test_cond):
                avoided_losers.append({
                    "symbol": p.get("symbol"),
                    "strategy": p.get("strategy"),
                    "pnl_pct": p.get("pnl_pct"),
                })

    return {
        "today_total": len(today_picks),
        "today_winners": len(winners_today),
        "today_losers": len(losers_today),
        "baseline_metrics": baseline_metrics,
        "best_single_filter_change": best_improvement,
        "losers_avoided": avoided_losers[:5],
    }


# ---------------------------------------------------------------------------
# Active picks unrealized P/L
# ---------------------------------------------------------------------------

def analyze_active_picks(active_picks: list) -> dict:
    """Analyze unrealized P/L on active picks."""
    if not active_picks:
        return {"message": "No active picks."}

    total = len(active_picks)
    unrealized = []
    for p in active_picks:
        entry = p.get("entry_price", 0)
        current = p.get("current_price") or p.get("high_water_mark")
        if entry and current and entry > 0:
            pnl = (current - entry) / entry
            signal = p.get("signal_type") or p.get("direction", "BUY")
            if signal in ("SELL", "SHORT"):
                pnl = -pnl
            unrealized.append({
                "symbol": p.get("symbol"),
                "strategy": p.get("strategy"),
                "unrealized_pnl_pct": round(pnl * 100, 2),
                "confidence": p.get("confidence"),
                "hold_days": p.get("hold_days"),
            })

    unrealized.sort(key=lambda x: x["unrealized_pnl_pct"], reverse=True)
    avg_unr = (sum(u["unrealized_pnl_pct"] for u in unrealized) / len(unrealized)
               if unrealized else 0)

    return {
        "total_active": total,
        "avg_unrealized_pnl_pct": round(avg_unr, 2),
        "top_5": unrealized[:5],
        "bottom_5": unrealized[-5:],
    }


# ---------------------------------------------------------------------------
# Main analysis
# ---------------------------------------------------------------------------

def run_analysis():
    """Run the full permutation analysis."""
    print("=" * 70)
    print("  OPTIMAL ENTRY FINDER — Permutation Analysis")
    print("=" * 70)

    # Load data
    print("\n[1/5] Loading picks...")
    all_closed = load_picks(CLOSED_PICKS_PATH)
    active_picks = load_picks(ACTIVE_PICKS_PATH)
    print(f"  Closed picks: {len(all_closed)}")
    print(f"  Active picks: {len(active_picks)}")

    if not all_closed:
        print("\n  [ERROR] No closed picks found. Cannot run analysis.")
        sys.exit(1)

    # Filter to last 7 days
    now = datetime.now(timezone.utc)
    seven_days_ago = now - timedelta(days=7)
    today_str = now.strftime("%Y-%m-%d")

    week_picks = []
    today_picks = []
    for p in all_closed:
        ed = parse_date(p.get("entry_date"))
        if ed >= seven_days_ago:
            week_picks.append(p)
        if p.get("entry_date") == today_str:
            today_picks.append(p)

    print(f"  Picks this week (7d): {len(week_picks)}")
    print(f"  Picks today ({today_str}): {len(today_picks)}")

    # If not enough weekly picks, use all data
    analysis_picks = week_picks if len(week_picks) >= 20 else all_closed
    analysis_label = "7-day" if len(week_picks) >= 20 else "all-time"
    if analysis_picks is all_closed:
        print(f"  [INFO] Only {len(week_picks)} weekly picks — using all {len(all_closed)} picks")

    # Baseline metrics (current defaults)
    print("\n[2/5] Computing baseline (current defaults)...")
    baseline_filtered = [p for p in analysis_picks if pick_matches_conditions(p, CURRENT_DEFAULTS)]
    baseline_metrics = compute_metrics(baseline_filtered)
    print(f"  CURRENT SETTINGS: {format_conditions_short(CURRENT_DEFAULTS)}")
    print(f"  -> {baseline_metrics['win_rate']*100:.1f}% WR, "
          f"{baseline_metrics['trade_count']} trades, "
          f"expectancy={baseline_metrics['expectancy']:.6f}, "
          f"PF={baseline_metrics['profit_factor']:.2f}")

    # Generate permutations
    print("\n[3/5] Generating permutations (smart-sampled)...")
    permutations = generate_permutations(max_combos=2500)
    print(f"  Testing {len(permutations)} unique condition sets...")

    # Evaluate each permutation
    results = []
    min_trades = max(5, len(analysis_picks) * 0.02)  # At least 2% of picks or 5

    for i, cond in enumerate(permutations):
        filtered = [p for p in analysis_picks if pick_matches_conditions(p, cond)]
        if len(filtered) < min_trades:
            continue
        metrics = compute_metrics(filtered)
        results.append({
            "conditions": cond,
            "metrics": metrics,
        })

    print(f"  {len(results)} permutations had >= {int(min_trades)} qualifying trades")

    # Rank by expectancy (primary), then profit factor (secondary)
    results.sort(key=lambda r: (r["metrics"]["expectancy"], r["metrics"]["profit_factor"]),
                 reverse=True)

    # Top 20
    top_20 = results[:20]

    # Print report
    print("\n" + "=" * 70)
    print("  TOP 20 OPTIMAL ENTRY CONDITIONS")
    print(f"  (Analysis period: {analysis_label}, {len(analysis_picks)} picks)")
    print("=" * 70)

    for i, r in enumerate(top_20):
        m = r["metrics"]
        c = r["conditions"]
        marker = ""
        if m["expectancy"] > baseline_metrics["expectancy"] * 1.5:
            marker = " ***"
        print(f"\n  #{i+1}{marker}")
        print(f"  {format_conditions_short(c)}")
        print(f"  WR: {m['win_rate']*100:.1f}% | Trades: {m['trade_count']} | "
              f"Expect: {m['expectancy']:.6f} | PF: {m['profit_factor']:.2f} | "
              f"Avg PnL: {m['avg_pnl']*100:.3f}%")

    # Comparison with baseline
    if top_20:
        best = top_20[0]
        bm = best["metrics"]
        print("\n" + "-" * 70)
        print("  COMPARISON: CURRENT vs OPTIMAL")
        print("-" * 70)

        print(f"\n  CURRENT : {format_conditions_short(CURRENT_DEFAULTS)}")
        print(f"           WR={baseline_metrics['win_rate']*100:.1f}%, "
              f"expect={baseline_metrics['expectancy']:.6f}, "
              f"PF={baseline_metrics['profit_factor']:.2f}, "
              f"trades={baseline_metrics['trade_count']}")

        print(f"\n  OPTIMAL : {format_conditions_short(best['conditions'])}")
        print(f"           WR={bm['win_rate']*100:.1f}%, "
              f"expect={bm['expectancy']:.6f}, "
              f"PF={bm['profit_factor']:.2f}, "
              f"trades={bm['trade_count']}")

        # Improvement
        if baseline_metrics["win_rate"] > 0:
            wr_imp = ((bm["win_rate"] - baseline_metrics["win_rate"])
                      / baseline_metrics["win_rate"] * 100)
        else:
            wr_imp = float("inf") if bm["win_rate"] > 0 else 0

        if baseline_metrics["expectancy"] != 0:
            exp_imp = ((bm["expectancy"] - baseline_metrics["expectancy"])
                       / abs(baseline_metrics["expectancy"]) * 100)
        else:
            exp_imp = float("inf") if bm["expectancy"] > 0 else 0

        print(f"\n  IMPROVEMENT: {'+' if wr_imp >= 0 else ''}{wr_imp:.1f}% win rate, "
              f"{'+' if exp_imp >= 0 else ''}{exp_imp:.1f}% expectancy")

    # Today analysis
    print("\n" + "=" * 70)
    print("  TODAY'S ANALYSIS")
    print("=" * 70)

    today_analysis = analyze_today(today_picks, ENTRY_CONDITIONS)
    if "message" in today_analysis:
        print(f"\n  {today_analysis['message']}")
    else:
        ta = today_analysis
        bm_t = ta["baseline_metrics"]
        print(f"\n  Today: {ta['today_total']} picks "
              f"({ta['today_winners']}W / {ta['today_losers']}L)")
        print(f"  Baseline WR: {bm_t['win_rate']*100:.1f}%, "
              f"expectancy: {bm_t['expectancy']:.6f}")

        bsf = ta.get("best_single_filter_change")
        if bsf:
            print(f"\n  BEST SINGLE FILTER CHANGE: {bsf['dimension']} = {bsf['value']}")
            print(f"  -> Kept {bsf['trades_kept']} trades, dropped {bsf['trades_dropped']}")
            print(f"  -> New WR: {bsf['metrics']['win_rate']*100:.1f}%, "
                  f"expectancy: {bsf['metrics']['expectancy']:.6f}")
            print(f"  -> Expectancy improvement: {bsf['improvement_expectancy']:.6f}")
            if ta.get("losers_avoided"):
                print("  Losers that would have been avoided:")
                for la in ta["losers_avoided"]:
                    print(f"    - {la['symbol']} ({la['strategy']}): "
                          f"{(la['pnl_pct'] or 0)*100:.2f}%")
        else:
            print("\n  No single filter change improves today's results.")

    # Active picks analysis
    print("\n" + "=" * 70)
    print("  ACTIVE PICKS — UNREALIZED P/L")
    print("=" * 70)

    active_analysis = analyze_active_picks(active_picks)
    if "message" in active_analysis:
        print(f"\n  {active_analysis['message']}")
    else:
        aa = active_analysis
        print(f"\n  Active: {aa['total_active']} positions")
        print(f"  Avg unrealized P/L: {aa['avg_unrealized_pnl_pct']:.2f}%")
        if aa.get("top_5"):
            print("  Top 5:")
            for t in aa["top_5"]:
                print(f"    + {t['symbol']}: {t['unrealized_pnl_pct']:+.2f}% "
                      f"({t['strategy']}, conf={t['confidence']})")
        if aa.get("bottom_5"):
            print("  Bottom 5:")
            for b in aa["bottom_5"]:
                print(f"    - {b['symbol']}: {b['unrealized_pnl_pct']:+.2f}% "
                      f"({b['strategy']}, conf={b['confidence']})")

    # Save results
    print("\n[5/5] Saving results...")
    output = {
        "generated_at": now.isoformat(),
        "analysis_period": analysis_label,
        "total_picks_analyzed": len(analysis_picks),
        "permutations_tested": len(permutations),
        "permutations_qualifying": len(results),
        "min_trades_threshold": int(min_trades),
        "baseline": {
            "conditions": serialize_conditions(CURRENT_DEFAULTS),
            "metrics": baseline_metrics,
        },
        "top_20": [
            {
                "rank": i + 1,
                "conditions": serialize_conditions(r["conditions"]),
                "metrics": r["metrics"],
            }
            for i, r in enumerate(top_20)
        ],
        "today_analysis": {
            k: (v if not isinstance(v, dict) else v)
            for k, v in today_analysis.items()
        },
        "active_picks_analysis": active_analysis,
    }

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, default=str)
    print(f"  Saved to: {OUTPUT_PATH}")

    print("\n" + "=" * 70)
    print("  ANALYSIS COMPLETE")
    print("=" * 70)

    return output


if __name__ == "__main__":
    run_analysis()
