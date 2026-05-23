#!/usr/bin/env python3
"""
Missed Opportunity Analyzer — Self-Improving Feedback Loop
==========================================================
Runs hourly to:
  1. Identify top Binance gainers we did NOT have picks on
  2. Identify wrong guesses (SL_HIT picks) and analyze why
  3. Detect recurring patterns in misses and failures
  4. Generate actionable recommendations for the scanner
  5. Provide get_universe_additions() for scanner integration

Uses 3+ API failover chain per project rules.
"""

from __future__ import annotations

import json
import os
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent
DATA_DIR = SCRIPT_DIR / "data"
ACTIVE_PICKS_PATH = DATA_DIR / "active_picks.json"
CLOSED_PICKS_PATH = DATA_DIR / "closed_picks.json"
DYNAMIC_UNIVERSE_PATH = DATA_DIR / "dynamic_universe.json"
MISSED_GAINERS_LOG = DATA_DIR / "missed_gainers_log.json"
WRONG_GUESSES_LOG = DATA_DIR / "wrong_guesses_log.json"
IMPROVEMENT_REPORT = DATA_DIR / "hourly_improvement_report.json"

# ---------------------------------------------------------------------------
# Binance failover endpoints (NEVER single endpoint per project rules)
# ---------------------------------------------------------------------------
BINANCE_TICKER_ENDPOINTS = [
    "https://api.binance.com/api/v3/ticker/24hr",
    "https://api1.binance.com/api/v3/ticker/24hr",
    "https://api2.binance.com/api/v3/ticker/24hr",
    "https://api3.binance.com/api/v3/ticker/24hr",
]

# Fallback: CoinGecko top gainers
COINGECKO_GAINERS_URL = "https://api.coingecko.com/api/v3/coins/markets"

REQUEST_TIMEOUT = 10
RATE_LIMIT_SLEEP = 0.5

# Thresholds
MIN_VOLUME_USD = 2_000_000
MIN_GAIN_PCT = 10.0
TOP_N_GAINERS = 20
UNIVERSE_ADD_THRESHOLD = 3        # missed N+ times in 7 days => recommend add
UNIVERSE_ADD_MIN_VOLUME = 5_000_000
STRATEGY_BAD_SL_RATE = 0.60       # >60% SL rate => flag strategy
LOG_RETENTION_DAYS = 30


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _load_json(path: Path, default=None):
    if default is None:
        default = []
    if not path.exists():
        return default
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return default


def _save_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)


def _prune_old_entries(entries: list, days: int = LOG_RETENTION_DAYS) -> list:
    """Remove log entries older than `days`."""
    cutoff = (_now_utc() - timedelta(days=days)).isoformat()
    return [e for e in entries if e.get("timestamp", "") >= cutoff]


# ---------------------------------------------------------------------------
# 1. Fetch top Binance gainers with failover
# ---------------------------------------------------------------------------

def fetch_binance_tickers() -> list[dict]:
    """Fetch 24h tickers from Binance with 4-endpoint failover."""
    for url in BINANCE_TICKER_ENDPOINTS:
        try:
            resp = requests.get(url, timeout=REQUEST_TIMEOUT)
            if resp.status_code == 200:
                return resp.json()
        except (requests.RequestException, ValueError):
            pass
        time.sleep(RATE_LIMIT_SLEEP)

    # Fallback: CoinGecko top 250 by market cap
    print("  [WARN] All Binance endpoints failed, trying CoinGecko fallback...")
    try:
        resp = requests.get(
            COINGECKO_GAINERS_URL,
            params={
                "vs_currency": "usd",
                "order": "volume_desc",
                "per_page": 250,
                "page": 1,
                "sparkline": "false",
                "price_change_percentage": "24h",
            },
            timeout=REQUEST_TIMEOUT,
        )
        if resp.status_code == 200:
            cg_data = resp.json()
            # Convert CoinGecko format to Binance-like format
            tickers = []
            for coin in cg_data:
                sym = (coin.get("symbol", "") or "").upper() + "USDT"
                pct = coin.get("price_change_percentage_24h") or 0
                vol = coin.get("total_volume") or 0
                price = coin.get("current_price") or 0
                tickers.append({
                    "symbol": sym,
                    "priceChangePercent": str(pct),
                    "quoteVolume": str(vol),
                    "lastPrice": str(price),
                })
            return tickers
    except (requests.RequestException, ValueError):
        pass

    print("  [ERROR] All ticker sources failed")
    return []


def get_top_gainers(tickers: list[dict]) -> list[dict]:
    """Filter and rank top USDT gainers."""
    gainers = []
    for t in tickers:
        symbol = t.get("symbol", "")
        if not symbol.endswith("USDT"):
            continue
        # Skip stablecoins and leveraged tokens
        base = symbol.replace("USDT", "")
        if base in ("USDC", "BUSD", "DAI", "TUSD", "FDUSD", "USDP"):
            continue
        if any(x in base for x in ("UP", "DOWN", "BULL", "BEAR")):
            continue

        try:
            pct = float(t.get("priceChangePercent", 0))
            vol = float(t.get("quoteVolume", 0))
            price = float(t.get("lastPrice", 0))
        except (ValueError, TypeError):
            continue

        if vol >= MIN_VOLUME_USD and pct >= MIN_GAIN_PCT:
            gainers.append({
                "symbol": symbol,
                "gain_24h": round(pct, 2),
                "volume": round(vol, 2),
                "price": price,
            })

    gainers.sort(key=lambda x: x["gain_24h"], reverse=True)
    return gainers[:TOP_N_GAINERS]


# ---------------------------------------------------------------------------
# 2. Identify missed gainers
# ---------------------------------------------------------------------------

def load_universe_symbols() -> set[str]:
    """Load all symbols from dynamic_universe.json."""
    data = _load_json(DYNAMIC_UNIVERSE_PATH, default={})
    symbols = set()
    for key in ("core_symbols", "dynamic_symbols"):
        for s in data.get(key, []):
            symbols.add(s)
    return symbols


def load_pick_symbols() -> set[str]:
    """Load symbols from active and recent closed picks."""
    symbols = set()
    for path in (ACTIVE_PICKS_PATH, CLOSED_PICKS_PATH):
        picks = _load_json(path, default=[])
        for p in picks:
            symbols.add(p.get("symbol", ""))
    return symbols


def identify_missed_gainers(top_gainers: list[dict]) -> list[dict]:
    """Find top gainers we didn't have picks on."""
    universe = load_universe_symbols()
    pick_symbols = load_pick_symbols()

    missed = []
    for g in top_gainers:
        sym = g["symbol"]
        if sym in pick_symbols:
            continue  # We had a pick — not missed

        in_universe = sym in universe
        if in_universe:
            reason = "in universe but no strategy fired"
        else:
            reason = "not in universe"

        missed.append({
            "symbol": sym,
            "gain_24h": g["gain_24h"],
            "volume": g["volume"],
            "price": g.get("price", 0),
            "in_universe": in_universe,
            "reason_missed": reason,
            "timestamp": _now_utc().isoformat(),
        })

    return missed


# ---------------------------------------------------------------------------
# 3. Identify wrong guesses (SL_HIT picks)
# ---------------------------------------------------------------------------

def identify_wrong_guesses() -> list[dict]:
    """Find recent closed picks that hit stop-loss."""
    closed = _load_json(CLOSED_PICKS_PATH, default=[])
    cutoff = (_now_utc() - timedelta(hours=24)).isoformat()

    wrong = []
    for p in closed:
        if p.get("exit_reason") != "SL_HIT":
            continue
        exit_date = p.get("exit_date", "")
        if exit_date and exit_date < cutoff[:10]:
            continue  # Older than 24h

        extra = {}
        extra_raw = p.get("extra_json", "")
        if extra_raw and isinstance(extra_raw, str):
            try:
                extra = json.loads(extra_raw)
            except (json.JSONDecodeError, TypeError):
                pass

        wrong.append({
            "symbol": p.get("symbol", ""),
            "strategy": p.get("strategy", ""),
            "signal_type": p.get("signal_type", "BUY"),
            "confidence": p.get("confidence", 0),
            "ml_score": p.get("ml_score"),
            "pnl_pct": p.get("pnl_pct", 0),
            "entry_price": p.get("entry_price", 0),
            "exit_price": p.get("exit_price", 0),
            "rsi_at_entry": p.get("rsi_at_entry"),
            "volume_ratio": p.get("volume_ratio"),
            "regime_at_entry": p.get("regime_at_entry"),
            "hold_days": p.get("hold_days", 0),
            "entry_date": p.get("entry_date", ""),
            "exit_date": exit_date,
            "reason": _diagnose_wrong_guess(p, extra),
            "timestamp": _now_utc().isoformat(),
        })

    return wrong


def _diagnose_wrong_guess(pick: dict, extra: dict) -> str:
    """Generate a brief reason why this pick failed."""
    reasons = []

    conf = pick.get("confidence", 0)
    if conf and conf < 0.7:
        reasons.append("low confidence")

    rsi = pick.get("rsi_at_entry")
    signal = pick.get("signal_type", "BUY")
    if rsi is not None:
        if signal == "BUY" and rsi > 70:
            reasons.append("overbought RSI at entry")
        elif signal == "SELL" and rsi < 30:
            reasons.append("oversold RSI at entry")

    vol_ratio = pick.get("volume_ratio")
    if vol_ratio is not None and vol_ratio < 0.5:
        reasons.append("low volume")

    regime = pick.get("regime_at_entry", "")
    if regime == "backfill":
        reasons.append("backfill candle")

    if not reasons:
        reasons.append("no obvious red flag")

    return "; ".join(reasons)


# ---------------------------------------------------------------------------
# 4. Pattern detection over historical logs
# ---------------------------------------------------------------------------

def detect_patterns(missed_log: list, wrong_log: list) -> dict:
    """Analyze recurring patterns in misses and failures."""
    now = _now_utc()
    week_ago = (now - timedelta(days=7)).isoformat()
    month_ago = (now - timedelta(days=30)).isoformat()

    # --- Missed categories (approximate from symbol naming) ---
    missed_symbols_7d = Counter()
    missed_not_in_universe = 0
    missed_in_universe = 0
    for entry in missed_log:
        ts = entry.get("timestamp", "")
        if ts < week_ago:
            continue
        sym = entry.get("symbol", "")
        missed_symbols_7d[sym] += 1
        if entry.get("in_universe"):
            missed_in_universe += 1
        else:
            missed_not_in_universe += 1

    # --- Worst strategies by SL rate ---
    strategy_stats = defaultdict(lambda: {"sl": 0, "total": 0})
    for entry in wrong_log:
        ts = entry.get("timestamp", "")
        if ts < month_ago:
            continue
        strat = entry.get("strategy", "unknown")
        strategy_stats[strat]["sl"] += 1
        strategy_stats[strat]["total"] += 1

    # Also count non-SL closed picks to get true total per strategy
    closed = _load_json(CLOSED_PICKS_PATH, default=[])
    for p in closed:
        strat = p.get("strategy", "unknown")
        if strat in strategy_stats:
            # Only count total if we have SL entries for this strategy
            pass  # Total already tracked from wrong_log; we supplement below

    # Compute full totals from closed picks
    strat_total_closed = Counter()
    for p in closed:
        strat_total_closed[p.get("strategy", "unknown")] += 1

    worst_strategies = {}
    for strat, stats in strategy_stats.items():
        total = max(strat_total_closed.get(strat, stats["total"]), 1)
        sl_rate = round(100 * stats["sl"] / total)
        if total >= 5:  # Need minimum sample
            worst_strategies[strat] = {
                "sl_rate": sl_rate,
                "sl_count": stats["sl"],
                "total_closed": total,
            }

    # --- Symbols to add (missed 3+ times in 7 days, >$5M volume) ---
    symbols_to_add = []
    universe = load_universe_symbols()
    for sym, count in missed_symbols_7d.most_common(50):
        if count >= UNIVERSE_ADD_THRESHOLD and sym not in universe:
            # Check average volume from log
            vols = [
                e.get("volume", 0)
                for e in missed_log
                if e.get("symbol") == sym and e.get("timestamp", "") >= week_ago
            ]
            avg_vol = sum(vols) / len(vols) if vols else 0
            if avg_vol >= UNIVERSE_ADD_MIN_VOLUME:
                symbols_to_add.append(sym)

    return {
        "missed_symbol_freq_7d": dict(missed_symbols_7d.most_common(20)),
        "missed_not_in_universe": missed_not_in_universe,
        "missed_in_universe": missed_in_universe,
        "worst_strategies": worst_strategies,
        "symbols_to_add": symbols_to_add,
    }


# ---------------------------------------------------------------------------
# 5. Generate recommendations
# ---------------------------------------------------------------------------

def generate_recommendations(patterns: dict) -> list[str]:
    """Produce actionable text recommendations."""
    recs = []

    # Universe additions
    for sym in patterns.get("symbols_to_add", []):
        freq = patterns.get("missed_symbol_freq_7d", {}).get(sym, 0)
        recs.append(
            f"Add {sym} to dynamic universe (missed {freq} times in 7 days)"
        )

    # Bad strategies
    for strat, stats in patterns.get("worst_strategies", {}).items():
        if stats["sl_rate"] >= STRATEGY_BAD_SL_RATE * 100:
            recs.append(
                f"Review {strat}: {stats['sl_rate']}% SL rate over "
                f"{stats['total_closed']} closed picks — consider parameter adjustment"
            )

    # General observations
    miss_not = patterns.get("missed_not_in_universe", 0)
    miss_in = patterns.get("missed_in_universe", 0)
    total_miss = miss_not + miss_in
    if total_miss > 0 and miss_not / max(total_miss, 1) > 0.7:
        recs.append(
            f"{round(100*miss_not/total_miss)}% of missed gainers are outside our universe "
            f"— expand dynamic universe coverage"
        )

    if not recs:
        recs.append("No urgent recommendations at this time")

    return recs


# ---------------------------------------------------------------------------
# 6. Public API for scanner integration
# ---------------------------------------------------------------------------

def get_universe_additions() -> list[str]:
    """
    Returns symbols that should be added to the dynamic universe.
    Called by scanner.py during universe loading.

    Criteria: missed 3+ times in 7 days with >$5M avg volume.
    """
    missed_log = _load_json(MISSED_GAINERS_LOG, default=[])
    if not missed_log:
        return []

    week_ago = (_now_utc() - timedelta(days=7)).isoformat()
    universe = load_universe_symbols()

    symbol_counts = Counter()
    symbol_volumes = defaultdict(list)

    for entry in missed_log:
        ts = entry.get("timestamp", "")
        if ts < week_ago:
            continue
        sym = entry.get("symbol", "")
        if sym and sym not in universe:
            symbol_counts[sym] += 1
            symbol_volumes[sym].append(entry.get("volume", 0))

    additions = []
    for sym, count in symbol_counts.most_common(20):
        if count >= UNIVERSE_ADD_THRESHOLD:
            avg_vol = sum(symbol_volumes[sym]) / len(symbol_volumes[sym])
            if avg_vol >= UNIVERSE_ADD_MIN_VOLUME:
                additions.append(sym)

    return additions


# ---------------------------------------------------------------------------
# Main run
# ---------------------------------------------------------------------------

def run_analysis() -> dict:
    """Execute the full hourly analysis cycle."""
    print("=" * 60)
    print("MISSED OPPORTUNITY ANALYZER — Hourly Self-Improvement Scan")
    print(f"Time: {_now_utc().strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print("=" * 60)

    # Step 1: Fetch market data
    print("\n[1/6] Fetching Binance 24h tickers (4-endpoint failover)...")
    tickers = fetch_binance_tickers()
    print(f"  Got {len(tickers)} tickers")

    top_gainers = get_top_gainers(tickers)
    print(f"  Top gainers (>{MIN_GAIN_PCT}% gain, >${MIN_VOLUME_USD/1e6:.0f}M vol): {len(top_gainers)}")
    for g in top_gainers[:5]:
        print(f"    {g['symbol']:>12s}  +{g['gain_24h']:6.1f}%  vol=${g['volume']/1e6:.1f}M")

    # Step 2: Identify missed gainers
    print("\n[2/6] Identifying missed gainers...")
    missed = identify_missed_gainers(top_gainers)
    print(f"  Missed gainers: {len(missed)}")
    for m in missed[:5]:
        tag = "IN-UNIV" if m["in_universe"] else "NOT-UNIV"
        print(f"    {m['symbol']:>12s}  +{m['gain_24h']:6.1f}%  [{tag}] {m['reason_missed']}")

    # Step 3: Identify wrong guesses
    print("\n[3/6] Analyzing wrong guesses (SL_HIT in last 24h)...")
    wrong = identify_wrong_guesses()
    print(f"  Wrong guesses: {len(wrong)}")
    for w in wrong[:5]:
        print(f"    {w['symbol']:>12s}  {w['strategy']:<30s}  pnl={w['pnl_pct']}%  [{w['reason']}]")

    # Step 4: Update persistent logs
    print("\n[4/6] Updating persistent logs...")
    missed_log = _load_json(MISSED_GAINERS_LOG, default=[])
    wrong_log = _load_json(WRONG_GUESSES_LOG, default=[])

    missed_log.extend(missed)
    wrong_log.extend(wrong)

    # Prune old entries
    missed_log = _prune_old_entries(missed_log)
    wrong_log = _prune_old_entries(wrong_log)

    _save_json(MISSED_GAINERS_LOG, missed_log)
    _save_json(WRONG_GUESSES_LOG, wrong_log)
    print(f"  Missed log: {len(missed_log)} entries (last {LOG_RETENTION_DAYS} days)")
    print(f"  Wrong log: {len(wrong_log)} entries (last {LOG_RETENTION_DAYS} days)")

    # Step 5: Detect patterns
    print("\n[5/6] Detecting recurring patterns...")
    patterns = detect_patterns(missed_log, wrong_log)
    print(f"  Symbols to add to universe: {patterns.get('symbols_to_add', [])}")
    print(f"  Worst strategies: {list(patterns.get('worst_strategies', {}).keys())}")

    # Step 6: Generate recommendations
    print("\n[6/6] Generating recommendations...")
    recs = generate_recommendations(patterns)
    for i, r in enumerate(recs, 1):
        print(f"  {i}. {r}")

    # Build report
    report = {
        "timestamp": _now_utc().isoformat(),
        "missed_gainers": missed,
        "wrong_guesses": wrong,
        "recurring_patterns": {
            "missed_symbol_freq_7d": patterns.get("missed_symbol_freq_7d", {}),
            "missed_not_in_universe": patterns.get("missed_not_in_universe", 0),
            "missed_in_universe": patterns.get("missed_in_universe", 0),
            "worst_strategies": patterns.get("worst_strategies", {}),
            "symbols_to_add": patterns.get("symbols_to_add", []),
        },
        "recommendations": recs,
        "stats": {
            "tickers_fetched": len(tickers),
            "top_gainers_found": len(top_gainers),
            "missed_count": len(missed),
            "wrong_guess_count": len(wrong),
            "log_total_missed": len(missed_log),
            "log_total_wrong": len(wrong_log),
        },
    }

    _save_json(IMPROVEMENT_REPORT, report)
    print(f"\n  Report saved to {IMPROVEMENT_REPORT}")

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print(f"  Missed top gainers this hour: {len(missed)}")
    print(f"  Wrong guesses (24h):          {len(wrong)}")
    print(f"  Universe additions suggested:  {len(patterns.get('symbols_to_add', []))}")
    print(f"  Recommendations:               {len(recs)}")
    print("=" * 60)

    return report


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    run_analysis()
