#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NOTE — SNAPSHOT-RESOLVER ARTIFACT (2026-06-03): WR/PF here is inflated by single
daily-snapshot TP/SL resolution (no intrabar OHLC path) — intraday SL touches are missed.
Do not size up on these numbers. See docs/RESOLVER_SNAPSHOT_ARTIFACT_AFFECTED_PORTFOLIOS_2026-06-03.md

ALPHA_ENGINE -- Crypto Test Portfolio Tracker
=============================================
Four virtual portfolios each starting with $10,000, tracking NAV, Sharpe,
max drawdown, win rate, total return, Sortino, and profit factor.

Portfolios:
  1. Conservative  -- BTC/ETH only, long bias, RSI < 40 + SMA(200) uptrend
  2. Aggressive    -- Top 10 alts by 7-day momentum, volume breakout
  3. Market Neutral -- Long top 3 / Short bottom 3 by 7-day return
  4. Copy Trader Best -- Follow 70%+ WR strategies from active/closed picks

Runs every 30 min via GitHub Actions. State persists in data/crypto_portfolio_state.json.

Usage:
  python crypto_test_portfolios.py          # run all 4 portfolios
  python crypto_test_portfolios.py --report # print latest results only
"""
from __future__ import annotations

import json
import math
import os
import sys
import time
import traceback
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Optional

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
DATA_DIR = Path(__file__).resolve().parent / "data"
STATE_FILE = DATA_DIR / "crypto_portfolio_state.json"
RESULTS_FILE = DATA_DIR / "crypto_portfolio_results.json"
ACTIVE_PICKS_FILE = DATA_DIR / "active_picks.json"
CLOSED_PICKS_FILE = DATA_DIR / "closed_picks.json"

INITIAL_CAPITAL = 10_000.0

# ---------------------------------------------------------------------------
# Binance 4-mirror failover (MANDATORY per project rules)
# ---------------------------------------------------------------------------
BINANCE_MIRRORS = [
    "https://api.binance.com",
    "https://api1.binance.com",
    "https://api2.binance.com",
    "https://api3.binance.com",
]

# Top 20 coins by market cap for ranking (market neutral + aggressive)
TOP20_SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT",
    "ADAUSDT", "DOGEUSDT", "AVAXUSDT", "DOTUSDT", "LINKUSDT",
    "NEARUSDT", "SUIUSDT", "MATICUSDT", "ATOMUSDT", "LTCUSDT",
    "UNIUSDT", "APTUSDT", "FILUSDT", "ARBUSDT", "OPUSDT",
]

# Large / mid / small-cap buckets for aggressive portfolio
LARGE_CAP = {"BTCUSDT", "ETHUSDT", "SOLUSDT"}
MID_CAP = {"AVAXUSDT", "LINKUSDT", "DOTUSDT", "NEARUSDT", "SUIUSDT"}

# ---------------------------------------------------------------------------
# Helpers: HTTP with retry
# ---------------------------------------------------------------------------
try:
    import requests
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "requests"])
    import requests

try:
    import numpy as np
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "numpy"])
    import numpy as np


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _iso() -> str:
    return _utcnow().isoformat()


def _http_get(url: str, params: dict | None = None, timeout: int = 15) -> dict | list | None:
    """GET with simple retry."""
    for attempt in range(3):
        try:
            r = requests.get(url, params=params, timeout=timeout)
            if r.status_code == 200:
                return r.json()
        except Exception:
            pass
        if attempt < 2:
            time.sleep(1 * (attempt + 1))
    return None


# ---------------------------------------------------------------------------
# Binance API helpers (4-mirror failover)
# ---------------------------------------------------------------------------
def fetch_price(symbol: str) -> Optional[float]:
    """Fetch latest price for a single symbol from Binance with 4-mirror failover."""
    for mirror in BINANCE_MIRRORS:
        data = _http_get(f"{mirror}/api/v3/ticker/price", {"symbol": symbol})
        if data and "price" in data:
            return float(data["price"])
    return None


def fetch_crypto_prices(symbols: list[str]) -> dict[str, float]:
    """Fetch latest prices for multiple symbols. Returns {symbol: price}."""
    prices: dict[str, float] = {}
    for mirror in BINANCE_MIRRORS:
        data = _http_get(f"{mirror}/api/v3/ticker/price")
        if data and isinstance(data, list):
            lookup = {item["symbol"]: float(item["price"]) for item in data if "symbol" in item}
            for s in symbols:
                if s not in prices and s in lookup:
                    prices[s] = lookup[s]
            if len(prices) >= len(symbols):
                break
    return prices


def fetch_klines(symbol: str, interval: str = "1d", limit: int = 210) -> list[list]:
    """Fetch OHLCV klines from Binance with 4-mirror failover."""
    for mirror in BINANCE_MIRRORS:
        data = _http_get(
            f"{mirror}/api/v3/klines",
            {"symbol": symbol, "interval": interval, "limit": limit},
        )
        if data and isinstance(data, list) and len(data) > 0:
            return data
    return []


def fetch_24h_tickers() -> list[dict]:
    """Fetch 24hr ticker data for all symbols."""
    for mirror in BINANCE_MIRRORS:
        data = _http_get(f"{mirror}/api/v3/ticker/24hr")
        if data and isinstance(data, list):
            return data
    return []


def fetch_7d_returns(symbols: list[str]) -> dict[str, float]:
    """Compute 7-day returns for given symbols using daily klines."""
    returns: dict[str, float] = {}
    for sym in symbols:
        klines = fetch_klines(sym, "1d", 8)
        if klines and len(klines) >= 2:
            try:
                close_now = float(klines[-1][4])
                close_7d = float(klines[0][4])
                if close_7d > 0:
                    returns[sym] = (close_now - close_7d) / close_7d * 100.0
            except (IndexError, ValueError):
                pass
    return returns


# ---------------------------------------------------------------------------
# Technical indicator helpers (from klines)
# ---------------------------------------------------------------------------
def _closes_from_klines(klines: list[list]) -> list[float]:
    return [float(k[4]) for k in klines]


def compute_sma(closes: list[float], period: int) -> Optional[float]:
    if len(closes) < period:
        return None
    return sum(closes[-period:]) / period


def compute_rsi(closes: list[float], period: int = 14) -> Optional[float]:
    if len(closes) < period + 1:
        return None
    gains, losses = [], []
    for i in range(-period, 0):
        diff = closes[i] - closes[i - 1]
        gains.append(max(diff, 0))
        losses.append(max(-diff, 0))
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


def compute_vol_ratio(klines: list[list], lookback: int = 20) -> Optional[float]:
    """Current volume / average of last `lookback` bars."""
    if len(klines) < lookback + 1:
        return None
    volumes = [float(k[5]) for k in klines]
    avg_vol = sum(volumes[-(lookback + 1):-1]) / lookback
    if avg_vol <= 0:
        return None
    return volumes[-1] / avg_vol


# ---------------------------------------------------------------------------
# Portfolio definitions
# ---------------------------------------------------------------------------
def _default_portfolio(name: str, portfolio_type: str) -> dict:
    return {
        "name": name,
        "type": portfolio_type,
        "initial_capital": INITIAL_CAPITAL,
        "cash": INITIAL_CAPITAL,
        "positions": [],       # list of position dicts
        "closed_trades": [],   # completed trades
        "nav_history": [{"ts": _iso(), "nav": INITIAL_CAPITAL}],
        "created_at": _iso(),
        "last_updated": _iso(),
    }


def _new_position(symbol: str, direction: str, entry_price: float, size_usd: float,
                  trailing_stop_pct: float = 0.05, take_profit: float | None = None,
                  stop_loss: float | None = None, time_stop_hours: float | None = None,
                  meta: dict | None = None) -> dict:
    qty = size_usd / entry_price if entry_price > 0 else 0
    pos = {
        "symbol": symbol,
        "direction": direction,
        "entry_price": entry_price,
        "entry_time": _iso(),
        "size_usd": size_usd,
        "qty": qty,
        "trailing_stop_pct": trailing_stop_pct,
        "high_water_mark": entry_price,
        "low_water_mark": entry_price,
        "take_profit": take_profit,
        "stop_loss": stop_loss,
        "time_stop_hours": time_stop_hours,
        "meta": meta or {},
    }
    return pos


def _close_position(pos: dict, exit_price: float, reason: str) -> dict:
    direction = pos.get("direction", "LONG")
    if direction == "LONG":
        pnl_pct = (exit_price - pos["entry_price"]) / pos["entry_price"]
    else:
        pnl_pct = (pos["entry_price"] - exit_price) / pos["entry_price"]
    pnl_usd = pnl_pct * pos["size_usd"]
    return {
        "symbol": pos["symbol"],
        "direction": direction,
        "entry_price": pos["entry_price"],
        "entry_time": pos["entry_time"],
        "exit_price": exit_price,
        "exit_time": _iso(),
        "exit_reason": reason,
        "pnl_pct": round(pnl_pct, 6),
        "pnl_usd": round(pnl_usd, 2),
        "size_usd": pos["size_usd"],
        "meta": pos.get("meta", {}),
    }


# ---------------------------------------------------------------------------
# Portfolio 1: Conservative (BTC/ETH only)
# ---------------------------------------------------------------------------
CONSERVATIVE_SYMBOLS = ["BTCUSDT", "ETHUSDT"]
CONSERVATIVE_ALLOC = {"BTCUSDT": 0.70, "ETHUSDT": 0.30}
CONSERVATIVE_MAX_POSITIONS = 3


def evaluate_conservative_entries(portfolio: dict, prices: dict, klines_cache: dict) -> list[dict]:
    """Entry: RSI(14) < 40 AND price > SMA(200). Long only."""
    signals = []
    n_positions = len(portfolio["positions"])
    if n_positions >= CONSERVATIVE_MAX_POSITIONS:
        return signals

    held_symbols = {p["symbol"] for p in portfolio["positions"]}
    for sym in CONSERVATIVE_SYMBOLS:
        if sym in held_symbols:
            continue
        klines = klines_cache.get(sym)
        if not klines or len(klines) < 201:
            continue
        closes = _closes_from_klines(klines)
        current_price = prices.get(sym)
        if current_price is None:
            continue
        r = compute_rsi(closes, 14)
        sma200 = compute_sma(closes, 200)
        if r is None or sma200 is None:
            continue
        if r < 40 and current_price > sma200:
            alloc_pct = CONSERVATIVE_ALLOC.get(sym, 0.5)
            max_usd = portfolio["cash"] * alloc_pct
            size = min(max_usd, portfolio["cash"] * 0.5)  # don't exceed 50% cash per trade
            if size < 10:
                continue
            signals.append({
                "symbol": sym,
                "direction": "LONG",
                "size_usd": round(size, 2),
                "entry_price": current_price,
                "trailing_stop_pct": 0.05,
                "meta": {"rsi": round(r, 2), "sma200": round(sma200, 2), "portfolio": "conservative"},
            })
    return signals


def evaluate_conservative_exits(portfolio: dict, prices: dict, klines_cache: dict) -> list[tuple[int, float, str]]:
    """Exit: 5% trailing stop OR RSI > 75. Returns [(position_index, exit_price, reason)]."""
    exits = []
    for i, pos in enumerate(portfolio["positions"]):
        current_price = prices.get(pos["symbol"])
        if current_price is None:
            continue
        # Update high water mark
        if current_price > pos["high_water_mark"]:
            pos["high_water_mark"] = current_price
        # Trailing stop: 5% below HWM
        trail_price = pos["high_water_mark"] * (1 - pos["trailing_stop_pct"])
        if current_price <= trail_price:
            exits.append((i, current_price, "TRAILING_STOP"))
            continue
        # RSI exit
        klines = klines_cache.get(pos["symbol"])
        if klines and len(klines) > 15:
            r = compute_rsi(_closes_from_klines(klines), 14)
            if r is not None and r > 75:
                exits.append((i, current_price, "RSI_OVERBOUGHT"))
                continue
    return exits


# ---------------------------------------------------------------------------
# Portfolio 2: Aggressive (top 10 alts by momentum)
# ---------------------------------------------------------------------------
AGGRESSIVE_MAX_POSITIONS = 10
AGGRESSIVE_TIME_STOP_HOURS = 48.0


def evaluate_aggressive_entries(portfolio: dict, prices: dict, klines_cache: dict,
                                returns_7d: dict, tickers_24h: dict) -> list[dict]:
    """Entry: 7d return > 5% AND volume > 2x 20-day avg. Allocate 30/40/30 large/mid/small."""
    signals = []
    n_pos = len(portfolio["positions"])
    if n_pos >= AGGRESSIVE_MAX_POSITIONS:
        return signals

    held = {p["symbol"] for p in portfolio["positions"]}

    # Candidates: positive 7d momentum + volume confirmation
    candidates = []
    for sym, ret in sorted(returns_7d.items(), key=lambda x: x[1], reverse=True):
        if sym in held:
            continue
        if ret <= 5.0:
            continue
        klines = klines_cache.get(sym)
        vr = compute_vol_ratio(klines, 20) if klines else None
        if vr is None or vr < 2.0:
            continue
        candidates.append((sym, ret, vr))

    # Pick up to fill slots
    slots = AGGRESSIVE_MAX_POSITIONS - n_pos
    for sym, ret, vr in candidates[:slots]:
        price = prices.get(sym)
        if price is None or price <= 0:
            continue
        # Determine allocation bucket
        if sym in LARGE_CAP:
            bucket_pct = 0.30
        elif sym in MID_CAP:
            bucket_pct = 0.40
        else:
            bucket_pct = 0.30
        max_per_pos = portfolio["cash"] * bucket_pct / max(1, min(slots, 3))
        size = min(max_per_pos, portfolio["cash"] * 0.15, portfolio["cash"])
        if size < 10:
            continue
        signals.append({
            "symbol": sym,
            "direction": "LONG",
            "size_usd": round(size, 2),
            "entry_price": price,
            "trailing_stop_pct": 0.08,
            "time_stop_hours": AGGRESSIVE_TIME_STOP_HOURS,
            "meta": {"ret_7d": round(ret, 2), "vol_ratio": round(vr, 2), "portfolio": "aggressive"},
        })
    return signals


def evaluate_aggressive_exits(portfolio: dict, prices: dict) -> list[tuple[int, float, str]]:
    """Exit: 8% trailing stop OR 48h time stop."""
    exits = []
    now = _utcnow()
    for i, pos in enumerate(portfolio["positions"]):
        current_price = prices.get(pos["symbol"])
        if current_price is None:
            continue
        if current_price > pos["high_water_mark"]:
            pos["high_water_mark"] = current_price
        # Trailing stop
        trail = pos["high_water_mark"] * (1 - pos["trailing_stop_pct"])
        if current_price <= trail:
            exits.append((i, current_price, "TRAILING_STOP"))
            continue
        # Time stop
        if pos.get("time_stop_hours"):
            entry_dt = datetime.fromisoformat(pos["entry_time"])
            if (now - entry_dt).total_seconds() > pos["time_stop_hours"] * 3600:
                exits.append((i, current_price, "TIME_STOP"))
                continue
    return exits


# ---------------------------------------------------------------------------
# Portfolio 3: Market Neutral (long top 3, short bottom 3 by 7d return)
# ---------------------------------------------------------------------------
NEUTRAL_POSITION_SIZE = 1666.67  # ~$10k / 6 positions
NEUTRAL_REBALANCE_HOURS = 168.0  # weekly


def evaluate_neutral_rebalance(portfolio: dict, prices: dict, returns_7d: dict) -> tuple[list[dict], bool]:
    """
    Weekly rebalance: close all, re-rank, long top 3, short bottom 3.
    Returns (new_entry_signals, should_close_all).
    """
    now = _utcnow()
    last_updated = datetime.fromisoformat(portfolio["last_updated"])
    hours_since = (now - last_updated).total_seconds() / 3600.0

    # Only rebalance weekly (or on first run with no positions)
    if portfolio["positions"] and hours_since < NEUTRAL_REBALANCE_HOURS:
        return [], False

    # Rank by 7d return
    ranked = sorted(returns_7d.items(), key=lambda x: x[1], reverse=True)
    if len(ranked) < 6:
        return [], False

    top3 = [sym for sym, _ in ranked[:3]]
    bottom3 = [sym for sym, _ in ranked[-3:]]

    signals = []
    for sym in top3:
        price = prices.get(sym)
        if price and price > 0:
            size = min(NEUTRAL_POSITION_SIZE, portfolio["cash"] + sum(p["size_usd"] for p in portfolio["positions"]))
            size = min(size, NEUTRAL_POSITION_SIZE)
            signals.append({
                "symbol": sym,
                "direction": "LONG",
                "size_usd": round(min(size, NEUTRAL_POSITION_SIZE), 2),
                "entry_price": price,
                "trailing_stop_pct": 0.15,  # wider for weekly holds
                "meta": {"rank": "top3", "portfolio": "neutral"},
            })
    for sym in bottom3:
        price = prices.get(sym)
        if price and price > 0:
            signals.append({
                "symbol": sym,
                "direction": "SHORT",
                "size_usd": round(min(NEUTRAL_POSITION_SIZE, 1666.67), 2),
                "entry_price": price,
                "trailing_stop_pct": 0.15,
                "meta": {"rank": "bottom3", "portfolio": "neutral"},
            })

    should_close = len(portfolio["positions"]) > 0
    return signals, should_close


# ---------------------------------------------------------------------------
# Portfolio 4: Copy Trader Best (follow 70%+ WR strategies)
# ---------------------------------------------------------------------------
COPY_MAX_PER_POSITION = 1000.0
COPY_MIN_TRADES = 10
COPY_MIN_WR = 0.70


def _load_json_safe(path: Path) -> list:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def _get_qualifying_strategies() -> dict[str, dict]:
    """Find strategies with 70%+ WR on 10+ closed trades. Returns {strategy: stats}."""
    closed = _load_json_safe(CLOSED_PICKS_FILE)
    strategy_stats: dict[str, dict] = {}
    for pick in closed:
        strat = pick.get("strategy", "unknown")
        if strat not in strategy_stats:
            strategy_stats[strat] = {"total": 0, "wins": 0, "pnl_sum": 0.0}
        strategy_stats[strat]["total"] += 1
        status = pick.get("status", "")
        if status in ("WON", "TP_HIT"):
            strategy_stats[strat]["wins"] += 1
        pnl = pick.get("pnl_pct")
        if pnl is not None:
            strategy_stats[strat]["pnl_sum"] += pnl

    qualifying = {}
    for strat, stats in strategy_stats.items():
        if stats["total"] >= COPY_MIN_TRADES:
            wr = stats["wins"] / stats["total"]
            if wr >= COPY_MIN_WR:
                qualifying[strat] = {
                    "win_rate": round(wr, 4),
                    "total_trades": stats["total"],
                    "wins": stats["wins"],
                    "avg_pnl": round(stats["pnl_sum"] / stats["total"], 6),
                }
    return qualifying


def evaluate_copy_entries(portfolio: dict, prices: dict) -> list[dict]:
    """Enter picks from qualifying strategies in active_picks.json."""
    qualifying = _get_qualifying_strategies()
    if not qualifying:
        return []

    active = _load_json_safe(ACTIVE_PICKS_FILE)
    held_ids = {p["meta"].get("pick_id") for p in portfolio["positions"] if p.get("meta")}
    signals = []

    for pick in active:
        strat = pick.get("strategy", "")
        if strat not in qualifying:
            continue
        pick_id = pick.get("id", "")
        if pick_id in held_ids:
            continue
        cat = pick.get("category", "")
        if cat != "crypto":
            continue
        sym = pick.get("symbol", "")
        price = prices.get(sym) or pick.get("entry_price")
        if not price or price <= 0:
            continue
        direction = pick.get("direction", "LONG")
        tp = pick.get("take_profit")
        sl = pick.get("stop_loss")
        size = min(COPY_MAX_PER_POSITION, portfolio["cash"])
        if size < 10:
            continue
        signals.append({
            "symbol": sym,
            "direction": direction,
            "size_usd": round(size, 2),
            "entry_price": price,
            "take_profit": tp,
            "stop_loss": sl,
            "trailing_stop_pct": 0.10,
            "meta": {
                "pick_id": pick_id,
                "strategy": strat,
                "strategy_wr": qualifying[strat]["win_rate"],
                "portfolio": "copy_trader",
            },
        })
    return signals


def evaluate_copy_exits(portfolio: dict, prices: dict) -> list[tuple[int, float, str]]:
    """Exit on pick's own TP/SL."""
    exits = []
    for i, pos in enumerate(portfolio["positions"]):
        price = prices.get(pos["symbol"])
        if price is None:
            continue
        direction = pos.get("direction", "LONG")
        tp = pos.get("take_profit")
        sl = pos.get("stop_loss")
        if direction == "LONG":
            if tp and price >= tp:
                exits.append((i, price, "TP_HIT"))
                continue
            if sl and price <= sl:
                exits.append((i, price, "SL_HIT"))
                continue
        else:  # SHORT
            if tp and price <= tp:
                exits.append((i, price, "TP_HIT"))
                continue
            if sl and price >= sl:
                exits.append((i, price, "SL_HIT"))
                continue
        # Fallback trailing stop
        if price > pos.get("high_water_mark", price):
            pos["high_water_mark"] = price
        if price < pos.get("low_water_mark", price):
            pos["low_water_mark"] = price
        if direction == "LONG":
            hwm = pos.get("high_water_mark", price)
            if hwm > 0 and (hwm - price) / hwm > pos.get("trailing_stop_pct", 0.10):
                exits.append((i, price, "TRAILING_STOP"))
        else:
            lwm = pos.get("low_water_mark", price)
            if lwm > 0 and (price - lwm) / lwm > pos.get("trailing_stop_pct", 0.10):
                exits.append((i, price, "TRAILING_STOP"))
    return exits


# ---------------------------------------------------------------------------
# Portfolio update engine
# ---------------------------------------------------------------------------
def _apply_exits(portfolio: dict, exits: list[tuple[int, float, str]]):
    """Close positions and move to closed_trades. Process in reverse index order."""
    for idx, exit_price, reason in sorted(exits, key=lambda x: x[0], reverse=True):
        if idx < len(portfolio["positions"]):
            pos = portfolio["positions"].pop(idx)
            trade = _close_position(pos, exit_price, reason)
            portfolio["closed_trades"].append(trade)
            portfolio["cash"] += pos["size_usd"] + trade["pnl_usd"]


def _apply_entries(portfolio: dict, signals: list[dict]):
    """Open new positions from signals."""
    for sig in signals:
        size = sig["size_usd"]
        if size > portfolio["cash"]:
            size = portfolio["cash"]
        if size < 10:
            continue
        pos = _new_position(
            symbol=sig["symbol"],
            direction=sig["direction"],
            entry_price=sig["entry_price"],
            size_usd=size,
            trailing_stop_pct=sig.get("trailing_stop_pct", 0.05),
            take_profit=sig.get("take_profit"),
            stop_loss=sig.get("stop_loss"),
            time_stop_hours=sig.get("time_stop_hours"),
            meta=sig.get("meta", {}),
        )
        portfolio["positions"].append(pos)
        portfolio["cash"] -= size


def _compute_nav(portfolio: dict, prices: dict) -> float:
    """NAV = cash + sum of mark-to-market position values."""
    nav = portfolio["cash"]
    for pos in portfolio["positions"]:
        price = prices.get(pos["symbol"], pos["entry_price"])
        direction = pos.get("direction", "LONG")
        if direction == "LONG":
            unrealized = (price - pos["entry_price"]) / pos["entry_price"] * pos["size_usd"]
        else:
            unrealized = (pos["entry_price"] - price) / pos["entry_price"] * pos["size_usd"]
        nav += pos["size_usd"] + unrealized
    return round(nav, 2)


def update_portfolio(portfolio: dict, prices: dict, klines_cache: dict,
                     returns_7d: dict, tickers_24h: dict):
    """Main cycle: evaluate exits, then entries, update NAV."""
    ptype = portfolio["type"]

    # --- Exits ---
    exits = []
    if ptype == "conservative":
        exits = evaluate_conservative_exits(portfolio, prices, klines_cache)
    elif ptype == "aggressive":
        exits = evaluate_aggressive_exits(portfolio, prices)
    elif ptype == "neutral":
        # Check if rebalance needed (closes all positions)
        new_signals, should_close = evaluate_neutral_rebalance(portfolio, prices, returns_7d)
        if should_close:
            # Close all positions
            all_exits = []
            for i, pos in enumerate(portfolio["positions"]):
                p = prices.get(pos["symbol"], pos["entry_price"])
                all_exits.append((i, p, "REBALANCE"))
            _apply_exits(portfolio, all_exits)
        if new_signals:
            _apply_entries(portfolio, new_signals)
        # Update NAV and return early for neutral
        nav = _compute_nav(portfolio, prices)
        portfolio["nav_history"].append({"ts": _iso(), "nav": nav})
        portfolio["last_updated"] = _iso()
        return
    elif ptype == "copy_trader":
        exits = evaluate_copy_exits(portfolio, prices)

    _apply_exits(portfolio, exits)

    # --- Entries ---
    entries = []
    if ptype == "conservative":
        entries = evaluate_conservative_entries(portfolio, prices, klines_cache)
    elif ptype == "aggressive":
        entries = evaluate_aggressive_entries(portfolio, prices, klines_cache, returns_7d, tickers_24h)
    elif ptype == "copy_trader":
        entries = evaluate_copy_entries(portfolio, prices)

    _apply_entries(portfolio, entries)

    # --- NAV ---
    nav = _compute_nav(portfolio, prices)
    portfolio["nav_history"].append({"ts": _iso(), "nav": nav})
    portfolio["last_updated"] = _iso()


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------
def compute_metrics(portfolio: dict) -> dict:
    """Compute Sharpe, Sortino, max drawdown, win rate, total return, profit factor."""
    nav_hist = portfolio.get("nav_history", [])
    closed = portfolio.get("closed_trades", [])

    # Total return
    initial = portfolio.get("initial_capital", INITIAL_CAPITAL)
    current_nav = nav_hist[-1]["nav"] if nav_hist else initial
    total_return_pct = (current_nav - initial) / initial * 100.0

    # NAV-based returns for Sharpe/Sortino
    navs = [h["nav"] for h in nav_hist]
    returns = []
    for i in range(1, len(navs)):
        if navs[i - 1] > 0:
            returns.append((navs[i] - navs[i - 1]) / navs[i - 1])

    # Sharpe (annualized, assume 48 updates/day for 30min intervals)
    sharpe = 0.0
    sortino = 0.0
    if len(returns) >= 2:
        mean_r = np.mean(returns)
        std_r = np.std(returns, ddof=1)
        if std_r > 0:
            sharpe = (mean_r / std_r) * math.sqrt(48 * 365)
        # Sortino
        downside = [r for r in returns if r < 0]
        if downside:
            down_std = np.std(downside, ddof=1) if len(downside) > 1 else abs(downside[0])
            if down_std > 0:
                sortino = (mean_r / down_std) * math.sqrt(48 * 365)

    # Max drawdown
    max_dd = 0.0
    peak = 0.0
    for nav_val in navs:
        if nav_val > peak:
            peak = nav_val
        if peak > 0:
            dd = (peak - nav_val) / peak
            if dd > max_dd:
                max_dd = dd

    # Win rate
    wins = sum(1 for t in closed if t.get("pnl_usd", 0) > 0)
    total_trades = len(closed)
    win_rate = wins / total_trades if total_trades > 0 else 0.0

    # Profit factor
    gross_profit = sum(t["pnl_usd"] for t in closed if t.get("pnl_usd", 0) > 0)
    gross_loss = abs(sum(t["pnl_usd"] for t in closed if t.get("pnl_usd", 0) < 0))
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else (999.0 if gross_profit > 0 else 0.0)

    return {
        "nav": round(current_nav, 2),
        "total_return_pct": round(total_return_pct, 4),
        "sharpe": round(sharpe, 4),
        "sortino": round(sortino, 4),
        "max_drawdown_pct": round(max_dd * 100, 4),
        "win_rate": round(win_rate, 4),
        "total_trades": total_trades,
        "wins": wins,
        "losses": total_trades - wins,
        "profit_factor": round(profit_factor, 4),
        "open_positions": len(portfolio.get("positions", [])),
        "cash": round(portfolio.get("cash", 0), 2),
    }


# ---------------------------------------------------------------------------
# State persistence
# ---------------------------------------------------------------------------
def load_state() -> dict:
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def save_state(state: dict):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    tmp = STATE_FILE.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, default=str)
    tmp.replace(STATE_FILE)


def save_results(results: dict):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    tmp = RESULTS_FILE.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, default=str)
    tmp.replace(RESULTS_FILE)


# ---------------------------------------------------------------------------
# Main runner
# ---------------------------------------------------------------------------
def run_all_portfolios(report_only: bool = False):
    """Run all 4 portfolios, compute metrics, save state + results."""
    print(f"{'=' * 60}")
    print(f"  CRYPTO TEST PORTFOLIOS -- {_iso()}")
    print(f"{'=' * 60}")

    # Load state
    state = load_state()

    # Initialize portfolios if missing
    portfolio_defs = [
        ("conservative", "Crypto Conservative"),
        ("aggressive", "Crypto Aggressive"),
        ("neutral", "Crypto Market Neutral"),
        ("copy_trader", "Copy Trader Best"),
    ]
    for ptype, pname in portfolio_defs:
        if ptype not in state:
            state[ptype] = _default_portfolio(pname, ptype)

    if report_only:
        _print_comparison(state)
        return

    # Fetch market data
    print("\n[1/4] Fetching prices...")
    all_symbols = list(set(
        CONSERVATIVE_SYMBOLS + TOP20_SYMBOLS +
        [p["symbol"] for pf in state.values() if isinstance(pf, dict)
         for p in pf.get("positions", [])]
    ))
    prices = fetch_crypto_prices(all_symbols)
    print(f"  Got prices for {len(prices)} symbols")

    print("[2/4] Fetching klines for indicators...")
    klines_cache: dict[str, list] = {}
    # Only fetch klines for symbols we need indicators on
    kline_symbols = list(set(CONSERVATIVE_SYMBOLS + TOP20_SYMBOLS))
    for sym in kline_symbols:
        kl = fetch_klines(sym, "1d", 210)
        if kl:
            klines_cache[sym] = kl
        time.sleep(0.1)  # rate limit courtesy
    print(f"  Got klines for {len(klines_cache)} symbols")

    print("[3/4] Computing 7-day returns...")
    returns_7d = {}
    for sym in TOP20_SYMBOLS:
        kl = klines_cache.get(sym)
        if kl and len(kl) >= 8:
            try:
                close_now = float(kl[-1][4])
                close_7d = float(kl[-8][4]) if len(kl) >= 8 else float(kl[0][4])
                if close_7d > 0:
                    returns_7d[sym] = (close_now - close_7d) / close_7d * 100.0
            except (IndexError, ValueError):
                pass
    print(f"  Got 7d returns for {len(returns_7d)} symbols")

    # Also fetch dynamic top gainers for aggressive small-cap bucket
    tickers_24h = {}
    all_tickers = fetch_24h_tickers()
    for t in all_tickers:
        sym = t.get("symbol", "")
        if sym.endswith("USDT"):
            try:
                tickers_24h[sym] = {
                    "price": float(t.get("lastPrice", 0)),
                    "volume": float(t.get("quoteVolume", 0)),
                    "change_pct": float(t.get("priceChangePercent", 0)),
                }
                # Add price to prices dict if missing
                if sym not in prices and tickers_24h[sym]["price"] > 0:
                    prices[sym] = tickers_24h[sym]["price"]
            except (ValueError, TypeError):
                pass

    # Add top gainers to returns_7d for aggressive portfolio
    # Use 24h change as proxy for small-caps not in TOP20
    top_gainers = sorted(
        [(sym, info["change_pct"]) for sym, info in tickers_24h.items()
         if info["volume"] > 1_000_000 and sym not in TOP20_SYMBOLS],
        key=lambda x: x[1], reverse=True,
    )[:20]
    for sym, change in top_gainers:
        if sym not in returns_7d:
            returns_7d[sym] = change  # approximate

    print("[4/4] Updating portfolios...")
    for ptype, pname in portfolio_defs:
        try:
            update_portfolio(state[ptype], prices, klines_cache, returns_7d, tickers_24h)
            print(f"  {pname}: OK")
        except Exception as e:
            print(f"  {pname}: ERROR - {e}")
            traceback.print_exc()

    # Compute and display metrics
    _print_comparison(state)

    # Save
    save_state(state)

    results = {
        "timestamp": _iso(),
        "portfolios": {},
    }
    for ptype, pname in portfolio_defs:
        metrics = compute_metrics(state[ptype])
        results["portfolios"][ptype] = {
            "name": pname,
            "metrics": metrics,
        }
    # Add copy trader strategy breakdown
    if "copy_trader" in state:
        qualifying = _get_qualifying_strategies()
        results["portfolios"]["copy_trader"]["qualifying_strategies"] = qualifying
        # Per-strategy performance from closed trades
        strat_perf: dict[str, dict] = {}
        for trade in state["copy_trader"].get("closed_trades", []):
            strat = trade.get("meta", {}).get("strategy", "unknown")
            if strat not in strat_perf:
                strat_perf[strat] = {"trades": 0, "wins": 0, "pnl_sum": 0.0}
            strat_perf[strat]["trades"] += 1
            if trade.get("pnl_usd", 0) > 0:
                strat_perf[strat]["wins"] += 1
            strat_perf[strat]["pnl_sum"] += trade.get("pnl_usd", 0)
        results["portfolios"]["copy_trader"]["strategy_breakdown"] = strat_perf

    save_results(results)
    print(f"\nState saved to {STATE_FILE}")
    print(f"Results saved to {RESULTS_FILE}")


def _print_comparison(state: dict):
    """Print comparison table of all portfolios."""
    print(f"\n{'=' * 80}")
    print(f"  PORTFOLIO COMPARISON TABLE -- {_iso()}")
    print(f"{'=' * 80}")
    header = f"{'Portfolio':<22} {'NAV':>10} {'Return%':>9} {'Sharpe':>8} {'Sortino':>8} {'MaxDD%':>8} {'WinRate':>8} {'Trades':>7} {'PF':>7}"
    print(header)
    print("-" * 80)

    for ptype in ["conservative", "aggressive", "neutral", "copy_trader"]:
        pf = state.get(ptype)
        if not pf:
            continue
        m = compute_metrics(pf)
        row = (
            f"{pf['name']:<22} "
            f"${m['nav']:>9,.2f} "
            f"{m['total_return_pct']:>8.2f}% "
            f"{m['sharpe']:>8.2f} "
            f"{m['sortino']:>8.2f} "
            f"{m['max_drawdown_pct']:>7.2f}% "
            f"{m['win_rate']:>7.1%} "
            f"{m['total_trades']:>7d} "
            f"{m['profit_factor']:>7.2f}"
        )
        print(row)
    print("-" * 80)
    print(f"  Open positions: ", end="")
    for ptype in ["conservative", "aggressive", "neutral", "copy_trader"]:
        pf = state.get(ptype)
        if pf:
            n = len(pf.get("positions", []))
            print(f"{pf['name'].split()[-1]}={n}  ", end="")
    print()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    # Windows UTF-8 fix
    if sys.platform == "win32":
        try:
            sys.stdout.reconfigure(encoding="utf-8")
            sys.stderr.reconfigure(encoding="utf-8")
        except Exception:
            pass

    report_only = "--report" in sys.argv
    run_all_portfolios(report_only=report_only)
