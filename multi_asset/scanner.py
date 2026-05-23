#!/usr/bin/env python3
"""
MULTI-ASSET SCANNER v1.1
=========================
Scans futures, stocks, forex, ETFs, and penny stocks using proven strategies.
Produces picks in the same JSON format as alpha_engine/scanner.py for
seamless integration with the audit dashboard.

Features:
  - Drawdown circuit breaker (portfolio -5% pause, single-pick auto-close)
  - Correlation group limits (max 3 picks per correlated group)
  - Market regime detection (BULL/BEAR/CHOP via SPY+VIX)
  - Long/short balance enforcement (30% short minimum in BEAR regime)

Usage:
  python multi_asset/scanner.py                    # Full scan
  python multi_asset/scanner.py --futures-only     # Futures only
  python multi_asset/scanner.py --stocks-only      # Stocks only
  python multi_asset/scanner.py --forex-only       # Forex only
  python multi_asset/scanner.py --etfs-only        # ETFs only
  python multi_asset/scanner.py --backtest         # Run backtest on all classes
  python multi_asset/scanner.py --dry-run          # Show signals without saving
  python multi_asset/scanner.py --status           # Show risk metrics without scanning

No fake data. Real yfinance prices. Proven strategies only.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
import hashlib
from datetime import datetime, timezone, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

try:
    import yfinance as yf
except ImportError:
    print("ERROR: yfinance required. pip install yfinance")
    sys.exit(1)

# Non-crypto macro/regime gates (import gracefully so scanner still runs without alpha_engine)
try:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "alpha_engine"))
    from non_crypto_quality_gate import (
        equity_macro_gate,
        forex_macro_gate,
        vix_confidence_adj,
        INVERSE_PENDING_STRATEGIES as _INVERSE_PENDING,
    )
    _MACRO_GATES_AVAILABLE = True
except ImportError:
    _MACRO_GATES_AVAILABLE = False
    def equity_macro_gate(data): return True, "gates unavailable"
    def forex_macro_gate(data, symbol): return True, "gates unavailable"
    def vix_confidence_adj(data, strategy_name=""): return 1.0
    _INVERSE_PENDING = frozenset()

# Multi-Asset Strategy Engineering (600 Variants) Integration
try:
    from alpha_engine.generated_v2_bundle import ALL_GENERATED_STRATEGIES
    from alpha_engine.strategy_runner import run_strategy as run_universal_strategy
    _GENERATED_BUNDLE_AVAILABLE = True
except ImportError:
    ALL_GENERATED_STRATEGIES = []
    _GENERATED_BUNDLE_AVAILABLE = False
    def run_universal_strategy(strat_def, df): return []

# Commodity & Futures-specific strategies (v1.0)
try:
    from multi_asset.commodity_futures_strategies import (
        COMMODITY_STRATEGIES as _CF_STRATEGIES,
        COMMODITY_VIX_STRATEGIES as _CF_VIX_STRATEGIES,
        COMMODITY_CROSS_STRATEGIES as _CF_CROSS_STRATEGIES,
        COMMODITY_SYMBOLS as _CF_COMMODITY_SYMBOLS,
        FUTURES_SYMBOLS as _CF_FUTURES_SYMBOLS,
        commodity_momentum as _commodity_momentum,
        bond_equity_rotation as _bond_equity_rotation,
        dr_copper_indicator as _dr_copper_indicator,
        gold_safe_haven as _gold_safe_haven,
        treasury_yield_curve as _treasury_yield_curve,
        credit_spread_strategy as _credit_spread_strategy,
        duration_rotation as _duration_rotation,
        futures_momentum as _futures_momentum,
        precious_metals_momentum as _precious_metals_momentum,
        energy_sector_rotation as _energy_sector_rotation,
    )
    _COMMODITY_FUTURES_AVAILABLE = True
except ImportError:
    _COMMODITY_FUTURES_AVAILABLE = False
    _CF_STRATEGIES = {}
    _CF_VIX_STRATEGIES = {}
    _CF_CROSS_STRATEGIES = {}
    _CF_COMMODITY_SYMBOLS = {}
    _CF_FUTURES_SYMBOLS = {}

# Forex-specific strategies (v1.0)
try:
    from multi_asset.forex_strategies import (
        FOREX_STRATEGIES as _FX_STRATEGIES,
        scan_forex as _scan_forex,
        DXY_TICKER as _DXY_TICKER,
    )
    _FOREX_STRATEGIES_AVAILABLE = True
except ImportError:
    _FOREX_STRATEGIES_AVAILABLE = False
    _FX_STRATEGIES = {}
    _DXY_TICKER = "DX-Y.NYB"
    def _scan_forex(symbols, data, dxy_df=None, killed_strategies=None, use_dxy_filter=True): return []

# Equity/ETF-specific strategies (v1.0)
try:
    from multi_asset.equity_strategies import (
        EQUITY_ETF_STRATEGIES as _EQ_STRATEGIES,
        EQUITY_ETF_SYMBOLS as _EQ_SYMBOLS,
        run_all_equity_strategies as _run_equity_strategies,
    )
    _EQUITY_STRATEGIES_AVAILABLE = True
except ImportError:
    _EQUITY_STRATEGIES_AVAILABLE = False
    _EQ_STRATEGIES = {}
    _EQ_SYMBOLS = {}
    def _run_equity_strategies(data, vix_data=None, spy_data=None): return []

# ---------------------------------------------------------------------------
# Paths & constants
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
DATA_DIR = SCRIPT_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

ACTIVE_PICKS_FILE = DATA_DIR / "multi_asset_picks.json"
CLOSED_PICKS_FILE = DATA_DIR / "multi_asset_closed.json"
BACKTEST_FILE = DATA_DIR / "backtest_results.json"
STATE_FILE = DATA_DIR / "scanner_state.json"

VERSION = "1.1"

CIRCUIT_BREAKER_FILE = DATA_DIR / "circuit_breaker.json"

# ---------------------------------------------------------------------------
# Symbol universes
# ---------------------------------------------------------------------------
FUTURES = {
    "ES=F":  {"name": "S&P 500 E-mini",   "cat": "futures"},
    "NQ=F":  {"name": "Nasdaq 100 E-mini", "cat": "futures"},
    "YM=F":  {"name": "Dow E-mini",        "cat": "futures"},
    # "CL=F" REMOVED: 26 futures trades, 3.8% WR, -29.82% PnL — worse than random
    "GC=F":  {"name": "Gold",              "cat": "futures"},
    "SI=F":  {"name": "Silver",            "cat": "futures"},
    "ZN=F":  {"name": "10-Year T-Note",    "cat": "futures"},
    "HG=F":  {"name": "Copper",              "cat": "commodity"},  # reclassified: scores COMMODITY not FUTURES
    "PL=F":  {"name": "Platinum",            "cat": "commodity"},  # reclassified: scores COMMODITY not FUTURES
}

STOCKS = {
    "AAPL":  {"name": "Apple",     "cat": "stock"},
    "MSFT":  {"name": "Microsoft", "cat": "stock"},
    "NVDA":  {"name": "Nvidia",    "cat": "stock"},
    "GOOGL": {"name": "Alphabet",  "cat": "stock"},
    "AMZN":  {"name": "Amazon",    "cat": "stock"},
    "META":  {"name": "Meta",      "cat": "stock"},
    "TSLA":  {"name": "Tesla",     "cat": "stock"},
    "JPM":   {"name": "JPMorgan",  "cat": "stock"},
    "V":     {"name": "Visa",      "cat": "stock"},
}

FOREX = {
    "EURUSD=X": {"name": "EUR/USD", "cat": "forex", "carry_yield_diff": -0.5},
    "USDJPY=X": {"name": "USD/JPY", "cat": "forex", "carry_yield_diff": 4.5},
    "GBPUSD=X": {"name": "GBP/USD", "cat": "forex", "carry_yield_diff": 0.25},
    "AUDUSD=X": {"name": "AUD/USD", "cat": "forex", "carry_yield_diff": 0.75},
    "NZDUSD=X": {"name": "NZD/USD", "cat": "forex", "carry_yield_diff": 1.0},
    "USDCAD=X": {"name": "USD/CAD", "cat": "forex", "carry_yield_diff": 0.5},
    "USDCHF=X": {"name": "USD/CHF", "cat": "forex", "carry_yield_diff": 2.0},
    "EURJPY=X": {"name": "EUR/JPY", "cat": "forex", "carry_yield_diff": 4.0},
}

ETFS = {
    "SPY":  {"name": "S&P 500 ETF",      "cat": "etf"},
    "QQQ":  {"name": "Nasdaq 100 ETF",   "cat": "etf"},
    "XLK":  {"name": "Technology Select", "cat": "etf"},
    "XLF":  {"name": "Financial Select",  "cat": "etf"},
    "XLE":  {"name": "Energy Select",     "cat": "etf"},
    "GLD":  {"name": "Gold ETF",          "cat": "etf"},
    "TLT":  {"name": "20+ Year Treasury", "cat": "etf"},
    "IWM":  {"name": "Russell 2000",      "cat": "etf"},
    # Bond ETFs for bond strategies
    "IEF":  {"name": "7-10 Year Treasury", "cat": "etf"},
    "SHY":  {"name": "1-3 Year Treasury",  "cat": "etf"},
    "BND":  {"name": "Total Bond Market",  "cat": "etf"},
    "HYG":  {"name": "High Yield Corp",    "cat": "etf"},
    "LQD":  {"name": "Inv. Grade Corp",    "cat": "etf"},
    "AGG":  {"name": "Agg Bond Index",     "cat": "etf"},
    "TIP":  {"name": "TIPS",               "cat": "etf"},
    # Commodity ETFs for expanded commodity strategies
    "SLV":  {"name": "Silver ETF",         "cat": "etf"},
    "USO":  {"name": "US Oil Fund",        "cat": "etf"},
    "UNG":  {"name": "US Natural Gas",     "cat": "etf"},
    "PPLT": {"name": "Platinum ETF",       "cat": "etf"},
}

PENNY = {
    "SOFI": {"name": "SoFi",      "cat": "penny"},
    "NIO":  {"name": "NIO",       "cat": "penny"},
    "PLTR": {"name": "Palantir",  "cat": "penny"},
    "MARA": {"name": "Marathon",  "cat": "penny"},
    "RIOT": {"name": "Riot",      "cat": "penny"},
    "IONQ": {"name": "IonQ",      "cat": "penny"},
}

# THE GREAT PURGE (2026-03-11): Forex and penny removed from default scanning.
# Forex: macd_divergence 0W/3L, bb_mean_reversion 0W/3L — no edge found.
# Penny: SOFI -1.31%, IONQ -96.65% (institutional) — too volatile, no proven strategy.
# All AIs (Claude, Grok, Antigravity, Mercury, Kilo-Code) unanimously agreed.
# Keeping dicts + --forex-only flag for historical reference / future resurrection.
# Merge commodity/futures symbols from dedicated module
_EXTRA_CF_SYMS = {}
if _COMMODITY_FUTURES_AVAILABLE:
    for _s, _i in {**_CF_COMMODITY_SYMBOLS, **_CF_FUTURES_SYMBOLS}.items():
        if _s not in FUTURES:  # Don't duplicate existing futures
            _EXTRA_CF_SYMS[_s] = _i

ALL_SYMBOLS = {**FUTURES, **STOCKS, **ETFS, **_EXTRA_CF_SYMS}  # Concentrated: ETFs + stocks + commodities + dedicated CF

# Risk parameters per category: (stop_loss_pct, take_profit_pct, max_hold_days)
RISK_PARAMS = {
    "futures":    (-0.04, 0.08, 10),
    "commodity":  (-0.04, 0.08, 10),
    "stock":      (-0.06, 0.12, 10),
    "forex":      (-0.025, 0.03, 14),
    "etf":        (-0.05, 0.10, 15),
    "penny":      (-0.12, 0.25, 5),
}

# Non-crypto quality thresholds (aligned with pick_quality_monitor.py policy)
NON_CRYPTO_MIN_CONFIDENCE = 0.50
MIN_RR_GATE = 1.5
NON_CRYPTO_DISTANCE_LIMITS = {
    "forex": {"tp_max_pct": 5.0, "sl_max_pct": 3.0},
    "commodity": {"tp_max_pct": 15.0, "sl_max_pct": 10.0},
    "futures": {"tp_max_pct": 20.0, "sl_max_pct": 15.0},
    "equity": {"tp_max_pct": 30.0, "sl_max_pct": 20.0},
    "stock": {"tp_max_pct": 30.0, "sl_max_pct": 20.0},
    "stocks": {"tp_max_pct": 30.0, "sl_max_pct": 20.0},
    "etf": {"tp_max_pct": 30.0, "sl_max_pct": 20.0},
    "bond": {"tp_max_pct": 10.0, "sl_max_pct": 5.0},
}


# ---------------------------------------------------------------------------
# Correlation groups — max 3 picks per correlated group
# ---------------------------------------------------------------------------
CORRELATION_GROUPS = {
    "us_equity_index": ["SPY", "QQQ", "ES=F", "NQ=F", "XLK", "IWM", "YM=F"],
    "us_bonds": ["TLT", "IEF", "SHY", "BND", "AGG", "TIP", "ZN=F", "ZB=F"],
    "credit_bonds": ["HYG", "LQD"],
    "gold": ["GLD", "GC=F"],
    "silver_plat": ["SLV", "SI=F", "PPLT"],
    "oil_energy": ["XLE", "CL=F", "USO", "UNG"],  # CL=F re-added for commodity-specific strategies only
    "nat_gas": ["NG=F"],
    "copper": ["HG=F"],
    "agriculture": ["CORN", "WEAT", "SOYB"],
    "usd_pairs": ["EURUSD=X", "GBPUSD=X", "AUDUSD=X", "NZDUSD=X", "USDCAD=X", "USDCHF=X"],
    "jpy_cross": ["USDJPY=X", "EURJPY=X"],
}
MAX_PER_CORRELATION_GROUP = 3

# Reverse lookup: symbol -> group name
_SYMBOL_TO_CORR_GROUP: dict[str, str] = {}
for _grp, _syms in CORRELATION_GROUPS.items():
    for _s in _syms:
        _SYMBOL_TO_CORR_GROUP[_s] = _grp


# ---------------------------------------------------------------------------
# Regime detection
# ---------------------------------------------------------------------------
REGIME_BULL = "BULL"
REGIME_BEAR = "BEAR"
REGIME_CHOP = "CHOP"

# In BEAR regime, require at least this fraction of short-side exposure
BEAR_MIN_SHORT_PCT = 0.30


# ---------------------------------------------------------------------------
# Circuit breaker thresholds
# ---------------------------------------------------------------------------
PORTFOLIO_DRAWDOWN_PAUSE_THRESHOLD = -0.05   # -5% total portfolio → pause 24h
SINGLE_PICK_DRAWDOWN_STANDARD = -0.03        # -3% non-penny → auto-close
SINGLE_PICK_DRAWDOWN_PENNY = -0.08           # -8% penny → auto-close
CIRCUIT_BREAKER_PAUSE_HOURS = 24


def _load_circuit_breaker_state() -> dict:
    """Load circuit breaker state from disk."""
    if CIRCUIT_BREAKER_FILE.exists():
        try:
            with open(CIRCUIT_BREAKER_FILE) as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {"paused": False, "paused_until": None, "last_check": None,
            "total_unrealized_pnl": 0.0, "auto_closed": [], "regime": REGIME_CHOP}


def _save_circuit_breaker_state(state: dict):
    """Persist circuit breaker state."""
    with open(CIRCUIT_BREAKER_FILE, "w") as f:
        json.dump(_sanitize(state), f, indent=2, default=str)


def check_circuit_breakers(active: list[dict], data: dict[str, pd.DataFrame]) -> tuple[list[dict], list[dict], dict]:
    """
    Drawdown circuit breaker:
      - Computes total portfolio unrealized PnL from active picks
      - If total drawdown exceeds -5%, pause new entries for 24h
      - If any single pick hits -3% (non-penny) or -8% (penny), auto-close it

    Returns: (still_open, force_closed, cb_state)
    """
    cb = _load_circuit_breaker_state()
    now = datetime.now(timezone.utc)
    cb["last_check"] = now.isoformat()

    still_open = []
    force_closed = []

    total_unrealized = 0.0
    pick_count = 0

    for pick in active:
        symbol = pick["symbol"]
        df = data.get(symbol)
        if df is None or df.empty:
            still_open.append(pick)
            continue

        current_price = float(df["Close"].iloc[-1])
        entry = pick["entry_price"]
        direction = pick["direction"]

        if direction == "LONG":
            pnl_pct = (current_price / entry) - 1
        else:
            pnl_pct = 1 - (current_price / entry)

        pick["unrealized_pnl_pct"] = pnl_pct
        pick["current_price"] = current_price
        total_unrealized += pnl_pct
        pick_count += 1

        # Single-pick drawdown check
        cat = pick.get("category", "stock")
        threshold = SINGLE_PICK_DRAWDOWN_PENNY if cat == "penny" else SINGLE_PICK_DRAWDOWN_STANDARD

        if pnl_pct < threshold:
            pick["status"] = "LOST"
            pick["exit_price"] = current_price
            pick["exit_reason"] = "CIRCUIT_BREAKER"
            pick["pnl_pct"] = pnl_pct
            pick["closed_at"] = now.isoformat()
            force_closed.append(pick)
            print(f"  [CIRCUIT BREAKER] Auto-closed {symbol} ({direction}) at {pnl_pct*100:+.2f}% "
                  f"(threshold: {threshold*100:.0f}%)")
        else:
            still_open.append(pick)

    # Portfolio-level drawdown check
    avg_unrealized = total_unrealized / pick_count if pick_count > 0 else 0.0
    cb["total_unrealized_pnl"] = total_unrealized
    cb["avg_unrealized_pnl"] = avg_unrealized
    cb["pick_count"] = pick_count
    cb["auto_closed"] = [
        {"symbol": p["symbol"], "pnl_pct": p["pnl_pct"], "closed_at": p["closed_at"]}
        for p in force_closed
    ]

    if avg_unrealized < PORTFOLIO_DRAWDOWN_PAUSE_THRESHOLD:
        pause_until = (now + timedelta(hours=CIRCUIT_BREAKER_PAUSE_HOURS)).isoformat()
        cb["paused"] = True
        cb["paused_until"] = pause_until
        cb["pause_reason"] = (f"Portfolio avg drawdown {avg_unrealized*100:+.2f}% "
                              f"exceeds {PORTFOLIO_DRAWDOWN_PAUSE_THRESHOLD*100:.0f}% threshold")
        print(f"  [CIRCUIT BREAKER] PAUSED — portfolio avg drawdown {avg_unrealized*100:+.2f}%")
        print(f"    New entries blocked until {pause_until}")
    else:
        # Check if an existing pause has expired
        if cb.get("paused") and cb.get("paused_until"):
            try:
                pause_end = datetime.fromisoformat(cb["paused_until"])
                if now >= pause_end:
                    cb["paused"] = False
                    cb["paused_until"] = None
                    cb["pause_reason"] = None
                    print(f"  [CIRCUIT BREAKER] Pause expired — new entries allowed")
            except (ValueError, TypeError):
                cb["paused"] = False

    _save_circuit_breaker_state(cb)
    return still_open, force_closed, cb


def detect_regime(vix_data: pd.DataFrame | None, spy_data: pd.DataFrame | None) -> str:
    """
    Market regime detection:
      BULL: SPY > 200d SMA and VIX < 20
      BEAR: SPY < 200d SMA and VIX > 25
      CHOP: otherwise
    """
    if spy_data is None or len(spy_data) < 200:
        return REGIME_CHOP
    if vix_data is None or vix_data.empty:
        return REGIME_CHOP

    spy_close = spy_data["Close"]
    spy_price = float(spy_close.iloc[-1])
    spy_sma200 = float(sma(spy_close, 200).iloc[-1])

    vix_close = vix_data["Close"]
    try:
        vix_last = vix_close.iloc[-1]
        if hasattr(vix_last, 'values'): vix_last = vix_last.values[0]
        vix_val = float(vix_last)
    except:
        vix_val = 20.0 # Default neutral

    if not all(np.isfinite([spy_price, spy_sma200, vix_val])):
        return REGIME_CHOP

    if spy_price > spy_sma200 and vix_val < 20:
        return REGIME_BULL
    elif spy_price < spy_sma200 and vix_val > 25:
        return REGIME_BEAR
    else:
        return REGIME_CHOP


def _get_long_short_balance(active: list[dict]) -> tuple[float, float]:
    """Return (long_pct, short_pct) of active picks."""
    if not active:
        return 0.5, 0.5
    longs = sum(1 for p in active if p.get("direction") == "LONG")
    shorts = sum(1 for p in active if p.get("direction") == "SHORT")
    total = longs + shorts
    if total == 0:
        return 0.5, 0.5
    return longs / total, shorts / total


def _apply_correlation_limits(new_signals: list[dict], active: list[dict]) -> list[dict]:
    """Enforce max picks per correlation group."""
    # Count active picks per correlation group
    group_counts: dict[str, int] = {}
    for p in active:
        grp = _SYMBOL_TO_CORR_GROUP.get(p["symbol"])
        if grp:
            group_counts[grp] = group_counts.get(grp, 0) + 1

    filtered = []
    for sig in new_signals:
        grp = _SYMBOL_TO_CORR_GROUP.get(sig["symbol"])
        if grp:
            if group_counts.get(grp, 0) >= MAX_PER_CORRELATION_GROUP:
                print(f"    Skipped {sig['symbol']} ({sig['strategy']}): "
                      f"correlation group '{grp}' at max ({MAX_PER_CORRELATION_GROUP})")
                continue
            group_counts[grp] = group_counts.get(grp, 0) + 1
        filtered.append(sig)
    return filtered


def _prioritize_short_signals(new_signals: list[dict], active: list[dict],
                              regime: str) -> list[dict]:
    """In BEAR regime, boost short signals to the front if short % is too low."""
    if regime != REGIME_BEAR:
        return new_signals

    _, short_pct = _get_long_short_balance(active)
    if short_pct >= BEAR_MIN_SHORT_PCT:
        return new_signals

    # Sort: SHORT signals first, then by confidence descending
    shorts = [s for s in new_signals if s.get("direction") == "SHORT"]
    longs = [s for s in new_signals if s.get("direction") != "SHORT"]
    shorts.sort(key=lambda s: s.get("confidence", 0), reverse=True)
    longs.sort(key=lambda s: s.get("confidence", 0), reverse=True)

    print(f"  [REGIME] BEAR regime detected, short exposure {short_pct*100:.0f}% < "
          f"{BEAR_MIN_SHORT_PCT*100:.0f}% minimum — prioritizing SHORT signals")
    return shorts + longs


def show_risk_status():
    """Display current portfolio risk metrics without scanning (--status flag)."""
    print(f"\n{'='*60}")
    print(f"MULTI-ASSET SCANNER v{VERSION} — RISK STATUS")
    print(f"{'='*60}")

    # Load state
    active = load_picks(ACTIVE_PICKS_FILE)
    closed = load_picks(CLOSED_PICKS_FILE)
    cb = _load_circuit_breaker_state()

    # Circuit breaker status
    print(f"\n  CIRCUIT BREAKER:")
    if cb.get("paused"):
        print(f"    Status: PAUSED")
        print(f"    Paused until: {cb.get('paused_until', 'unknown')}")
        print(f"    Reason: {cb.get('pause_reason', 'unknown')}")
    else:
        print(f"    Status: ACTIVE (entries allowed)")

    print(f"    Total unrealized PnL: {cb.get('total_unrealized_pnl', 0)*100:+.2f}%")
    print(f"    Avg unrealized PnL:   {cb.get('avg_unrealized_pnl', 0)*100:+.2f}%")
    print(f"    Last check: {cb.get('last_check', 'never')}")

    # Regime
    regime = cb.get("regime", REGIME_CHOP)
    print(f"\n  MARKET REGIME: {regime}")

    # Long/short balance
    long_pct, short_pct = _get_long_short_balance(active)
    print(f"\n  LONG/SHORT BALANCE:")
    print(f"    Long:  {long_pct*100:.0f}% ({sum(1 for p in active if p.get('direction')=='LONG')} picks)")
    print(f"    Short: {short_pct*100:.0f}% ({sum(1 for p in active if p.get('direction')=='SHORT')} picks)")
    if regime == REGIME_BEAR and short_pct < BEAR_MIN_SHORT_PCT:
        print(f"    WARNING: Short exposure below {BEAR_MIN_SHORT_PCT*100:.0f}% minimum for BEAR regime")

    # Correlation group usage
    group_counts: dict[str, list[str]] = {}
    for p in active:
        grp = _SYMBOL_TO_CORR_GROUP.get(p["symbol"])
        if grp:
            group_counts.setdefault(grp, []).append(p["symbol"])
    if group_counts:
        print(f"\n  CORRELATION GROUPS:")
        for grp in sorted(group_counts.keys()):
            syms = group_counts[grp]
            status = "FULL" if len(syms) >= MAX_PER_CORRELATION_GROUP else f"{len(syms)}/{MAX_PER_CORRELATION_GROUP}"
            print(f"    {grp}: [{status}] {', '.join(syms)}")

    # Active picks summary
    print(f"\n  PORTFOLIO:")
    print(f"    Active picks: {len(active)}")
    print(f"    Closed picks: {len(closed)}")
    if active:
        by_cat: dict[str, int] = {}
        for p in active:
            cat = p.get("category", "unknown")
            by_cat[cat] = by_cat.get(cat, 0) + 1
        for cat in sorted(by_cat.keys()):
            print(f"    {cat}: {by_cat[cat]}")

    # Recent auto-closes
    if cb.get("auto_closed"):
        print(f"\n  RECENT AUTO-CLOSES (circuit breaker):")
        for ac in cb["auto_closed"][-5:]:
            print(f"    {ac['symbol']} | PnL: {ac['pnl_pct']*100:+.2f}% | {ac['closed_at']}")

    print(f"\n{'='*60}\n")


def _sanitize(obj):
    """Replace NaN/Inf with None for JSON serialization."""
    if isinstance(obj, dict):
        return {k: _sanitize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize(v) for v in obj]
    if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
        return None
    if hasattr(obj, "item"):
        v = obj.item()
        if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
            return None
        return v
    return obj


def _pick_id(strategy: str, symbol: str, dt: str) -> str:
    return f"{strategy}::{symbol}::{dt}"


def _to_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _pct_distance(a: float, b: float) -> float:
    if a <= 0:
        return float("inf")
    return abs(b - a) / abs(a) * 100.0


def _validate_non_crypto_signal_quality(sig: dict) -> list[str]:
    """
    Validate pre-entry quality for non-crypto signals.
    Returns a list of issue codes; empty list means signal is valid.
    """
    category = str(sig.get("category", "")).lower()
    if category in ("crypto", "meme"):
        return []

    issues = []
    direction = str(sig.get("direction", "")).upper()
    entry = _to_float(sig.get("entry_price"))
    tp = _to_float(sig.get("take_profit"))
    sl = _to_float(sig.get("stop_loss"))
    confidence = _to_float(sig.get("confidence"))
    rr = _to_float(sig.get("risk_reward"))

    if not entry or entry <= 0:
        issues.append("invalid_entry")
        return issues

    if direction not in ("LONG", "SHORT"):
        issues.append("invalid_direction")
        return issues

    if not tp or tp <= 0:
        issues.append("missing_tp")
    if not sl or sl <= 0:
        issues.append("missing_sl")

    if tp and tp > 0:
        if direction == "LONG" and tp <= entry:
            issues.append("tp_wrong_side")
        elif direction == "SHORT" and tp >= entry:
            issues.append("tp_wrong_side")

    if sl and sl > 0:
        if direction == "LONG" and sl >= entry:
            issues.append("sl_wrong_side")
        elif direction == "SHORT" and sl <= entry:
            issues.append("sl_wrong_side")

    if confidence is None or confidence < NON_CRYPTO_MIN_CONFIDENCE:
        issues.append("low_confidence")

    if rr is None or rr < MIN_RR_GATE:
        issues.append("low_rr")

    limits = NON_CRYPTO_DISTANCE_LIMITS.get(category)
    if limits and tp and tp > 0:
        if _pct_distance(entry, tp) > limits["tp_max_pct"]:
            issues.append("tp_too_far")
    if limits and sl and sl > 0:
        if _pct_distance(entry, sl) > limits["sl_max_pct"]:
            issues.append("sl_too_far")

    return issues


def _apply_non_crypto_quality_gate(signals: list[dict]) -> tuple[list[dict], dict[str, int]]:
    """Filter non-crypto signals that fail minimum quality constraints."""
    # Defensive import of pre-emission policy gates (FX session + ATR reach).
    # Fail-open if the policy module is missing/broken so the scanner still runs.
    try:
        from alpha_engine.non_crypto_policy import passes_non_crypto_policy
        _policy_available = True
    except Exception:
        _policy_available = False

    # Map scanner-side `category` strings to the `asset_class` tags the policy
    # gates expect. The scanner pipeline emits signals with `category` only;
    # the policy wants an uppercase `asset_class`.
    _cat_to_asset_class = {
        "forex": "FOREX",
        "commodity": "COMMODITY",
        "futures": "FUTURES",
        "bond": "BOND",
        "etf": "ETF",
        "equity": "EQUITY",
        "stock": "EQUITY",
    }

    kept = []
    rejected: dict[str, int] = {}
    for sig in signals:
        issues = _validate_non_crypto_signal_quality(sig)
        if issues:
            for issue in set(issues):
                rejected[issue] = rejected.get(issue, 0) + 1
            continue

        # Pre-emission policy gates (FX session, ATR reachability).
        if _policy_available:
            try:
                if not sig.get("asset_class"):
                    cat = str(sig.get("category", "")).lower()
                    mapped = _cat_to_asset_class.get(cat)
                    if mapped:
                        sig["asset_class"] = mapped
                ok, reason = passes_non_crypto_policy(sig)
                if not ok:
                    key = reason.split(":", 1)[0] if reason else "policy_blocked"
                    rejected[key] = rejected.get(key, 0) + 1
                    continue
            except Exception:
                # Fail-open on unexpected gate errors.
                pass

        kept.append(sig)
    return kept, rejected


# ---------------------------------------------------------------------------
# Technical Indicators (self-contained — no dependency on alpha_engine)
# ---------------------------------------------------------------------------

def sma(series: pd.Series, period: int) -> pd.Series:
    return series.rolling(period).mean()

def ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()

def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0.0)).rolling(period).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))

def atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(period).mean()

def adx(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    plus_dm = high.diff()
    minus_dm = -low.diff()
    plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0.0)
    minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0.0)
    atr_val = atr(high, low, close, period)
    plus_di = 100 * ema(plus_dm, period) / atr_val.replace(0, np.nan)
    minus_di = 100 * ema(minus_dm, period) / atr_val.replace(0, np.nan)
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    return ema(dx, period)

def bollinger_bands(series: pd.Series, period: int = 20, std_mult: float = 2.0):
    mid = sma(series, period)
    std = series.rolling(period).std()
    return mid, mid + std_mult * std, mid - std_mult * std

def macd(series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
    ema_fast = ema(series, fast)
    ema_slow = ema(series, slow)
    macd_line = ema_fast - ema_slow
    signal_line = ema(macd_line, signal)
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


# ---------------------------------------------------------------------------
# STRATEGIES — Proven, research-backed
# ---------------------------------------------------------------------------

def connors_rsi2(df: pd.DataFrame, symbol: str, info: dict) -> list[dict]:
    """
    Connors RSI-2: Buy when RSI(2) < 10, price above 200d SMA.
    PROVEN: 75.7% WR on SPY (p=6e-6, Sharpe 4.84).
    """
    signals = []
    if len(df) < 200:
        return signals

    close = df["Close"]
    rsi_2 = rsi(close, 2)
    sma_200 = sma(close, 200)
    sma_5 = sma(close, 5)

    rsi_val = float(rsi_2.iloc[-1])
    price = float(close.iloc[-1])
    sma200_val = float(sma_200.iloc[-1])
    sma5_val = float(sma_5.iloc[-1])

    if not all(np.isfinite([rsi_val, price, sma200_val, sma5_val])):
        return signals

    cat = info.get("cat", "stock")
    sl_pct, tp_pct, max_hold = RISK_PARAMS.get(cat, RISK_PARAMS["stock"])

    # BUY: RSI(2) < 10 and price above 200d SMA (uptrend filter)
    if rsi_val < 10 and price > sma200_val:
        atr_val = float(atr(df["High"], df["Low"], close, 14).iloc[-1])
        signals.append({
            "strategy": "connors_rsi2",
            "symbol": symbol,
            "category": cat,
            "direction": "LONG",
            "signal_type": "STRONG_BUY",
            "entry_price": price,
            "take_profit": price * (1 + abs(tp_pct)),
            "stop_loss": price * (1 + sl_pct),  # sl_pct is negative
            "confidence": min(0.95, 0.70 + (10 - rsi_val) * 0.025),
            "risk_reward": abs(tp_pct) / abs(sl_pct),
            "reason": f"RSI(2)={rsi_val:.1f} < 10, price ${price:.2f} > 200d SMA ${sma200_val:.2f}",
            "rsi_at_entry": rsi_val,
            "atr_at_entry": atr_val,
        })

    # SELL: RSI(2) > 90 and price below 200d SMA (downtrend filter)
    if rsi_val > 90 and price < sma200_val:
        atr_val = float(atr(df["High"], df["Low"], close, 14).iloc[-1])
        signals.append({
            "strategy": "connors_rsi2",
            "symbol": symbol,
            "category": cat,
            "direction": "SHORT",
            "signal_type": "STRONG_SELL",
            "entry_price": price,
            "take_profit": price * (1 - abs(tp_pct)),
            "stop_loss": price * (1 - sl_pct),
            "confidence": min(0.95, 0.70 + (rsi_val - 90) * 0.025),
            "risk_reward": abs(tp_pct) / abs(sl_pct),
            "reason": f"RSI(2)={rsi_val:.1f} > 90, price ${price:.2f} < 200d SMA ${sma200_val:.2f}",
            "rsi_at_entry": rsi_val,
            "atr_at_entry": atr_val,
        })

    return signals


def mean_reversion_bollinger(df: pd.DataFrame, symbol: str, info: dict) -> list[dict]:
    """
    Bollinger Band mean reversion: buy below lower band + RSI < 30.
    Well-documented edge on equity indices and forex.
    """
    signals = []
    if len(df) < 50:
        return signals

    close = df["Close"]
    rsi_14 = rsi(close, 14)
    mid, upper, lower = bollinger_bands(close, 20, 2.0)

    price = float(close.iloc[-1])
    rsi_val = float(rsi_14.iloc[-1])
    lower_val = float(lower.iloc[-1])
    upper_val = float(upper.iloc[-1])
    mid_val = float(mid.iloc[-1])

    if not all(np.isfinite([price, rsi_val, lower_val, upper_val])):
        return signals

    cat = info.get("cat", "stock")
    sl_pct, tp_pct, _ = RISK_PARAMS.get(cat, RISK_PARAMS["stock"])

    # BUY: price below lower BB + RSI < 30
    if price < lower_val and rsi_val < 30:
        signals.append({
            "strategy": "mean_reversion_bollinger",
            "symbol": symbol,
            "category": cat,
            "direction": "LONG",
            "signal_type": "BUY",
            "entry_price": price,
            "take_profit": mid_val,  # Target: middle band
            "stop_loss": price * (1 + sl_pct),
            "confidence": min(0.85, 0.60 + (30 - rsi_val) * 0.01),
            "risk_reward": abs(mid_val - price) / abs(price * sl_pct) if abs(price * sl_pct) > 0 else 1.0,
            "reason": f"Price ${price:.2f} < lower BB ${lower_val:.2f}, RSI(14)={rsi_val:.1f}",
            "rsi_at_entry": rsi_val,
        })

    # SELL: price above upper BB + RSI > 70
    if price > upper_val and rsi_val > 70:
        signals.append({
            "strategy": "mean_reversion_bollinger",
            "symbol": symbol,
            "category": cat,
            "direction": "SHORT",
            "signal_type": "SELL",
            "entry_price": price,
            "take_profit": mid_val,
            "stop_loss": price * (1 - sl_pct),
            "confidence": min(0.85, 0.60 + (rsi_val - 70) * 0.01),
            "risk_reward": abs(price - mid_val) / abs(price * sl_pct) if abs(price * sl_pct) > 0 else 1.0,
            "reason": f"Price ${price:.2f} > upper BB ${upper_val:.2f}, RSI(14)={rsi_val:.1f}",
            "rsi_at_entry": rsi_val,
        })

    return signals


def ema_stack_momentum(df: pd.DataFrame, symbol: str, info: dict) -> list[dict]:
    """
    EMA Stack: EMA 9 > 21 > 50 > 200 = strong uptrend.
    Confirmed by ADX > 25 (trend strength).
    """
    signals = []
    if len(df) < 200:
        return signals

    close = df["Close"]
    ema9 = float(ema(close, 9).iloc[-1])
    ema21 = float(ema(close, 21).iloc[-1])
    ema50 = float(ema(close, 50).iloc[-1])
    ema200 = float(ema(close, 200).iloc[-1])
    adx_val = float(adx(df["High"], df["Low"], close, 14).iloc[-1])
    price = float(close.iloc[-1])

    if not all(np.isfinite([ema9, ema21, ema50, ema200, adx_val, price])):
        return signals

    cat = info.get("cat", "stock")
    sl_pct, tp_pct, _ = RISK_PARAMS.get(cat, RISK_PARAMS["stock"])

    # LONG: full bullish stack + ADX confirms trend
    if ema9 > ema21 > ema50 > ema200 and adx_val > 25:
        # Use EMA50 as stop only if it provides real downside protection (below entry)
        dynamic_sl = ema50 if ema50 < price * 0.99 else price * (1 + sl_pct)
        signals.append({
            "strategy": "ema_stack_momentum",
            "symbol": symbol,
            "category": cat,
            "direction": "LONG",
            "signal_type": "BUY",
            "entry_price": price,
            "take_profit": price * (1 + abs(tp_pct)),
            "stop_loss": dynamic_sl,
            "confidence": min(0.85, 0.55 + adx_val * 0.005),
            "risk_reward": abs(price * tp_pct) / abs(price - dynamic_sl) if abs(price - dynamic_sl) > 0 else 1.0,
            "reason": f"EMA stack aligned bullish, ADX={adx_val:.1f}",
            "rsi_at_entry": float(rsi(close, 14).iloc[-1]),
        })

    # SHORT: full bearish stack + ADX confirms
    if ema9 < ema21 < ema50 < ema200 and adx_val > 25:
        dynamic_sl_short = ema50 if ema50 > price * 1.01 else price * (1 - sl_pct)
        signals.append({
            "strategy": "ema_stack_momentum",
            "symbol": symbol,
            "category": cat,
            "direction": "SHORT",
            "signal_type": "SELL",
            "entry_price": price,
            "take_profit": price * (1 - abs(tp_pct)),
            "stop_loss": dynamic_sl_short,
            "confidence": min(0.85, 0.55 + adx_val * 0.005),
            "risk_reward": abs(price * tp_pct) / abs(dynamic_sl_short - price) if abs(dynamic_sl_short - price) > 0 else 1.0,
            "reason": f"EMA stack aligned bearish, ADX={adx_val:.1f}",
            "rsi_at_entry": float(rsi(close, 14).iloc[-1]),
        })

    return signals


def macd_divergence(df: pd.DataFrame, symbol: str, info: dict) -> list[dict]:
    """
    MACD histogram divergence: price makes new low but MACD histogram
    makes higher low = bullish divergence (and vice versa).
    """
    signals = []
    if len(df) < 50:
        return signals

    close = df["Close"]
    macd_line, signal_line, histogram = macd(close)

    price = float(close.iloc[-1])
    hist_now = float(histogram.iloc[-1])
    hist_5ago = float(histogram.iloc[-6]) if len(histogram) > 5 else hist_now

    if not all(np.isfinite([price, hist_now, hist_5ago])):
        return signals

    price_low_now = float(close.iloc[-5:].min())
    price_low_prev = float(close.iloc[-15:-5].min()) if len(close) > 15 else price_low_now

    cat = info.get("cat", "stock")
    sl_pct, tp_pct, _ = RISK_PARAMS.get(cat, RISK_PARAMS["stock"])

    # Bullish divergence: price lower low, MACD higher low
    if price_low_now < price_low_prev and hist_now > hist_5ago and hist_now < 0:
        signals.append({
            "strategy": "macd_divergence",
            "symbol": symbol,
            "category": cat,
            "direction": "LONG",
            "signal_type": "BUY",
            "entry_price": price,
            "take_profit": price * (1 + abs(tp_pct)),
            "stop_loss": price * (1 + sl_pct),
            "confidence": 0.65,
            "risk_reward": abs(tp_pct) / abs(sl_pct),
            "reason": f"Bullish MACD divergence: price lower low, histogram higher low",
            "rsi_at_entry": float(rsi(close, 14).iloc[-1]),
        })

    return signals


def vix_reversal(df: pd.DataFrame, symbol: str, info: dict, vix_data: pd.DataFrame | None = None) -> list[dict]:
    """
    VIX spike reversal: When VIX spikes >20% then drops back, buy equities/ETFs.
    Only applicable to stock and ETF categories.
    """
    signals = []
    cat = info.get("cat", "stock")
    if cat not in ("stock", "etf", "futures"):
        return signals
    if vix_data is None or len(vix_data) < 7:  # need 7 rows: 6 for lagged window + 1
        return signals
    if len(df) < 20:
        return signals

    vix_close = vix_data["Close"]
    vix_now = float(vix_close.iloc[-1].item() if hasattr(vix_close.iloc[-1], 'item') else vix_close.iloc[-1])
    vix_5d_ago = float(vix_close.iloc[-5].item() if hasattr(vix_close.iloc[-5], 'item') else vix_close.iloc[-5])
    vix_peak = float(vix_close.iloc[-5:].max().item() if hasattr(vix_close.iloc[-5:].max(), 'item') else vix_close.iloc[-5:].max())

    if not all(np.isfinite([vix_now, vix_5d_ago, vix_peak])):
        return signals

    # VIX spiked >20% in last 5 days and is now reversing down
    spike = (vix_peak / vix_5d_ago - 1) if vix_5d_ago > 0 else 0
    reversal = vix_now < vix_peak * 0.9  # VIX dropped >10% from peak

    if spike > 0.20 and reversal:
        close = df["Close"]
        price = float(close.iloc[-1])
        sl_pct, tp_pct, _ = RISK_PARAMS.get(cat, RISK_PARAMS["stock"])

        signals.append({
            "strategy": "vix_reversal",
            "symbol": symbol,
            "category": cat,
            "direction": "LONG",
            "signal_type": "BUY",
            "entry_price": price,
            "take_profit": price * (1 + abs(tp_pct)),
            "stop_loss": price * (1 + sl_pct),
            "confidence": min(0.80, 0.55 + spike * 0.5),
            "risk_reward": abs(tp_pct) / abs(sl_pct),
            "reason": f"VIX spike {spike*100:.1f}% then reversed, buying fear",
            "rsi_at_entry": float(rsi(close, 14).iloc[-1]),
        })

    return signals


# ---------------------------------------------------------------------------
# HYPEROPT-TUNED STRATEGIES — use optimal params per symbol from hyperopt results
# ---------------------------------------------------------------------------

# Optimal parameters discovered by hyperopt grid search (2y backtest, walk-forward)
# Only includes configs with WR > 65% and >10 trades
HYPEROPT_OPTIMAL = {
    # Bollinger MR — top performer across all asset classes
    "bollinger_mr": {
        "ZN=F":     {"bb_period": 20, "bb_std": 2.5, "rsi_buy": 25, "rsi_sell": 75},  # 88.9% WR
        "NZDUSD=X": {"bb_period": 20, "bb_std": 1.5, "rsi_buy": 25, "rsi_sell": 75},  # 88.2% WR
        "GBPUSD=X": {"bb_period": 20, "bb_std": 2.0, "rsi_buy": 30, "rsi_sell": 75},  # 85.7% WR
        "EURUSD=X": {"bb_period": 20, "bb_std": 2.0, "rsi_buy": 30, "rsi_sell": 75},  # 85.0% WR
        "AMZN":     {"bb_period": 20, "bb_std": 2.0, "rsi_buy": 25, "rsi_sell": 75},  # 92.3% WR
        "XLF":      {"bb_period": 20, "bb_std": 2.0, "rsi_buy": 25, "rsi_sell": 75},  # 87.5% WR
        "ES=F":     {"bb_period": 20, "bb_std": 2.0, "rsi_buy": 25, "rsi_sell": 75},  # 75.0% WR
        "XLE":      {"bb_period": 20, "bb_std": 2.0, "rsi_buy": 25, "rsi_sell": 75},  # 73.3% WR
        "AUDUSD=X": {"bb_period": 20, "bb_std": 1.5, "rsi_buy": 25, "rsi_sell": 75},  # forex default
        "USDCAD=X": {"bb_period": 20, "bb_std": 1.5, "rsi_buy": 25, "rsi_sell": 75},  # forex default
        "USDCHF=X": {"bb_period": 20, "bb_std": 1.5, "rsi_buy": 25, "rsi_sell": 75},  # forex default
    },
    # Connors RSI-2 — proven on indices and gold
    "connors_rsi2": {
        "GLD":   {"rsi_period": 3, "rsi_buy": 10, "rsi_sell": 85, "sma_trend": 200},  # 92.0% WR
        "GC=F":  {"rsi_period": 3, "rsi_buy": 10, "rsi_sell": 85, "sma_trend": 200},  # 87.5% WR
        "IWM":   {"rsi_period": 3, "rsi_buy": 10, "rsi_sell": 90, "sma_trend": 150},  # 75.0% WR
        "SPY":   {"rsi_period": 2, "rsi_buy": 15, "rsi_sell": 90, "sma_trend": 150},  # 72.9% WR
        "ES=F":  {"rsi_period": 3, "rsi_buy": 15, "rsi_sell": 85, "sma_trend": 150},  # 74.5% WR
        "QQQ":   {"rsi_period": 2, "rsi_buy": 15, "rsi_sell": 85, "sma_trend": 150},  # 71.4% WR
        "SI=F":  {"rsi_period": 2, "rsi_buy": 10, "rsi_sell": 85, "sma_trend": 200},  # 72.2% WR
        "NQ=F":  {"rsi_period": 2, "rsi_buy": 10, "rsi_sell": 85, "sma_trend": 150},  # 66.7% WR
        "V":     {"rsi_period": 3, "rsi_buy": 15, "rsi_sell": 90, "sma_trend": 150},  # 71.0% WR
        "GOOGL": {"rsi_period": 3, "rsi_buy": 10, "rsi_sell": 90, "sma_trend": 200},  # 67.7% WR
    },
    # MACD Divergence — strong on commodities and value stocks
    "macd_div": {
        "GC=F":  {"fast": 12, "slow": 26, "signal": 9, "div_lookback": 10},  # 76.5% WR
        "JPM":   {"fast": 12, "slow": 26, "signal": 9, "div_lookback": 10},  # 82.8% WR
        "XLE":   {"fast": 12, "slow": 26, "signal": 9, "div_lookback": 5},   # 80.0% WR
        "PLTR":  {"fast": 12, "slow": 26, "signal": 9, "div_lookback": 10},  # 81.5% WR
        "SI=F":  {"fast": 12, "slow": 26, "signal": 9, "div_lookback": 10},  # 81.1% WR
        "GLD":   {"fast": 12, "slow": 26, "signal": 9, "div_lookback": 5},   # 73.3% WR
        "RIOT":  {"fast": 12, "slow": 26, "signal": 9, "div_lookback": 10},  # 69.0% WR
        "YM=F":  {"fast": 12, "slow": 26, "signal": 9, "div_lookback": 10},  # 72.0% WR
        "META":  {"fast": 12, "slow": 26, "signal": 9, "div_lookback": 5},   # 67.2% WR
        "SPY":   {"fast": 12, "slow": 26, "signal": 9, "div_lookback": 10},  # 66.7% WR
    },
    # EMA Stack — proven on ETFs and gold
    "ema_stack": {
        "GLD":  {"ema_fast": 9, "ema_mid": 21, "ema_slow": 50, "ema_trend": 200, "adx_threshold": 25},  # 80.4% WR
        "SPY":  {"ema_fast": 8, "ema_mid": 21, "ema_slow": 50, "ema_trend": 200, "adx_threshold": 25},  # 79.3% WR
        "IWM":  {"ema_fast": 8, "ema_mid": 21, "ema_slow": 50, "ema_trend": 200, "adx_threshold": 25},  # 72.7% WR
        "GC=F": {"ema_fast": 9, "ema_mid": 21, "ema_slow": 50, "ema_trend": 200, "adx_threshold": 25},  # 68.2% WR
        "XLK":  {"ema_fast": 8, "ema_mid": 21, "ema_slow": 50, "ema_trend": 200, "adx_threshold": 25},  # 67.3% WR
        "QQQ":  {"ema_fast": 8, "ema_mid": 21, "ema_slow": 50, "ema_trend": 200, "adx_threshold": 25},  # 68.8% WR
    },
}


def hyperopt_bollinger_mr(df: pd.DataFrame, symbol: str, info: dict) -> list[dict]:
    """
    Hyperopt-tuned Bollinger MR: uses per-symbol optimal parameters.
    Backtested WR: 73-92% across asset classes.
    """
    signals = []
    params = HYPEROPT_OPTIMAL.get("bollinger_mr", {}).get(symbol)
    if params is None:
        return signals  # No proven params for this symbol — skip

    if len(df) < 50:
        return signals

    close = df["Close"]
    rsi_14 = rsi(close, 14)
    mid, upper, lower = bollinger_bands(close, params["bb_period"], params["bb_std"])

    price = float(close.iloc[-1])
    rsi_val = float(rsi_14.iloc[-1])
    lower_val = float(lower.iloc[-1])
    upper_val = float(upper.iloc[-1])
    mid_val = float(mid.iloc[-1])

    if not all(np.isfinite([price, rsi_val, lower_val, upper_val, mid_val])):
        return signals

    cat = info.get("cat", "stock")
    sl_pct, tp_pct, _ = RISK_PARAMS.get(cat, RISK_PARAMS["stock"])

    # BUY: price below lower BB + RSI < tuned threshold
    if price < lower_val and rsi_val < params["rsi_buy"]:
        signals.append({
            "strategy": "hyperopt_bollinger_mr",
            "symbol": symbol,
            "category": cat,
            "direction": "LONG",
            "signal_type": "STRONG_BUY",
            "entry_price": price,
            "take_profit": mid_val,  # Target: middle band (proven mean-reversion target)
            "stop_loss": price * (1 + sl_pct),
            "confidence": min(0.92, 0.72 + (params["rsi_buy"] - rsi_val) * 0.015),
            "risk_reward": abs(mid_val - price) / abs(price * sl_pct) if abs(price * sl_pct) > 0 else 1.0,
            "reason": f"HYPEROPT Bollinger MR: price ${price:.2f} < BB_lower ${lower_val:.2f}, RSI={rsi_val:.1f}<{params['rsi_buy']}",
            "rsi_at_entry": rsi_val,
            "hyperopt_params": params,
        })

    # SELL: price above upper BB + RSI > tuned threshold
    if price > upper_val and rsi_val > params["rsi_sell"]:
        signals.append({
            "strategy": "hyperopt_bollinger_mr",
            "symbol": symbol,
            "category": cat,
            "direction": "SHORT",
            "signal_type": "STRONG_SELL",
            "entry_price": price,
            "take_profit": mid_val,
            "stop_loss": price * (1 - sl_pct),
            "confidence": min(0.92, 0.72 + (rsi_val - params["rsi_sell"]) * 0.015),
            "risk_reward": abs(price - mid_val) / abs(price * sl_pct) if abs(price * sl_pct) > 0 else 1.0,
            "reason": f"HYPEROPT Bollinger MR: price ${price:.2f} > BB_upper ${upper_val:.2f}, RSI={rsi_val:.1f}>{params['rsi_sell']}",
            "rsi_at_entry": rsi_val,
            "hyperopt_params": params,
        })

    return signals


def hyperopt_connors_rsi2(df: pd.DataFrame, symbol: str, info: dict) -> list[dict]:
    """
    Hyperopt-tuned Connors RSI-2: per-symbol optimal RSI period and thresholds.
    Backtested WR: 67-92% across indices and commodities.
    """
    signals = []
    params = HYPEROPT_OPTIMAL.get("connors_rsi2", {}).get(symbol)
    if params is None:
        return signals

    if len(df) < 200:
        return signals

    close = df["Close"]
    rsi_val_series = rsi(close, params["rsi_period"])
    sma_trend = sma(close, params["sma_trend"])

    rsi_val = float(rsi_val_series.iloc[-1])
    price = float(close.iloc[-1])
    trend_val = float(sma_trend.iloc[-1])

    if not all(np.isfinite([rsi_val, price, trend_val])):
        return signals

    cat = info.get("cat", "stock")
    sl_pct, tp_pct, _ = RISK_PARAMS.get(cat, RISK_PARAMS["stock"])

    # BUY: RSI below tuned threshold + price above trend SMA
    if rsi_val < params["rsi_buy"] and price > trend_val:
        signals.append({
            "strategy": "hyperopt_connors_rsi2",
            "symbol": symbol,
            "category": cat,
            "direction": "LONG",
            "signal_type": "STRONG_BUY",
            "entry_price": price,
            "take_profit": price * (1 + abs(tp_pct)),
            "stop_loss": price * (1 + sl_pct),
            "confidence": min(0.95, 0.75 + (params["rsi_buy"] - rsi_val) * 0.02),
            "risk_reward": abs(tp_pct) / abs(sl_pct),
            "reason": f"HYPEROPT RSI({params['rsi_period']})={rsi_val:.1f}<{params['rsi_buy']}, price>${trend_val:.0f} SMA({params['sma_trend']})",
            "rsi_at_entry": rsi_val,
            "hyperopt_params": params,
        })

    # SELL: RSI above tuned threshold + price below trend SMA
    if rsi_val > params["rsi_sell"] and price < trend_val:
        signals.append({
            "strategy": "hyperopt_connors_rsi2",
            "symbol": symbol,
            "category": cat,
            "direction": "SHORT",
            "signal_type": "STRONG_SELL",
            "entry_price": price,
            "take_profit": price * (1 - abs(tp_pct)),
            "stop_loss": price * (1 - sl_pct),
            "confidence": min(0.95, 0.75 + (rsi_val - params["rsi_sell"]) * 0.02),
            "risk_reward": abs(tp_pct) / abs(sl_pct),
            "reason": f"HYPEROPT RSI({params['rsi_period']})={rsi_val:.1f}>{params['rsi_sell']}, price<${trend_val:.0f} SMA({params['sma_trend']})",
            "rsi_at_entry": rsi_val,
            "hyperopt_params": params,
        })

    return signals


def hyperopt_macd_div(df: pd.DataFrame, symbol: str, info: dict) -> list[dict]:
    """
    Hyperopt-tuned MACD Divergence: per-symbol lookback windows.
    Backtested WR: 67-83% on commodities and value stocks.
    """
    signals = []
    params = HYPEROPT_OPTIMAL.get("macd_div", {}).get(symbol)
    if params is None:
        return signals

    if len(df) < 50:
        return signals

    close = df["Close"]
    macd_line, signal_line, histogram = macd(close, params["fast"], params["slow"], params["signal"])

    price = float(close.iloc[-1])
    hist_now = float(histogram.iloc[-1])
    lb = params["div_lookback"]
    hist_prev = float(histogram.iloc[-lb-1]) if len(histogram) > lb else hist_now

    if not all(np.isfinite([price, hist_now, hist_prev])):
        return signals

    price_low_now = float(close.iloc[-lb:].min())
    price_low_prev = float(close.iloc[-lb*2:-lb].min()) if len(close) > lb*2 else price_low_now

    cat = info.get("cat", "stock")
    sl_pct, tp_pct, _ = RISK_PARAMS.get(cat, RISK_PARAMS["stock"])

    # Bullish divergence: price lower low, MACD higher low
    if price_low_now < price_low_prev and hist_now > hist_prev and hist_now < 0:
        signals.append({
            "strategy": "hyperopt_macd_div",
            "symbol": symbol,
            "category": cat,
            "direction": "LONG",
            "signal_type": "BUY",
            "entry_price": price,
            "take_profit": price * (1 + abs(tp_pct)),
            "stop_loss": price * (1 + sl_pct),
            "confidence": 0.72,
            "risk_reward": abs(tp_pct) / abs(sl_pct),
            "reason": f"HYPEROPT MACD div (lb={lb}): price lower low, histogram higher low",
            "rsi_at_entry": float(rsi(close, 14).iloc[-1]),
            "hyperopt_params": params,
        })

    return signals


def extreme_oversold_bounce(df: pd.DataFrame, symbol: str, info: dict) -> list[dict]:
    """
    Extreme Oversold Bounce: RSI(2) < 5 + price below BB lower band.
    NO trend filter — works in selloffs. Tight TP (1-3%), tight SL.
    Research: Connors & Alvarez "Short Term Trading Strategies That Work" —
    buying at RSI(2)<5 has 85%+ WR with 1-3 day holding period.
    """
    signals = []
    if len(df) < 50:
        return signals

    close = df["Close"]
    rsi2 = float(rsi(close, 2).iloc[-1])
    rsi14 = float(rsi(close, 14).iloc[-1])
    price = float(close.iloc[-1])
    mid, upper, lower = bollinger_bands(close, 20, 2.0)
    lower_val = float(lower.iloc[-1])
    mid_val = float(mid.iloc[-1])

    if not all(np.isfinite([rsi2, rsi14, price, lower_val, mid_val])):
        return signals

    cat = info.get("cat", "stock")

    # Tighter risk params for bounce trades
    BOUNCE_RISK = {
        "futures": (-0.02, 0.03, 3),
        "stock":   (-0.025, 0.04, 3),
        "forex":   (-0.015, 0.02, 3),
        "etf":     (-0.02, 0.035, 3),
        "penny":   (-0.05, 0.08, 3),
    }
    sl_pct, tp_pct, max_hold = BOUNCE_RISK.get(cat, BOUNCE_RISK["stock"])

    # EXTREME OVERSOLD: RSI(2) < 5 AND price near/below lower BB (within 1%)
    if rsi2 < 5 and price < lower_val * 1.01:
        # Confidence scales with how extreme the oversold is
        conf = min(0.90, 0.70 + (5 - rsi2) * 0.04 + (lower_val - price) / price * 10)
        # TP = minimum of fixed TP or middle band (whichever is closer)
        tp_price = min(price * (1 + abs(tp_pct)), mid_val)

        signals.append({
            "strategy": "extreme_oversold_bounce",
            "symbol": symbol,
            "category": cat,
            "direction": "LONG",
            "signal_type": "STRONG_BUY",
            "entry_price": price,
            "take_profit": tp_price,
            "stop_loss": price * (1 + sl_pct),
            "confidence": conf,
            "risk_reward": abs(tp_price - price) / abs(price * sl_pct) if abs(price * sl_pct) > 0 else 1.0,
            "reason": f"EXTREME OVERSOLD: RSI(2)={rsi2:.1f}<5, price ${price:.2f} < BB_lower ${lower_val:.2f}, RSI(14)={rsi14:.1f}",
            "rsi_at_entry": rsi14,
            "max_hold_days": max_hold,
        })

    # MODERATE OVERSOLD: RSI(2) < 10 AND price below lower BB AND RSI(14) < 35
    elif rsi2 < 10 and price < lower_val and rsi14 < 35:
        tp_price = min(price * (1 + abs(tp_pct)), mid_val)
        signals.append({
            "strategy": "extreme_oversold_bounce",
            "symbol": symbol,
            "category": cat,
            "direction": "LONG",
            "signal_type": "BUY",
            "entry_price": price,
            "take_profit": tp_price,
            "stop_loss": price * (1 + sl_pct),
            "confidence": min(0.80, 0.60 + (10 - rsi2) * 0.02),
            "risk_reward": abs(tp_price - price) / abs(price * sl_pct) if abs(price * sl_pct) > 0 else 1.0,
            "reason": f"OVERSOLD BOUNCE: RSI(2)={rsi2:.1f}<10, price ${price:.2f} < BB ${lower_val:.2f}, RSI(14)={rsi14:.1f}",
            "rsi_at_entry": rsi14,
            "max_hold_days": max_hold,
        })

    return signals


def rsi_overbought_short(df: pd.DataFrame, symbol: str, info: dict) -> list[dict]:
    """RSI overbought SHORT — mirror of proven oversold LONG edge.

    If RSI(2)<5 LONG has Sharpe 1.46 and 60.9% WR, the mirror
    RSI(2)>95 SHORT works in confirmed downtrends (below SMA200).
    Triple confirmation: RSI(2)>95 + below SMA200 + RSI(14)>65.
    """
    signals = []
    if len(df) < 200:
        return signals

    cat = info.get("cat", "stock")
    if cat == "penny":
        return signals  # Skip penny — hard to borrow

    close = df["Close"]
    price = float(close.iloc[-1])
    rsi2 = float(rsi(close, 2).iloc[-1])
    rsi14 = float(rsi(close, 14).iloc[-1])
    sma200_val = float(sma(close, 200).iloc[-1])
    mid, upper, _ = bollinger_bands(close, 20, 2.0)
    upper_val = float(upper.iloc[-1])
    mid_val = float(mid.iloc[-1])

    if not all(np.isfinite([rsi2, rsi14, price, sma200_val, upper_val, mid_val])):
        return signals

    SHORT_RISK = {
        "futures": (-0.03, 0.02, 3),
        "stock":   (-0.04, 0.025, 3),
        "forex":   (-0.02, 0.015, 3),
        "etf":     (-0.035, 0.02, 3),
    }
    sl_pct, tp_pct, max_hold = SHORT_RISK.get(cat, SHORT_RISK["stock"])

    # SHORT: RSI(2) > 95 + price below SMA(200) + RSI(14) > 65
    if rsi2 > 95 and price < sma200_val and rsi14 > 65:
        conf = min(0.90, 0.70 + (rsi2 - 95) * 0.04)
        if price > upper_val:
            conf += 0.05  # Above upper BB in downtrend = strong fade

        tp_price = max(price * (1 - abs(tp_pct)), mid_val)
        sl_price = price * (1 + abs(sl_pct))

        signals.append({
            "strategy": "rsi_overbought_short",
            "symbol": symbol,
            "category": cat,
            "direction": "SHORT",
            "signal_type": "STRONG_SELL",
            "entry_price": price,
            "take_profit": tp_price,
            "stop_loss": sl_price,
            "confidence": conf,
            "risk_reward": abs(price - tp_price) / abs(sl_price - price) if abs(sl_price - price) > 0 else 1.0,
            "reason": f"RSI OVERBOUGHT SHORT: RSI(2)={rsi2:.1f}>95, below SMA200, RSI(14)={rsi14:.1f}",
            "rsi_at_entry": rsi14,
            "max_hold_days": max_hold,
        })

    return signals


def bb_mean_reversion_forex(df: pd.DataFrame, symbol: str, info: dict) -> list[dict]:
    """
    Bollinger Band mean-reversion for forex in CHOP regimes.
    Replaces macd_divergence for forex — ranging markets suit BB MR.
    Entry: price at lower/upper BB + RSI(14) confirmation.
    Exit: BB middle band (mean reversion target).
    """
    signals = []
    cat = info.get("cat", "stock")
    if cat != "forex":
        return signals  # Only for forex pairs

    if len(df) < 30:
        return signals

    close = df["Close"]
    price = float(close.iloc[-1])
    if not np.isfinite(price) or price <= 0:
        return signals

    # BB(20, 2.0)
    bb_mid = close.rolling(20).mean()
    bb_std = close.rolling(20).std()
    bb_upper = bb_mid + 2.0 * bb_std
    bb_lower = bb_mid - 2.0 * bb_std

    mid_val = float(bb_mid.iloc[-1])
    upper_val = float(bb_upper.iloc[-1])
    lower_val = float(bb_lower.iloc[-1])
    band_width = upper_val - lower_val

    if not all(np.isfinite([mid_val, upper_val, lower_val])) or band_width <= 0:
        return signals

    rsi14 = float(rsi(close, 14).iloc[-1])
    if not np.isfinite(rsi14):
        return signals

    sl_pct, tp_pct, max_hold = RISK_PARAMS.get(cat, RISK_PARAMS["stock"])

    # LONG: price at/below lower BB + RSI(14) < 35
    if price <= lower_val and rsi14 < 35:
        conf = min(0.85, 0.60 + (35 - rsi14) * 0.01)
        tp_price = mid_val  # Target: mean reversion to middle band
        sl_price = price - 1.5 * band_width  # 1.5x band width below entry

        signals.append({
            "strategy": "bb_mean_reversion_forex",
            "symbol": symbol,
            "category": cat,
            "direction": "LONG",
            "signal_type": "BUY",
            "entry_price": price,
            "take_profit": tp_price,
            "stop_loss": sl_price,
            "confidence": conf,
            "risk_reward": abs(tp_price - price) / abs(price - sl_price) if abs(price - sl_price) > 0 else 1.0,
            "reason": f"BB MR Forex LONG: price at lower BB, RSI(14)={rsi14:.1f}<35",
            "rsi_at_entry": rsi14,
            "max_hold_days": max_hold,
        })

    # SHORT: price at/above upper BB + RSI(14) > 65
    if price >= upper_val and rsi14 > 65:
        conf = min(0.85, 0.60 + (rsi14 - 65) * 0.01)
        tp_price = mid_val  # Target: mean reversion to middle band
        sl_price = price + 1.5 * band_width  # 1.5x band width above entry

        signals.append({
            "strategy": "bb_mean_reversion_forex",
            "symbol": symbol,
            "category": cat,
            "direction": "SHORT",
            "signal_type": "SELL",
            "entry_price": price,
            "take_profit": tp_price,
            "stop_loss": sl_price,
            "confidence": conf,
            "risk_reward": abs(price - tp_price) / abs(sl_price - price) if abs(sl_price - price) > 0 else 1.0,
            "reason": f"BB MR Forex SHORT: price at upper BB, RSI(14)={rsi14:.1f}>65",
            "rsi_at_entry": rsi14,
            "max_hold_days": max_hold,
        })

    return signals


# ---------------------------------------------------------------------------
# Keltner Compression Expansion — PROVEN 72.9% WR (p=0.0015)
# Ported from battleground/incubator. Parameters from Antigravity's audit:
# EMA(20), ATR(14)x1.5, BB SMA(20)/StdDev(2.0), volume>1.3x, HMA trend filter
# TP: 1.5x ATR, SL: 1.0x ATR, max hold 8 bars (32h on 4h)
# ---------------------------------------------------------------------------

def _hma(series: pd.Series, period: int = 21) -> pd.Series:
    """Hull Moving Average — lag-reduced trend filter."""
    half = max(1, period // 2)
    sqrt_n = max(1, int(period ** 0.5))
    wma_half = series.ewm(span=half, adjust=False).mean()
    wma_full = series.ewm(span=period, adjust=False).mean()
    raw = 2 * wma_half - wma_full
    return raw.ewm(span=sqrt_n, adjust=False).mean()


def keltner_compression_expansion(df: pd.DataFrame, symbol: str, info: dict) -> list[dict]:
    """
    Keltner Compression Expansion: BB squeezes inside KC, then breakout with volume.
    PROVEN: 72.9% WR on BTC (48 trades, p=0.0015), 66.7% on SOL (36 trades, p=0.0455).
    Ported from battleground's statistically proven implementation.

    Entry conditions:
    1. Bollinger Bands inside Keltner Channel (compression/squeeze)
    2. Price breaks out of KC in direction of HMA trend
    3. Volume > 1.3x 20-period median

    Parameters (Antigravity-verified):
    - KC: EMA(20), ATR(14) x 1.5
    - BB: SMA(20), StdDev(2.0)
    - TP: 1.5x ATR(14) from entry
    - SL: 1.0x ATR(14) from entry
    """
    signals = []
    if len(df) < 80:
        return signals

    close = df["Close"]
    high = df["High"]
    low = df["Low"]
    vol = df["Volume"] if "Volume" in df.columns else None

    price = float(close.iloc[-1])

    # Keltner Channel: EMA(20) ± 1.5 * ATR(14)
    kc_ema = ema(close, 20)
    atr14 = atr(high, low, close, 14)
    kc_upper = kc_ema + 1.5 * atr14
    kc_lower = kc_ema - 1.5 * atr14

    # Bollinger Bands: SMA(20), StdDev(2.0)
    bb_mid, bb_upper, bb_lower = bollinger_bands(close, 20, 2.0)

    # Check squeeze: BB inside KC (previous bar — squeeze must exist before breakout)
    bb_up_prev = float(bb_upper.iloc[-2])
    bb_lo_prev = float(bb_lower.iloc[-2])
    kc_up_prev = float(kc_upper.iloc[-2])
    kc_lo_prev = float(kc_lower.iloc[-2])

    squeeze = bb_up_prev < kc_up_prev and bb_lo_prev > kc_lo_prev

    if not squeeze:
        return signals

    kc_up_now = float(kc_upper.iloc[-1])
    kc_lo_now = float(kc_lower.iloc[-1])
    atr_now = float(atr14.iloc[-1])

    if not all(np.isfinite([price, kc_up_now, kc_lo_now, atr_now])) or atr_now <= 0:
        return signals

    # Volume confirmation: > 1.3x 20-period median
    vol_ok = True
    if vol is not None and len(vol) >= 20:
        vol_now = float(vol.iloc[-1])
        vol_median = float(vol.rolling(20).median().iloc[-1])
        if np.isfinite(vol_now) and np.isfinite(vol_median) and vol_median > 0:
            vol_ok = vol_now > 1.3 * vol_median
        else:
            vol_ok = True  # pass if no volume data

    if not vol_ok:
        return signals

    # HMA trend filter
    hma_val = _hma(close, 21)
    hma_rising = float(hma_val.iloc[-1]) > float(hma_val.iloc[-2])

    cat = info.get("cat", "stock")

    # Time-of-day gate: UTC 05:00-13:00 (highest WR window per Antigravity audit)
    from datetime import datetime as dt_cls, timezone as tz_cls
    now_utc = dt_cls.now(tz_cls.utc)
    in_optimal_window = 5 <= now_utc.hour <= 13

    # LONG: price breaks above KC upper + HMA rising
    if price > kc_up_now and hma_rising:
        conf = min(0.95, 0.65 + (price - kc_up_now) / (atr_now + 1e-12) * 0.15)
        if in_optimal_window:
            conf = min(0.95, conf + 0.05)  # boost confidence in optimal window
        tp_price = price + 1.5 * atr_now
        sl_price = price - 1.0 * atr_now
        rr = 1.5  # fixed 1.5:1 R:R

        signals.append({
            "strategy": "keltner_compression_expansion",
            "symbol": symbol,
            "category": cat,
            "direction": "LONG",
            "signal_type": "BUY",
            "entry_price": price,
            "take_profit": round(tp_price, 6),
            "stop_loss": round(sl_price, 6),
            "confidence": round(conf, 3),
            "risk_reward": rr,
            "reason": f"Keltner squeeze breakout UP: price ${price:.2f} > KC upper ${kc_up_now:.2f}, "
                       f"HMA rising, vol OK, ATR={atr_now:.2f}",
            "atr_at_entry": round(atr_now, 6),
            "squeeze_detected": True,
            "optimal_window": in_optimal_window,
        })

    # SHORT: price breaks below KC lower + HMA falling
    elif price < kc_lo_now and not hma_rising:
        conf = min(0.95, 0.65 + (kc_lo_now - price) / (atr_now + 1e-12) * 0.15)
        if in_optimal_window:
            conf = min(0.95, conf + 0.05)
        tp_price = price - 1.5 * atr_now
        sl_price = price + 1.0 * atr_now
        rr = 1.5

        signals.append({
            "strategy": "keltner_compression_expansion",
            "symbol": symbol,
            "category": cat,
            "direction": "SHORT",
            "signal_type": "SELL",
            "entry_price": price,
            "take_profit": round(tp_price, 6),
            "stop_loss": round(sl_price, 6),
            "confidence": round(conf, 3),
            "risk_reward": rr,
            "reason": f"Keltner squeeze breakdown: price ${price:.2f} < KC lower ${kc_lo_now:.2f}, "
                       f"HMA falling, vol OK, ATR={atr_now:.2f}",
            "atr_at_entry": round(atr_now, 6),
            "squeeze_detected": True,
            "optimal_window": in_optimal_window,
        })

    return signals


# Strategy registry — HYPEROPT-TUNED strategies FIRST (higher priority)
STRATEGIES = {
    "keltner_compression_expansion": keltner_compression_expansion,  # PROVEN: 72.9% WR, p=0.0015
    "extreme_oversold_bounce": extreme_oversold_bounce,
    "hyperopt_bollinger_mr": hyperopt_bollinger_mr,
    "hyperopt_connors_rsi2": hyperopt_connors_rsi2,
    "hyperopt_macd_div": hyperopt_macd_div,
    "connors_rsi2": connors_rsi2,
    "mean_reversion_bollinger": mean_reversion_bollinger,
    "ema_stack_momentum": ema_stack_momentum,
    "macd_divergence": macd_divergence,  # Disabled for forex via regime filter in scan()
    "rsi_overbought_short": rsi_overbought_short,
    "bb_mean_reversion_forex": bb_mean_reversion_forex,
}

# VIX strategies — RE-ENABLED as cross-asset variant
# vix_spike_reversal hits 72% WR on equities (banned in crypto only).
# The vix_reversal function already filters to stock/etf/futures categories.
VIX_STRATEGIES = {
    "vix_reversal": vix_reversal,  # RE-ENABLED: 72% WR on equities (CANDIDATE)
}


# ---------------------------------------------------------------------------
# Data fetching — with failover sources
# ---------------------------------------------------------------------------

# Failover API keys (from environment or defaults)
ALPHA_VANTAGE_KEY = os.environ.get("ALPHA_VANTAGE_KEY", "")
TWELVE_DATA_KEY = os.environ.get("TWELVE_DATA_KEY", "")
POLYGON_KEY = os.environ.get("POLYGON_API_KEY", "")


def _yf_download_with_retry(tickers: str, period: str = "1y", interval: str = "1d",
                            group_by=None, max_retries: int = 3,
                            label: str = "yfinance") -> pd.DataFrame | None:
    """Execute a yf.download with exponential backoff retry.

    Retries up to *max_retries* times with delays of 2s, 4s, 8s … before
    giving up and returning None.  This prevents stale signals caused by
    transient Yahoo Finance API failures.
    """
    base_delay = 2  # seconds
    last_err = None

    for attempt in range(1, max_retries + 1):
        try:
            raw = yf.download(tickers, period=period, interval=interval,
                              group_by=group_by,
                              auto_adjust=True, threads=True, progress=False)
            if raw is not None and not raw.empty:
                return raw
            # Empty response – treat as transient failure and retry
            last_err = "empty response"
        except Exception as e:
            last_err = e

        if attempt < max_retries + 1:
            delay = base_delay * (2 ** (attempt - 1))  # 2, 4, 8
            print(f"    [{label}] Attempt {attempt}/{max_retries} failed ({last_err}), "
                  f"retrying in {delay}s...")
            time.sleep(delay)

    print(f"    [{label}] All {max_retries} attempts failed ({last_err})")
    return None


def _fetch_yfinance(symbols: dict, period: str = "1y", interval: str = "1d") -> dict[str, pd.DataFrame]:
    """Primary data source: yfinance (Yahoo Finance) with retry + backoff."""
    tickers = " ".join(symbols.keys())
    print(f"    [yfinance] Fetching {len(symbols)} symbols...")

    raw = _yf_download_with_retry(
        tickers, period=period, interval=interval,
        group_by="ticker" if len(symbols) > 1 else None,
        max_retries=3, label="yfinance",
    )

    if raw is None or raw.empty:
        print("    [yfinance] WARNING: returning None after retries — data is stale")
        return {}

    data = {}
    if len(symbols) == 1:
        sym = list(symbols.keys())[0]
        if not raw.empty and len(raw) > 20:
            data[sym] = raw.dropna()
    else:
        for sym in symbols:
            try:
                if sym in raw.columns.get_level_values(0):
                    df = raw[sym].dropna()
                    if len(df) > 20:
                        data[sym] = df
            except (KeyError, TypeError):
                pass

    return data


def _yf_ticker_to_av(symbol: str) -> str:
    """Convert yfinance ticker to Alpha Vantage format."""
    if symbol.endswith("=F"):
        return symbol  # AV doesn't support futures well
    if symbol.endswith("=X"):
        # EURUSD=X -> from_currency=EUR, to_currency=USD
        return symbol  # Special handling in _fetch_alpha_vantage_single
    return symbol


def _fetch_alpha_vantage_single(symbol: str, info: dict) -> pd.DataFrame | None:
    """Fallback 1: Alpha Vantage free API (5 calls/min, 500/day)."""
    if not ALPHA_VANTAGE_KEY:
        return None

    import urllib.request
    cat = info.get("cat", "stock")

    try:
        if cat == "forex":
            # Forex uses FX_DAILY
            pair = symbol.replace("=X", "")
            from_c, to_c = pair[:3], pair[3:]
            url = (f"https://www.alphavantage.co/query?function=FX_DAILY"
                   f"&from_symbol={from_c}&to_symbol={to_c}"
                   f"&outputsize=full&apikey={ALPHA_VANTAGE_KEY}")
            data_key = "Time Series FX (Daily)"
        elif cat == "futures":
            return None  # AV doesn't support futures
        else:
            url = (f"https://www.alphavantage.co/query?function=TIME_SERIES_DAILY"
                   f"&symbol={symbol}&outputsize=full&apikey={ALPHA_VANTAGE_KEY}")
            data_key = "Time Series (Daily)"

        req = urllib.request.Request(url, headers={"User-Agent": "MultiAssetScanner/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw = json.loads(resp.read())

        if data_key not in raw:
            return None

        ts = raw[data_key]
        rows = []
        for date_str, vals in ts.items():
            rows.append({
                "Date": pd.Timestamp(date_str),
                "Open": float(vals.get("1. open", 0)),
                "High": float(vals.get("2. high", 0)),
                "Low": float(vals.get("3. low", 0)),
                "Close": float(vals.get("4. close", 0)),
                "Volume": float(vals.get("5. volume", 0)) if "5. volume" in vals else 0,
            })

        if len(rows) < 20:
            return None

        df = pd.DataFrame(rows).set_index("Date").sort_index()
        # Limit to last 252 trading days
        return df.tail(252)

    except Exception as e:
        print(f"    [alpha_vantage] {symbol} failed: {e}")
        return None


def _fetch_twelve_data_single(symbol: str, info: dict) -> pd.DataFrame | None:
    """Fallback 2: Twelve Data API (800 calls/day free)."""
    if not TWELVE_DATA_KEY:
        return None

    import urllib.request
    cat = info.get("cat", "stock")

    try:
        clean_sym = symbol.replace("=F", "").replace("=X", "")
        if cat == "forex":
            clean_sym = f"{clean_sym[:3]}/{clean_sym[3:]}"

        url = (f"https://api.twelvedata.com/time_series?"
               f"symbol={clean_sym}&interval=1day&outputsize=252"
               f"&apikey={TWELVE_DATA_KEY}")

        req = urllib.request.Request(url, headers={"User-Agent": "MultiAssetScanner/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw = json.loads(resp.read())

        if raw.get("status") != "ok" or "values" not in raw:
            return None

        rows = []
        for v in raw["values"]:
            rows.append({
                "Date": pd.Timestamp(v["datetime"]),
                "Open": float(v["open"]),
                "High": float(v["high"]),
                "Low": float(v["low"]),
                "Close": float(v["close"]),
                "Volume": float(v.get("volume", 0)),
            })

        if len(rows) < 20:
            return None

        return pd.DataFrame(rows).set_index("Date").sort_index()

    except Exception as e:
        print(f"    [twelve_data] {symbol} failed: {e}")
        return None


def _fetch_polygon_single(symbol: str, info: dict) -> pd.DataFrame | None:
    """Fallback 3: Polygon.io API (5 calls/min free)."""
    if not POLYGON_KEY:
        return None

    import urllib.request
    cat = info.get("cat", "stock")

    try:
        clean_sym = symbol.replace("=F", "").replace("=X", "")
        if cat == "forex":
            clean_sym = f"C:{clean_sym}"

        end = datetime.now().strftime("%Y-%m-%d")
        start = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")

        url = (f"https://api.polygon.io/v2/aggs/ticker/{clean_sym}/range/1/day"
               f"/{start}/{end}?adjusted=true&sort=asc&apiKey={POLYGON_KEY}")

        req = urllib.request.Request(url, headers={"User-Agent": "MultiAssetScanner/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw = json.loads(resp.read())

        if raw.get("resultsCount", 0) < 20:
            return None

        rows = []
        for bar in raw["results"]:
            rows.append({
                "Date": pd.Timestamp(bar["t"], unit="ms"),
                "Open": float(bar["o"]),
                "High": float(bar["h"]),
                "Low": float(bar["l"]),
                "Close": float(bar["c"]),
                "Volume": float(bar.get("v", 0)),
            })

        return pd.DataFrame(rows).set_index("Date").sort_index()

    except Exception as e:
        print(f"    [polygon] {symbol} failed: {e}")
        return None


def fetch_data(symbols: dict, period: str = "1y", interval: str = "1d") -> dict[str, pd.DataFrame]:
    """
    Fetch OHLCV data with failover:
      1. yfinance (batch, no API key needed)
      2. Alpha Vantage (individual, free tier)
      3. Twelve Data (individual, free tier)
      4. Polygon.io (individual, free tier)
    """
    print(f"  Fetching {len(symbols)} symbols...")

    # Primary: yfinance batch download
    data = _fetch_yfinance(symbols, period, interval)
    print(f"    [yfinance] Got {len(data)}/{len(symbols)} symbols")

    # Identify missing symbols
    missing = {s: info for s, info in symbols.items() if s not in data}
    if not missing:
        return data

    print(f"    {len(missing)} symbols missing, trying failover APIs...")

    # Failover: try each missing symbol individually
    failover_sources = [
        ("alpha_vantage", _fetch_alpha_vantage_single),
        ("twelve_data", _fetch_twelve_data_single),
        ("polygon", _fetch_polygon_single),
    ]

    for sym, info in missing.items():
        for source_name, fetch_fn in failover_sources:
            df = fetch_fn(sym, info)
            if df is not None and len(df) > 20:
                data[sym] = df
                print(f"    [{source_name}] Got {sym}")
                break

    still_missing = [s for s in symbols if s not in data]
    if still_missing:
        print(f"    WARNING: {len(still_missing)} symbols have no data: {', '.join(still_missing[:5])}")

    print(f"  Total: {len(data)}/{len(symbols)} symbols with data")
    return data


# ---------------------------------------------------------------------------
# Backtesting engine
# ---------------------------------------------------------------------------

def backtest_strategy(strategy_fn, df: pd.DataFrame, symbol: str, info: dict,
                      lookback_days: int = 252) -> dict:
    """
    Walk-forward backtest: simulate the strategy on historical data.
    Returns stats: trades, wins, losses, win_rate, sharpe, sortino, calmar,
    profit_factor, max_dd, max_dd_duration, avg_win, avg_loss, expectancy.
    """
    cat = info.get("cat", "stock")
    sl_pct, tp_pct, max_hold = RISK_PARAMS.get(cat, RISK_PARAMS["stock"])

    trades = []
    # Slide a window and check signals at each point
    min_window = 210  # Need 200+ bars for SMA200
    if len(df) < min_window + 20:
        return {"trades": 0, "win_rate": 0, "sharpe": 0, "max_dd": 0}

    step = 2  # Check every 2 bars for more trade samples
    for i in range(min_window, len(df) - max_hold, step):
        window = df.iloc[:i]
        signals = strategy_fn(window, symbol, info)

        for sig in signals:
            entry_price = sig["entry_price"]
            direction = sig["direction"]

            # Simulate forward
            future = df.iloc[i:i + max_hold]
            if len(future) < 2:
                continue

            pnl = 0
            exit_price = float(future["Close"].iloc[-1])
            exit_reason = "TIME_EXPIRY"

            for j in range(len(future)):
                bar_high = float(future["High"].iloc[j])
                bar_low = float(future["Low"].iloc[j])

                if direction == "LONG":
                    # Check SL
                    if bar_low <= entry_price * (1 + sl_pct):
                        exit_price = entry_price * (1 + sl_pct)
                        pnl = sl_pct
                        exit_reason = "STOP_LOSS"
                        break
                    # Check TP
                    if bar_high >= entry_price * (1 + abs(tp_pct)):
                        exit_price = entry_price * (1 + abs(tp_pct))
                        pnl = abs(tp_pct)
                        exit_reason = "TAKE_PROFIT"
                        break
                else:  # SHORT
                    if bar_high >= entry_price * (1 - sl_pct):
                        exit_price = entry_price * (1 - sl_pct)
                        pnl = sl_pct  # negative
                        exit_reason = "STOP_LOSS"
                        break
                    if bar_low <= entry_price * (1 - abs(tp_pct)):
                        exit_price = entry_price * (1 - abs(tp_pct))
                        pnl = abs(tp_pct)
                        exit_reason = "TAKE_PROFIT"
                        break

            if pnl == 0:
                # Expired — calculate actual P&L
                if direction == "LONG":
                    pnl = (exit_price / entry_price) - 1
                else:
                    pnl = 1 - (exit_price / entry_price)

            trades.append({
                "entry_price": entry_price,
                "exit_price": exit_price,
                "pnl_pct": pnl,
                "direction": direction,
                "exit_reason": exit_reason,
            })

    if not trades:
        return {"trades": 0, "win_rate": 0, "sharpe": 0, "sortino": 0,
                "calmar": 0, "profit_factor": 0, "max_dd": 0,
                "max_dd_duration": 0, "expectancy": 0}

    wins = sum(1 for t in trades if t["pnl_pct"] > 0)
    losses = sum(1 for t in trades if t["pnl_pct"] <= 0)
    pnls = np.array([t["pnl_pct"] for t in trades])
    win_rate = wins / len(trades) if trades else 0

    mean_pnl = float(np.mean(pnls))
    std_pnl = float(np.std(pnls)) if len(pnls) > 1 else 1.0
    ann = np.sqrt(50)  # annualize assuming ~50 trades/year

    # Sharpe ratio (annualized)
    sharpe = (mean_pnl / std_pnl) * ann if std_pnl > 0 else 0

    # Sortino ratio — only penalizes downside deviation (hedge fund standard)
    downside = pnls[pnls < 0]
    downside_std = float(np.std(downside)) if len(downside) > 1 else 1.0
    sortino = (mean_pnl / downside_std) * ann if downside_std > 0 else 0

    # Profit factor — gross wins / gross losses (>1.5 is strong)
    gross_wins = float(np.sum(pnls[pnls > 0])) if np.any(pnls > 0) else 0
    gross_losses = float(np.abs(np.sum(pnls[pnls < 0]))) if np.any(pnls < 0) else 1.0
    profit_factor = gross_wins / gross_losses if gross_losses > 0 else 0

    # Avg win / avg loss
    avg_win = float(np.mean(pnls[pnls > 0])) if np.any(pnls > 0) else 0
    avg_loss = float(np.mean(pnls[pnls < 0])) if np.any(pnls < 0) else 0

    # Expectancy per trade (Kelly-adjacent)
    expectancy = (win_rate * avg_win) + ((1 - win_rate) * avg_loss)

    # Max drawdown + duration
    equity = np.cumsum(pnls)
    peak = np.maximum.accumulate(equity)
    dd = peak - equity
    max_dd = float(np.max(dd)) if len(dd) > 0 else 0

    # Max drawdown duration (trades in drawdown)
    in_dd = dd > 0
    max_dd_dur = 0
    cur_dur = 0
    for d in in_dd:
        if d:
            cur_dur += 1
            max_dd_dur = max(max_dd_dur, cur_dur)
        else:
            cur_dur = 0

    # Calmar ratio — annualized return / max drawdown
    total_ret = float(np.sum(pnls))
    calmar = (total_ret / max_dd) if max_dd > 0 else 0

    return {
        "trades": len(trades),
        "wins": wins,
        "losses": losses,
        "win_rate": round(win_rate, 4),
        "sharpe": round(float(sharpe), 2),
        "sortino": round(float(sortino), 2),
        "calmar": round(float(calmar), 2),
        "profit_factor": round(float(profit_factor), 2),
        "max_dd": round(max_dd, 4),
        "max_dd_duration": max_dd_dur,
        "avg_win": round(avg_win, 4),
        "avg_loss": round(avg_loss, 4),
        "expectancy": round(float(expectancy), 4),
        "mean_pnl": round(float(mean_pnl), 4),
        "total_return": round(float(total_ret), 4),
        "trade_details": trades[-5:],  # Last 5 trades for inspection
    }


# ---------------------------------------------------------------------------
# Pick management
# ---------------------------------------------------------------------------

def load_picks(filepath: Path) -> list[dict]:
    if filepath.exists():
        with open(filepath) as f:
            return json.load(f)
    return []


def save_picks(picks: list[dict], filepath: Path):
    with open(filepath, "w") as f:
        json.dump(_sanitize(picks), f, indent=2, default=str)


def check_open_picks(active: list[dict], data: dict[str, pd.DataFrame]) -> tuple[list[dict], list[dict]]:
    """Check TP/SL/expiry on open picks. Returns (still_open, newly_closed)."""
    still_open = []
    closed = []

    for pick in active:
        symbol = pick["symbol"]
        df = data.get(symbol)
        if df is None or df.empty:
            still_open.append(pick)
            continue

        current_price = float(df["Close"].iloc[-1])
        pick["current_price"] = current_price

        direction = pick["direction"]
        tp = pick.get("take_profit", 0)
        sl = pick.get("stop_loss", 0)
        cat = pick.get("category", "stock")

        # Calculate unrealized P&L
        entry = pick["entry_price"]
        if direction == "LONG":
            pick["unrealized_pnl_pct"] = (current_price / entry) - 1
        else:
            pick["unrealized_pnl_pct"] = 1 - (current_price / entry)

        # ATR-based trailing stop for ALL asset classes
        # Activate after pick is in profit; trail distance varies by asset class
        # This prevents the overnight reversal problem (e.g., SI=F +2.98% → -0.61%)
        TRAIL_ATR_MULT = {
            "penny": 0.5,    # tight trail for volatile pennies
            "futures": 0.75, # moderate trail for futures
            "forex": 0.5,    # tight trail for forex
            "stock": 1.0,    # wider trail for stocks (more noise)
            "etf": 0.75,     # moderate trail for ETFs
        }
        trail_mult = TRAIL_ATR_MULT.get(cat, 0.75)
        if df is not None and len(df) >= 14:
            atr_series = atr(df["High"], df["Low"], df["Close"], 14)
            atr14 = float(atr_series.iloc[-1])
            if np.isfinite(atr14) and atr14 > 0:
                trail_dist = trail_mult * atr14
                # Track high-water mark for better trailing
                if direction == "LONG":
                    hwm = max(current_price, pick.get("hwm", current_price))
                    pick["hwm"] = hwm
                    if hwm > entry:  # only trail when in profit
                        new_sl = hwm - trail_dist
                        if new_sl > sl:
                            pick["stop_loss"] = new_sl
                            pick["trailing_active"] = True
                            sl = new_sl
                elif direction == "SHORT":
                    lwm = min(current_price, pick.get("hwm", current_price))
                    pick["hwm"] = lwm  # low-water mark stored in hwm field
                    if lwm < entry:  # only trail when in profit
                        new_sl = lwm + trail_dist
                        if sl == 0 or new_sl < sl:
                            pick["stop_loss"] = new_sl
                            pick["trailing_active"] = True
                            sl = new_sl

        # Check TP/SL
        hit_tp = False
        hit_sl = False
        if direction == "LONG":
            hit_tp = current_price >= tp if tp else False
            hit_sl = current_price <= sl if sl else False
        else:
            hit_tp = current_price <= tp if tp else False
            hit_sl = current_price >= sl if sl else False

        # Check time expiry
        _, _, max_hold = RISK_PARAMS.get(cat, RISK_PARAMS["stock"])
        created = datetime.fromisoformat(pick["timestamp"])
        hold_days = (datetime.now(timezone.utc) - created).days
        expired = hold_days >= max_hold

        if hit_tp:
            # PnL-sign guard (loop2 #3 2026-05-08): SHORT/inverse picks can
            # carry a negative unrealized_pnl_pct even when "TP" is hit due to
            # direction-aware computation upstream. Mirror the hit_sl branch
            # below so WON requires actual positive pnl. Cleaned ~1,247
            # historical WON-mislabel rows.
            pick["status"] = "WON" if pick["unrealized_pnl_pct"] > 0 else "LOST"
            pick["exit_price"] = tp
            pick["exit_reason"] = "TAKE_PROFIT"
            pick["pnl_pct"] = pick["unrealized_pnl_pct"]
            pick["closed_at"] = datetime.now(timezone.utc).isoformat()
            closed.append(pick)
        elif hit_sl:
            is_trailing = pick.get("trailing_active", False)
            pick["status"] = "WON" if pick["unrealized_pnl_pct"] > 0 else "LOST"
            pick["exit_price"] = sl
            pick["exit_reason"] = "TRAILING_STOP" if is_trailing else "STOP_LOSS"
            pick["pnl_pct"] = pick["unrealized_pnl_pct"]
            pick["closed_at"] = datetime.now(timezone.utc).isoformat()
            closed.append(pick)
        elif expired:
            pick["status"] = "CLOSED"
            pick["exit_price"] = current_price
            pick["exit_reason"] = "TIME_EXPIRY"
            pick["pnl_pct"] = pick["unrealized_pnl_pct"]
            pick["closed_at"] = datetime.now(timezone.utc).isoformat()
            closed.append(pick)
        else:
            pick["hold_days"] = hold_days
            still_open.append(pick)

    return still_open, closed


# ---------------------------------------------------------------------------
# Main scan
# ---------------------------------------------------------------------------

# Map category to DB-compatible asset_class
_CAT_TO_ASSET_CLASS = {
    "futures": "FUTURES", "commodity": "COMMODITY", "stock": "EQUITY",
    "forex": "FOREX", "etf": "ETF", "penny": "PENNY_STOCK",
    "crypto": "CRYPTO", "meme": "MEMECOIN", "bond": "BOND",
}


def _build_kill_list(closed_archive: list[dict], min_trades: int = 10, min_wr: float = 0.40) -> set[str]:
    """WR kill-switch: auto-disable strategies with WR < min_wr after min_trades closed trades."""
    from collections import defaultdict
    stats: dict[str, dict] = defaultdict(lambda: {"wins": 0, "total": 0})
    for pick in closed_archive:
        strat = pick.get("strategy", "")
        if not strat:
            continue
        stats[strat]["total"] += 1
        if pick.get("status") == "WON":
            stats[strat]["wins"] += 1

    killed = set()
    for strat, s in stats.items():
        if s["total"] >= min_trades:
            wr = s["wins"] / s["total"]
            if wr < min_wr:
                killed.add(strat)
                print(f"  [KILL-SWITCH] {strat}: WR={wr*100:.1f}% ({s['wins']}/{s['total']}) < {min_wr*100:.0f}% — DISABLED")
    return killed


def scan(symbols: dict, data: dict[str, pd.DataFrame],
         vix_data: pd.DataFrame | None = None,
         regime: str = REGIME_CHOP,
         killed_strategies: set[str] | None = None) -> list[dict]:
    """Run all strategies on the given data."""
    all_signals = []
    now_iso = datetime.now(timezone.utc).isoformat()
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    killed = killed_strategies or set()

    # Build macro gate data dict once (gates need SPY + VIX + symbol frames)
    gate_data = dict(data)
    if vix_data is not None:
        gate_data["^VIX"] = vix_data

    # Pre-compute equity macro gate for the whole scan pass
    equity_gate_ok, equity_gate_reason = equity_macro_gate(gate_data) if _MACRO_GATES_AVAILABLE else (True, "gates unavailable")
    if not equity_gate_ok:
        print(f"  [EQUITY MACRO GATE] Blocking all equity LONG signals: {equity_gate_reason}")

    for symbol, info in symbols.items():
        df = data.get(symbol)
        if df is None:
            continue

        cat = info.get("cat", "stock")
        asset_class = _CAT_TO_ASSET_CLASS.get(cat, "EQUITY")

        # Per-symbol forex macro gate
        if cat == "forex" and _MACRO_GATES_AVAILABLE:
            fx_gate_ok, fx_gate_reason = forex_macro_gate(gate_data, symbol)
            if not fx_gate_ok:
                print(f"  [FOREX MACRO GATE] {symbol} blocked: {fx_gate_reason}")
                continue

        for strat_name, strat_fn in STRATEGIES.items():
            # --- WR kill-switch ---
            if strat_name in killed:
                continue
            # --- Inverse-pending: skip entirely (confidence halved at source, but scanner respects kill) ---
            if strat_name in _INVERSE_PENDING:
                continue
            # --- Regime / asset-class filters ---
            # macd_divergence: disable for forex (0/3 winning, no edge)
            if strat_name == "macd_divergence" and cat == "forex":
                continue
            # connors_rsi2: disable for index futures in CHOP (avg -0.38%)
            # Commodity futures (CL, GC, HG) are exempt
            if strat_name == "connors_rsi2" and cat == "futures" and regime == REGIME_CHOP:
                if symbol not in ("GC=F", "HG=F", "SI=F"):  # CL=F removed from universe
                    continue
            try:
                signals = strat_fn(df, symbol, info)
                # ema_stack SHORTs on penny stocks don't work (SOFI -1.31% confirmed)
                if strat_name == "ema_stack_momentum" and cat == "penny":
                    signals = [s for s in signals if s.get("direction") != "SHORT"]
                for sig in signals:
                    # --- Equity macro gate: block LONG equity entries in bear market ---
                    if cat in ("stock", "etf") and sig.get("direction") == "LONG" and not equity_gate_ok:
                        continue

                    # --- VIX confidence adjustment (non-crypto only) ---
                    if cat != "crypto" and _MACRO_GATES_AVAILABLE:
                        vix_mult = vix_confidence_adj(gate_data, strategy_name=strat_name)
                        if vix_mult <= 0.0:
                            continue  # Hard block (should not happen post-relaxation, safety net)
                        if "confidence" in sig:
                            sig["confidence"] = round(sig["confidence"] * vix_mult, 3)

                    sig["id"] = _pick_id(sig["strategy"], symbol, today)
                    sig["timestamp"] = now_iso
                    sig["created_at"] = now_iso
                    sig["status"] = "OPEN"
                    sig["source_system"] = "multi_asset_scanner"
                    sig["asset_class"] = asset_class
                    # Compute risk_reward if not set
                    if "risk_reward" not in sig and sig.get("take_profit") and sig.get("stop_loss"):
                        tp_dist = abs(sig["take_profit"] - sig["entry_price"])
                        sl_dist = abs(sig["stop_loss"] - sig["entry_price"])
                        sig["risk_reward"] = round(tp_dist / sl_dist, 2) if sl_dist > 0 else 1.0
                    all_signals.append(sig)
            except Exception as e:
                print(f"  ERROR: {strat_name} on {symbol}: {e}")

        # --- 600-Variant Integrated Bundle Scan (v1.5) ---
        if _GENERATED_BUNDLE_AVAILABLE:
            for strat_def in ALL_GENERATED_STRATEGIES:
                # Filter by asset class to save compute
                strat_asset = strat_def.get("asset_class", "MULTI")
                if strat_asset != "MULTI" and strat_asset != asset_class:
                    continue
                
                try:
                    gen_signals = run_universal_strategy(strat_def, df)
                    for sig in gen_signals:
                        # Apply ATR-standardized exits from v1.5 milestone
                        # Standard for bundle: ATR x 1.5 (TP) / ATR x 0.75 (SL)
                        if "take_profit" not in sig or "stop_loss" not in sig:
                            atr_series = atr(df["High"], df["Low"], df["Close"], 14)
                            curr_atr = float(atr_series.iloc[-1])
                            if np.isfinite(curr_atr) and curr_atr > 0:
                                entry_p = sig.get("entry_price", float(df["Close"].iloc[-1]))
                                if sig["direction"] == "LONG":
                                    sig["take_profit"] = entry_p + (1.5 * curr_atr)
                                    sig["stop_loss"] = entry_p - (0.75 * curr_atr)
                                else:
                                    sig["take_profit"] = entry_p - (1.5 * curr_atr)
                                    sig["stop_loss"] = entry_p + (0.75 * curr_atr)

                        sig["strategy"] = strat_def["id"]
                        sig["id"] = _pick_id(sig["strategy"], symbol, today)
                        sig["timestamp"] = now_iso
                        sig["created_at"] = now_iso
                        sig["status"] = "OPEN"
                        sig["source_system"] = "multi_asset_scanner"
                        sig["asset_class"] = asset_class
                        
                        # Confidence cap/floor
                        sig["confidence"] = max(0.50, min(0.95, sig.get("confidence", 0.70)))
                        
                        # RR calculation
                        if "risk_reward" not in sig and sig.get("take_profit") and sig.get("stop_loss"):
                            tp_dist = abs(sig["take_profit"] - sig.get("entry_price", float(df["Close"].iloc[-1])))
                            sl_dist = abs(sig["stop_loss"] - sig.get("entry_price", float(df["Close"].iloc[-1])))
                            sig["risk_reward"] = round(tp_dist / sl_dist, 2) if sl_dist > 0 else 1.0
                            
                        # Macro gate check for bundle signals
                        if cat in ("stock", "etf") and sig.get("direction") == "LONG" and not equity_gate_ok:
                            continue
                            
                        all_signals.append(sig)
                except Exception as e:
                    pass # Skip faulty variants

        # VIX-dependent strategies
        for strat_name, strat_fn in VIX_STRATEGIES.items():
            try:
                signals = strat_fn(df, symbol, info, vix_data=vix_data)
                for sig in signals:
                    sig["id"] = _pick_id(sig["strategy"], symbol, today)
                    sig["timestamp"] = now_iso
                    sig["created_at"] = now_iso
                    sig["status"] = "OPEN"
                    sig["source_system"] = "multi_asset_scanner"
                    sig["asset_class"] = asset_class
                    if "risk_reward" not in sig and sig.get("take_profit") and sig.get("stop_loss"):
                        tp_dist = abs(sig["take_profit"] - sig["entry_price"])
                        sl_dist = abs(sig["stop_loss"] - sig["entry_price"])
                        sig["risk_reward"] = round(tp_dist / sl_dist, 2) if sl_dist > 0 else 1.0
                    all_signals.append(sig)
            except Exception as e:
                print(f"  ERROR: {strat_name} on {symbol}: {e}")

    # --- Equity/ETF dedicated strategies (v1.0) ---
    if _EQUITY_STRATEGIES_AVAILABLE:
        try:
            spy_df = data.get("SPY")
            eq_signals = _run_equity_strategies(data, vix_data=vix_data, spy_data=spy_df)
            for sig in eq_signals:
                strat_name = sig.get("strategy", "")
                if strat_name in killed:
                    continue
                cat = sig.get("category", "stock")
                # Equity macro gate: block LONG equity entries in bear market
                if cat in ("stock", "etf") and sig.get("direction") == "LONG" and not equity_gate_ok:
                    continue
                # VIX confidence adjustment
                if _MACRO_GATES_AVAILABLE:
                    vix_mult = vix_confidence_adj(gate_data, strategy_name=strat_name)
                    if vix_mult <= 0.0:
                        continue
                    if "confidence" in sig:
                        sig["confidence"] = round(sig["confidence"] * vix_mult, 3)
                sig["id"] = _pick_id(strat_name, sig.get("symbol", ""), today)
                sig["created_at"] = now_iso
                sig["status"] = "OPEN"
                sig["source_system"] = "multi_asset_scanner"
                # Use category to assign correct asset_class (ETF vs EQUITY)
                sig_cat = sig.get("category", cat)
                sig["asset_class"] = _CAT_TO_ASSET_CLASS.get(sig_cat, "EQUITY")
                if "risk_reward" not in sig and sig.get("take_profit") and sig.get("stop_loss"):
                    tp_dist = abs(sig["take_profit"] - sig["entry_price"])
                    sl_dist = abs(sig["stop_loss"] - sig["entry_price"])
                    sig["risk_reward"] = round(tp_dist / sl_dist, 2) if sl_dist > 0 else 1.0
                all_signals.append(sig)
        except Exception as e:
            print(f"  ERROR: equity_etf_strategies: {e}")

    return all_signals


def main():
    parser = argparse.ArgumentParser(description="Multi-Asset Scanner v" + VERSION)
    parser.add_argument("--futures-only", action="store_true")
    parser.add_argument("--stocks-only", action="store_true")
    parser.add_argument("--forex-only", action="store_true")
    parser.add_argument("--etfs-only", action="store_true")
    parser.add_argument("--backtest", action="store_true", help="Run backtests")
    parser.add_argument("--dry-run", action="store_true", help="Don't save picks")
    parser.add_argument("--status", action="store_true", help="Show risk metrics without scanning")
    args = parser.parse_args()

    # --status: show risk dashboard and exit
    if args.status:
        show_risk_status()
        return

    # Select symbols — multiple flags can be combined (e.g. --futures-only --forex-only)
    any_filter = args.futures_only or args.stocks_only or args.forex_only or args.etfs_only
    if any_filter:
        symbols = {}
        parts = []
        if args.futures_only:
            symbols.update(FUTURES)
            parts.append("futures")
        if args.stocks_only:
            symbols.update(STOCKS)
            parts.append("stocks")
        if args.forex_only:
            symbols.update(FOREX)
            parts.append("forex")
        if args.etfs_only:
            symbols.update(ETFS)
            parts.append("etfs")
        label = "+".join(parts)
    else:
        symbols = dict(ALL_SYMBOLS)
        # Merge equity/ETF strategy symbols for data download
        if _EQUITY_STRATEGIES_AVAILABLE:
            for sym, info in _EQ_SYMBOLS.items():
                if sym not in symbols:
                    symbols[sym] = info
        label = "all"

    start = time.time()
    print(f"\n{'='*60}")
    print(f"MULTI-ASSET SCANNER v{VERSION}")
    print(f"{'='*60}")
    bundle_count = len(ALL_GENERATED_STRATEGIES) if _GENERATED_BUNDLE_AVAILABLE else 0
    eq_count = len(_EQ_STRATEGIES) if _EQUITY_STRATEGIES_AVAILABLE else 0
    cf_count = (len(_CF_STRATEGIES) + len(_CF_VIX_STRATEGIES) + len(_CF_CROSS_STRATEGIES)) if _COMMODITY_FUTURES_AVAILABLE else 0
    print(f"Mode: {label} | Symbols: {len(symbols)} | Strategies: {len(STRATEGIES) + len(VIX_STRATEGIES) + eq_count + cf_count} (+ {bundle_count} variants)")
    print()

    # Fetch data
    print("[1/4] Fetching market data...")
    data = fetch_data(symbols)
    if not data:
        print("FATAL: No data. Aborting.")
        sys.exit(1)

    # Fetch VIX for VIX-dependent strategies (with retry + backoff)
    vix_data = None
    vix_raw = _yf_download_with_retry("^VIX", period="3mo", interval="1d",
                                       max_retries=3, label="VIX")
    if vix_raw is not None and not vix_raw.empty:
        vix_data = vix_raw
        print(f"  VIX data: {len(vix_data)} bars")
    else:
        print("  VIX data unavailable after retries")

    # Detect market regime
    spy_data = data.get("SPY")
    regime = detect_regime(vix_data, spy_data)
    prev_cb = _load_circuit_breaker_state()
    prev_regime = prev_cb.get("regime", REGIME_CHOP)
    if regime != prev_regime:
        print(f"  [REGIME CHANGE] {prev_regime} -> {regime}")
    else:
        print(f"  Market regime: {regime}")

    # Check existing picks
    print("[2/4] Checking open picks...")
    active = load_picks(ACTIVE_PICKS_FILE)
    closed_archive = load_picks(CLOSED_PICKS_FILE)

    if active:
        active, newly_closed = check_open_picks(active, data)
        if newly_closed:
            closed_archive.extend(newly_closed)
            print(f"  Closed {len(newly_closed)} pick(s): " +
                  ", ".join(f"{p['symbol']} {p['exit_reason']}" for p in newly_closed))

    # Run circuit breakers BEFORE scanning for new signals
    print("  Running circuit breakers...")
    if active:
        active, cb_closed, cb_state = check_circuit_breakers(active, data)
        if cb_closed:
            closed_archive.extend(cb_closed)
            print(f"  Circuit breaker closed {len(cb_closed)} pick(s)")
    else:
        cb_state = _load_circuit_breaker_state()

    # THE GREAT PURGE: force-close any remaining forex/penny picks
    purge_cats = {"forex", "penny"}
    purged = [p for p in active if p.get("category") in purge_cats]
    if purged:
        for p in purged:
            current_price = None
            df = data.get(p["symbol"])
            if df is not None and len(df) > 0:
                current_price = float(df["Close"].iloc[-1])
            p["status"] = "CLOSED"
            p["exit_price"] = current_price or p.get("entry_price", 0)
            p["exit_reason"] = "PURGE_FOREX_PENNY"
            p["pnl_pct"] = p.get("unrealized_pnl_pct", 0)
            p["closed_at"] = datetime.now(timezone.utc).isoformat()
            closed_archive.append(p)
        active = [p for p in active if p.get("category") not in purge_cats]
        print(f"  [PURGE] Closed {len(purged)} forex/penny pick(s): " +
              ", ".join(f"{p['symbol']} ({p['pnl_pct']:+.2f}%)" for p in purged))

    # Store regime in circuit breaker state
    cb_state["regime"] = regime
    _save_circuit_breaker_state(cb_state)

    # Check if circuit breaker has paused new entries
    entries_paused = cb_state.get("paused", False)
    if entries_paused:
        print(f"  [CIRCUIT BREAKER] New entries PAUSED until {cb_state.get('paused_until')}")

    # Run backtest if requested
    if args.backtest:
        print("[BACKTEST] Fetching 2-year data for extended backtests...")
        bt_data = fetch_data(symbols, period="2y")
        if not bt_data:
            bt_data = data  # fallback to 1y
        print(f"  Backtest data: {len(bt_data)} symbols, avg {int(np.mean([len(d) for d in bt_data.values()]))} bars")
        print("[BACKTEST] Running walk-forward backtests...")
        results = {}
        for strat_name, strat_fn in STRATEGIES.items():
            for symbol, info in symbols.items():
                df = bt_data.get(symbol)
                if df is None:
                    continue
                key = f"{strat_name}::{symbol}"
                bt = backtest_strategy(strat_fn, df, symbol, info)
                if bt["trades"] > 0:
                    results[key] = bt
                    wr_str = f"{bt['win_rate']*100:.1f}%"
                    print(f"  {key}: {bt['trades']} trades, WR={wr_str}, "
                          f"Sharpe={bt['sharpe']}, Sortino={bt.get('sortino',0)}, "
                          f"PF={bt.get('profit_factor',0)}, MaxDD={bt['max_dd']*100:.1f}%")

        save_picks(results, BACKTEST_FILE)
        print(f"\n  Backtest results saved to {BACKTEST_FILE}")

        # Print summary table
        print(f"\n{'='*70}")
        print(f"  BACKTEST SUMMARY")
        print(f"{'='*70}")
        print(f"  {'Strategy::Symbol':<40} {'Trades':>6} {'WR':>8} {'Sharpe':>8} {'Sortino':>8} {'PF':>6} {'Return':>10}")
        print(f"  {'-'*40} {'-'*6} {'-'*8} {'-'*8} {'-'*8} {'-'*6} {'-'*10}")
        for key in sorted(results.keys()):
            r = results[key]
            print(f"  {key:<40} {r['trades']:>6} {r['win_rate']*100:>7.1f}% {r['sharpe']:>8.2f} {r.get('sortino',0):>8.2f} {r.get('profit_factor',0):>6.2f} {r['total_return']*100:>9.1f}%")

        elapsed = time.time() - start
        print(f"\n  Backtest completed in {elapsed:.1f}s")
        return

    # WR kill-switch: auto-disable strategies with poor forward-test WR
    killed_strategies = _build_kill_list(closed_archive)

    # Scan for new signals
    print(f"[3/4] Scanning {len(data)} symbols with {len(STRATEGIES) + len(VIX_STRATEGIES)} strategies...")

    if entries_paused:
        new_signals = []
        print(f"  Skipping scan — circuit breaker has paused new entries")
    else:
        new_signals = scan(symbols, data, vix_data, regime=regime,
                           killed_strategies=killed_strategies)
        print(f"  Raw signals: {len(new_signals)}")

        # --- Forex-specific strategies (v1.0) ---
        # Run purpose-built forex strategies when forex symbols are in the scan
        forex_syms = {s: info for s, info in symbols.items() if info.get("cat") == "forex"}
        if forex_syms and _FOREX_STRATEGIES_AVAILABLE:
            print(f"  [FOREX] Running {len(_FX_STRATEGIES)} forex-specific strategies "
                  f"on {len(forex_syms)} pairs...")
            # Fetch DXY data for macro filter
            dxy_data = None
            dxy_raw = _yf_download_with_retry(_DXY_TICKER, period="1y", interval="1d",
                                               max_retries=2, label="DXY")
            if dxy_raw is not None and not dxy_raw.empty:
                dxy_data = dxy_raw
                print(f"    DXY data: {len(dxy_data)} bars")
            else:
                print(f"    DXY data unavailable — DXY filter disabled")

            fx_signals = _scan_forex(forex_syms, data, dxy_df=dxy_data,
                                     killed_strategies=killed_strategies,
                                     use_dxy_filter=(dxy_data is not None))
            if fx_signals:
                new_signals.extend(fx_signals)
                print(f"    Forex strategies generated {len(fx_signals)} signal(s)")
            else:
                print(f"    Forex strategies: no signals")

        # --- Commodity & Futures-specific strategies (v1.0) ---
        if _COMMODITY_FUTURES_AVAILABLE:
            cf_count = len(_CF_STRATEGIES) + len(_CF_VIX_STRATEGIES) + len(_CF_CROSS_STRATEGIES)
            cf_syms = {s: info for s, info in symbols.items()
                       if info.get("cat") in ("commodity", "futures")}
            print(f"  [COMMODITY/FUTURES] Running {cf_count} strategies "
                  f"on {len(cf_syms)} symbols...")

            now_iso_cf = datetime.now(timezone.utc).isoformat()
            today_cf = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            cf_signals = []

            # Per-symbol strategies
            for sym, info in cf_syms.items():
                df = data.get(sym)
                if df is None or len(df) < 20:
                    continue
                for strat_name, strat_fn in _CF_STRATEGIES.items():
                    if strat_name in (killed_strategies or set()):
                        continue
                    try:
                        sigs = strat_fn(df, sym, info)
                        for sig in sigs:
                            sig["id"] = _pick_id(sig["strategy"], sym, today_cf)
                            sig["timestamp"] = now_iso_cf
                            sig["created_at"] = now_iso_cf
                            sig["status"] = "OPEN"
                            sig["source_system"] = "multi_asset_scanner"
                            sig["asset_class"] = _CAT_TO_ASSET_CLASS.get(
                                info.get("cat", "commodity"), "COMMODITY")
                            cf_signals.append(sig)
                    except Exception as e:
                        print(f"    ERROR: {strat_name} on {sym}: {e}")

            # VIX-dependent strategies (gold safe haven)
            spy_data_cf = data.get("SPY")
            for sym, info in cf_syms.items():
                df = data.get(sym)
                if df is None:
                    continue
                try:
                    sigs = _gold_safe_haven(df, sym, info,
                                            vix_data=vix_data, spy_data=spy_data_cf)
                    for sig in sigs:
                        sig["id"] = _pick_id(sig["strategy"], sym, today_cf)
                        sig["timestamp"] = now_iso_cf
                        sig["created_at"] = now_iso_cf
                        sig["status"] = "OPEN"
                        sig["source_system"] = "multi_asset_scanner"
                        sig["asset_class"] = _CAT_TO_ASSET_CLASS.get(
                            info.get("cat", "commodity"), "COMMODITY")
                        cf_signals.append(sig)
                except Exception as e:
                    print(f"    ERROR: gold_safe_haven on {sym}: {e}")

            # Dr. Copper (cross-asset: reads copper data, signals on cyclicals)
            copper_data = data.get("HG=F")
            for sym, info in cf_syms.items():
                df = data.get(sym)
                if df is None:
                    continue
                try:
                    sigs = _dr_copper_indicator(df, sym, info, copper_data=copper_data)
                    for sig in sigs:
                        sig["id"] = _pick_id(sig["strategy"], sym, today_cf)
                        sig["timestamp"] = now_iso_cf
                        sig["created_at"] = now_iso_cf
                        sig["status"] = "OPEN"
                        sig["source_system"] = "multi_asset_scanner"
                        sig["asset_class"] = _CAT_TO_ASSET_CLASS.get(
                            info.get("cat", "commodity"), "COMMODITY")
                        cf_signals.append(sig)
                except Exception as e:
                    print(f"    ERROR: dr_copper on {sym}: {e}")

            # Cross-asset strategies (called once, not per-symbol)
            try:
                momentum_sigs = _commodity_momentum(data)
                for sig in momentum_sigs:
                    sig["id"] = _pick_id(sig["strategy"], sig["symbol"], today_cf)
                    sig["timestamp"] = now_iso_cf
                    sig["created_at"] = now_iso_cf
                    sig["status"] = "OPEN"
                    sig["source_system"] = "multi_asset_scanner"
                    sig["asset_class"] = _CAT_TO_ASSET_CLASS.get(
                        sig.get("category", "commodity"), "COMMODITY")
                    cf_signals.append(sig)
            except Exception as e:
                print(f"    ERROR: commodity_momentum: {e}")

            try:
                rotation_sigs = _bond_equity_rotation(data)
                for sig in rotation_sigs:
                    sig["id"] = _pick_id(sig["strategy"], sig["symbol"], today_cf)
                    sig["timestamp"] = now_iso_cf
                    sig["created_at"] = now_iso_cf
                    sig["status"] = "OPEN"
                    sig["source_system"] = "multi_asset_scanner"
                    sig["asset_class"] = _CAT_TO_ASSET_CLASS.get(
                        sig.get("category", "futures"), "FUTURES")
                    cf_signals.append(sig)
            except Exception as e:
                print(f"    ERROR: bond_equity_rotation: {e}")

            # --- NEW cross-asset strategies (v1.1): bond, futures, PM, energy ---
            _new_cross_strategies = [
                ("treasury_yield_curve", _treasury_yield_curve),
                ("credit_spread", _credit_spread_strategy),
                ("duration_rotation", _duration_rotation),
                ("futures_momentum", _futures_momentum),
                ("precious_metals_momentum", _precious_metals_momentum),
                ("energy_sector_rotation", _energy_sector_rotation),
            ]
            for _strat_name, _strat_fn in _new_cross_strategies:
                if _strat_name in (killed_strategies or set()):
                    continue
                try:
                    _sigs = _strat_fn(data)
                    for sig in _sigs:
                        sig["id"] = _pick_id(sig["strategy"], sig["symbol"], today_cf)
                        sig["timestamp"] = now_iso_cf
                        sig["created_at"] = now_iso_cf
                        sig["status"] = "OPEN"
                        sig["source_system"] = "multi_asset_scanner"
                        sig["asset_class"] = _CAT_TO_ASSET_CLASS.get(
                            sig.get("category", "commodity"), "COMMODITY")
                        cf_signals.append(sig)
                except Exception as e:
                    print(f"    ERROR: {_strat_name}: {e}")

            if cf_signals:
                new_signals.extend(cf_signals)
                print(f"    Commodity/futures strategies generated {len(cf_signals)} signal(s)")
            else:
                print(f"    Commodity/futures strategies: no signals")

    # --- Non-crypto quality gate: filter invalid TP/SL/confidence/distance upfront ---
    pre_quality = len(new_signals)
    new_signals, rejected_quality = _apply_non_crypto_quality_gate(new_signals)
    quality_removed = pre_quality - len(new_signals)
    if quality_removed > 0:
        print(f"  [QUALITY GATE] Filtered {quality_removed} non-crypto signals pre-entry")
        for issue, count in sorted(rejected_quality.items(), key=lambda kv: kv[1], reverse=True):
            print(f"    - {issue}: {count}")

    # --- RR Gate: Mercury data shows RR>=1.5 lifts WR 39%->68% ---
    pre_rr = len(new_signals)
    new_signals = [s for s in new_signals if s.get("risk_reward", 0) >= MIN_RR_GATE]
    rr_removed = pre_rr - len(new_signals)
    if rr_removed > 0:
        print(f"  [RR GATE] Filtered {rr_removed} signals with R:R < {MIN_RR_GATE}")

    # Deduplicate against existing picks
    existing_ids = {p["id"] for p in active}
    # Track strategy::symbol pairs to allow different strategies on same symbol
    existing_strat_sym = {(p["strategy"], p["symbol"]) for p in active}
    new_signals = [s for s in new_signals if s["id"] not in existing_ids]
    # Skip only if SAME strategy already has a pick on this symbol
    new_signals = [s for s in new_signals if (s["strategy"], s["symbol"]) not in existing_strat_sym]
    # Max 2 picks per symbol (different strategies)
    sym_counts = {}
    for p in active:
        sym_counts[p["symbol"]] = sym_counts.get(p["symbol"], 0) + 1
    sym_filtered = []
    for s in new_signals:
        if sym_counts.get(s["symbol"], 0) < 2:
            sym_filtered.append(s)
            sym_counts[s["symbol"]] = sym_counts.get(s["symbol"], 0) + 1
    new_signals = sym_filtered
    # Cap strategy concentration: max 10 picks per strategy
    MAX_PER_STRATEGY = 10
    strat_counts = {}
    for p in active:
        st = p.get("strategy", "")
        strat_counts[st] = strat_counts.get(st, 0) + 1
    capped = []
    for s in new_signals:
        st = s.get("strategy", "")
        if strat_counts.get(st, 0) < MAX_PER_STRATEGY:
            capped.append(s)
            strat_counts[st] = strat_counts.get(st, 0) + 1
    new_signals = capped

    # Apply correlation group limits
    new_signals = _apply_correlation_limits(new_signals, active)

    # Prioritize short signals in BEAR regime
    new_signals = _prioritize_short_signals(new_signals, active, regime)

    print(f"  New signals (after dedup + caps + correlation + regime): {len(new_signals)}")

    # Add new picks
    if not args.dry_run and new_signals:
        active.extend(new_signals)
        print(f"  Opened {len(new_signals)} new pick(s)")

    # Save
    print("[4/4] Saving state...")
    if not args.dry_run:
        save_picks(active, ACTIVE_PICKS_FILE)
        save_picks(closed_archive, CLOSED_PICKS_FILE)

    # Report
    elapsed = time.time() - start
    print(f"\n{'='*60}")
    print(f"  SCAN COMPLETE ({elapsed:.1f}s)")
    print(f"{'='*60}")
    print(f"  Active picks: {len(active)}")
    print(f"  Closed picks: {len(closed_archive)}")
    print(f"  New signals:  {len(new_signals)}")
    print(f"  Market regime: {regime}")
    long_pct, short_pct = _get_long_short_balance(active)
    print(f"  Long/Short:   {long_pct*100:.0f}% / {short_pct*100:.0f}%")
    if entries_paused:
        print(f"  Circuit breaker: PAUSED (until {cb_state.get('paused_until', '?')})")
    else:
        print(f"  Circuit breaker: OK")

    if new_signals:
        print(f"\n  NEW SIGNALS:")
        for sig in new_signals:
            print(f"    {sig['direction']:>5} {sig['symbol']:<10} @ ${sig['entry_price']:.2f} "
                  f"| TP ${sig['take_profit']:.2f} SL ${sig['stop_loss']:.2f} "
                  f"| {sig['strategy']} | conf={sig['confidence']:.2f}")

    if active:
        # Group by category
        by_cat = {}
        for p in active:
            cat = p.get("category", "unknown")
            by_cat.setdefault(cat, []).append(p)

        print(f"\n  ACTIVE PICKS BY CLASS:")
        for cat in sorted(by_cat.keys()):
            picks = by_cat[cat]
            print(f"    {cat}: {len(picks)} pick(s)")
            for p in picks:
                pnl = p.get("unrealized_pnl_pct", 0)
                pnl_str = f"{pnl*100:+.2f}%" if pnl else "n/a"
                print(f"      {p['direction']:>5} {p['symbol']:<10} {pnl_str}")

    # Also export in alpha_engine-compatible format for sync_all_picks_to_mysql.py
    alpha_compat = DATA_DIR / "active_picks.json"
    save_picks(active, alpha_compat)
    print(f"\n  Exported {len(active)} picks to {alpha_compat}")


if __name__ == "__main__":
    main()
