#!/usr/bin/env python3
"""
Crypto Portfolio A/B/C/D Backtesting System
============================================
Downloads 90 days of 4H candles for top 12 crypto pairs via api_failover,
then backtests 4 portfolio variants with different entry conditions.

Portfolio A (Golden Filter):    LONG only, Confidence >= 0.70, R:R 1-2x
Portfolio B (Copy Trader Only): copy_hl_NMTD_25M + binance_smart_money picks
Portfolio C (Momentum+Volume):  Price > 20-EMA, Vol > 2x avg, RSI 40-65
Portfolio D (Mean Reversion):   RSI(2) < 10, Price > 200-SMA, oversold bounce

Results saved to alpha_engine/data/crypto_portfolio_backtest.json
"""

from __future__ import annotations

import json
import logging
import math
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# Windows UTF-8 fix
if sys.platform == "win32":
    for _s in (sys.stdout, sys.stderr):
        if hasattr(_s, "reconfigure"):
            try:
                _s.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass

# Setup path so we can import api_failover
sys.path.insert(0, str(Path(__file__).resolve().parent))

try:
    from api_failover import fetch_klines
except ImportError:
    # Fallback: define minimal fetch_klines using urllib
    import urllib.request
    import urllib.error

    _BINANCE_BASES = [
        "https://data-api.binance.vision",
        "https://api.binance.us",
        "https://api.binance.com",
        "https://api1.binance.com",
        "https://api2.binance.com",
        "https://api3.binance.com",
    ]
    _BYBIT_BASE = "https://api.bybit.com"

    def fetch_klines(symbol, interval="4h", limit=100):
        """Minimal failover fetch_klines."""
        import json as _json
        for base in _BINANCE_BASES:
            try:
                url = f"{base}/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
                req = urllib.request.Request(url, headers={"User-Agent": "CryptoBacktest/1.0"})
                with urllib.request.urlopen(req, timeout=10) as resp:
                    data = _json.loads(resp.read())
                    if isinstance(data, list) and len(data) > 0:
                        return data
            except Exception:
                continue
        # Bybit fallback
        _interval_map = {"4h": "240", "1h": "60", "1d": "D"}
        bi = _interval_map.get(interval, "240")
        try:
            url = f"{_BYBIT_BASE}/v5/market/kline?category=linear&symbol={symbol}&interval={bi}&limit={limit}"
            req = urllib.request.Request(url, headers={"User-Agent": "CryptoBacktest/1.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = _json.loads(resp.read())
                if data and data.get("retCode") == 0:
                    raw = data.get("result", {}).get("list", [])
                    if raw:
                        return [[int(k[0]), k[1], k[2], k[3], k[4], k[5]] for k in reversed(raw)]
        except Exception:
            pass
        return None


logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("crypto_backtest")

# ============================================================================
# Constants
# ============================================================================
SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT", "DOGEUSDT",
    "AVAXUSDT", "DOTUSDT", "LINKUSDT", "NEARUSDT", "FETUSDT", "RENDERUSDT",
]

INTERVAL = "4h"
# 90 days * 6 candles/day = 540 candles
CANDLES_NEEDED = 540
INITIAL_CAPITAL = 10000.0
POSITION_SIZE_PCT = 0.05  # 5% of capital per trade


# ============================================================================
# Helpers: Technical Indicators (pure Python + no numpy dependency at runtime)
# ============================================================================
def _to_floats(klines: list, idx: int) -> list:
    """Extract float values from kline column index."""
    result = []
    for k in klines:
        try:
            result.append(float(k[idx]))
        except (ValueError, TypeError, IndexError):
            result.append(0.0)
    return result


def ema(data: list, period: int) -> list:
    """Exponential moving average."""
    if len(data) < period:
        return [None] * len(data)
    result = [None] * (period - 1)
    k = 2.0 / (period + 1)
    # seed with SMA
    sma_val = sum(data[:period]) / period
    result.append(sma_val)
    for i in range(period, len(data)):
        val = data[i] * k + result[-1] * (1 - k)
        result.append(val)
    return result


def sma(data: list, period: int) -> list:
    """Simple moving average."""
    result = [None] * (period - 1)
    for i in range(period - 1, len(data)):
        result.append(sum(data[i - period + 1:i + 1]) / period)
    return result


def rsi(data: list, period: int = 14) -> list:
    """Relative Strength Index."""
    if len(data) < period + 1:
        return [None] * len(data)
    deltas = [data[i] - data[i - 1] for i in range(1, len(data))]
    gains = [max(0, d) for d in deltas]
    losses = [max(0, -d) for d in deltas]

    result = [None] * period  # first 'period' values are None (shifted by 1 from deltas)

    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    if avg_loss == 0:
        result.append(100.0)
    else:
        rs = avg_gain / avg_loss
        result.append(100.0 - 100.0 / (1.0 + rs))

    for i in range(period, len(deltas)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        if avg_loss == 0:
            result.append(100.0)
        else:
            rs = avg_gain / avg_loss
            result.append(100.0 - 100.0 / (1.0 + rs))

    return result


def atr(highs: list, lows: list, closes: list, period: int = 14) -> list:
    """Average True Range."""
    if len(closes) < 2:
        return [None] * len(closes)
    trs = [highs[0] - lows[0]]  # first TR is just high-low
    for i in range(1, len(closes)):
        tr = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1])
        )
        trs.append(tr)

    result = [None] * (period - 1)
    atr_val = sum(trs[:period]) / period
    result.append(atr_val)
    for i in range(period, len(trs)):
        atr_val = (atr_val * (period - 1) + trs[i]) / period
        result.append(atr_val)
    return result


def volume_sma(volumes: list, period: int = 20) -> list:
    """Volume simple moving average."""
    return sma(volumes, period)


# ============================================================================
# Data Download
# ============================================================================
def download_candles(symbols: list, interval: str = "4h",
                     limit: int = 540) -> dict:
    """Download candles for all symbols using api_failover.

    Returns: {symbol: {opens, highs, lows, closes, volumes, timestamps}}
    """
    data = {}
    # Binance API max klines per request is 1000, so 540 is fine in one call
    for sym in symbols:
        log.info("Downloading %s %s candles (limit=%d)...", sym, interval, limit)
        klines = fetch_klines(sym, interval, limit)
        if not klines or len(klines) < 50:
            log.warning("  %s: only got %d candles, skipping",
                        sym, len(klines) if klines else 0)
            continue

        timestamps = _to_floats(klines, 0)
        opens = _to_floats(klines, 1)
        highs = _to_floats(klines, 2)
        lows = _to_floats(klines, 3)
        closes = _to_floats(klines, 4)
        volumes = _to_floats(klines, 5)

        data[sym] = {
            "timestamps": timestamps,
            "opens": opens,
            "highs": highs,
            "lows": lows,
            "closes": closes,
            "volumes": volumes,
            "count": len(klines),
        }
        log.info("  %s: %d candles downloaded", sym, len(klines))
        # Rate limiting between calls
        time.sleep(0.3)

    return data


# ============================================================================
# Trade Tracking
# ============================================================================
class Trade:
    """Single trade record."""
    def __init__(self, symbol: str, direction: str, entry_price: float,
                 tp_price: float, sl_price: float, entry_time: float,
                 strategy: str = ""):
        self.symbol = symbol
        self.direction = direction  # LONG or SHORT
        self.entry_price = entry_price
        self.tp_price = tp_price
        self.sl_price = sl_price
        self.entry_time = entry_time
        self.exit_price = 0.0
        self.exit_time = 0.0
        self.pnl_pct = 0.0
        self.result = ""  # WIN, LOSS, TIMEOUT
        self.strategy = strategy
        self.closed = False

    def check_exit(self, high: float, low: float, close: float,
                   timestamp: float) -> bool:
        """Check if TP or SL hit. Returns True if trade closed."""
        if self.closed:
            return True

        if self.direction == "LONG":
            # Check SL first (worst case)
            if low <= self.sl_price:
                self.exit_price = self.sl_price
                self.pnl_pct = (self.sl_price - self.entry_price) / self.entry_price * 100
                self.result = "LOSS"
                self.closed = True
            # Check TP
            elif high >= self.tp_price:
                self.exit_price = self.tp_price
                self.pnl_pct = (self.tp_price - self.entry_price) / self.entry_price * 100
                self.result = "WIN"
                self.closed = True
        else:  # SHORT
            if high >= self.sl_price:
                self.exit_price = self.sl_price
                self.pnl_pct = (self.entry_price - self.sl_price) / self.entry_price * 100
                self.result = "LOSS"
                self.closed = True
            elif low <= self.tp_price:
                self.exit_price = self.tp_price
                self.pnl_pct = (self.entry_price - self.tp_price) / self.entry_price * 100
                self.result = "WIN"
                self.closed = True

        if self.closed:
            self.exit_time = timestamp
        return self.closed

    def force_close(self, close: float, timestamp: float):
        """Force close at current price (timeout/end of backtest)."""
        if self.closed:
            return
        self.exit_price = close
        self.exit_time = timestamp
        if self.direction == "LONG":
            self.pnl_pct = (close - self.entry_price) / self.entry_price * 100
        else:
            self.pnl_pct = (self.entry_price - close) / self.entry_price * 100
        self.result = "WIN" if self.pnl_pct > 0 else "LOSS"
        self.closed = True


class TrailingTrade(Trade):
    """Trade with trailing stop functionality."""
    def __init__(self, symbol, direction, entry_price, tp_price, sl_price,
                 entry_time, trail_pct=3.0, strategy=""):
        super().__init__(symbol, direction, entry_price, tp_price, sl_price,
                         entry_time, strategy)
        self.trail_pct = trail_pct
        self.peak_price = entry_price if direction == "LONG" else entry_price
        self.trailing_sl = sl_price

    def check_exit(self, high, low, close, timestamp):
        if self.closed:
            return True

        if self.direction == "LONG":
            # Update peak and trailing SL
            if high > self.peak_price:
                self.peak_price = high
                new_trailing = self.peak_price * (1 - self.trail_pct / 100)
                if new_trailing > self.trailing_sl:
                    self.trailing_sl = new_trailing

            # Check trailing SL
            if low <= self.trailing_sl:
                self.exit_price = self.trailing_sl
                self.pnl_pct = (self.trailing_sl - self.entry_price) / self.entry_price * 100
                self.result = "WIN" if self.pnl_pct > 0 else "LOSS"
                self.closed = True
            # Check TP
            elif high >= self.tp_price:
                self.exit_price = self.tp_price
                self.pnl_pct = (self.tp_price - self.entry_price) / self.entry_price * 100
                self.result = "WIN"
                self.closed = True
        else:  # SHORT
            if low < self.peak_price:
                self.peak_price = low
                new_trailing = self.peak_price * (1 + self.trail_pct / 100)
                if new_trailing < self.trailing_sl:
                    self.trailing_sl = new_trailing

            if high >= self.trailing_sl:
                self.exit_price = self.trailing_sl
                self.pnl_pct = (self.entry_price - self.trailing_sl) / self.entry_price * 100
                self.result = "WIN" if self.pnl_pct > 0 else "LOSS"
                self.closed = True
            elif low <= self.tp_price:
                self.exit_price = self.tp_price
                self.pnl_pct = (self.entry_price - self.tp_price) / self.entry_price * 100
                self.result = "WIN"
                self.closed = True

        if self.closed:
            self.exit_time = timestamp
        return self.closed


class RSIExitTrade(Trade):
    """Trade that exits when RSI reaches a target (for mean reversion)."""
    def __init__(self, symbol, direction, entry_price, sl_price,
                 entry_time, rsi_target=60.0, strategy=""):
        # Set TP very high - RSI target handles exit
        tp_price = entry_price * 1.20 if direction == "LONG" else entry_price * 0.80
        super().__init__(symbol, direction, entry_price, tp_price, sl_price,
                         entry_time, strategy)
        self.rsi_target = rsi_target
        self.rsi_exit = False

    def check_exit_with_rsi(self, high, low, close, timestamp, current_rsi):
        """Check exits including RSI target."""
        if self.closed:
            return True

        # Check SL first
        if self.direction == "LONG" and low <= self.sl_price:
            self.exit_price = self.sl_price
            self.pnl_pct = (self.sl_price - self.entry_price) / self.entry_price * 100
            self.result = "LOSS"
            self.closed = True
            self.exit_time = timestamp
            return True

        # Check RSI target
        if current_rsi is not None and current_rsi > self.rsi_target:
            self.exit_price = close
            self.pnl_pct = (close - self.entry_price) / self.entry_price * 100
            self.result = "WIN" if self.pnl_pct > 0 else "LOSS"
            self.rsi_exit = True
            self.closed = True
            self.exit_time = timestamp
            return True

        return False


# ============================================================================
# Portfolio Metrics
# ============================================================================
def compute_metrics(trades: list, initial_capital: float = 10000.0) -> dict:
    """Compute portfolio performance metrics from trade list."""
    if not trades:
        return {
            "win_rate": 0, "profit_factor": 0, "sharpe": 0, "sortino": 0,
            "max_drawdown_pct": 0, "total_return_pct": 0, "num_trades": 0,
            "best_trade_pct": 0, "worst_trade_pct": 0, "avg_trade_pct": 0,
            "wins": 0, "losses": 0, "gross_profit": 0, "gross_loss": 0,
        }

    pnls = [t.pnl_pct for t in trades]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p <= 0]

    win_rate = len(wins) / len(pnls) * 100 if pnls else 0
    gross_profit = sum(wins)
    gross_loss = abs(sum(losses))
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else (
        999.0 if gross_profit > 0 else 0.0)

    # Equity curve for drawdown
    equity = initial_capital
    equity_curve = [initial_capital]
    for pnl_pct in pnls:
        trade_pnl = equity * POSITION_SIZE_PCT * (pnl_pct / 100)
        equity += trade_pnl
        equity_curve.append(equity)

    # Max drawdown
    peak = equity_curve[0]
    max_dd = 0.0
    for eq in equity_curve:
        if eq > peak:
            peak = eq
        dd = (peak - eq) / peak * 100 if peak > 0 else 0
        if dd > max_dd:
            max_dd = dd

    total_return = (equity_curve[-1] - initial_capital) / initial_capital * 100

    # Sharpe & Sortino (annualized, assuming 4H bars ~ 6 trades/day)
    avg_pnl = sum(pnls) / len(pnls) if pnls else 0
    if len(pnls) > 1:
        variance = sum((p - avg_pnl) ** 2 for p in pnls) / (len(pnls) - 1)
        std_dev = math.sqrt(variance) if variance > 0 else 0.001
        # Annualize: ~1460 4H periods/year, but trades are less frequent
        # Use sqrt(N) where N = approximate trades per year
        annual_factor = math.sqrt(len(pnls) * (365 / 90))  # scale from 90d to 365d
        sharpe = (avg_pnl / std_dev) * annual_factor if std_dev > 0 else 0

        # Sortino: only downside deviation
        downside = [p for p in pnls if p < 0]
        if downside:
            down_var = sum(p ** 2 for p in downside) / len(downside)
            down_std = math.sqrt(down_var) if down_var > 0 else 0.001
            sortino = (avg_pnl / down_std) * annual_factor if down_std > 0 else 0
        else:
            sortino = sharpe * 2  # no losses = great sortino
    else:
        sharpe = 0
        sortino = 0

    best_trade = max(pnls) if pnls else 0
    worst_trade = min(pnls) if pnls else 0

    # Find best/worst trade details
    best_t = max(trades, key=lambda t: t.pnl_pct) if trades else None
    worst_t = min(trades, key=lambda t: t.pnl_pct) if trades else None

    return {
        "win_rate": round(win_rate, 2),
        "profit_factor": round(profit_factor, 3),
        "sharpe": round(sharpe, 3),
        "sortino": round(sortino, 3),
        "max_drawdown_pct": round(max_dd, 2),
        "total_return_pct": round(total_return, 2),
        "num_trades": len(trades),
        "best_trade_pct": round(best_trade, 3),
        "worst_trade_pct": round(worst_trade, 3),
        "avg_trade_pct": round(avg_pnl, 3),
        "wins": len(wins),
        "losses": len(losses),
        "gross_profit": round(gross_profit, 3),
        "gross_loss": round(gross_loss, 3),
        "final_equity": round(equity_curve[-1], 2),
        "best_trade_detail": f"{best_t.symbol} {best_t.pnl_pct:+.2f}%" if best_t else "",
        "worst_trade_detail": f"{worst_t.symbol} {worst_t.pnl_pct:+.2f}%" if worst_t else "",
    }


# ============================================================================
# Portfolio A: Golden Filter (LONG only, Confidence >= 0.70, R:R 1-2x)
# ============================================================================
def backtest_portfolio_a(market_data: dict) -> dict:
    """Portfolio A: Golden Filter.

    LONG only + simulated confidence >= 0.70 + R:R [1.0, 2.0)
    TP: 1.5x ATR, SL: 1.0x ATR

    Confidence proxy: We use a composite of RSI not overbought (< 70),
    price above EMA20, and positive momentum as confidence filter.
    """
    log.info("=== Backtesting Portfolio A: Golden Filter ===")
    all_trades = []

    for sym, d in market_data.items():
        closes = d["closes"]
        highs = d["highs"]
        lows = d["lows"]
        volumes = d["volumes"]
        timestamps = d["timestamps"]
        n = len(closes)

        if n < 220:
            continue

        ema20 = ema(closes, 20)
        rsi14 = rsi(closes, 14)
        atr14 = atr(highs, lows, closes, 14)
        ema50 = ema(closes, 50)

        open_trades = []

        for i in range(200, n):
            # Check open trades
            still_open = []
            for t in open_trades:
                if not t.check_exit(highs[i], lows[i], closes[i], timestamps[i]):
                    still_open.append(t)
            open_trades = still_open

            # Skip if already have open trade for this symbol
            if any(t.symbol == sym and not t.closed for t in open_trades):
                continue

            # Golden filter conditions:
            if (ema20[i] is None or rsi14[i] is None or atr14[i] is None
                    or ema50[i] is None):
                continue

            # Confidence proxy: trending + not overbought + volume confirmation
            trending = closes[i] > ema20[i] and ema20[i] > ema50[i]
            not_overbought = 30 < rsi14[i] < 70
            momentum = closes[i] > closes[i - 4]  # positive 4-bar momentum

            # Simulate confidence score
            confidence = 0.0
            if trending:
                confidence += 0.35
            if not_overbought:
                confidence += 0.25
            if momentum:
                confidence += 0.20
            if volumes[i] > 0 and i >= 1 and volumes[i] > volumes[i - 1]:
                confidence += 0.15
            # Small RSI bonus
            if rsi14[i] and 45 < rsi14[i] < 60:
                confidence += 0.05

            if confidence < 0.70:
                continue

            # R:R check: TP = 1.5x ATR, SL = 1.0x ATR
            tp_dist = 1.5 * atr14[i]
            sl_dist = 1.0 * atr14[i]
            rr = tp_dist / sl_dist if sl_dist > 0 else 0
            if rr < 1.0 or rr >= 2.0:
                continue

            entry = closes[i]
            tp = entry + tp_dist
            sl = entry - sl_dist

            trade = Trade(sym, "LONG", entry, tp, sl, timestamps[i],
                          strategy="golden_filter")
            open_trades.append(trade)
            all_trades.append(trade)

        # Force close remaining
        for t in open_trades:
            if not t.closed:
                t.force_close(closes[-1], timestamps[-1])

    metrics = compute_metrics(all_trades)
    log.info("Portfolio A: %d trades, WR=%.1f%%, PF=%.3f, Return=%.2f%%",
             metrics["num_trades"], metrics["win_rate"],
             metrics["profit_factor"], metrics["total_return_pct"])
    return {"name": "Portfolio A: Golden Filter", "metrics": metrics,
            "description": "LONG only + Confidence >= 0.70 + R:R [1.0-2.0) + TP 1.5x ATR / SL 1.0x ATR"}


# ============================================================================
# Portfolio B: Copy Trader Only (simulated copy_hl_NMTD_25M + smart money)
# ============================================================================
def backtest_portfolio_b(market_data: dict) -> dict:
    """Portfolio B: Copy Trader Only.

    Simulates copy_hl_NMTD_25M (81% WR) and binance_smart_money (55% WR).
    Uses tight TP/SL based on historical performance.

    copy_hl_NMTD_25M: High-leverage NMTD strategy (tight stops, quick TP)
    binance_smart_money: Follows whale wallet accumulation patterns
    """
    log.info("=== Backtesting Portfolio B: Copy Trader Only ===")
    all_trades = []

    for sym, d in market_data.items():
        closes = d["closes"]
        highs = d["highs"]
        lows = d["lows"]
        volumes = d["volumes"]
        timestamps = d["timestamps"]
        n = len(closes)

        if n < 220:
            continue

        ema9 = ema(closes, 9)
        ema21 = ema(closes, 21)
        rsi14 = rsi(closes, 14)
        atr14 = atr(highs, lows, closes, 14)
        vol_sma = volume_sma(volumes, 20)

        open_trades = []

        for i in range(200, n):
            still_open = []
            for t in open_trades:
                if not t.check_exit(highs[i], lows[i], closes[i], timestamps[i]):
                    still_open.append(t)
            open_trades = still_open

            if any(t.symbol == sym and not t.closed for t in open_trades):
                continue

            if (ema9[i] is None or ema21[i] is None or rsi14[i] is None
                    or atr14[i] is None or vol_sma[i] is None):
                continue

            # Strategy 1: copy_hl_NMTD_25M (81% WR) - tight scalp
            # Fast EMA cross + momentum + volume spike
            nmtd_signal = (
                ema9[i] > ema21[i]
                and ema9[i - 1] is not None and ema21[i - 1] is not None
                and (ema9[i - 1] <= ema21[i - 1] or  # fresh cross
                     (ema9[i] - ema21[i]) > (ema9[i - 1] - ema21[i - 1]))  # accelerating
                and rsi14[i] > 50
                and rsi14[i] < 75
                and vol_sma[i] > 0
                and volumes[i] > vol_sma[i] * 1.3
            )

            # Strategy 2: binance_smart_money (55% WR) - whale accumulation
            # Look for volume spike with price consolidation (accumulation)
            smart_money_signal = (
                vol_sma[i] > 0
                and volumes[i] > vol_sma[i] * 2.5  # big volume spike
                and abs(closes[i] - closes[i - 1]) / closes[i - 1] < 0.02  # low price change
                and closes[i] > ema21[i]  # above trend
                and rsi14[i] > 40 and rsi14[i] < 65
            )

            if nmtd_signal:
                entry = closes[i]
                # NMTD uses tight stops: TP ~2%, SL ~1%
                tp = entry * 1.02
                sl = entry * 0.99
                trade = Trade(sym, "LONG", entry, tp, sl, timestamps[i],
                              strategy="copy_hl_NMTD_25M")
                open_trades.append(trade)
                all_trades.append(trade)

            elif smart_money_signal:
                entry = closes[i]
                # Smart money: wider TP/SL based on ATR
                tp = entry + 2.0 * atr14[i]
                sl = entry - 1.5 * atr14[i]
                trade = Trade(sym, "LONG", entry, tp, sl, timestamps[i],
                              strategy="binance_smart_money")
                open_trades.append(trade)
                all_trades.append(trade)

        for t in open_trades:
            if not t.closed:
                t.force_close(closes[-1], timestamps[-1])

    metrics = compute_metrics(all_trades)
    log.info("Portfolio B: %d trades, WR=%.1f%%, PF=%.3f, Return=%.2f%%",
             metrics["num_trades"], metrics["win_rate"],
             metrics["profit_factor"], metrics["total_return_pct"])

    # Per-strategy breakdown
    nmtd_trades = [t for t in all_trades if t.strategy == "copy_hl_NMTD_25M"]
    sm_trades = [t for t in all_trades if t.strategy == "binance_smart_money"]

    return {
        "name": "Portfolio B: Copy Trader Only",
        "metrics": metrics,
        "description": "copy_hl_NMTD_25M (81% WR) + binance_smart_money (55% WR) picks",
        "sub_strategies": {
            "copy_hl_NMTD_25M": compute_metrics(nmtd_trades),
            "binance_smart_money": compute_metrics(sm_trades),
        }
    }


# ============================================================================
# Portfolio C: Momentum + Volume
# ============================================================================
def backtest_portfolio_c(market_data: dict) -> dict:
    """Portfolio C: Momentum + Volume.

    Enter when: Price > 20-EMA AND Volume > 2x average AND RSI(14) 40-65
    TP: +5%, SL: -3%, trailing stop at 3% from peak
    LONG only in bull regime, SHORT allowed in bear
    """
    log.info("=== Backtesting Portfolio C: Momentum + Volume ===")
    all_trades = []

    for sym, d in market_data.items():
        closes = d["closes"]
        highs = d["highs"]
        lows = d["lows"]
        volumes = d["volumes"]
        timestamps = d["timestamps"]
        n = len(closes)

        if n < 220:
            continue

        ema20 = ema(closes, 20)
        rsi14 = rsi(closes, 14)
        vol_avg = volume_sma(volumes, 20)
        sma200 = sma(closes, 200)

        open_trades = []

        for i in range(200, n):
            still_open = []
            for t in open_trades:
                if not t.check_exit(highs[i], lows[i], closes[i], timestamps[i]):
                    still_open.append(t)
            open_trades = still_open

            if any(t.symbol == sym and not t.closed for t in open_trades):
                continue

            if (ema20[i] is None or rsi14[i] is None or vol_avg[i] is None
                    or sma200[i] is None):
                continue

            # Regime detection
            bull_regime = closes[i] > sma200[i]
            bear_regime = closes[i] < sma200[i]

            # Volume spike
            vol_spike = vol_avg[i] > 0 and volumes[i] > 2.0 * vol_avg[i]

            # LONG signal: price > 20-EMA, vol > 2x avg, RSI 40-65
            if (bull_regime and closes[i] > ema20[i] and vol_spike
                    and 40 <= rsi14[i] <= 65):
                entry = closes[i]
                tp = entry * 1.05  # +5%
                sl = entry * 0.97  # -3%
                trade = TrailingTrade(sym, "LONG", entry, tp, sl,
                                      timestamps[i], trail_pct=3.0,
                                      strategy="momentum_volume_long")
                open_trades.append(trade)
                all_trades.append(trade)

            # SHORT signal: bear regime, price < 20-EMA, vol spike, RSI 40-65
            elif (bear_regime and closes[i] < ema20[i] and vol_spike
                  and 40 <= rsi14[i] <= 65):
                entry = closes[i]
                tp = entry * 0.95  # -5% target
                sl = entry * 1.03  # +3% stop
                trade = TrailingTrade(sym, "SHORT", entry, tp, sl,
                                      timestamps[i], trail_pct=3.0,
                                      strategy="momentum_volume_short")
                open_trades.append(trade)
                all_trades.append(trade)

        for t in open_trades:
            if not t.closed:
                t.force_close(closes[-1], timestamps[-1])

    metrics = compute_metrics(all_trades)
    log.info("Portfolio C: %d trades, WR=%.1f%%, PF=%.3f, Return=%.2f%%",
             metrics["num_trades"], metrics["win_rate"],
             metrics["profit_factor"], metrics["total_return_pct"])
    return {"name": "Portfolio C: Momentum + Volume", "metrics": metrics,
            "description": "Price > 20-EMA + Vol > 2x avg + RSI 40-65, TP +5% / SL -3% / Trailing 3%"}


# ============================================================================
# Portfolio D: Mean Reversion
# ============================================================================
def backtest_portfolio_d(market_data: dict) -> dict:
    """Portfolio D: Mean Reversion.

    Enter when: RSI(2) < 10 AND Price > 200-SMA (oversold bounce in uptrend)
    TP: RSI(2) > 60, SL: -3%
    BUY only
    """
    log.info("=== Backtesting Portfolio D: Mean Reversion ===")
    all_trades = []

    for sym, d in market_data.items():
        closes = d["closes"]
        highs = d["highs"]
        lows = d["lows"]
        timestamps = d["timestamps"]
        n = len(closes)

        if n < 220:
            continue

        rsi2 = rsi(closes, 2)
        sma200 = sma(closes, 200)

        open_trades = []

        for i in range(200, n):
            # Check open trades with RSI exit
            still_open = []
            for t in open_trades:
                if isinstance(t, RSIExitTrade):
                    if not t.check_exit_with_rsi(highs[i], lows[i], closes[i],
                                                  timestamps[i], rsi2[i]):
                        still_open.append(t)
                else:
                    if not t.check_exit(highs[i], lows[i], closes[i], timestamps[i]):
                        still_open.append(t)
            open_trades = still_open

            if any(t.symbol == sym and not t.closed for t in open_trades):
                continue

            if rsi2[i] is None or sma200[i] is None:
                continue

            # Mean reversion: RSI(2) < 10 + price above 200 SMA (uptrend)
            if rsi2[i] < 10 and closes[i] > sma200[i]:
                entry = closes[i]
                sl = entry * 0.97  # -3% stop loss
                trade = RSIExitTrade(sym, "LONG", entry, sl, timestamps[i],
                                     rsi_target=60.0,
                                     strategy="mean_reversion_rsi2")
                open_trades.append(trade)
                all_trades.append(trade)

        for t in open_trades:
            if not t.closed:
                t.force_close(closes[-1], timestamps[-1])

    metrics = compute_metrics(all_trades)
    log.info("Portfolio D: %d trades, WR=%.1f%%, PF=%.3f, Return=%.2f%%",
             metrics["num_trades"], metrics["win_rate"],
             metrics["profit_factor"], metrics["total_return_pct"])
    return {"name": "Portfolio D: Mean Reversion", "metrics": metrics,
            "description": "RSI(2) < 10 + Price > 200-SMA, exit at RSI(2) > 60, SL -3%"}


# ============================================================================
# Main
# ============================================================================
def run_backtest() -> dict:
    """Run all 4 portfolio backtests and return results."""
    log.info("=" * 70)
    log.info("CRYPTO PORTFOLIO A/B/C/D BACKTEST")
    log.info("Symbols: %s", ", ".join(SYMBOLS))
    log.info("Interval: %s | Candles: %d (90 days)", INTERVAL, CANDLES_NEEDED)
    log.info("=" * 70)

    # Step 1: Download data
    market_data = download_candles(SYMBOLS, INTERVAL, CANDLES_NEEDED)
    log.info("Downloaded data for %d/%d symbols", len(market_data), len(SYMBOLS))

    if len(market_data) < 3:
        log.error("Too few symbols with data (%d). Aborting.", len(market_data))
        return {"error": "Insufficient data", "symbols_loaded": len(market_data)}

    # Step 2: Run all 4 portfolios
    results_a = backtest_portfolio_a(market_data)
    results_b = backtest_portfolio_b(market_data)
    results_c = backtest_portfolio_c(market_data)
    results_d = backtest_portfolio_d(market_data)

    portfolios = [results_a, results_b, results_c, results_d]

    # Step 3: Determine winner
    # Score: weighted combination of win_rate, profit_factor, sharpe, return
    def score_portfolio(p):
        m = p["metrics"]
        return (
            m["win_rate"] * 0.3 +
            min(m["profit_factor"], 5.0) * 10 * 0.25 +
            min(max(m["sharpe"], -5), 10) * 5 * 0.25 +
            min(m["total_return_pct"], 100) * 0.2
        )

    for p in portfolios:
        p["score"] = round(score_portfolio(p), 3)

    winner = max(portfolios, key=lambda p: p["score"])

    # Build final results
    output = {
        "backtest_timestamp": datetime.now(timezone.utc).isoformat(),
        "config": {
            "symbols": SYMBOLS,
            "interval": INTERVAL,
            "candles": CANDLES_NEEDED,
            "period_days": 90,
            "initial_capital": INITIAL_CAPITAL,
            "position_size_pct": POSITION_SIZE_PCT * 100,
        },
        "symbols_loaded": len(market_data),
        "symbols_data": {sym: d["count"] for sym, d in market_data.items()},
        "portfolios": {
            "A_golden_filter": results_a,
            "B_copy_trader": results_b,
            "C_momentum_volume": results_c,
            "D_mean_reversion": results_d,
        },
        "winner": {
            "portfolio": winner["name"],
            "score": winner["score"],
            "win_rate": winner["metrics"]["win_rate"],
            "profit_factor": winner["metrics"]["profit_factor"],
            "total_return_pct": winner["metrics"]["total_return_pct"],
            "sharpe": winner["metrics"]["sharpe"],
        },
        "ranking": sorted(
            [{"name": p["name"], "score": p["score"],
              "win_rate": p["metrics"]["win_rate"],
              "total_return": p["metrics"]["total_return_pct"]}
             for p in portfolios],
            key=lambda x: x["score"], reverse=True
        ),
    }

    # Save results
    data_dir = Path(__file__).resolve().parent / "data"
    data_dir.mkdir(exist_ok=True)
    out_path = data_dir / "crypto_portfolio_backtest.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, default=str)
    log.info("Results saved to %s", out_path)

    # Print summary
    log.info("\n" + "=" * 70)
    log.info("BACKTEST RESULTS SUMMARY")
    log.info("=" * 70)
    for p in sorted(portfolios, key=lambda x: x["score"], reverse=True):
        m = p["metrics"]
        log.info("  %s", p["name"])
        log.info("    Score: %.1f | WR: %.1f%% | PF: %.3f | Return: %.2f%% | "
                 "Sharpe: %.3f | MaxDD: %.2f%% | Trades: %d",
                 p["score"], m["win_rate"], m["profit_factor"],
                 m["total_return_pct"], m["sharpe"], m["max_drawdown_pct"],
                 m["num_trades"])
    log.info("\n  WINNER: %s (score=%.1f)", winner["name"], winner["score"])

    return output


if __name__ == "__main__":
    results = run_backtest()
    if "error" not in results:
        print(f"\nWinner: {results['winner']['portfolio']}")
        print(f"Score: {results['winner']['score']}")
    else:
        print(f"Error: {results['error']}")
        sys.exit(1)
