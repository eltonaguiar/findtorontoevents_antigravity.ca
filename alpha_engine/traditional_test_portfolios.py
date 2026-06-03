#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NOTE — SNAPSHOT-RESOLVER ARTIFACT (2026-06-03): WR/PF here is inflated by single
daily-snapshot TP/SL resolution (no intrabar OHLC path) — intraday SL touches are missed.
Do not size up on these numbers. See docs/RESOLVER_SNAPSHOT_ARTIFACT_AFFECTED_PORTFOLIOS_2026-06-03.md

Traditional Asset Test Portfolios (5-8)
========================================
Portfolio 5: Forex Carry — JPY crosses with momentum/volatility gates
Portfolio 6: Stocks Dividend — extends PORTFOLIO_A from non_crypto_ab_tester.py
Portfolio 7: All-Weather — Ray Dalio inspired benchmark (buy-and-hold)
Portfolio 8: Copy Trader Forex Best — top 5 forex traders by WR

Each portfolio starts with $10,000 virtual capital.
Tracks NAV, Sharpe, Sortino, max DD, WR, total return, profit factor.
Persists state to data/traditional_portfolio_state.json.
Results to data/traditional_portfolio_results.json.

Usage:
    python -m alpha_engine.traditional_test_portfolios           # run all
    python -m alpha_engine.traditional_test_portfolios --force   # ignore market hours
"""

from __future__ import annotations

import datetime as _dt
import json
import math
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_DIR = Path(__file__).resolve().parent
_DATA_DIR = _DIR / "data"
_STATE_FILE = _DATA_DIR / "traditional_portfolio_state.json"
_RESULTS_FILE = _DATA_DIR / "traditional_portfolio_results.json"
_FOREX_DB_FILE = _DIR.parent / "copy_trader_intel" / "data" / "forex_trader_database.json"

START_CAPITAL = 10_000.0

# ---------------------------------------------------------------------------
# Market-hours check (NYSE 09:30-16:00 ET, weekdays; Forex 24/5)
# ---------------------------------------------------------------------------

def _now_et() -> _dt.datetime:
    """Current time in US/Eastern."""
    try:
        from zoneinfo import ZoneInfo
        return _dt.datetime.now(ZoneInfo("America/New_York"))
    except Exception:
        utc_now = _dt.datetime.now(_dt.timezone.utc)
        return utc_now.astimezone(_dt.timezone(_dt.timedelta(hours=-4)))


def _is_equity_market_hours(now_et: Optional[_dt.datetime] = None) -> bool:
    """NYSE 09:30-16:00 ET, Mon-Fri."""
    et = now_et or _now_et()
    if et.weekday() >= 5:
        return False
    hour, minute = et.hour, et.minute
    if hour < 9 or (hour == 9 and minute < 30):
        return False
    if hour >= 16:
        return False
    return True


def _is_forex_hours(now_et: Optional[_dt.datetime] = None) -> bool:
    """Forex markets open Sun 17:00 ET - Fri 17:00 ET (24/5)."""
    et = now_et or _now_et()
    wd = et.weekday()
    hour = et.hour
    # Closed: Saturday all day, Sunday before 17:00 ET, Friday after 17:00 ET
    if wd == 5:  # Saturday
        return False
    if wd == 6 and hour < 17:  # Sunday before 17:00
        return False
    if wd == 4 and hour >= 17:  # Friday after 17:00
        return False
    return True


def _is_any_market_open(now_et: Optional[_dt.datetime] = None) -> bool:
    et = now_et or _now_et()
    return _is_equity_market_hours(et) or _is_forex_hours(et)


# ---------------------------------------------------------------------------
# Price fetching — 3-source failover (yfinance -> Alpha Vantage -> Yahoo JSON)
# ---------------------------------------------------------------------------

def fetch_traditional_prices(symbols: List[str]) -> Dict[str, float]:
    """Fetch latest prices with 3-source failover chain."""
    prices: Dict[str, float] = {}

    # Attempt 1: yfinance
    try:
        prices = _fetch_yfinance(symbols)
    except Exception:
        pass

    missing = [s for s in symbols if s not in prices or prices[s] <= 0]
    if not missing:
        return prices

    # Attempt 2: Alpha Vantage
    try:
        av = _fetch_alpha_vantage(missing)
        prices.update(av)
    except Exception:
        pass

    missing = [s for s in symbols if s not in prices or prices[s] <= 0]
    if not missing:
        return prices

    # Attempt 3: Yahoo Finance JSON (no library)
    try:
        yh = _fetch_yahoo_json(missing)
        prices.update(yh)
    except Exception:
        pass

    return prices


def _fetch_yfinance(symbols: List[str]) -> Dict[str, float]:
    import yfinance as yf  # type: ignore[import-untyped]
    prices: Dict[str, float] = {}
    tickers = yf.Tickers(" ".join(symbols))
    for sym in symbols:
        try:
            info = tickers.tickers[sym].fast_info
            price = getattr(info, "last_price", None) or getattr(info, "previous_close", None)
            if price and float(price) > 0:
                prices[sym] = round(float(price), 4)
        except Exception:
            continue
    return prices


def _fetch_alpha_vantage(symbols: List[str]) -> Dict[str, float]:
    import requests
    api_key = os.environ.get("ALPHA_VANTAGE_API_KEY", "demo")
    prices: Dict[str, float] = {}
    for sym in symbols:
        try:
            url = (
                f"https://www.alphavantage.co/query"
                f"?function=GLOBAL_QUOTE&symbol={sym}&apikey={api_key}"
            )
            r = requests.get(url, timeout=10)
            data = r.json()
            price_str = data.get("Global Quote", {}).get("05. price", "0")
            price = float(price_str)
            if price > 0:
                prices[sym] = round(price, 4)
        except Exception:
            continue
    return prices


def _fetch_yahoo_json(symbols: List[str]) -> Dict[str, float]:
    import requests
    prices: Dict[str, float] = {}
    for sym in symbols:
        try:
            url = (
                f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}"
                f"?interval=1d&range=1d"
            )
            headers = {"User-Agent": "Mozilla/5.0"}
            r = requests.get(url, headers=headers, timeout=10)
            data = r.json()
            meta = data["chart"]["result"][0]["meta"]
            price = float(meta.get("regularMarketPrice", 0))
            if price > 0:
                prices[sym] = round(price, 4)
        except Exception:
            continue
    return prices


def _fetch_historical_prices(symbol: str, period: str = "90d") -> List[float]:
    """Fetch daily close prices for volatility/momentum calcs. Returns list of closes."""
    try:
        import yfinance as yf  # type: ignore[import-untyped]
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period=period)
        if hist is not None and len(hist) > 0:
            return [round(float(c), 6) for c in hist["Close"].tolist()]
    except Exception:
        pass
    return []


# ---------------------------------------------------------------------------
# Helper math
# ---------------------------------------------------------------------------

def _std(values: List[float]) -> float:
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    var = sum((v - mean) ** 2 for v in values) / (len(values) - 1)
    return math.sqrt(var)


def _momentum_20d(closes: List[float]) -> float:
    """20-day momentum: return over last 20 bars."""
    if len(closes) < 21:
        return 0.0
    return (closes[-1] / closes[-21]) - 1.0


def _volatility_ratio(closes: List[float], short_window: int = 20, long_window: int = 60) -> float:
    """Ratio of short-term vol to long-term vol baseline."""
    if len(closes) < long_window + 1:
        return 1.0
    returns = [(closes[i] / closes[i - 1]) - 1.0 for i in range(1, len(closes))]
    short_ret = returns[-short_window:]
    long_ret = returns[-long_window:]
    short_vol = _std(short_ret) if len(short_ret) >= 2 else 0.0
    long_vol = _std(long_ret) if len(long_ret) >= 2 else 0.001
    if long_vol == 0:
        return 1.0
    return short_vol / long_vol


def _rsi(closes: List[float], period: int = 2) -> float:
    """Simple RSI calculation."""
    if len(closes) < period + 1:
        return 50.0
    changes = [closes[i] - closes[i - 1] for i in range(len(closes) - period, len(closes))]
    gains = [c for c in changes if c > 0]
    losses = [-c for c in changes if c < 0]
    avg_gain = sum(gains) / period if gains else 0.0
    avg_loss = sum(losses) / period if losses else 0.001
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


# ---------------------------------------------------------------------------
# State persistence
# ---------------------------------------------------------------------------

def _load_state() -> Dict[str, Any]:
    if _STATE_FILE.exists():
        try:
            return json.loads(_STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _save_state(state: Dict[str, Any]) -> None:
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    _STATE_FILE.write_text(
        json.dumps(state, indent=2, default=str), encoding="utf-8"
    )


def _init_portfolio_state(portfolio_id: str, state: Dict[str, Any]) -> Dict[str, Any]:
    """Ensure a portfolio has initialized state."""
    if portfolio_id not in state:
        state[portfolio_id] = {
            "capital": START_CAPITAL,
            "nav": START_CAPITAL,
            "positions": {},
            "closed_trades": [],
            "snapshots": [],
            "carry_income": 0.0,
            "dividend_income": 0.0,
            "last_rebalance": None,
            "created_at": _dt.datetime.now(_dt.timezone.utc).isoformat(),
        }
    return state[portfolio_id]


# ---------------------------------------------------------------------------
# Portfolio 5: Forex Carry (JPY crosses)
# ---------------------------------------------------------------------------

PORTFOLIO_5 = {
    "id": "p5_forex_carry",
    "name": "Portfolio 5: Forex Carry",
    "description": "4 high-yield JPY crosses, carry direction long, momentum+vol gate",
    "allocations": {
        "AUDJPY=X": 0.25,
        "GBPJPY=X": 0.25,
        "USDJPY=X": 0.25,
        "NZDJPY=X": 0.25,
    },
    "entry_rules": {
        "direction": "long",  # long high-yield vs JPY
        "momentum_positive_20d": True,
        "vol_gate_max": 1.5,  # vol < 1.5x 60d baseline
    },
    "exit_rules": {
        "vol_gate_trigger": 1.5,
        "stop_loss_pct": 0.01,   # 1.0% fixed SL
        "take_profit_pct": 0.015,  # 1.5% TP
    },
    "rebalance": "monthly",
    "estimated_annual_carry_bps": 250,  # ~2.5% annual carry income estimate
}


def evaluate_entries_p5(pstate: Dict[str, Any], prices: Dict[str, float]) -> List[Dict[str, Any]]:
    """Check entry criteria for Forex Carry portfolio."""
    entries = []
    alloc = PORTFOLIO_5["allocations"]

    for sym, weight in alloc.items():
        if sym in pstate.get("positions", {}):
            continue  # already in position

        closes = _fetch_historical_prices(sym, period="90d")
        if len(closes) < 21:
            continue

        mom = _momentum_20d(closes)
        vol_ratio = _volatility_ratio(closes)

        # Entry: carry direction long ONLY when 20d momentum positive AND vol < 1.5x baseline
        if mom > 0 and vol_ratio < PORTFOLIO_5["entry_rules"]["vol_gate_max"]:
            price = prices.get(sym, 0.0)
            if price <= 0:
                continue
            allocation_usd = pstate["capital"] * weight
            shares = allocation_usd / price
            entries.append({
                "symbol": sym,
                "side": "long",
                "entry_price": price,
                "shares": round(shares, 6),
                "allocation_usd": round(allocation_usd, 2),
                "momentum_20d": round(mom, 4),
                "vol_ratio": round(vol_ratio, 4),
                "sl_price": round(price * (1.0 - PORTFOLIO_5["exit_rules"]["stop_loss_pct"]), 6),
                "tp_price": round(price * (1.0 + PORTFOLIO_5["exit_rules"]["take_profit_pct"]), 6),
                "entered_at": _dt.datetime.now(_dt.timezone.utc).isoformat(),
            })
    return entries


def evaluate_exits_p5(pstate: Dict[str, Any], prices: Dict[str, float]) -> List[Dict[str, Any]]:
    """Check exit criteria for Forex Carry positions."""
    exits = []
    positions = pstate.get("positions", {})

    for sym, pos in list(positions.items()):
        price = prices.get(sym, 0.0)
        if price <= 0:
            continue

        entry_price = pos["entry_price"]
        reason = None

        # Exit 1: volatility gate triggers
        closes = _fetch_historical_prices(sym, period="90d")
        if len(closes) >= 21:
            vol_ratio = _volatility_ratio(closes)
            if vol_ratio > PORTFOLIO_5["exit_rules"]["vol_gate_trigger"]:
                reason = "vol_gate"

        # Exit 2: stop loss
        if price <= pos.get("sl_price", 0):
            reason = "stop_loss"

        # Exit 3: take profit
        if price >= pos.get("tp_price", float("inf")):
            reason = "take_profit"

        if reason:
            pnl = (price - entry_price) * pos["shares"]
            exits.append({
                "symbol": sym,
                "exit_price": price,
                "entry_price": entry_price,
                "shares": pos["shares"],
                "pnl": round(pnl, 2),
                "reason": reason,
                "exited_at": _dt.datetime.now(_dt.timezone.utc).isoformat(),
            })
    return exits


def _accrue_carry_income(pstate: Dict[str, Any]) -> float:
    """Estimate daily carry income from open JPY cross positions."""
    # ~2.5% annual carry spread / 252 trading days = ~0.01% per day per position
    positions = pstate.get("positions", {})
    if not positions:
        return 0.0
    daily_carry_rate = PORTFOLIO_5["estimated_annual_carry_bps"] / 10000.0 / 252.0
    total_carry = 0.0
    for sym, pos in positions.items():
        notional = pos.get("allocation_usd", 0.0)
        carry = notional * daily_carry_rate
        total_carry += carry
    return round(total_carry, 4)


# ---------------------------------------------------------------------------
# Portfolio 6: Stocks Dividend (extends PORTFOLIO_A from non_crypto_ab_tester.py)
# ---------------------------------------------------------------------------

# Import PORTFOLIO_A definition
try:
    from alpha_engine.non_crypto_ab_tester import PORTFOLIO_A as _PORTFOLIO_A_RAW
except ImportError:
    # Fallback: define inline if import fails (CI environment)
    _PORTFOLIO_A_RAW = [
        {"symbol": "AAPL",  "weight": 0.08, "category": "blue_chip"},
        {"symbol": "MSFT",  "weight": 0.08, "category": "blue_chip"},
        {"symbol": "JNJ",   "weight": 0.08, "category": "blue_chip"},
        {"symbol": "PG",    "weight": 0.08, "category": "blue_chip"},
        {"symbol": "KO",    "weight": 0.08, "category": "blue_chip"},
        {"symbol": "BRK-B", "weight": 0.10, "category": "financial"},
        {"symbol": "JPM",   "weight": 0.10, "category": "financial"},
        {"symbol": "TLT",   "weight": 0.15, "category": "bond"},
        {"symbol": "BND",   "weight": 0.15, "category": "bond"},
        {"symbol": "GLD",   "weight": 0.10, "category": "gold"},
    ]

# Estimated annual dividend yields (conservative estimates)
_DIVIDEND_YIELDS = {
    "AAPL": 0.005,   # ~0.5%
    "MSFT": 0.007,   # ~0.7%
    "JNJ": 0.030,    # ~3.0%
    "PG": 0.025,     # ~2.5%
    "KO": 0.030,     # ~3.0%
    "BRK-B": 0.000,  # Berkshire pays no dividend
    "JPM": 0.025,    # ~2.5%
    "TLT": 0.035,    # ~3.5% (bond ETF distributions)
    "BND": 0.033,    # ~3.3%
    "GLD": 0.000,    # Gold pays no dividend
}

PORTFOLIO_6 = {
    "id": "p6_stocks_dividend",
    "name": "Portfolio 6: Stocks Dividend",
    "description": "PORTFOLIO_A with dividend tracking (est 2-3% annual yield)",
    "allocations": {e["symbol"]: e["weight"] for e in _PORTFOLIO_A_RAW},
    "holdings": _PORTFOLIO_A_RAW,
    "dividend_yields": _DIVIDEND_YIELDS,
    "rebalance": "buy_and_hold",
}


def evaluate_entries_p6(pstate: Dict[str, Any], prices: Dict[str, float]) -> List[Dict[str, Any]]:
    """Portfolio 6 is buy-and-hold. Enter all positions on first run."""
    entries = []
    for entry in _PORTFOLIO_A_RAW:
        sym = entry["symbol"]
        if sym in pstate.get("positions", {}):
            continue
        price = prices.get(sym, 0.0)
        if price <= 0:
            continue
        allocation = pstate["capital"] * entry["weight"]
        shares = allocation / price
        entries.append({
            "symbol": sym,
            "side": "long",
            "entry_price": price,
            "shares": round(shares, 6),
            "allocation_usd": round(allocation, 2),
            "category": entry.get("category", ""),
            "entered_at": _dt.datetime.now(_dt.timezone.utc).isoformat(),
        })
    return entries


def evaluate_exits_p6(pstate: Dict[str, Any], prices: Dict[str, float]) -> List[Dict[str, Any]]:
    """Portfolio 6 is buy-and-hold. No exits."""
    return []


def _accrue_dividend_income(pstate: Dict[str, Any], prices: Dict[str, float]) -> float:
    """Estimate daily dividend income from stock positions."""
    positions = pstate.get("positions", {})
    if not positions:
        return 0.0
    total_div = 0.0
    for sym, pos in positions.items():
        annual_yield = _DIVIDEND_YIELDS.get(sym, 0.0)
        daily_yield = annual_yield / 252.0
        current_price = prices.get(sym, pos.get("entry_price", 0.0))
        position_value = pos["shares"] * current_price
        daily_dividend = position_value * daily_yield
        total_div += daily_dividend
    return round(total_div, 4)


# ---------------------------------------------------------------------------
# Portfolio 7: All-Weather (Ray Dalio inspired — BENCHMARK)
# ---------------------------------------------------------------------------

PORTFOLIO_7 = {
    "id": "p7_all_weather",
    "name": "Portfolio 7: All-Weather (Benchmark)",
    "description": "Ray Dalio: 30% VTI, 40% TLT, 15% GLD, 7.5% DBC, 7.5% TIP",
    "allocations": {
        "VTI": 0.30,   # Stocks
        "TLT": 0.40,   # Long-term bonds
        "GLD": 0.15,   # Gold
        "DBC": 0.075,  # Commodities
        "TIP": 0.075,  # TIPS
    },
    "entry_rules": "buy_and_hold",
    "exit_rules": "none",
    "rebalance": "quarterly",
    "drift_trigger_pct": 0.05,  # 5% drift triggers rebalance
}


def evaluate_entries_p7(pstate: Dict[str, Any], prices: Dict[str, float]) -> List[Dict[str, Any]]:
    """All-Weather: buy everything on first run (buy-and-hold)."""
    entries = []
    for sym, weight in PORTFOLIO_7["allocations"].items():
        if sym in pstate.get("positions", {}):
            continue
        price = prices.get(sym, 0.0)
        if price <= 0:
            continue
        allocation = pstate["capital"] * weight
        shares = allocation / price
        entries.append({
            "symbol": sym,
            "side": "long",
            "entry_price": price,
            "shares": round(shares, 6),
            "allocation_usd": round(allocation, 2),
            "target_weight": weight,
            "entered_at": _dt.datetime.now(_dt.timezone.utc).isoformat(),
        })
    return entries


def evaluate_exits_p7(pstate: Dict[str, Any], prices: Dict[str, float]) -> List[Dict[str, Any]]:
    """All-Weather: no exits (pure buy-and-hold). Rebalancing handled separately."""
    return []


def _check_rebalance_p7(pstate: Dict[str, Any], prices: Dict[str, float]) -> bool:
    """Check if quarterly rebalance + 5% drift trigger is met."""
    last_reb = pstate.get("last_rebalance")
    now = _dt.datetime.now(_dt.timezone.utc)

    # Quarterly check
    if last_reb:
        try:
            last_dt = _dt.datetime.fromisoformat(last_reb)
            if last_dt.tzinfo is None:
                last_dt = last_dt.replace(tzinfo=_dt.timezone.utc)
            days_since = (now - last_dt).days
            if days_since < 90:
                return False
        except Exception:
            pass

    # Check drift
    positions = pstate.get("positions", {})
    if not positions:
        return False

    total_value = 0.0
    values = {}
    for sym, pos in positions.items():
        price = prices.get(sym, pos.get("entry_price", 0.0))
        val = pos["shares"] * price
        values[sym] = val
        total_value += val

    if total_value <= 0:
        return False

    for sym, target_weight in PORTFOLIO_7["allocations"].items():
        actual_weight = values.get(sym, 0.0) / total_value
        drift = abs(actual_weight - target_weight)
        if drift >= PORTFOLIO_7["drift_trigger_pct"]:
            return True

    return False


def _rebalance_p7(pstate: Dict[str, Any], prices: Dict[str, float]) -> None:
    """Rebalance All-Weather portfolio to target weights."""
    positions = pstate.get("positions", {})
    total_value = 0.0
    for sym, pos in positions.items():
        price = prices.get(sym, pos.get("entry_price", 0.0))
        total_value += pos["shares"] * price

    if total_value <= 0:
        return

    for sym, target_weight in PORTFOLIO_7["allocations"].items():
        price = prices.get(sym, 0.0)
        if price <= 0:
            continue
        target_value = total_value * target_weight
        target_shares = target_value / price
        if sym in positions:
            positions[sym]["shares"] = round(target_shares, 6)
            positions[sym]["allocation_usd"] = round(target_value, 2)
        else:
            positions[sym] = {
                "symbol": sym,
                "side": "long",
                "entry_price": price,
                "shares": round(target_shares, 6),
                "allocation_usd": round(target_value, 2),
                "entered_at": _dt.datetime.now(_dt.timezone.utc).isoformat(),
            }

    pstate["positions"] = positions
    pstate["last_rebalance"] = _dt.datetime.now(_dt.timezone.utc).isoformat()
    print(f"  [P7] Rebalanced All-Weather to target weights. NAV=${total_value:,.2f}")


# ---------------------------------------------------------------------------
# Portfolio 8: Copy Trader Forex Best
# ---------------------------------------------------------------------------

def _load_top_forex_traders(min_trades: int = 50, top_n: int = 5) -> List[Dict[str, Any]]:
    """Load top forex traders by WR from forex_trader_database.json."""
    if not _FOREX_DB_FILE.exists():
        # Fallback hardcoded from the database
        return [
            {"id": "zulu_002", "name": "GainsPTWS", "win_rate": 0.80,
             "strategy_type": "scalping", "pairs": ["EURUSD=X", "GBPUSD=X", "USDJPY=X", "EURCHF=X", "GBPJPY=X"]},
            {"id": "etoro_001", "name": "OlivierDanvel", "win_rate": 0.65,
             "strategy_type": "swing", "pairs": ["EURUSD=X", "GBPUSD=X", "USDJPY=X", "EURGBP=X", "AUDUSD=X"]},
            {"id": "zulu_003", "name": "YunoriYK", "win_rate": 0.65,
             "strategy_type": "trend_following", "pairs": ["EURUSD=X", "GBPUSD=X", "USDJPY=X", "AUDUSD=X"]},
            {"id": "etoro_003", "name": "FundManagerZech", "win_rate": 0.625,
             "strategy_type": "diversified", "pairs": ["USDCHF=X", "EURUSD=X", "GBPUSD=X"]},
            {"id": "zulu_001", "name": "Rydwaves", "win_rate": 0.62,
             "strategy_type": "elliott_wave", "pairs": ["EURUSD=X", "GBPUSD=X", "USDJPY=X", "EURGBP=X", "AUDUSD=X"]},
        ]

    try:
        data = json.loads(_FOREX_DB_FILE.read_text(encoding="utf-8"))
        traders = data.get("traders", [])
    except Exception:
        return []

    # Filter forex-focused traders
    forex_traders = []
    for t in traders:
        focus = t.get("asset_focus", "")
        if "forex" not in focus.lower():
            continue
        wr = t.get("win_rate", 0)
        if wr <= 0:
            continue
        # Use follower count as proxy for trade volume when trades field missing
        pairs_raw = t.get("pairs_traded", [])
        # Normalize pair names for yfinance (EUR/USD -> EURUSD=X)
        pairs = [p.replace("/", "") + "=X" for p in pairs_raw]
        forex_traders.append({
            "id": t.get("id", "unknown"),
            "name": t.get("name", t.get("username", "unknown")),
            "win_rate": float(wr),
            "strategy_type": t.get("strategy_type", "unknown"),
            "pairs": pairs,
            "monthly_return": t.get("monthly_return_pct", 0),
        })

    # Sort by win_rate descending, take top N
    forex_traders.sort(key=lambda x: x["win_rate"], reverse=True)
    return forex_traders[:top_n]


_CACHED_TOP_TRADERS: Optional[List[Dict[str, Any]]] = None


def _get_top_traders() -> List[Dict[str, Any]]:
    global _CACHED_TOP_TRADERS
    if _CACHED_TOP_TRADERS is None:
        _CACHED_TOP_TRADERS = _load_top_forex_traders()
    return _CACHED_TOP_TRADERS


PORTFOLIO_8 = {
    "id": "p8_copy_trader_forex",
    "name": "Portfolio 8: Copy Trader Forex Best",
    "description": "Top 5 forex traders by WR, equal weight, carry+RSI2+mean reversion",
    "weight_per_trader": 0.20,  # equal weight 5 traders
    "strategies": ["carry", "rsi2", "mean_reversion"],
}


def _trader_signal_fires(trader: Dict[str, Any], sym: str, closes: List[float]) -> Optional[str]:
    """Check if carry, RSI2, or mean reversion fires for this pair."""
    if len(closes) < 21:
        return None

    strategy = trader.get("strategy_type", "")

    # Carry signal: positive momentum
    mom = _momentum_20d(closes)
    if mom > 0 and "JPY" in sym:
        return "carry"

    # RSI2 mean-reversion: RSI(2) < 10 = oversold buy
    rsi_val = _rsi(closes, period=2)
    if rsi_val < 10:
        return "rsi2_oversold"

    # Mean reversion: price > 2 std below 20-period mean
    if len(closes) >= 20:
        recent = closes[-20:]
        mean_price = sum(recent) / len(recent)
        std_price = _std(recent)
        if std_price > 0 and closes[-1] < mean_price - 2 * std_price:
            return "mean_reversion"

    return None


def evaluate_entries_p8(pstate: Dict[str, Any], prices: Dict[str, float]) -> List[Dict[str, Any]]:
    """Check if forex strategies fire AND align with top trader preferred pairs."""
    entries = []
    traders = _get_top_traders()
    if not traders:
        return entries

    weight_per = PORTFOLIO_8["weight_per_trader"]
    capital_per_trader = pstate["capital"] * weight_per

    for trader in traders:
        trader_id = trader["id"]
        # Each trader gets equal capital split across their preferred pairs
        pairs = trader.get("pairs", [])
        if not pairs:
            continue

        capital_per_pair = capital_per_trader / len(pairs)

        for sym in pairs:
            pos_key = f"{trader_id}_{sym}"
            if pos_key in pstate.get("positions", {}):
                continue

            price = prices.get(sym, 0.0)
            if price <= 0:
                continue

            closes = _fetch_historical_prices(sym, period="90d")
            signal = _trader_signal_fires(trader, sym, closes)
            if signal is None:
                continue

            shares = capital_per_pair / price
            # TP/SL based on strategy
            if signal == "carry":
                tp_pct, sl_pct = 0.015, 0.01
            elif signal == "rsi2_oversold":
                tp_pct, sl_pct = 0.01, 0.008
            else:  # mean_reversion
                tp_pct, sl_pct = 0.012, 0.01

            entries.append({
                "symbol": sym,
                "pos_key": pos_key,
                "trader_id": trader_id,
                "trader_name": trader["name"],
                "side": "long",
                "signal": signal,
                "entry_price": price,
                "shares": round(shares, 6),
                "allocation_usd": round(capital_per_pair, 2),
                "sl_price": round(price * (1.0 - sl_pct), 6),
                "tp_price": round(price * (1.0 + tp_pct), 6),
                "entered_at": _dt.datetime.now(_dt.timezone.utc).isoformat(),
            })

    return entries


def evaluate_exits_p8(pstate: Dict[str, Any], prices: Dict[str, float]) -> List[Dict[str, Any]]:
    """Check TP/SL exits for copy trader positions."""
    exits = []
    for pos_key, pos in list(pstate.get("positions", {}).items()):
        sym = pos["symbol"]
        price = prices.get(sym, 0.0)
        if price <= 0:
            continue

        reason = None
        if price <= pos.get("sl_price", 0):
            reason = "stop_loss"
        elif price >= pos.get("tp_price", float("inf")):
            reason = "take_profit"

        if reason:
            pnl = (price - pos["entry_price"]) * pos["shares"]
            exits.append({
                "pos_key": pos_key,
                "symbol": sym,
                "trader_id": pos.get("trader_id", ""),
                "trader_name": pos.get("trader_name", ""),
                "exit_price": price,
                "entry_price": pos["entry_price"],
                "shares": pos["shares"],
                "signal": pos.get("signal", ""),
                "pnl": round(pnl, 2),
                "reason": reason,
                "exited_at": _dt.datetime.now(_dt.timezone.utc).isoformat(),
            })
    return exits


# ---------------------------------------------------------------------------
# Generic portfolio update cycle
# ---------------------------------------------------------------------------

def update_portfolio(
    portfolio_id: str,
    portfolio_def: Dict[str, Any],
    state: Dict[str, Any],
    prices: Dict[str, float],
    eval_entries_fn,
    eval_exits_fn,
) -> Dict[str, Any]:
    """Main update cycle for any portfolio."""
    pstate = _init_portfolio_state(portfolio_id, state)
    now_iso = _dt.datetime.now(_dt.timezone.utc).isoformat()

    # --- Evaluate exits first ---
    exits = eval_exits_fn(pstate, prices)
    for ex in exits:
        pos_key = ex.get("pos_key", ex.get("symbol", ""))
        if pos_key in pstate["positions"]:
            del pstate["positions"][pos_key]
        # Return capital
        pstate["capital"] += ex.get("allocation_usd", 0) + ex.get("pnl", 0)
        ex["portfolio"] = portfolio_id
        pstate["closed_trades"].append(ex)
        print(f"  [{portfolio_id}] EXIT {ex.get('symbol','')} reason={ex.get('reason','')} PnL=${ex.get('pnl',0):.2f}")

    # --- Evaluate entries ---
    entries = eval_entries_fn(pstate, prices)
    for en in entries:
        pos_key = en.get("pos_key", en.get("symbol", ""))
        pstate["positions"][pos_key] = en
        pstate["capital"] -= en.get("allocation_usd", 0)
        print(f"  [{portfolio_id}] ENTRY {en.get('symbol','')} @ {en.get('entry_price',0):.4f}")

    # --- Compute current NAV ---
    nav = pstate["capital"]
    for pos_key, pos in pstate["positions"].items():
        sym = pos["symbol"]
        price = prices.get(sym, pos.get("entry_price", 0.0))
        nav += pos["shares"] * price

    # Add accrued income
    nav += pstate.get("carry_income", 0.0)
    nav += pstate.get("dividend_income", 0.0)

    pstate["nav"] = round(nav, 2)

    # --- Snapshot ---
    pstate["snapshots"].append({
        "timestamp": now_iso,
        "nav": pstate["nav"],
        "positions_count": len(pstate["positions"]),
        "capital_available": round(pstate["capital"], 2),
    })

    return pstate


# ---------------------------------------------------------------------------
# Metrics computation
# ---------------------------------------------------------------------------

def compute_metrics(snapshots: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Compute Sharpe, Sortino, max DD, WR, total return, profit factor."""
    if len(snapshots) < 2:
        return {
            "total_return_pct": 0.0,
            "sharpe": 0.0,
            "sortino": 0.0,
            "max_drawdown_pct": 0.0,
            "win_rate": 0.0,
            "profit_factor": 0.0,
            "num_snapshots": len(snapshots),
        }

    navs = [s["nav"] for s in snapshots if s.get("nav", 0) > 0]
    if len(navs) < 2:
        return {
            "total_return_pct": 0.0,
            "sharpe": 0.0,
            "sortino": 0.0,
            "max_drawdown_pct": 0.0,
            "win_rate": 0.0,
            "profit_factor": 0.0,
            "num_snapshots": len(navs),
        }

    returns = [(navs[i] / navs[i - 1]) - 1.0 for i in range(1, len(navs))]
    total_return_pct = round(((navs[-1] / navs[0]) - 1.0) * 100, 2)

    # Win rate
    wins = sum(1 for r in returns if r > 0)
    losses = sum(1 for r in returns if r < 0)
    win_rate = round(wins / len(returns) * 100, 2) if returns else 0.0

    # Sharpe (annualised: 4 snapshots/day x 252 trading days)
    mean_r = sum(returns) / len(returns)
    std_r = _std(returns)
    periods_per_year = 4 * 252
    sharpe = 0.0
    if std_r > 0:
        sharpe = round((mean_r / std_r) * math.sqrt(periods_per_year), 2)

    # Sortino
    downside = [r for r in returns if r < 0]
    down_std = _std(downside) if downside else 0.0
    sortino = 0.0
    if down_std > 0:
        sortino = round((mean_r / down_std) * math.sqrt(periods_per_year), 2)

    # Max drawdown
    peak = navs[0]
    max_dd = 0.0
    for n in navs:
        if n > peak:
            peak = n
        dd = (peak - n) / peak
        if dd > max_dd:
            max_dd = dd
    max_drawdown_pct = round(max_dd * 100, 2)

    # Profit factor
    gross_profit = sum(r for r in returns if r > 0)
    gross_loss = abs(sum(r for r in returns if r < 0))
    profit_factor = round(gross_profit / gross_loss, 2) if gross_loss > 0 else 99.99

    return {
        "total_return_pct": total_return_pct,
        "sharpe": sharpe,
        "sortino": sortino,
        "max_drawdown_pct": max_drawdown_pct,
        "win_rate": win_rate,
        "profit_factor": profit_factor,
        "num_snapshots": len(navs),
    }


def compute_trade_metrics(closed_trades: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Compute trade-level WR and profit factor from closed trades."""
    if not closed_trades:
        return {"trade_wr": 0.0, "trade_pf": 0.0, "total_trades": 0}
    wins = sum(1 for t in closed_trades if t.get("pnl", 0) > 0)
    total = len(closed_trades)
    gross_profit = sum(t["pnl"] for t in closed_trades if t.get("pnl", 0) > 0)
    gross_loss = abs(sum(t["pnl"] for t in closed_trades if t.get("pnl", 0) < 0))
    pf = round(gross_profit / gross_loss, 2) if gross_loss > 0 else 99.99
    return {
        "trade_wr": round(wins / total * 100, 2) if total else 0.0,
        "trade_pf": pf,
        "total_trades": total,
        "total_pnl": round(gross_profit - gross_loss, 2),
    }


# ---------------------------------------------------------------------------
# Monthly rebalance check for P5
# ---------------------------------------------------------------------------

def _check_monthly_rebalance(pstate: Dict[str, Any]) -> bool:
    last_reb = pstate.get("last_rebalance")
    now = _dt.datetime.now(_dt.timezone.utc)
    if not last_reb:
        return True
    try:
        last_dt = _dt.datetime.fromisoformat(last_reb)
        if last_dt.tzinfo is None:
            last_dt = last_dt.replace(tzinfo=_dt.timezone.utc)
        return (now - last_dt).days >= 30
    except Exception:
        return True


# ---------------------------------------------------------------------------
# Trader performance tracking for P8
# ---------------------------------------------------------------------------

def _compute_trader_performance(closed_trades: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """Break down P8 performance by trader."""
    by_trader: Dict[str, List[Dict[str, Any]]] = {}
    for t in closed_trades:
        tid = t.get("trader_id", "unknown")
        by_trader.setdefault(tid, []).append(t)

    result = {}
    for tid, trades in by_trader.items():
        wins = sum(1 for t in trades if t.get("pnl", 0) > 0)
        total_pnl = sum(t.get("pnl", 0) for t in trades)
        name = trades[0].get("trader_name", tid) if trades else tid
        result[tid] = {
            "name": name,
            "trades": len(trades),
            "wins": wins,
            "wr": round(wins / len(trades) * 100, 2) if trades else 0.0,
            "total_pnl": round(total_pnl, 2),
        }
    return result


# ---------------------------------------------------------------------------
# Run all portfolios
# ---------------------------------------------------------------------------

_ALL_PORTFOLIOS = [
    {
        "def": PORTFOLIO_5,
        "entry_fn": evaluate_entries_p5,
        "exit_fn": evaluate_exits_p5,
    },
    {
        "def": PORTFOLIO_6,
        "entry_fn": evaluate_entries_p6,
        "exit_fn": evaluate_exits_p6,
    },
    {
        "def": PORTFOLIO_7,
        "entry_fn": evaluate_entries_p7,
        "exit_fn": evaluate_exits_p7,
    },
    {
        "def": PORTFOLIO_8,
        "entry_fn": evaluate_entries_p8,
        "exit_fn": evaluate_exits_p8,
    },
]


def run_all_portfolios(force: bool = False) -> Dict[str, Any]:
    """Run all 4 portfolios, print comparison, save results."""
    et_now = _now_et()
    now_utc = _dt.datetime.now(_dt.timezone.utc)

    if not force and not _is_any_market_open(et_now):
        print(f"[TradPortfolios] All markets closed at {now_utc.isoformat()}. Use --force to override.")
        # Still load and display existing metrics
        state = _load_state()
        return _build_results(state, skipped=True)

    print(f"[TradPortfolios] Running at {now_utc.isoformat()}")
    print(f"  Equity hours: {_is_equity_market_hours(et_now)} | Forex hours: {_is_forex_hours(et_now)}")

    state = _load_state()

    # Gather all symbols needed
    all_symbols: List[str] = []
    all_symbols.extend(PORTFOLIO_5["allocations"].keys())
    all_symbols.extend(PORTFOLIO_6["allocations"].keys())
    all_symbols.extend(PORTFOLIO_7["allocations"].keys())

    # P8: gather all trader preferred pairs
    traders = _get_top_traders()
    for t in traders:
        all_symbols.extend(t.get("pairs", []))

    all_symbols = list(set(all_symbols))
    print(f"  Fetching prices for {len(all_symbols)} symbols ...")
    prices = fetch_traditional_prices(all_symbols)
    print(f"  Got {len(prices)}/{len(all_symbols)} prices")

    if not prices:
        print("[TradPortfolios] ERROR: No prices fetched. Aborting.")
        return {"status": "error", "reason": "no_prices"}

    # --- Update each portfolio ---
    for pdef in _ALL_PORTFOLIOS:
        pid = pdef["def"]["id"]
        pname = pdef["def"]["name"]
        print(f"\n  === {pname} ===")

        # Portfolio-specific pre-update logic
        if pid == "p5_forex_carry":
            pstate = _init_portfolio_state(pid, state)
            # Accrue carry income
            carry = _accrue_carry_income(pstate)
            pstate["carry_income"] = round(pstate.get("carry_income", 0.0) + carry, 4)
            if carry > 0:
                print(f"  [P5] Carry income accrued: ${carry:.4f} (total: ${pstate['carry_income']:.2f})")
            # Monthly rebalance: close all positions to re-enter fresh
            if _check_monthly_rebalance(pstate) and pstate.get("positions"):
                print(f"  [P5] Monthly rebalance — closing all positions")
                for sym in list(pstate["positions"].keys()):
                    pos = pstate["positions"][sym]
                    price = prices.get(sym, pos.get("entry_price", 0))
                    pnl = (price - pos["entry_price"]) * pos["shares"]
                    pstate["closed_trades"].append({
                        "symbol": sym, "pnl": round(pnl, 2), "reason": "rebalance",
                        "exited_at": now_utc.isoformat(),
                    })
                    pstate["capital"] += pos.get("allocation_usd", 0) + pnl
                pstate["positions"] = {}
                pstate["last_rebalance"] = now_utc.isoformat()

        if pid == "p6_stocks_dividend":
            pstate = _init_portfolio_state(pid, state)
            div = _accrue_dividend_income(pstate, prices)
            pstate["dividend_income"] = round(pstate.get("dividend_income", 0.0) + div, 4)
            if div > 0:
                print(f"  [P6] Dividend income accrued: ${div:.4f} (total: ${pstate['dividend_income']:.2f})")

        if pid == "p7_all_weather":
            pstate = _init_portfolio_state(pid, state)
            if _check_rebalance_p7(pstate, prices):
                _rebalance_p7(pstate, prices)

        update_portfolio(
            pid, pdef["def"], state, prices,
            pdef["entry_fn"], pdef["exit_fn"],
        )

    _save_state(state)
    results = _build_results(state, skipped=False)

    # Save results JSON
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    _RESULTS_FILE.write_text(
        json.dumps(results, indent=2, default=str), encoding="utf-8"
    )
    print(f"\n  Results saved to {_RESULTS_FILE}")

    # Print comparison table
    _print_comparison(results)

    return results


def _build_results(state: Dict[str, Any], skipped: bool = False) -> Dict[str, Any]:
    """Build results dict from current state."""
    results: Dict[str, Any] = {
        "generated_at": _dt.datetime.now(_dt.timezone.utc).isoformat(),
        "start_capital": START_CAPITAL,
        "skipped": skipped,
        "portfolios": {},
    }

    for pdef in _ALL_PORTFOLIOS:
        pid = pdef["def"]["id"]
        pname = pdef["def"]["name"]
        pstate = state.get(pid, {})
        snapshots = pstate.get("snapshots", [])
        closed = pstate.get("closed_trades", [])
        nav_metrics = compute_metrics(snapshots)
        trade_metrics = compute_trade_metrics(closed)

        portfolio_result = {
            "name": pname,
            "description": pdef["def"].get("description", ""),
            "current_nav": pstate.get("nav", START_CAPITAL),
            "positions_count": len(pstate.get("positions", {})),
            "metrics": nav_metrics,
            "trade_metrics": trade_metrics,
            "carry_income": pstate.get("carry_income", 0.0),
            "dividend_income": pstate.get("dividend_income", 0.0),
        }

        # P6: total return = price + dividends
        if pid == "p6_stocks_dividend":
            price_return = nav_metrics.get("total_return_pct", 0.0)
            div_income = pstate.get("dividend_income", 0.0)
            div_return_pct = round((div_income / START_CAPITAL) * 100, 2)
            portfolio_result["total_return_with_dividends"] = round(price_return + div_return_pct, 2)
            portfolio_result["dividend_return_pct"] = div_return_pct

        # P5: separate carry income tracking
        if pid == "p5_forex_carry":
            carry = pstate.get("carry_income", 0.0)
            carry_return_pct = round((carry / START_CAPITAL) * 100, 2)
            portfolio_result["carry_return_pct"] = carry_return_pct
            price_return = nav_metrics.get("total_return_pct", 0.0)
            portfolio_result["total_return_with_carry"] = round(price_return + carry_return_pct, 2)

        # P8: per-trader breakdown
        if pid == "p8_copy_trader_forex":
            portfolio_result["trader_performance"] = _compute_trader_performance(closed)

        results["portfolios"][pid] = portfolio_result

    return results


def _print_comparison(results: Dict[str, Any]) -> None:
    """Print formatted comparison table."""
    sep = "=" * 100
    print(f"\n{sep}")
    print("  TRADITIONAL ASSET TEST PORTFOLIOS — COMPARISON")
    print(sep)

    header = f"  {'Metric':<28}"
    pids = ["p5_forex_carry", "p6_stocks_dividend", "p7_all_weather", "p8_copy_trader_forex"]
    short_names = ["P5:FX Carry", "P6:Dividend", "P7:AllWeather*", "P8:CopyTrader"]

    for sn in short_names:
        header += f" {sn:>16}"
    print(header)
    print("-" * 100)

    rows = [
        ("Current NAV",
         lambda p: f"${p.get('current_nav', 10000):,.2f}"),
        ("Total Return",
         lambda p: f"{p.get('metrics', {}).get('total_return_pct', 0):.2f}%"),
        ("Sharpe Ratio",
         lambda p: f"{p.get('metrics', {}).get('sharpe', 0):.2f}"),
        ("Sortino Ratio",
         lambda p: f"{p.get('metrics', {}).get('sortino', 0):.2f}"),
        ("Max Drawdown",
         lambda p: f"{p.get('metrics', {}).get('max_drawdown_pct', 0):.2f}%"),
        ("Win Rate (periods)",
         lambda p: f"{p.get('metrics', {}).get('win_rate', 0):.1f}%"),
        ("Profit Factor",
         lambda p: f"{p.get('metrics', {}).get('profit_factor', 0):.2f}"),
        ("Closed Trades",
         lambda p: f"{p.get('trade_metrics', {}).get('total_trades', 0)}"),
        ("Trade WR",
         lambda p: f"{p.get('trade_metrics', {}).get('trade_wr', 0):.1f}%"),
        ("Carry Income",
         lambda p: f"${p.get('carry_income', 0):.2f}"),
        ("Dividend Income",
         lambda p: f"${p.get('dividend_income', 0):.2f}"),
        ("Snapshots",
         lambda p: f"{p.get('metrics', {}).get('num_snapshots', 0)}"),
    ]

    portfolios = results.get("portfolios", {})
    for label, fmt_fn in rows:
        row = f"  {label:<28}"
        for pid in pids:
            p = portfolios.get(pid, {})
            row += f" {fmt_fn(p):>16}"
        print(row)

    print("-" * 100)
    print("  * P7 All-Weather is the BENCHMARK — others should beat it on risk-adjusted basis")

    # P8 trader breakdown
    p8 = portfolios.get("p8_copy_trader_forex", {})
    tp = p8.get("trader_performance", {})
    if tp:
        print(f"\n  --- P8 Trader Breakdown ---")
        for tid, info in sorted(tp.items(), key=lambda x: x[1].get("total_pnl", 0), reverse=True):
            print(f"    {info['name']:<20} trades={info['trades']:>3} WR={info['wr']:>6.1f}% PnL=${info['total_pnl']:>8.2f}")

    print(sep + "\n")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    force = "--force" in sys.argv
    run_all_portfolios(force=force)


if __name__ == "__main__":
    main()
