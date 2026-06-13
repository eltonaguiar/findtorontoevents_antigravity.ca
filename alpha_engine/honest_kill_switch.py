#!/usr/bin/env python3
"""
Honest Kill Switch — Data-Driven Strategy Killer
=================================================
Queries the *honest ledger* (at_signal_outcomes on MySQL) and automatically
kills strategies that fail statistical gates after sufficient sample size.

Criteria (user-defined, stricter than strategy_priority.py):
  - Minimum 30 closed trades before evaluation
  - Per-asset-class WR/PF gates (FOREX/COMMODITY stricter than CRYPTO/EQUITY)
  - Both WR and PF must pass for the strategy's dominant asset class
  - Falls back to global defaults (45% WR / 1.0 PF) for unknown classes

This is intentionally more aggressive than the existing auto-kill (30% WR, 20+ trades)
which requires mutation-before-kill. This module operates on REAL outcomes from the
honest ledger, not the potentially-corrupted closed_picks.json.

Integration:
  1. Writes killed strategies to alpha_engine/data/honest_kill_switch.json
  2. Appends entries to strategy_kill_list.json for suppression pipeline
  3. Provides is_strategy_killed() for production scanner to call

Usage:
    source ~/.config/findtorontoevents/windows_ported_env.sh
    python3 alpha_engine/honest_kill_switch.py                # dry-run report
    python3 alpha_engine/honest_kill_switch.py --apply        # write kill list
    python3 alpha_engine/honest_kill_switch.py --check <name> # check one strategy

Design based on Fincept Terminal's Alpha Arena kill switches:
  - 50% drawdown auto-kill → we use PF < 1.0 (negative expectancy)
  - Repeated failure detection → 30+ trades minimum
  - Append-only audit trail → JSON output with full rationale
"""

from __future__ import annotations

import copy
import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path


DATA_DIR = Path(__file__).resolve().parent / "data"
KILL_SWITCH_PATH = DATA_DIR / "honest_kill_switch.json"
# Must match strategy_suppression.py's _INSTITUTIONAL_KILL_LIST path
KILL_LIST_PATH = Path(__file__).resolve().parent / "strategy_kill_list.json"

# ---------------------------------------------------------------------------
# Configuration — the gates
# ---------------------------------------------------------------------------

MIN_TRADES = 30          # minimum closed trades before evaluation
MIN_WR = 0.45            # win rate threshold (below = KILL) — default / fallback
MIN_PF = 1.0             # profit factor threshold (below = KILL) — default / fallback

# Asset-class-specific thresholds.
# Data-driven from 17,329 closed trades in at_signal_outcomes:
#   CRYPTO: bulk of portfolio (8067 trades), 45% WR / 1.0 PF works well — 2 strong survivors
#   EQUITY: some strategies have high WR but low PF (regime_mild_bear 77.8% WR, 0.52 PF);
#           allow 0.8 PF since WR compensates (stocks_rsi2_pullback 45.6% WR, 4.76 PF)
#   FOREX:  chronically weak — 4/6 killed had PF < 0.31; only 2 survivors (WR 53-54%, PF 1.27-2.12)
#   COMMODITY: worst performer — both killed had 10-26% WR, PF 0.19-0.41
#   ETF:    too few trades for per-class tuning; uses CRYPTO defaults
ASSET_CLASS_THRESHOLDS: dict[str, dict[str, float]] = {
    #            min_wr  min_pf  min_trades
    "CRYPTO":    {"min_wr": 0.45, "min_pf": 1.0,  "min_trades": 30},
    "EQUITY":    {"min_wr": 0.45, "min_pf": 0.8,  "min_trades": 30},
    "ETF":       {"min_wr": 0.45, "min_pf": 1.0,  "min_trades": 30},
    "FOREX":     {"min_wr": 0.50, "min_pf": 1.2,  "min_trades": 30},
    "COMMODITY": {"min_wr": 0.50, "min_pf": 1.2,  "min_trades": 30},
    "FUTURES":   {"min_wr": 0.50, "min_pf": 1.2,  "min_trades": 30},
    "BOND":      {"min_wr": 0.45, "min_pf": 1.0,  "min_trades": 30},
}

# Asset classes to evaluate (skip UNKNOWN, BOND with < 20 trades)
EVALUATED_ASSET_CLASSES = {"CRYPTO", "EQUITY", "ETF", "FOREX", "COMMODITY"}

# Strategies that are EXEMPT from auto-kill (protected / manually curated)
def _load_protected_strategies() -> set[str]:
    """Load protected strategies from core_whitelist.json (consistent with strategy_priority.py)."""
    protected = set()
    # Hardcoded minimum set
    hardcoded = {
        "st_fear_greed_contrarian", "cftc_cot_commercial_signal",
        "atr_percentile_gate", "rs-breakout-scout",
        "mega_mutation_macd_rsi_m048", "fear_greed_contrarian",
    }
    protected.update(s.lower() for s in hardcoded)

    # Dynamic load from core_whitelist.json
    try:
        wl_path = DATA_DIR / "core_whitelist.json"
        if wl_path.exists():
            wl = json.loads(wl_path.read_text(encoding="utf-8"))
            for group in ("protected_strategies", "core_strategies", "incubator_strategies"):
                for item in wl.get(group, []):
                    if isinstance(item, str) and item.strip():
                        protected.add(item.strip().lower())
    except Exception:
        pass
    return protected


# Preserve originals so _override_globals can restore on re-entry
_ORIGINAL_THRESHOLDS: dict[str, dict[str, float]] = copy.deepcopy(ASSET_CLASS_THRESHOLDS)
_DEFAULT_THRESHOLDS: dict[str, float] = {"min_wr": MIN_WR, "min_pf": MIN_PF, "min_trades": MIN_TRADES}


def _override_globals(min_wr: float, min_pf: float, min_trades: int) -> None:
    """Override module-level thresholds (used by CLI args).

    Restores from original per-class thresholds first, then applies the
    global override so repeated calls don't compound.
    """
    global MIN_WR, MIN_PF, MIN_TRADES
    MIN_WR = min_wr
    MIN_PF = min_pf
    MIN_TRADES = min_trades
    # Restore originals then apply overrides
    for _ac, _orig in _ORIGINAL_THRESHOLDS.items():
        ASSET_CLASS_THRESHOLDS[_ac] = copy.deepcopy(_orig)
    for _ac in ASSET_CLASS_THRESHOLDS:
        ASSET_CLASS_THRESHOLDS[_ac]["min_wr"] = min_wr
        ASSET_CLASS_THRESHOLDS[_ac]["min_pf"] = min_pf
        ASSET_CLASS_THRESHOLDS[_ac]["min_trades"] = min_trades


def _get_thresholds_for_class(asset_class: str) -> dict[str, float]:
    """Return (min_wr, min_pf, min_trades) for the given asset class.

    Falls back to module-level MIN_WR/MIN_PF/MIN_TRADES for UNKNOWN or
    unrecognised asset classes. Returns a cached default dict to avoid
    allocating a new dict on every call.
    """
    ac = str(asset_class).upper().strip()
    return ASSET_CLASS_THRESHOLDS.get(ac, _DEFAULT_THRESHOLDS)


# Module-level cache for protected strategies
_PROTECTED_CACHE: set[str] | None = None

def _get_protected() -> set[str]:
    global _PROTECTED_CACHE
    if _PROTECTED_CACHE is None:
        _PROTECTED_CACHE = _load_protected_strategies()
    return _PROTECTED_CACHE


# ---------------------------------------------------------------------------
# MySQL connection
# ---------------------------------------------------------------------------

def _get_connection():
    """Get a MySQL connection to ejaguiar1_stocks on mysql.50webs.com."""
    try:
        import pymysql
    except ImportError:
        print("ERROR: pymysql not installed. Run: pip3 install pymysql")
        sys.exit(1)

    pw = os.environ.get("DB_PASS_STOCKS", "")
    if not pw:
        print("ERROR: DB_PASS_STOCKS env var not set. Source windows_ported_env.sh first.")
        sys.exit(1)

    return pymysql.connect(
        host="mysql.50webs.com",
        user="ejaguiar1_stocks",
        password=pw,
        database="ejaguiar1_stocks",
        connect_timeout=15,
        cursorclass=pymysql.cursors.DictCursor,
    )


# ---------------------------------------------------------------------------
# Core: Query honest ledger and compute strategy stats
# ---------------------------------------------------------------------------

def fetch_strategy_stats(conn) -> dict[str, dict]:
    """Query at_signal_outcomes for per-strategy performance.

    Returns dict of strategy_name -> {
        n, wins, losses, wr, pf, avg_pnl, total_pnl,
        asset_class_breakdown, source_system, first_seen, last_seen,
    }
    """
    cur = conn.cursor()
    cur.execute("""
        SELECT
            strategy,
            source_system,
            asset_class,
            COUNT(*) as n,
            SUM(CASE WHEN outcome IN ('WON', 'TP_HIT') THEN 1 ELSE 0 END) as wins,
            SUM(CASE WHEN outcome IN ('LOST', 'SL_HIT') THEN 1 ELSE 0 END) as losses,
            ROUND(AVG(CASE WHEN outcome NOT IN ('OPEN') THEN pnl_pct END), 4) as avg_pnl,
            ROUND(SUM(CASE WHEN outcome NOT IN ('OPEN') THEN pnl_pct ELSE 0 END), 2) as total_pnl,
            ROUND(SUM(CASE WHEN outcome IN ('WON', 'TP_HIT') AND pnl_pct IS NOT NULL
                        THEN ABS(pnl_pct) ELSE 0 END), 4) as gross_wins,
            ROUND(SUM(CASE WHEN outcome IN ('LOST', 'SL_HIT') AND pnl_pct IS NOT NULL
                        THEN ABS(pnl_pct) ELSE 0 END), 4) as gross_losses,
            MIN(closed_at) as first_seen,
            MAX(closed_at) as last_seen
        FROM at_signal_outcomes
        WHERE outcome IN ('WON', 'TP_HIT', 'LOST', 'SL_HIT', 'EXPIRED')
          AND pnl_pct IS NOT NULL
          AND strategy IS NOT NULL
          AND strategy != ''
        GROUP BY strategy, source_system, asset_class
        HAVING n >= 5
        ORDER BY n DESC
    """)
    rows = cur.fetchall()
    cur.close()

    # Aggregate by strategy (across asset classes and source systems)
    by_strategy: dict[str, dict] = defaultdict(lambda: {
        "n": 0, "wins": 0, "losses": 0,
        "gross_wins": 0.0, "gross_losses": 0.0,
        "total_pnl": 0.0, "pnl_values": [],
        "asset_classes": {}, "source_systems": set(),
        "first_seen": None, "last_seen": None,
    })

    for row in rows:
        strat = row["strategy"]
        s = by_strategy[strat]
        s["n"] += row["n"]
        s["wins"] += row["wins"]
        s["losses"] += row["losses"]
        s["gross_wins"] += float(row["gross_wins"] or 0)
        s["gross_losses"] += float(row["gross_losses"] or 0)
        s["total_pnl"] += float(row["total_pnl"] or 0)

        ac = row.get("asset_class") or "UNKNOWN"
        s["asset_classes"][ac] = s["asset_classes"].get(ac, 0) + row["n"]

        src = row.get("source_system") or "unknown"
        s["source_systems"].add(src)

        first = row.get("first_seen")
        last = row.get("last_seen")
        if first:
            first_str = str(first)
            if s["first_seen"] is None or first_str < s["first_seen"]:
                s["first_seen"] = first_str
        if last:
            last_str = str(last)
            if s["last_seen"] is None or last_str > s["last_seen"]:
                s["last_seen"] = last_str

    # Compute derived metrics
    results = {}
    for strat, s in by_strategy.items():
        closed = s["wins"] + s["losses"]
        if closed == 0:
            continue

        wr = s["wins"] / closed
        pf = (s["gross_wins"] / s["gross_losses"]) if s["gross_losses"] > 0 else (
            99.0 if s["gross_wins"] > 0 else 0.0
        )
        avg_pnl = s["total_pnl"] / s["n"] if s["n"] > 0 else 0.0

        results[strat] = {
            "n": s["n"],
            "closed": closed,
            "wins": s["wins"],
            "losses": s["losses"],
            "wr": round(wr, 4),
            "pf": round(pf, 4),
            "avg_pnl": round(avg_pnl, 4),
            "total_pnl": round(s["total_pnl"], 2),
            "gross_wins": round(s["gross_wins"], 4),
            "gross_losses": round(s["gross_losses"], 4),
            "asset_classes": s["asset_classes"],
            "source_systems": sorted(s["source_systems"]),
            "first_seen": s["first_seen"],
            "last_seen": s["last_seen"],
        }

    return results


# ---------------------------------------------------------------------------
# Kill decision logic
# ---------------------------------------------------------------------------

def evaluate_strategies(stats: dict[str, dict]) -> dict:
    """Evaluate all strategies against kill gates.

    Returns {
        "survivors": [...],   # strategies that PASS both gates
        "killed": [...],      # strategies that FAIL at least one gate
        "insufficient": [...],# strategies with < MIN_TRADES (not yet evaluable)
        "protected": [...],   # strategies exempt from kill
        "summary": {...},
    }
    """
    survivors = []
    killed = []
    insufficient = []
    protected = []

    for strat, s in sorted(stats.items(), key=lambda x: x[1]["n"], reverse=True):
        entry = {
            "strategy": strat,
            "n": s["n"],
            "closed": s["closed"],
            "wr": s["wr"],
            "pf": s["pf"],
            "avg_pnl": s["avg_pnl"],
            "total_pnl": s["total_pnl"],
            "dominant_asset_class": max(s["asset_classes"], key=s["asset_classes"].get)
                if s["asset_classes"] else "UNKNOWN",
            "source_systems": s["source_systems"],
        }

        # Protected strategies are exempt
        if strat.lower() in _get_protected():
            entry["status"] = "PROTECTED"
            entry["reason"] = f"Protected strategy — exempt from auto-kill"
            protected.append(entry)
            continue

        # Resolve per-asset-class thresholds early (needed for min_trades check too)
        ac = entry["dominant_asset_class"]
        ac_thresholds = _get_thresholds_for_class(ac)
        ac_min_wr = ac_thresholds["min_wr"]
        ac_min_pf = ac_thresholds["min_pf"]
        ac_min_trades = ac_thresholds["min_trades"]

        # Not enough trades yet (per-class min_trades)
        if s["n"] < ac_min_trades:
            entry["status"] = "INSUFFICIENT_DATA"
            entry["reason"] = f"Only {s['n']} trades (need {ac_min_trades}+)"
            insufficient.append(entry)
            continue

        # Check gates (per-asset-class thresholds)

        fails_wr = s["wr"] < ac_min_wr
        fails_pf = s["pf"] < ac_min_pf

        if fails_wr or fails_pf:
            reasons = []
            if fails_wr:
                reasons.append(f"WR={s['wr']:.1%} < {ac_min_wr:.0%}")
            if fails_pf:
                reasons.append(f"PF={s['pf']:.2f} < {ac_min_pf:.2f}")
            entry["status"] = "KILLED"
            entry["reason"] = "; ".join(reasons)
            entry["fail_wr"] = fails_wr
            entry["fail_pf"] = fails_pf
            entry["thresholds_applied"] = {
                "min_wr": ac_min_wr, "min_pf": ac_min_pf,
                "asset_class": ac,
            }
            killed.append(entry)
        else:
            entry["status"] = "SURVIVOR"
            entry["reason"] = f"WR={s['wr']:.1%} >= {ac_min_wr:.0%} AND PF={s['pf']:.2f} >= {ac_min_pf:.2f}"
            entry["thresholds_applied"] = {
                "min_wr": ac_min_wr, "min_pf": ac_min_pf,
                "asset_class": ac,
            }
            survivors.append(entry)

    # Summary
    total_evaluated = len(survivors) + len(killed)
    summary = {
        "total_strategies": len(stats),
        "evaluated": total_evaluated,
        "survivors": len(survivors),
        "killed": len(killed),
        "insufficient_data": len(insufficient),
        "protected": len(protected),
        "kill_rate": round(len(killed) / total_evaluated * 100, 1) if total_evaluated else 0,
        "criteria": {
            "min_trades": MIN_TRADES,
            "min_wr": MIN_WR,
            "min_pf": MIN_PF,
            "per_asset_class": ASSET_CLASS_THRESHOLDS,
        },
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
    }

    return {
        "survivors": survivors,
        "killed": killed,
        "insufficient": insufficient,
        "protected": protected,
        "summary": summary,
    }


# ---------------------------------------------------------------------------
# Persistence: write kill list and update suppression pipeline
# ---------------------------------------------------------------------------

def save_kill_switch_results(results: dict, apply: bool = False) -> None:
    """Save honest_kill_switch.json and optionally merge into strategy_kill_list.json."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # Invalidate caches so is_strategy_killed() picks up new data
    invalidate_cache()

    # Always save the full report
    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "criteria": results["summary"]["criteria"],
        "summary": results["summary"],
        "survivors": results["survivors"],
        "killed": results["killed"],
        "insufficient": results["insufficient"],
        "protected": results["protected"],
    }

    with open(KILL_SWITCH_PATH, "w") as f:
        json.dump(output, f, indent=2, default=str)
    print(f"  [KILL_SWITCH] Report saved to {KILL_SWITCH_PATH}")

    if not apply:
        print("  [KILL_SWITCH] DRY RUN — no kill list updated. Use --apply to write.")
        return

    # Merge killed strategies into strategy_kill_list.json
    killed_names = [k["strategy"] for k in results["killed"]]

    existing = {}
    if KILL_LIST_PATH.exists():
        try:
            with open(KILL_LIST_PATH) as f:
                existing = json.load(f)
        except (json.JSONDecodeError, IOError):
            pass

    # Merge: keep existing entries, add new ones
    existing_auto = set(existing.get("auto_kill_strategies", []))
    new_kills = set(killed_names) - existing_auto

    if new_kills:
        existing_auto.update(new_kills)
        existing["auto_kill_strategies"] = sorted(existing_auto)
        existing["honest_kill_switch"] = {
            "last_run": datetime.now(timezone.utc).isoformat(),
            "criteria": f"Per-asset-class gates (FOREX/COMMODITY stricter) on {MIN_TRADES}+ trades (honest ledger)",
            "per_asset_class_thresholds": ASSET_CLASS_THRESHOLDS,
            "newly_killed": sorted(new_kills),
            "total_killed": len(existing_auto),
        }

        with open(KILL_LIST_PATH, "w") as f:
            json.dump(existing, f, indent=2)
        print(f"  [KILL_SWITCH] Updated {KILL_LIST_PATH} with {len(new_kills)} new kills "
              f"(total: {len(existing_auto)})")
    else:
        print("  [KILL_SWITCH] No new strategies to kill — kill list unchanged.")


# ---------------------------------------------------------------------------
# Public API: check if a strategy is killed
# ---------------------------------------------------------------------------

_KILLED_CACHE: set[str] | None = None
_KILLED_REASONS: dict[str, str] = {}

def _load_killed_cache() -> None:
    """Load killed strategies from JSON into module-level cache."""
    global _KILLED_CACHE, _KILLED_REASONS
    _KILLED_CACHE = set()
    _KILLED_REASONS = {}
    if not KILL_SWITCH_PATH.exists():
        return
    try:
        with open(KILL_SWITCH_PATH) as f:
            data = json.load(f)
        for entry in data.get("killed", []):
            name = entry.get("strategy", "")
            if name:
                _KILLED_CACHE.add(name.lower())
                _KILLED_REASONS[name.lower()] = entry.get("reason", "killed")
    except (json.JSONDecodeError, IOError):
        pass

def is_strategy_killed(strategy_name: str) -> tuple[bool, str]:
    """Check if a strategy is killed by the honest kill switch.

    Returns (is_killed, reason) tuple. Uses module-level cache for performance.
    """
    if _KILLED_CACHE is None:
        _load_killed_cache()
    name_lower = strategy_name.lower()
    if name_lower in _KILLED_CACHE:
        return True, _KILLED_REASONS.get(name_lower, "killed by honest kill switch")
    return False, "not killed"


def get_killed_strategies() -> set[str]:
    """Return set of all strategy names killed by the honest kill switch."""
    if _KILLED_CACHE is None:
        _load_killed_cache()
    return set(_KILLED_CACHE or set())


def invalidate_cache() -> None:
    """Force reload of killed cache on next call (after --apply updates the file)."""
    global _KILLED_CACHE, _KILLED_REASONS, _PROTECTED_CACHE
    _KILLED_CACHE = None
    _KILLED_REASONS = {}
    _PROTECTED_CACHE = None


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Honest Kill Switch — data-driven strategy killer"
    )
    parser.add_argument("--apply", action="store_true",
                        help="Write killed strategies to strategy_kill_list.json")
    parser.add_argument("--check", type=str, metavar="STRATEGY",
                        help="Check if a specific strategy is killed")
    parser.add_argument("--min-wr", type=float, default=MIN_WR,
                        help=f"Minimum win rate (default: {MIN_WR})")
    parser.add_argument("--min-pf", type=float, default=MIN_PF,
                        help=f"Minimum profit factor (default: {MIN_PF})")
    parser.add_argument("--min-trades", type=int, default=MIN_TRADES,
                        help=f"Minimum trades for evaluation (default: {MIN_TRADES})")
    args = parser.parse_args()

    # Override module-level thresholds if custom args passed
    _override_globals(args.min_wr, args.min_pf, args.min_trades)

    # --check mode
    if args.check:
        killed, reason = is_strategy_killed(args.check)
        if killed:
            print(f"KILLED: {args.check} — {reason}")
            sys.exit(1)
        else:
            print(f"ALIVE: {args.check} — {reason}")
            sys.exit(0)

    # Full evaluation
    print("=" * 70)
    print("  HONEST KILL SWITCH — Data-Driven Strategy Evaluator")
    print(f"  Source: at_signal_outcomes (honest ledger)")
    print(f"  Default gates: WR >= {MIN_WR:.0%}, PF >= {MIN_PF:.2f}, min {MIN_TRADES} trades")
    print(f"  Per-class overrides:")
    for _ac, _t in sorted(ASSET_CLASS_THRESHOLDS.items()):
        print(f"    {_ac:<12s} WR >= {_t['min_wr']:.0%}, PF >= {_t['min_pf']:.2f}")
    print("=" * 70)
    print()

    print("Connecting to MySQL...")
    conn = _get_connection()

    print("Fetching strategy stats from at_signal_outcomes...")
    stats = fetch_strategy_stats(conn)
    print(f"  Found {len(stats)} strategies with outcome data")
    conn.close()

    print()
    print("Evaluating strategies against kill gates...")
    results = evaluate_strategies(stats)

    # Print report
    print()
    print("=" * 70)
    print(f"  KILLED ({len(results['killed'])} strategies — FAIL at least one gate):")
    print("=" * 70)
    for entry in results["killed"]:
        ac = entry.get("dominant_asset_class", "?")
        print(f"  ☠ {entry['strategy']:<45s} "
              f"n={entry['n']:>4d} WR={entry['wr']:.1%} PF={entry['pf']:.2f} "
              f"PnL={entry['total_pnl']:+.2f}% [{ac}]")
        print(f"    Reason: {entry['reason']}")

    print()
    print(f"  SURVIVORS ({len(results['survivors'])} strategies — PASS both gates):")
    print("-" * 70)
    for entry in results["survivors"]:
        ac = entry.get("dominant_asset_class", "?")
        print(f"  ✓ {entry['strategy']:<45s} "
              f"n={entry['n']:>4d} WR={entry['wr']:.1%} PF={entry['pf']:.2f} "
              f"PnL={entry['total_pnl']:+.2f}% [{ac}]")

    print()
    print(f"  INSUFFICIENT DATA ({len(results['insufficient'])} strategies — < {MIN_TRADES} trades):")
    print("-" * 70)
    for entry in results["insufficient"][:10]:
        ac = entry.get("dominant_asset_class", "?")
        print(f"  ? {entry['strategy']:<45s} n={entry['n']:>4d} [{ac}]")
    if len(results["insufficient"]) > 10:
        print(f"  ... and {len(results['insufficient']) - 10} more")

    if results["protected"]:
        print()
        print(f"  PROTECTED ({len(results['protected'])} strategies — exempt):")
        for entry in results["protected"]:
            print(f"  🛡 {entry['strategy']:<45s} n={entry['n']:>4d}")

    # Summary
    s = results["summary"]
    print()
    print("=" * 70)
    print(f"  SUMMARY")
    print(f"  Total strategies:       {s['total_strategies']}")
    print(f"  Evaluated (>= {MIN_TRADES} trades): {s['evaluated']}")
    print(f"  Survivors:              {s['survivors']}")
    print(f"  Killed:                 {s['killed']}")
    print(f"  Kill rate:              {s['kill_rate']:.1f}%")
    print(f"  Insufficient data:      {s['insufficient_data']}")
    print(f"  Protected:              {s['protected']}")
    print("=" * 70)

    # Save results
    save_kill_switch_results(results, apply=args.apply)


if __name__ == "__main__":
    main()
