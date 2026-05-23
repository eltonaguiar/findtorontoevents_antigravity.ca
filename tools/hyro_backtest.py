#!/usr/bin/env python3
"""
hyro_backtest.py — Prop-firm-constrained backtester for Hyro-style challenges.

Fetches Binance candles (mirror failover), runs playbook-style strategies,
simulates intrabar equity on each OHLC point, enforces simplified Hyro rules.

Usage:
  python tools/hyro_backtest.py
  python tools/hyro_backtest.py --symbol ETHUSDT --strategy volume --long-only --risk 1.5
  python tools/hyro_backtest.py --months 12 --all --long-only --save
  python tools/hyro_backtest.py --rsi2-long 12 --rsi2-short 88 --strategy rsi2
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
from datetime import datetime, timezone, timedelta
from typing import Any, Callable
from urllib.error import URLError, HTTPError
from urllib.request import Request, urlopen

# ── Hyro Rules (reference $5K account) ─────────────────────────────────────

HYRO = {
    "account_size": 5000,
    "max_risk_pct": 3.0,
    "max_daily_loss_pct": 5.0,
    "max_overall_loss_pct": 10.0,
    "consistency_rule_pct": 40.0,
    "phase1_target_pct": 10.0,
    "phase2_target_pct": 5.0,
    "min_trading_days_phase1": 10,
    "min_trading_days_phase2": 10,
    "max_risk_usdt": 5000 * 3.0 / 100,
    "max_daily_loss_usdt": 5000 * 5.0 / 100,
    "max_overall_loss_usdt": 5000 * 10.0 / 100,
    "consistency_max_daily_phase1": 5000 * 10.0 / 100 * 40.0 / 100,
    "consistency_max_daily_phase2": 5000 * 5.0 / 100 * 40.0 / 100,
    "profit_target_phase1": 5000 * 10.0 / 100,
    "profit_target_phase2": 5000 * 5.0 / 100,
}

BINANCE_BASES = [
    "https://api.binance.com",
    "https://api1.binance.com",
    "https://api2.binance.com",
    "https://api3.binance.com",
    "https://data-api.binance.vision",
    "https://api.binance.us",
]
if os.environ.get("GITHUB_ACTIONS"):
    _pref = ["https://data-api.binance.vision", "https://api.binance.us"]
    BINANCE_BASES = _pref + [b for b in BINANCE_BASES if b not in _pref]

_KUCOIN = "https://api.kucoin.com"


def _fetch_url(url: str, timeout: int = 30) -> Any:
    req = Request(url, headers={"User-Agent": "hyro-backtest/1.0"})
    with urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def _fetch_klines_chunk(
    symbol: str, interval: str, start_ms: int, end_ms: int, limit: int = 1000
) -> list | None:
    path = (
        f"/api/v3/klines?symbol={symbol}&interval={interval}"
        f"&startTime={int(start_ms)}&endTime={int(end_ms)}&limit={limit}"
    )
    for base in BINANCE_BASES:
        try:
            data = _fetch_url(base + path)
            if data and isinstance(data, list) and len(data) > 0:
                return data
        except (URLError, HTTPError, TimeoutError, json.JSONDecodeError, ValueError, OSError):
            continue
    # KuCoin fallback
    if symbol.endswith("USDT"):
        kc = symbol.replace("USDT", "") + "-USDT"
        tf = {"1h": "1hour", "4h": "4hour", "1d": "1day"}.get(interval, "1hour")
        url = (
            f"{_KUCOIN}/api/v1/market/candles?type={tf}&symbol={kc}"
            f"&startAt={start_ms // 1000}&endAt={end_ms // 1000}"
        )
        try:
            raw = _fetch_url(url)
            rows = (raw or {}).get("data") or []
            out = []
            for c in rows[:limit]:
                t_open = int(c[0]) * 1000
                out.append(
                    [
                        t_open,
                        str(c[1]),
                        str(c[3]),
                        str(c[4]),
                        str(c[2]),
                        str(c[5]),
                        t_open + 3_600_000 - 1,
                    ]
                )
            out.sort(key=lambda x: x[0])
            return out if out else None
        except (URLError, HTTPError, TimeoutError, json.JSONDecodeError, ValueError, OSError):
            pass
    return None


def fetch_candles(symbol: str, interval: str, start_ms: int, end_ms: int, limit: int = 1000) -> list:
    """Paginated candles; Binance mirrors + KuCoin fallback."""
    all_candles: list = []
    current_start = start_ms
    while current_start < end_ms:
        data = _fetch_klines_chunk(symbol, interval, current_start, end_ms, limit)
        if not data:
            print(f"ERROR: no candles for {symbol} @ {current_start}", file=sys.stderr)
            break
        all_candles.extend(data)
        last_close_time = data[-1][6]
        current_start = last_close_time + 1
        if len(data) < limit:
            break
        time.sleep(0.12)
    return all_candles


def parse_candles(raw: list) -> list[dict]:
    candles = []
    for c in raw:
        candles.append(
            {
                "open_time": c[0],
                "open": float(c[1]),
                "high": float(c[2]),
                "low": float(c[3]),
                "close": float(c[4]),
                "volume": float(c[5]),
                "close_time": c[6],
            }
        )
    return candles


def calc_sma(candles: list[dict], period: int, field: str = "close") -> list:
    vals = [c[field] for c in candles]
    result = [None] * len(vals)
    for i in range(period - 1, len(vals)):
        result[i] = sum(vals[i - period + 1 : i + 1]) / period
    return result


def calc_std(candles: list[dict], period: int, field: str = "close") -> list:
    vals = [c[field] for c in candles]
    result = [None] * len(vals)
    for i in range(period - 1, len(vals)):
        chunk = vals[i - period + 1 : i + 1]
        mean = sum(chunk) / period
        variance = sum((x - mean) ** 2 for x in chunk) / period
        result[i] = math.sqrt(variance)
    return result


def calc_rsi(candles: list[dict], period: int = 14) -> list:
    closes = [c["close"] for c in candles]
    result = [None] * len(closes)
    if len(closes) < period + 1:
        return result
    gains = []
    losses = []
    for i in range(1, len(closes)):
        change = closes[i] - closes[i - 1]
        gains.append(max(0, change))
        losses.append(max(0, -change))
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    if avg_loss == 0:
        result[period] = 100
    else:
        rs = avg_gain / avg_loss
        result[period] = 100 - (100 / (1 + rs))
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        if avg_loss == 0:
            result[i + 1] = 100
        else:
            rs = avg_gain / avg_loss
            result[i + 1] = 100 - (100 / (1 + rs))
    return result


def calc_atr(candles: list[dict], period: int = 14) -> list:
    result = [None] * len(candles)
    if len(candles) < period + 1:
        return result
    true_ranges = []
    for i in range(1, len(candles)):
        high = candles[i]["high"]
        low = candles[i]["low"]
        prev_close = candles[i - 1]["close"]
        tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
        true_ranges.append(tr)
    result[period] = sum(true_ranges[:period]) / period
    for i in range(period, len(true_ranges)):
        result[i + 1] = (result[i] * (period - 1) + true_ranges[i]) / period
    return result


def strategy_bollinger_reversion(candles: list[dict], params: dict | None = None) -> list[dict]:
    p = params or {}
    bb_period = p.get("bb_period", 20)
    bb_std_mult = p.get("bb_std_mult", 2.0)
    rsi_period = p.get("rsi_period", 14)
    rsi_long = p.get("rsi_long", 35)
    rsi_short = p.get("rsi_short", 65)
    atr_period = p.get("atr_period", 14)
    sma = calc_sma(candles, bb_period)
    std = calc_std(candles, bb_period)
    rsi = calc_rsi(candles, rsi_period)
    atr = calc_atr(candles, atr_period)
    signals = []
    for i in range(max(bb_period, rsi_period, atr_period) + 1, len(candles)):
        if sma[i] is None or std[i] is None or rsi[i] is None or atr[i] is None:
            continue
        upper = sma[i] + bb_std_mult * std[i]
        lower = sma[i] - bb_std_mult * std[i]
        mid = sma[i]
        candle = candles[i]
        if candle["low"] <= lower and rsi[i] < rsi_long:
            entry = lower
            sl = lower - atr[i]
            tp = mid
            rr = (tp - entry) / (entry - sl) if entry != sl else 0
            if rr >= 1.0:
                signals.append(
                    {
                        "index": i,
                        "time": candle["open_time"],
                        "direction": "LONG",
                        "entry": round(entry, 2),
                        "sl": round(sl, 2),
                        "tp": round(tp, 2),
                        "rr": round(rr, 2),
                        "strategy": "bollinger_reversion",
                    }
                )
        if candle["high"] >= upper and rsi[i] > rsi_short:
            entry = upper
            sl = upper + atr[i]
            tp = mid
            rr = (entry - tp) / (sl - entry) if sl != entry else 0
            if rr >= 1.0:
                signals.append(
                    {
                        "index": i,
                        "time": candle["open_time"],
                        "direction": "SHORT",
                        "entry": round(entry, 2),
                        "sl": round(sl, 2),
                        "tp": round(tp, 2),
                        "rr": round(rr, 2),
                        "strategy": "bollinger_reversion",
                    }
                )
    return signals


def strategy_rsi2_extreme(candles: list[dict], params: dict | None = None) -> list[dict]:
    p = params or {}
    rsi_period = p.get("rsi_period", 2)
    sma_filter_period = p.get("sma_filter", 200)
    sma_tp_period = p.get("sma_tp", 20)
    atr_period = p.get("atr_period", 14)
    rsi_long = p.get("rsi_long", 5)
    rsi_short = p.get("rsi_short", 95)
    rsi = calc_rsi(candles, rsi_period)
    sma_filter = calc_sma(candles, sma_filter_period)
    sma_tp = calc_sma(candles, sma_tp_period)
    atr = calc_atr(candles, atr_period)
    signals = []
    for i in range(max(sma_filter_period, sma_tp_period, atr_period) + 1, len(candles)):
        if rsi[i] is None or sma_filter[i] is None or sma_tp[i] is None or atr[i] is None:
            continue
        candle = candles[i]
        if rsi[i] < rsi_long and candle["close"] > sma_filter[i]:
            entry = candle["close"]
            sl = entry - 2 * atr[i]
            tp = sma_tp[i]
            if tp > entry:
                rr = (tp - entry) / (entry - sl) if entry != sl else 0
                if rr >= 1.0:
                    signals.append(
                        {
                            "index": i,
                            "time": candle["open_time"],
                            "direction": "LONG",
                            "entry": round(entry, 2),
                            "sl": round(sl, 2),
                            "tp": round(tp, 2),
                            "rr": round(rr, 2),
                            "strategy": "rsi2_extreme",
                        }
                    )
        if rsi[i] > rsi_short and candle["close"] < sma_filter[i]:
            entry = candle["close"]
            sl = entry + 2 * atr[i]
            tp = sma_tp[i]
            if tp < entry:
                rr = (entry - tp) / (sl - entry) if sl != entry else 0
                if rr >= 1.0:
                    signals.append(
                        {
                            "index": i,
                            "time": candle["open_time"],
                            "direction": "SHORT",
                            "entry": round(entry, 2),
                            "sl": round(sl, 2),
                            "tp": round(tp, 2),
                            "rr": round(rr, 2),
                            "strategy": "rsi2_extreme",
                        }
                    )
    return signals


def strategy_volume_breakout(candles: list[dict], params: dict | None = None) -> list[dict]:
    p = params or {}
    lookback = p.get("lookback", 20)
    vol_mult = p.get("vol_mult", 2.0)
    atr_period = p.get("atr_period", 14)
    tp_r = p.get("tp_r", 2.0)
    sl_atr_mult = p.get("sl_atr_mult", 1.5)
    atr = calc_atr(candles, atr_period)
    signals = []
    for i in range(max(lookback, atr_period) + 1, len(candles)):
        if atr[i] is None:
            continue
        candle = candles[i]
        window = candles[i - lookback : i]
        highs = [c["high"] for c in window]
        lows = [c["low"] for c in window]
        vols = [c["volume"] for c in window]
        prev_high = max(highs)
        prev_low = min(lows)
        avg_vol = sum(vols) / len(vols)
        if avg_vol == 0:
            continue
        if candle["close"] > prev_high and candle["volume"] > vol_mult * avg_vol:
            entry = candle["close"]
            sl = entry - sl_atr_mult * atr[i]
            risk = entry - sl
            tp = entry + tp_r * risk
            signals.append(
                {
                    "index": i,
                    "time": candle["open_time"],
                    "direction": "LONG",
                    "entry": round(entry, 2),
                    "sl": round(sl, 2),
                    "tp": round(tp, 2),
                    "rr": round(tp_r, 2),
                    "strategy": "volume_breakout",
                }
            )
        if candle["close"] < prev_low and candle["volume"] > vol_mult * avg_vol:
            entry = candle["close"]
            sl = entry + sl_atr_mult * atr[i]
            risk = sl - entry
            tp = entry - tp_r * risk
            signals.append(
                {
                    "index": i,
                    "time": candle["open_time"],
                    "direction": "SHORT",
                    "entry": round(entry, 2),
                    "sl": round(sl, 2),
                    "tp": round(tp, 2),
                    "rr": round(tp_r, 2),
                    "strategy": "volume_breakout",
                }
            )
    return signals


def strategy_sr_bounce(candles: list[dict], params: dict | None = None) -> list[dict]:
    p = params or {}
    pivot_lookback = p.get("pivot_lookback", 5)
    sr_lookback = p.get("sr_lookback", 50)
    atr_period = p.get("atr_period", 14)
    touch_tolerance_atr = p.get("touch_tolerance_atr", 0.5)
    tp_r = p.get("tp_r", 2.0)
    atr = calc_atr(candles, atr_period)
    signals = []
    for i in range(max(sr_lookback, atr_period, pivot_lookback * 2) + 1, len(candles)):
        if atr[i] is None:
            continue
        candle = candles[i]
        window = candles[i - sr_lookback : i]
        tolerance = touch_tolerance_atr * atr[i]
        supports = []
        resistances = []
        for j in range(pivot_lookback, len(window) - pivot_lookback):
            if all(
                window[j]["low"] <= window[j - k]["low"] and window[j]["low"] <= window[j + k]["low"]
                for k in range(1, pivot_lookback + 1)
            ):
                supports.append(window[j]["low"])
            if all(
                window[j]["high"] >= window[j - k]["high"]
                and window[j]["high"] >= window[j + k]["high"]
                for k in range(1, pivot_lookback + 1)
            ):
                resistances.append(window[j]["high"])
        if not supports or not resistances:
            continue
        for sup in supports:
            if abs(candle["low"] - sup) < tolerance and candle["close"] > sup:
                entry = candle["close"]
                sl = sup - 1.5 * atr[i]
                risk = entry - sl
                res_above = [r for r in resistances if r > entry]
                if res_above:
                    tp = min(res_above)
                    rr = (tp - entry) / risk if risk > 0 else 0
                    if rr >= 1.0:
                        signals.append(
                            {
                                "index": i,
                                "time": candle["open_time"],
                                "direction": "LONG",
                                "entry": round(entry, 2),
                                "sl": round(sl, 2),
                                "tp": round(tp, 2),
                                "rr": round(rr, 2),
                                "strategy": "sr_bounce",
                            }
                        )
                        break
                else:
                    tp = entry + tp_r * risk
                    signals.append(
                        {
                            "index": i,
                            "time": candle["open_time"],
                            "direction": "LONG",
                            "entry": round(entry, 2),
                            "sl": round(sl, 2),
                            "tp": round(tp, 2),
                            "rr": round(tp_r, 2),
                            "strategy": "sr_bounce",
                        }
                    )
                    break
        for res in resistances:
            if abs(candle["high"] - res) < tolerance and candle["close"] < res:
                entry = candle["close"]
                sl = res + 1.5 * atr[i]
                risk = sl - entry
                sup_below = [s for s in supports if s < entry]
                if sup_below:
                    tp = max(sup_below)
                    rr = (entry - tp) / risk if risk > 0 else 0
                    if rr >= 1.0:
                        signals.append(
                            {
                                "index": i,
                                "time": candle["open_time"],
                                "direction": "SHORT",
                                "entry": round(entry, 2),
                                "sl": round(sl, 2),
                                "tp": round(tp, 2),
                                "rr": round(rr, 2),
                                "strategy": "sr_bounce",
                            }
                        )
                        break
                else:
                    tp = entry - tp_r * risk
                    signals.append(
                        {
                            "index": i,
                            "time": candle["open_time"],
                            "direction": "SHORT",
                            "entry": round(entry, 2),
                            "sl": round(sl, 2),
                            "tp": round(tp, 2),
                            "rr": round(tp_r, 2),
                            "strategy": "sr_bounce",
                        }
                    )
                    break
    return signals


STRATEGIES: dict[str, Callable[..., list[dict]]] = {
    "bollinger": strategy_bollinger_reversion,
    "rsi2": strategy_rsi2_extreme,
    "volume": strategy_volume_breakout,
    "sr": strategy_sr_bounce,
}

STRATEGY_NAMES = {
    "bollinger": "Bollinger Band Reversion",
    "rsi2": "RSI(2) Extreme Reversion",
    "volume": "Volume Breakout",
    "sr": "S/R Bounce",
}

DEFAULT_BATCH_SYMBOLS = ("BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT")


class HyroSimulator:
    """Intrabar equity path O→L→H→C; trailing DD from peak equity at each point."""

    def __init__(self, account_size: float = 5000, risk_pct: float = 0.75):
        self.account_size = account_size
        self.risk_pct = risk_pct
        self.risk_usdt = account_size * risk_pct / 100
        self.equity = account_size
        self.high_water_equity = account_size
        self.max_drawdown_from_peak = 0.0
        self.daily_start_equity = account_size
        self.current_date = None
        self.min_equity_today = account_size
        self.trading_days: set[str] = set()
        self.daily_profit = 0.0
        self.total_pnl = 0.0
        self.trades: list[dict] = []
        self.failed = False
        self.fail_reason: str | None = None
        self.passed = False
        self.phase = 1
        self.daily_profits: dict[str, float] = {}

    def _get_date(self, timestamp_ms: int) -> str:
        return datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d")

    def _check_new_day(self, timestamp_ms: int) -> None:
        date = self._get_date(timestamp_ms)
        if self.current_date != date:
            if self.current_date is not None:
                self.daily_profits[self.current_date] = self.daily_profit
            self.current_date = date
            self.daily_start_equity = self.equity
            self.daily_profit = 0.0
            self.min_equity_today = self.equity

    def _consistency_cap(self) -> float:
        return (
            HYRO["consistency_max_daily_phase1"]
            if self.phase == 1
            else HYRO["consistency_max_daily_phase2"]
        )

    def _register_pnl(self, pnl: float, ts_ms: int) -> bool:
        """Apply closed PnL; fail if consistency cap exceeded (same UTC day)."""
        self.equity += pnl
        self.daily_profit += pnl
        self.total_pnl += pnl
        self.trading_days.add(self._get_date(ts_ms))
        if self.daily_profit > self._consistency_cap() + 1e-6:
            d = self._get_date(ts_ms)
            self.failed = True
            self.fail_reason = (
                f"consistency: realized on {d} ${self.daily_profit:.2f} > cap ${self._consistency_cap():.2f}"
            )
            return False
        return True

    def _intrabar_checks(self, equity_points: list[float], ts_ms: int) -> bool:
        """Update HWM and enforce overall + daily DD on each equity point."""
        for eq in equity_points:
            if eq > self.high_water_equity:
                self.high_water_equity = eq
            dd_peak = self.high_water_equity - eq
            self.max_drawdown_from_peak = max(self.max_drawdown_from_peak, dd_peak)
            if dd_peak >= HYRO["max_overall_loss_usdt"] - 1e-6:
                self.failed = True
                self.fail_reason = (
                    f"Overall trailing DD ${dd_peak:.2f} >= ${HYRO['max_overall_loss_usdt']:.2f}"
                )
                return False
            self.min_equity_today = min(self.min_equity_today, eq)
            daily_loss = self.daily_start_equity - self.min_equity_today
            if daily_loss >= HYRO["max_daily_loss_usdt"] - 1e-6:
                self.failed = True
                self.fail_reason = (
                    f"Daily DD ${daily_loss:.2f} >= ${HYRO['max_daily_loss_usdt']:.2f}"
                )
                return False
        return True

    def _equity_long(self, entry_price: float, size: float, px: float) -> float:
        return self.equity + (px - entry_price) * size

    def _equity_short(self, entry_price: float, size: float, px: float) -> float:
        return self.equity + (entry_price - px) * size

    def simulate_trade(self, signal: dict, candles: list[dict]) -> dict | None:
        if self.failed:
            return None
        entry_idx = signal["index"]
        direction = signal["direction"]
        entry_price = signal["entry"]
        sl_price = signal["sl"]
        tp_price = signal["tp"]
        if direction == "LONG":
            price_risk = entry_price - sl_price
        else:
            price_risk = sl_price - entry_price
        if price_risk <= 0:
            return None
        size = self.risk_usdt / price_risk
        position_value = size * entry_price
        if position_value > self.account_size * 10:
            size = (self.account_size * 10) / entry_price

        for j in range(entry_idx + 1, len(candles)):
            candle = candles[j]
            self._check_new_day(candle["open_time"])
            if self.failed:
                return None

            if direction == "LONG":
                pts = [
                    self._equity_long(entry_price, size, candle["open"]),
                    self._equity_long(entry_price, size, candle["low"]),
                    self._equity_long(entry_price, size, candle["high"]),
                    self._equity_long(entry_price, size, candle["close"]),
                ]
                if not self._intrabar_checks(pts, candle["open_time"]):
                    t = {
                        "direction": direction,
                        "entry": entry_price,
                        "exit": sl_price,
                        "exit_reason": "dd_breach",
                        "pnl": round(-self.risk_usdt, 2),
                        "pnl_pct": round(-self.risk_usdt / self.account_size * 100, 2),
                        "signal": signal,
                        "bars_held": j - entry_idx,
                    }
                    self.trades.append(t)
                    return t

                if candle["open"] <= sl_price:
                    pnl = (candle["open"] - entry_price) * size
                    if not self._register_pnl(pnl, candle["open_time"]):
                        return None
                    trade = self._trade_out(
                        direction, entry_price, candle["open"], "sl_gap", pnl, signal, j - entry_idx
                    )
                    return trade
                if candle["low"] <= sl_price:
                    pnl = (sl_price - entry_price) * size
                    if not self._register_pnl(pnl, candle["open_time"]):
                        return None
                    trade = self._trade_out(
                        direction, entry_price, sl_price, "sl_hit", pnl, signal, j - entry_idx
                    )
                    return trade
                if candle["high"] >= tp_price:
                    pnl = (tp_price - entry_price) * size
                    if not self._register_pnl(pnl, candle["open_time"]):
                        return None
                    trade = self._trade_out(
                        direction, entry_price, tp_price, "tp_hit", pnl, signal, j - entry_idx
                    )
                    self._maybe_pass()
                    return trade
            else:
                pts = [
                    self._equity_short(entry_price, size, candle["open"]),
                    self._equity_short(entry_price, size, candle["high"]),
                    self._equity_short(entry_price, size, candle["low"]),
                    self._equity_short(entry_price, size, candle["close"]),
                ]
                if not self._intrabar_checks(pts, candle["open_time"]):
                    t = {
                        "direction": direction,
                        "entry": entry_price,
                        "exit": sl_price,
                        "exit_reason": "dd_breach",
                        "pnl": round(-self.risk_usdt, 2),
                        "pnl_pct": round(-self.risk_usdt / self.account_size * 100, 2),
                        "signal": signal,
                        "bars_held": j - entry_idx,
                    }
                    self.trades.append(t)
                    return t
                if candle["open"] >= sl_price:
                    pnl = (entry_price - candle["open"]) * size
                    if not self._register_pnl(pnl, candle["open_time"]):
                        return None
                    return self._trade_out(
                        direction, entry_price, candle["open"], "sl_gap", pnl, signal, j - entry_idx
                    )
                if candle["high"] >= sl_price:
                    pnl = (entry_price - sl_price) * size
                    if not self._register_pnl(pnl, candle["open_time"]):
                        return None
                    return self._trade_out(
                        direction, entry_price, sl_price, "sl_hit", pnl, signal, j - entry_idx
                    )
                if candle["low"] <= tp_price:
                    pnl = (entry_price - tp_price) * size
                    if not self._register_pnl(pnl, candle["open_time"]):
                        return None
                    trade = self._trade_out(
                        direction, entry_price, tp_price, "tp_hit", pnl, signal, j - entry_idx
                    )
                    self._maybe_pass()
                    return trade

        last = candles[-1]
        if direction == "LONG":
            pnl = (last["close"] - entry_price) * size
        else:
            pnl = (entry_price - last["close"]) * size
        if not self._register_pnl(pnl, last["open_time"]):
            return None
        return self._trade_out(
            direction,
            entry_price,
            last["close"],
            "end_of_data",
            pnl,
            signal,
            len(candles) - entry_idx - 1,
        )

    def _trade_out(
        self,
        direction: str,
        entry: float,
        exit_px: float,
        reason: str,
        pnl: float,
        signal: dict,
        bars: int,
    ) -> dict:
        trade = {
            "direction": direction,
            "entry": entry,
            "exit": exit_px,
            "exit_reason": reason,
            "pnl": round(pnl, 2),
            "pnl_pct": round(pnl / self.account_size * 100, 2),
            "signal": signal,
            "bars_held": bars,
        }
        self.trades.append(trade)
        return trade

    def _maybe_pass(self) -> None:
        target = HYRO["profit_target_phase1"] if self.phase == 1 else HYRO["profit_target_phase2"]
        min_days = HYRO["min_trading_days_phase1"]
        if self.total_pnl >= target and len(self.trading_days) >= min_days:
            self.passed = True


def run_backtest(
    symbol: str,
    strategy_key: str,
    months: int = 6,
    risk_pct: float = 0.75,
    max_trades: int | None = None,
    long_only: bool = False,
    strategy_params: dict | None = None,
    quiet: bool = False,
) -> HyroSimulator | None:
    strategy_fn = STRATEGIES[strategy_key]
    strategy_name = STRATEGY_NAMES[strategy_key]
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=months * 30)
    start_ms = int(start.timestamp() * 1000)
    end_ms = int(now.timestamp() * 1000)
    if not quiet:
        print(f"\nFetching {symbol} 1h candles (~{months} months)...")
    raw = fetch_candles(symbol, "1h", start_ms, end_ms)
    candles = parse_candles(raw)
    if not candles:
        if not quiet:
            print("No candles - abort.")
        return None
    if not quiet:
        print(
            f"Got {len(candles)} candles ({candles[0]['open_time']} -> {candles[-1]['close_time']})"
        )
    signals = strategy_fn(candles, strategy_params)
    if not quiet:
        print(f"Running {strategy_name}... {len(signals)} signals")
    if not signals:
        if not quiet:
            print("No signals - skipping simulation.")
        return None
    signals.sort(key=lambda s: s["index"])
    sim = HyroSimulator(account_size=HYRO["account_size"], risk_pct=risk_pct)
    last_exit_idx = -1
    trades_taken = 0
    for signal in signals:
        if signal["index"] <= last_exit_idx:
            continue
        if long_only and signal["direction"] != "LONG":
            continue
        if sim.failed:
            break
        if max_trades is not None and trades_taken >= max_trades:
            break
        if sim.daily_profit >= sim._consistency_cap():
            continue
        result = sim.simulate_trade(signal, candles)
        if result:
            trades_taken += 1
            last_exit_idx = signal["index"] + result.get("bars_held", 0)
    if sim.failed:
        sim.passed = False
    if not quiet:
        print_report(sim, symbol, strategy_name, months)
    return sim


def print_report(sim: HyroSimulator, symbol: str, strategy_name: str, months: int) -> None:
    total = len(sim.trades)
    wins = [t for t in sim.trades if t["pnl"] > 0]
    losses = [t for t in sim.trades if t["pnl"] <= 0]
    win_rate = len(wins) / total * 100 if total > 0 else 0
    total_profit = sum(t["pnl"] for t in wins)
    total_loss = sum(t["pnl"] for t in losses)
    profit_factor = abs(total_profit / total_loss) if total_loss != 0 else float("inf")
    avg_win = total_profit / len(wins) if wins else 0
    avg_loss = total_loss / len(losses) if losses else 0
    status = "FAILED" if sim.failed else ("PASSED" if sim.passed else "INCOMPLETE")
    print(f"{'=' * 60}")
    print(f"  BACKTEST: {symbol} - {strategy_name}")
    print(f"  Window: ~{months} mo | Risk: {sim.risk_pct}% (${sim.risk_usdt:.2f}/trade)")
    print(f"{'=' * 60}")
    print(f"  CHALLENGE: {status}")
    if sim.fail_reason:
        print(f"  Reason:    {sim.fail_reason}")
    print(f"{'=' * 60}")
    print(f"  Trades:    {total}  |  WR: {win_rate:.1f}%")
    print(f"  PnL:       ${sim.total_pnl:.2f}  |  Final equity: ${sim.equity:.2f}")
    print(f"  Peak eq:   ${sim.high_water_equity:.2f}")
    print(f"  Max DD:    ${sim.max_drawdown_from_peak:.2f} (limit ${HYRO['max_overall_loss_usdt']:.0f})")
    print(f"  T-days:    {len(sim.trading_days)} (min {HYRO['min_trading_days_phase1']} for phase target)")
    if sim.trades:
        print(f"\n  Last trades:")
        for t in sim.trades[-5:]:
            print(
                f"    {t['direction']:<5} {t['exit_reason']:<12} pnl ${t['pnl']:.2f}  bars {t.get('bars_held', '?')}"
            )
    print()


def build_strategy_params(args: argparse.Namespace) -> dict:
    return {
        "rsi_long": args.rsi2_long,
        "rsi_short": args.rsi2_short,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Hyro-style prop backtester (Binance spot proxies)")
    parser.add_argument("--symbol", default="BTCUSDT")
    parser.add_argument("--strategy", default="bollinger", choices=list(STRATEGIES.keys()))
    parser.add_argument("--months", type=int, default=6)
    parser.add_argument("--risk", type=float, default=0.75, help="Risk %% of account per trade (notional stop)")
    parser.add_argument("--all", action="store_true", help="All strategies")
    parser.add_argument(
        "--symbols",
        nargs="+",
        default=list(DEFAULT_BATCH_SYMBOLS),
        help="Symbols when using --all (default: BTC ETH SOL BNB)",
    )
    parser.add_argument("--max-trades", type=int)
    parser.add_argument("--long-only", action="store_true")
    parser.add_argument("--rsi2-long", type=float, default=5.0, dest="rsi2_long", help="RSI(2) long threshold")
    parser.add_argument(
        "--rsi2-short", type=float, default=95.0, dest="rsi2_short", help="RSI(2) short threshold"
    )
    parser.add_argument("--save", action="store_true")
    parser.add_argument(
        "--output",
        default="audit_dashboard/data/hyro_backtest_results.json",
        help="JSON output path",
    )
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()

    strat_params = build_strategy_params(args)
    strategies_to_run = list(STRATEGIES.keys()) if args.all else [args.strategy]
    symbols_to_run = args.symbols if args.all else [args.symbol]

    all_results = []
    for sym in symbols_to_run:
        for strat in strategies_to_run:
            try:
                sim = run_backtest(
                    sym,
                    strat,
                    args.months,
                    args.risk,
                    args.max_trades,
                    args.long_only,
                    strat_params,
                    quiet=args.quiet,
                )
                if sim:
                    all_results.append(
                        {
                            "symbol": sym,
                            "strategy": strat,
                            "strategy_name": STRATEGY_NAMES[strat],
                            "months": args.months,
                            "risk_pct": args.risk,
                            "long_only": args.long_only,
                            "rsi2_long": args.rsi2_long,
                            "rsi2_short": args.rsi2_short,
                            "passed": sim.passed,
                            "failed": sim.failed,
                            "fail_reason": sim.fail_reason,
                            "total_trades": len(sim.trades),
                            "wins": len([t for t in sim.trades if t["pnl"] > 0]),
                            "win_rate": round(
                                len([t for t in sim.trades if t["pnl"] > 0]) / len(sim.trades) * 100,
                                1,
                            )
                            if sim.trades
                            else 0,
                            "total_pnl": round(sim.total_pnl, 2),
                            "final_equity": round(sim.equity, 2),
                            "peak_equity": round(sim.high_water_equity, 2),
                            "max_drawdown": round(sim.max_drawdown_from_peak, 2),
                            "trading_days": len(sim.trading_days),
                        }
                    )
            except Exception as e:
                print(f"ERROR {sym} {strat}: {e}", file=sys.stderr)

    if args.save and all_results:
        out = args.output
        os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
        with open(out, "w", encoding="utf-8") as f:
            json.dump(
                {"generated_at": datetime.now(timezone.utc).isoformat(), "results": all_results},
                f,
                indent=2,
            )
        print(f"Saved {len(all_results)} result rows -> {out}")


if __name__ == "__main__":
    main()
