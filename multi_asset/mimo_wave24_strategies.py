#!/usr/bin/env python3
"""
MIMO Wave 24 cross-asset strategy pack.

Thirty brand-new strategies (5 per asset class) built on reusable signal
families so they can be backtested consistently and extended safely.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import numpy as np
import pandas as pd


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sma(series: pd.Series, period: int) -> pd.Series:
    return series.rolling(period).mean()


def _ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()


def _rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0.0)).rolling(period).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def _atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(period).mean()


def _adx(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    up_move = high.diff()
    down_move = -low.diff()
    plus_dm = up_move.where((up_move > down_move) & (up_move > 0), 0.0)
    minus_dm = down_move.where((down_move > up_move) & (down_move > 0), 0.0)
    atr_val = _atr(high, low, close, period).replace(0, np.nan)
    plus_di = 100 * _ema(plus_dm, period) / atr_val
    minus_di = 100 * _ema(minus_dm, period) / atr_val
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    return _ema(dx, period)


def _bollinger_width(close: pd.Series, period: int = 20) -> tuple[pd.Series, pd.Series, pd.Series, pd.Series]:
    mid = _sma(close, period)
    std = close.rolling(period).std()
    upper = mid + 2.0 * std
    lower = mid - 2.0 * std
    width = (upper - lower) / mid.replace(0, np.nan)
    return mid, upper, lower, width


def _safe_float(value: Any) -> float:
    if hasattr(value, "item"):
        value = value.item()
    value = float(value)
    return value if np.isfinite(value) else float("nan")


def _volume_ratio(volume: pd.Series, period: int = 20) -> float:
    avg = _safe_float(volume.rolling(period).mean().iloc[-1])
    current = _safe_float(volume.iloc[-1])
    if not np.isfinite(avg) or avg <= 0 or not np.isfinite(current):
        return float("nan")
    return current / avg


def _make_signal(
    *,
    strategy_id: str,
    asset_class: str,
    symbol: str,
    direction: str,
    entry: float,
    tp: float,
    sl: float,
    confidence: float,
    rr: float,
    reason: str,
    max_hold_days: int,
    extra: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    if not all(np.isfinite([entry, tp, sl, confidence, rr])) or entry <= 0 or rr <= 0:
        return []
    return [{
        "strategy": strategy_id,
        "symbol": symbol,
        "category": asset_class,
        "asset_class": asset_class,
        "direction": direction,
        "signal_type": "BUY" if direction == "LONG" else "SELL",
        "entry_price": round(entry, 6),
        "take_profit": round(tp, 6),
        "stop_loss": round(sl, 6),
        "confidence": round(min(0.95, max(0.45, confidence)), 3),
        "risk_reward": round(rr, 2),
        "reason": reason,
        "max_hold_days": int(max_hold_days),
        "timestamp": _now_iso(),
        "extra": extra or {},
    }]


@dataclass(frozen=True)
class StrategySpec:
    strategy_id: str
    asset_class: str
    family: str
    symbols: tuple[str, ...]
    description: str
    benchmark_wr: float
    benchmark_pf: float
    params: dict[str, Any] = field(default_factory=dict)


CRYPTO_SYMBOLS = {
    "BTC-USD": {"name": "Bitcoin", "cat": "crypto"},
    "ETH-USD": {"name": "Ethereum", "cat": "crypto"},
    "SOL-USD": {"name": "Solana", "cat": "crypto"},
    "XRP-USD": {"name": "XRP", "cat": "crypto"},
    "DOGE-USD": {"name": "Dogecoin", "cat": "crypto"},
    "ADA-USD": {"name": "Cardano", "cat": "crypto"},
    "AVAX-USD": {"name": "Avalanche", "cat": "crypto"},
    "LINK-USD": {"name": "Chainlink", "cat": "crypto"},
}

EQUITY_SYMBOLS = {
    "AAPL": {"name": "Apple", "cat": "equity"},
    "MSFT": {"name": "Microsoft", "cat": "equity"},
    "NVDA": {"name": "Nvidia", "cat": "equity"},
    "META": {"name": "Meta", "cat": "equity"},
    "AMZN": {"name": "Amazon", "cat": "equity"},
    "PLTR": {"name": "Palantir", "cat": "equity"},
    "AMD": {"name": "AMD", "cat": "equity"},
    "SNOW": {"name": "Snowflake", "cat": "equity"},
    "JPM": {"name": "JPMorgan", "cat": "equity"},
    "XOM": {"name": "Exxon", "cat": "equity"},
    "UNH": {"name": "UnitedHealth", "cat": "equity"},
    "KO": {"name": "Coca-Cola", "cat": "equity"},
}

ETF_SYMBOLS = {
    "SPY": {"name": "S&P 500 ETF", "cat": "etf"},
    "QQQ": {"name": "Nasdaq 100 ETF", "cat": "etf"},
    "IWM": {"name": "Russell 2000 ETF", "cat": "etf"},
    "DIA": {"name": "Dow ETF", "cat": "etf"},
    "XLK": {"name": "Technology", "cat": "etf"},
    "XLF": {"name": "Financials", "cat": "etf"},
    "XLV": {"name": "Health Care", "cat": "etf"},
    "XLI": {"name": "Industrials", "cat": "etf"},
    "XLU": {"name": "Utilities", "cat": "etf"},
    "XLP": {"name": "Consumer Staples", "cat": "etf"},
    "TLT": {"name": "Long Treasuries", "cat": "etf"},
    "GLD": {"name": "Gold ETF", "cat": "etf"},
}

FOREX_SYMBOLS = {
    "EURUSD=X": {"name": "EUR/USD", "cat": "forex", "dxy_sign": -1.0, "carry": -0.5},
    "GBPUSD=X": {"name": "GBP/USD", "cat": "forex", "dxy_sign": -1.0, "carry": 0.25},
    "USDJPY=X": {"name": "USD/JPY", "cat": "forex", "dxy_sign": 1.0, "carry": 4.5},
    "AUDUSD=X": {"name": "AUD/USD", "cat": "forex", "dxy_sign": -1.0, "carry": 0.75},
    "USDCAD=X": {"name": "USD/CAD", "cat": "forex", "dxy_sign": 1.0, "carry": 0.5},
    "USDCHF=X": {"name": "USD/CHF", "cat": "forex", "dxy_sign": 1.0, "carry": 2.0},
    "NZDUSD=X": {"name": "NZD/USD", "cat": "forex", "dxy_sign": -1.0, "carry": 1.0},
    "EURJPY=X": {"name": "EUR/JPY", "cat": "forex", "dxy_sign": -0.2, "carry": 4.0},
}

FUTURES_SYMBOLS = {
    "ES=F": {"name": "S&P 500 E-mini", "cat": "futures"},
    "NQ=F": {"name": "Nasdaq 100 E-mini", "cat": "futures"},
    "YM=F": {"name": "Dow E-mini", "cat": "futures"},
    "RTY=F": {"name": "Russell 2000 E-mini", "cat": "futures"},
    "ZN=F": {"name": "10Y T-Note", "cat": "futures"},
    "ZB=F": {"name": "30Y T-Bond", "cat": "futures"},
}

COMMODITY_SYMBOLS = {
    "GC=F": {"name": "Gold", "cat": "commodity"},
    "SI=F": {"name": "Silver", "cat": "commodity"},
    "CL=F": {"name": "Crude Oil", "cat": "commodity"},
    "NG=F": {"name": "Natural Gas", "cat": "commodity"},
    "HG=F": {"name": "Copper", "cat": "commodity"},
    "CORN": {"name": "Corn ETF", "cat": "commodity"},
    "WEAT": {"name": "Wheat ETF", "cat": "commodity"},
    "SOYB": {"name": "Soybean ETF", "cat": "commodity"},
}

BENCHMARKS = {
    "spy": "SPY",
    "vix": "^VIX",
    "dxy": "DX-Y.NYB",
    "tlt": "TLT",
    "gld": "GLD",
}

ALL_METADATA: dict[str, dict[str, Any]] = {}
for universe in (CRYPTO_SYMBOLS, EQUITY_SYMBOLS, ETF_SYMBOLS, FOREX_SYMBOLS, FUTURES_SYMBOLS, COMMODITY_SYMBOLS):
    ALL_METADATA.update(universe)


def _trend_pullback(df: pd.DataFrame, symbol: str, spec: StrategySpec, history: dict[str, pd.DataFrame]) -> list[dict[str, Any]]:
    if len(df) < 120:
        return []
    close = df["Close"]
    high = df["High"]
    low = df["Low"]
    volume = df["Volume"]
    price = _safe_float(close.iloc[-1])
    ema_fast = _safe_float(_ema(close, spec.params.get("ema_fast", 21)).iloc[-1])
    ema_slow = _safe_float(_ema(close, spec.params.get("ema_slow", 55)).iloc[-1])
    rsi_val = _safe_float(_rsi(close, 14).iloc[-1])
    atr_val = _safe_float(_atr(high, low, close, 14).iloc[-1])
    vol_ratio = _volume_ratio(volume)
    if not all(np.isfinite([price, ema_fast, ema_slow, rsi_val, atr_val])):
        return []
    buffer_pct = float(spec.params.get("buffer_pct", 0.03))
    vol_min = float(spec.params.get("volume_min", 0.8))
    rr_target = float(spec.params.get("rr_target", 1.8))
    hold_days = int(spec.params.get("max_hold_days", 12))
    long_ok = (
        price > ema_slow
        and price <= ema_fast * (1 + buffer_pct)
        and price >= ema_fast * (1 - buffer_pct)
        and spec.params.get("rsi_long_min", 35) <= rsi_val <= spec.params.get("rsi_long_max", 58)
        and (not np.isfinite(vol_ratio) or vol_ratio >= vol_min)
    )
    short_ok = (
        spec.params.get("allow_short", False)
        and price < ema_slow
        and price >= ema_fast * (1 - buffer_pct)
        and price <= ema_fast * (1 + buffer_pct)
        and spec.params.get("rsi_short_min", 42) <= rsi_val <= spec.params.get("rsi_short_max", 68)
        and (not np.isfinite(vol_ratio) or vol_ratio >= vol_min)
    )
    if long_ok:
        tp = price + atr_val * spec.params.get("tp_atr", 2.2)
        sl = price - atr_val * spec.params.get("sl_atr", 1.2)
        rr = abs(tp - price) / abs(price - sl)
        if rr >= rr_target:
            return _make_signal(
                strategy_id=spec.strategy_id,
                asset_class=spec.asset_class,
                symbol=symbol,
                direction="LONG",
                entry=price,
                tp=tp,
                sl=sl,
                confidence=0.58 + min(0.18, max(0.0, (ema_fast / ema_slow - 1.0) * 8.0)),
                rr=rr,
                reason=f"Trend pullback: price near EMA{spec.params.get('ema_fast', 21)} inside uptrend, RSI={rsi_val:.1f}",
                max_hold_days=hold_days,
                extra={"ema_fast": round(ema_fast, 4), "ema_slow": round(ema_slow, 4), "rsi": round(rsi_val, 2), "volume_ratio": round(vol_ratio, 2) if np.isfinite(vol_ratio) else None},
            )
    if short_ok:
        tp = price - atr_val * spec.params.get("tp_atr", 2.0)
        sl = price + atr_val * spec.params.get("sl_atr", 1.1)
        rr = abs(tp - price) / abs(price - sl)
        if rr >= rr_target:
            return _make_signal(
                strategy_id=spec.strategy_id,
                asset_class=spec.asset_class,
                symbol=symbol,
                direction="SHORT",
                entry=price,
                tp=tp,
                sl=sl,
                confidence=0.57 + min(0.18, max(0.0, (ema_slow / ema_fast - 1.0) * 8.0)),
                rr=rr,
                reason=f"Trend pullback short: price rejected near EMA{spec.params.get('ema_fast', 21)}, RSI={rsi_val:.1f}",
                max_hold_days=hold_days,
                extra={"ema_fast": round(ema_fast, 4), "ema_slow": round(ema_slow, 4), "rsi": round(rsi_val, 2), "volume_ratio": round(vol_ratio, 2) if np.isfinite(vol_ratio) else None},
            )
    return []


def _breakout_squeeze(df: pd.DataFrame, symbol: str, spec: StrategySpec, history: dict[str, pd.DataFrame]) -> list[dict[str, Any]]:
    if len(df) < 140:
        return []
    close = df["Close"]
    high = df["High"]
    low = df["Low"]
    volume = df["Volume"]
    price = _safe_float(close.iloc[-1])
    ema_fast = _safe_float(_ema(close, spec.params.get("ema_fast", 20)).iloc[-1])
    ema_slow = _safe_float(_ema(close, spec.params.get("ema_slow", 50)).iloc[-1])
    adx_val = _safe_float(_adx(high, low, close, 14).iloc[-1])
    atr_val = _safe_float(_atr(high, low, close, 14).iloc[-1])
    _, _, _, width = _bollinger_width(close, spec.params.get("bb_period", 20))
    width_now = _safe_float(width.iloc[-1])
    width_ma = _safe_float(width.rolling(60).mean().iloc[-1])
    vol_ratio = _volume_ratio(volume)
    if not all(np.isfinite([price, ema_fast, ema_slow, adx_val, atr_val, width_now, width_ma])):
        return []
    squeeze_ok = width_now <= width_ma * spec.params.get("squeeze_mult", 0.8)
    breakout_window = int(spec.params.get("breakout_window", 20))
    highest_close = _safe_float(close.iloc[-breakout_window:].max())
    lowest_close = _safe_float(close.iloc[-breakout_window:].min())
    hold_days = int(spec.params.get("max_hold_days", 14))
    if squeeze_ok and price >= highest_close and ema_fast > ema_slow and adx_val >= spec.params.get("adx_min", 18) and (not np.isfinite(vol_ratio) or vol_ratio >= spec.params.get("volume_min", 0.9)):
        tp = price + atr_val * spec.params.get("tp_atr", 2.6)
        sl = price - atr_val * spec.params.get("sl_atr", 1.2)
        rr = abs(tp - price) / abs(price - sl)
        return _make_signal(
            strategy_id=spec.strategy_id,
            asset_class=spec.asset_class,
            symbol=symbol,
            direction="LONG",
            entry=price,
            tp=tp,
            sl=sl,
            confidence=0.60 + min(0.18, max(0.0, (adx_val - 18.0) * 0.01)),
            rr=rr,
            reason=f"Squeeze breakout long: BB width compressed then price broke {breakout_window}d high with ADX={adx_val:.1f}",
            max_hold_days=hold_days,
            extra={"adx": round(adx_val, 2), "bb_width": round(width_now, 4), "volume_ratio": round(vol_ratio, 2) if np.isfinite(vol_ratio) else None},
        )
    if spec.params.get("allow_short", False) and squeeze_ok and price <= lowest_close and ema_fast < ema_slow and adx_val >= spec.params.get("adx_min", 18):
        tp = price - atr_val * spec.params.get("tp_atr", 2.2)
        sl = price + atr_val * spec.params.get("sl_atr", 1.1)
        rr = abs(tp - price) / abs(price - sl)
        return _make_signal(
            strategy_id=spec.strategy_id,
            asset_class=spec.asset_class,
            symbol=symbol,
            direction="SHORT",
            entry=price,
            tp=tp,
            sl=sl,
            confidence=0.59 + min(0.18, max(0.0, (adx_val - 18.0) * 0.01)),
            rr=rr,
            reason=f"Squeeze breakout short: compression resolved lower with ADX={adx_val:.1f}",
            max_hold_days=hold_days,
            extra={"adx": round(adx_val, 2), "bb_width": round(width_now, 4)},
        )
    return []


def _shock_reversion(df: pd.DataFrame, symbol: str, spec: StrategySpec, history: dict[str, pd.DataFrame]) -> list[dict[str, Any]]:
    window = int(spec.params.get("return_window", 5))
    if len(df) < max(80, window + 20):
        return []
    close = df["Close"]
    high = df["High"]
    low = df["Low"]
    price = _safe_float(close.iloc[-1])
    prev = _safe_float(close.iloc[-(window + 1)])
    rsi_val = _safe_float(_rsi(close, spec.params.get("rsi_period", 4)).iloc[-1])
    ema_anchor = _safe_float(_ema(close, spec.params.get("anchor_ema", 20)).iloc[-1])
    atr_val = _safe_float(_atr(high, low, close, 14).iloc[-1])
    if not all(np.isfinite([price, prev, rsi_val, ema_anchor, atr_val])) or prev <= 0:
        return []
    ret = price / prev - 1.0
    hold_days = int(spec.params.get("max_hold_days", 8))
    long_trigger = ret <= spec.params.get("negative_threshold", -0.08) and rsi_val <= spec.params.get("rsi_long", 25)
    short_trigger = spec.params.get("allow_short", False) and ret >= spec.params.get("positive_threshold", 0.10) and rsi_val >= spec.params.get("rsi_short", 75)
    if long_trigger:
        tp = min(ema_anchor, price + atr_val * spec.params.get("tp_atr", 2.0)) if ema_anchor > price else price + atr_val * spec.params.get("tp_atr", 2.0)
        sl = price - atr_val * spec.params.get("sl_atr", 1.1)
        rr = abs(tp - price) / abs(price - sl) if price > sl else 0.0
        if rr >= spec.params.get("rr_min", 1.1):
            return _make_signal(
                strategy_id=spec.strategy_id,
                asset_class=spec.asset_class,
                symbol=symbol,
                direction="LONG",
                entry=price,
                tp=tp,
                sl=sl,
                confidence=0.57 + min(0.20, abs(ret) * 0.8),
                rr=rr,
                reason=f"Shock reversion long: {window}d return {ret:.1%}, RSI={rsi_val:.1f}",
                max_hold_days=hold_days,
                extra={"return_window": window, "return_pct": round(ret, 4), "rsi": round(rsi_val, 2), "ema_anchor": round(ema_anchor, 4)},
            )
    if short_trigger:
        tp = max(ema_anchor, price - atr_val * spec.params.get("tp_atr", 2.0)) if ema_anchor < price else price - atr_val * spec.params.get("tp_atr", 2.0)
        sl = price + atr_val * spec.params.get("sl_atr", 1.1)
        rr = abs(tp - price) / abs(price - sl) if sl > price else 0.0
        if rr >= spec.params.get("rr_min", 1.1):
            return _make_signal(
                strategy_id=spec.strategy_id,
                asset_class=spec.asset_class,
                symbol=symbol,
                direction="SHORT",
                entry=price,
                tp=tp,
                sl=sl,
                confidence=0.57 + min(0.20, abs(ret) * 0.8),
                rr=rr,
                reason=f"Shock reversion short: {window}d return {ret:.1%}, RSI={rsi_val:.1f}",
                max_hold_days=hold_days,
                extra={"return_window": window, "return_pct": round(ret, 4), "rsi": round(rsi_val, 2), "ema_anchor": round(ema_anchor, 4)},
            )
    return []


def _relative_strength_rotation(df: pd.DataFrame, symbol: str, spec: StrategySpec, history: dict[str, pd.DataFrame]) -> list[dict[str, Any]]:
    lookback = int(spec.params.get("lookback", 63))
    if len(df) < lookback + 20:
        return []
    scores: list[tuple[str, float]] = []
    for peer in spec.symbols:
        peer_df = history.get(peer)
        if peer_df is None or len(peer_df) < lookback + 5:
            continue
        peer_close = peer_df["Close"]
        ret = _safe_float(peer_close.iloc[-1] / peer_close.iloc[-(lookback + 1)] - 1.0)
        if np.isfinite(ret):
            scores.append((peer, ret))
    if len(scores) < max(3, len(spec.symbols) // 2):
        return []
    scores.sort(key=lambda item: item[1], reverse=True)
    top_count = max(1, int(spec.params.get("top_count", 2)))
    bottom_count = max(1, int(spec.params.get("bottom_count", 2)))
    top_set = {name for name, _ in scores[:top_count]}
    bottom_set = {name for name, _ in scores[-bottom_count:]}
    close = df["Close"]
    high = df["High"]
    low = df["Low"]
    price = _safe_float(close.iloc[-1])
    ema_fast = _safe_float(_ema(close, 20).iloc[-1])
    ema_slow = _safe_float(_ema(close, 50).iloc[-1])
    atr_val = _safe_float(_atr(high, low, close, 14).iloc[-1])
    if not all(np.isfinite([price, ema_fast, ema_slow, atr_val])):
        return []
    hold_days = int(spec.params.get("max_hold_days", 18))
    if symbol in top_set and price > ema_fast > ema_slow:
        tp = price + atr_val * spec.params.get("tp_atr", 2.4)
        sl = price - atr_val * spec.params.get("sl_atr", 1.2)
        rr = abs(tp - price) / abs(price - sl)
        return _make_signal(
            strategy_id=spec.strategy_id,
            asset_class=spec.asset_class,
            symbol=symbol,
            direction="LONG",
            entry=price,
            tp=tp,
            sl=sl,
            confidence=0.60 + min(0.17, max(0.0, scores[0][1] - scores[-1][1])),
            rr=rr,
            reason=f"Relative-strength leader: top {top_count} of {len(scores)} over {lookback}d",
            max_hold_days=hold_days,
            extra={"top_peer": scores[0][0], "top_return": round(scores[0][1], 4), "bottom_peer": scores[-1][0], "bottom_return": round(scores[-1][1], 4)},
        )
    if spec.params.get("allow_short", False) and symbol in bottom_set and price < ema_fast < ema_slow:
        tp = price - atr_val * spec.params.get("tp_atr", 2.0)
        sl = price + atr_val * spec.params.get("sl_atr", 1.1)
        rr = abs(tp - price) / abs(price - sl)
        return _make_signal(
            strategy_id=spec.strategy_id,
            asset_class=spec.asset_class,
            symbol=symbol,
            direction="SHORT",
            entry=price,
            tp=tp,
            sl=sl,
            confidence=0.58 + min(0.15, max(0.0, scores[0][1] - scores[-1][1])),
            rr=rr,
            reason=f"Relative-strength laggard short: bottom {bottom_count} over {lookback}d",
            max_hold_days=hold_days,
            extra={"top_peer": scores[0][0], "bottom_peer": scores[-1][0]},
        )
    return []


def _gap_reversion(df: pd.DataFrame, symbol: str, spec: StrategySpec, history: dict[str, pd.DataFrame]) -> list[dict[str, Any]]:
    if len(df) < 80:
        return []
    open_price = _safe_float(df["Open"].iloc[-1])
    prev_close = _safe_float(df["Close"].iloc[-2])
    close = _safe_float(df["Close"].iloc[-1])
    high = df["High"]
    low = df["Low"]
    atr_val = _safe_float(_atr(high, low, df["Close"], 14).iloc[-1])
    if not all(np.isfinite([open_price, prev_close, close, atr_val])) or prev_close <= 0:
        return []
    gap = open_price / prev_close - 1.0
    rsi_val = _safe_float(_rsi(df["Close"], 5).iloc[-1])
    hold_days = int(spec.params.get("max_hold_days", 4))
    gap_min = float(spec.params.get("gap_min", 0.012))
    if gap <= -gap_min and rsi_val < spec.params.get("rsi_long", 35):
        entry = close
        tp = min(prev_close, entry + atr_val * spec.params.get("tp_atr", 1.6))
        sl = entry - atr_val * spec.params.get("sl_atr", 1.0)
        rr = abs(tp - entry) / abs(entry - sl) if entry > sl else 0.0
        return _make_signal(
            strategy_id=spec.strategy_id,
            asset_class=spec.asset_class,
            symbol=symbol,
            direction="LONG",
            entry=entry,
            tp=tp,
            sl=sl,
            confidence=0.58 + min(0.16, abs(gap) * 4.0),
            rr=rr,
            reason=f"Gap reversion long: gap {gap:.1%}, RSI={rsi_val:.1f}",
            max_hold_days=hold_days,
            extra={"gap_pct": round(gap, 4), "rsi": round(rsi_val, 2)},
        )
    if gap >= gap_min and spec.params.get("allow_short", True) and rsi_val > spec.params.get("rsi_short", 65):
        entry = close
        tp = max(prev_close, entry - atr_val * spec.params.get("tp_atr", 1.6))
        sl = entry + atr_val * spec.params.get("sl_atr", 1.0)
        rr = abs(tp - entry) / abs(entry - sl) if sl > entry else 0.0
        return _make_signal(
            strategy_id=spec.strategy_id,
            asset_class=spec.asset_class,
            symbol=symbol,
            direction="SHORT",
            entry=entry,
            tp=tp,
            sl=sl,
            confidence=0.58 + min(0.16, abs(gap) * 4.0),
            rr=rr,
            reason=f"Gap reversion short: gap {gap:.1%}, RSI={rsi_val:.1f}",
            max_hold_days=hold_days,
            extra={"gap_pct": round(gap, 4), "rsi": round(rsi_val, 2)},
        )
    return []


def _macro_regime(df: pd.DataFrame, symbol: str, spec: StrategySpec, history: dict[str, pd.DataFrame]) -> list[dict[str, Any]]:
    if len(df) < 120:
        return []
    benchmark_key = spec.params.get("benchmark_key")
    benchmark_symbol = BENCHMARKS.get(benchmark_key or "", benchmark_key)
    benchmark = history.get(benchmark_symbol or "")
    if benchmark is None or len(benchmark) < 120:
        return []
    close = df["Close"]
    high = df["High"]
    low = df["Low"]
    price = _safe_float(close.iloc[-1])
    atr_val = _safe_float(_atr(high, low, close, 14).iloc[-1])
    ema_fast = _safe_float(_ema(close, 20).iloc[-1])
    ema_slow = _safe_float(_ema(close, 50).iloc[-1])
    bench_close = benchmark["Close"]
    bench_fast = _safe_float(_ema(bench_close, 20).iloc[-1])
    bench_slow = _safe_float(_ema(bench_close, 50).iloc[-1])
    bench_rsi = _safe_float(_rsi(bench_close, 14).iloc[-1])
    if not all(np.isfinite([price, atr_val, ema_fast, ema_slow, bench_fast, bench_slow, bench_rsi])):
        return []
    hold_days = int(spec.params.get("max_hold_days", 12))
    mode = spec.params.get("mode", "risk_on")
    if mode == "dxy_alignment":
        meta = ALL_METADATA.get(symbol, {})
        sign = float(meta.get("dxy_sign", 1.0))
        dxy_up = bench_fast > bench_slow
        go_long = (sign > 0 and dxy_up and ema_fast > ema_slow) or (sign < 0 and not dxy_up and ema_fast > ema_slow)
        go_short = spec.params.get("allow_short", False) and ((sign > 0 and not dxy_up and ema_fast < ema_slow) or (sign < 0 and dxy_up and ema_fast < ema_slow))
        if go_long:
            tp = price + atr_val * spec.params.get("tp_atr", 2.0)
            sl = price - atr_val * spec.params.get("sl_atr", 1.1)
            rr = abs(tp - price) / abs(price - sl)
            return _make_signal(
                strategy_id=spec.strategy_id,
                asset_class=spec.asset_class,
                symbol=symbol,
                direction="LONG",
                entry=price,
                tp=tp,
                sl=sl,
                confidence=0.59 + min(0.16, abs(bench_fast / bench_slow - 1.0) * 15.0),
                rr=rr,
                reason=f"Macro alignment long: DXY trend matched {symbol} correlation sign {sign:+.1f}",
                max_hold_days=hold_days,
                extra={"benchmark": benchmark_symbol, "bench_rsi": round(bench_rsi, 2), "dxy_sign": sign},
            )
        if go_short:
            tp = price - atr_val * spec.params.get("tp_atr", 1.9)
            sl = price + atr_val * spec.params.get("sl_atr", 1.0)
            rr = abs(tp - price) / abs(price - sl)
            return _make_signal(
                strategy_id=spec.strategy_id,
                asset_class=spec.asset_class,
                symbol=symbol,
                direction="SHORT",
                entry=price,
                tp=tp,
                sl=sl,
                confidence=0.58 + min(0.16, abs(bench_fast / bench_slow - 1.0) * 15.0),
                rr=rr,
                reason=f"Macro alignment short: DXY trend opposed {symbol}",
                max_hold_days=hold_days,
                extra={"benchmark": benchmark_symbol, "bench_rsi": round(bench_rsi, 2), "dxy_sign": sign},
            )
        return []
    if mode == "fear_bid":
        vix_df = history.get(BENCHMARKS["vix"])
        spy_df = history.get(BENCHMARKS["spy"])
        if vix_df is None or spy_df is None or len(vix_df) < 50 or len(spy_df) < 50:
            return []
        vix_last = _safe_float(vix_df["Close"].iloc[-1])
        spy_rsi = _safe_float(_rsi(spy_df["Close"], 14).iloc[-1])
        if not all(np.isfinite([vix_last, spy_rsi])):
            return []
        if vix_last >= spec.params.get("vix_min", 24) and spy_rsi <= spec.params.get("spy_rsi_max", 40) and ema_fast > ema_slow:
            tp = price + atr_val * spec.params.get("tp_atr", 2.3)
            sl = price - atr_val * spec.params.get("sl_atr", 1.1)
            rr = abs(tp - price) / abs(price - sl)
            return _make_signal(
                strategy_id=spec.strategy_id,
                asset_class=spec.asset_class,
                symbol=symbol,
                direction="LONG",
                entry=price,
                tp=tp,
                sl=sl,
                confidence=0.63 + min(0.15, max(0.0, (vix_last - spec.params.get('vix_min', 24)) * 0.01)),
                rr=rr,
                reason=f"Fear-bid long: VIX={vix_last:.1f}, SPY RSI={spy_rsi:.1f}",
                max_hold_days=hold_days,
                extra={"vix": round(vix_last, 2), "spy_rsi": round(spy_rsi, 2)},
            )
        return []
    if mode == "bond_vs_equity":
        spy_df = history.get(BENCHMARKS["spy"])
        if spy_df is None or len(spy_df) < 120:
            return []
        spy_fast = _safe_float(_ema(spy_df["Close"], 20).iloc[-1])
        spy_slow = _safe_float(_ema(spy_df["Close"], 50).iloc[-1])
        if not all(np.isfinite([spy_fast, spy_slow])):
            return []
        risk_off = spy_fast < spy_slow
        wants_bonds = symbol in {"TLT", "ZB=F", "ZN=F"}
        wants_equities = symbol in {"SPY", "QQQ", "IWM", "ES=F", "NQ=F", "YM=F", "RTY=F"}
        if ((risk_off and wants_bonds) or ((not risk_off) and wants_equities)) and ema_fast > ema_slow:
            tp = price + atr_val * spec.params.get("tp_atr", 2.2)
            sl = price - atr_val * spec.params.get("sl_atr", 1.1)
            rr = abs(tp - price) / abs(price - sl)
            return _make_signal(
                strategy_id=spec.strategy_id,
                asset_class=spec.asset_class,
                symbol=symbol,
                direction="LONG",
                entry=price,
                tp=tp,
                sl=sl,
                confidence=0.60 + (0.08 if risk_off and wants_bonds else 0.05),
                rr=rr,
                reason=f"Bond/equity regime long: risk_off={risk_off}, benchmark=SPY",
                max_hold_days=hold_days,
                extra={"risk_off": risk_off, "spy_fast": round(spy_fast, 4), "spy_slow": round(spy_slow, 4)},
            )
        return []
    return []


def _seasonal_bias(df: pd.DataFrame, symbol: str, spec: StrategySpec, history: dict[str, pd.DataFrame]) -> list[dict[str, Any]]:
    if len(df) < 80:
        return []
    last_date = pd.Timestamp(df.index[-1])
    month = int(last_date.month)
    buy_months = set(spec.params.get("buy_months", []))
    sell_months = set(spec.params.get("sell_months", []))
    close = df["Close"]
    high = df["High"]
    low = df["Low"]
    price = _safe_float(close.iloc[-1])
    rsi_val = _safe_float(_rsi(close, 14).iloc[-1])
    ema_fast = _safe_float(_ema(close, 20).iloc[-1])
    atr_val = _safe_float(_atr(high, low, close, 14).iloc[-1])
    if not all(np.isfinite([price, rsi_val, ema_fast, atr_val])):
        return []
    hold_days = int(spec.params.get("max_hold_days", 14))
    if month in buy_months and rsi_val < spec.params.get("rsi_long_max", 62) and price >= ema_fast * 0.96:
        tp = price + atr_val * spec.params.get("tp_atr", 2.1)
        sl = price - atr_val * spec.params.get("sl_atr", 1.1)
        rr = abs(tp - price) / abs(price - sl)
        return _make_signal(
            strategy_id=spec.strategy_id,
            asset_class=spec.asset_class,
            symbol=symbol,
            direction="LONG",
            entry=price,
            tp=tp,
            sl=sl,
            confidence=0.60,
            rr=rr,
            reason=f"Seasonal long window month={month}, RSI={rsi_val:.1f}",
            max_hold_days=hold_days,
            extra={"month": month, "rsi": round(rsi_val, 2)},
        )
    if month in sell_months and spec.params.get("allow_short", True) and rsi_val > spec.params.get("rsi_short_min", 40):
        tp = price - atr_val * spec.params.get("tp_atr", 1.9)
        sl = price + atr_val * spec.params.get("sl_atr", 1.0)
        rr = abs(tp - price) / abs(price - sl)
        return _make_signal(
            strategy_id=spec.strategy_id,
            asset_class=spec.asset_class,
            symbol=symbol,
            direction="SHORT",
            entry=price,
            tp=tp,
            sl=sl,
            confidence=0.58,
            rr=rr,
            reason=f"Seasonal short window month={month}, RSI={rsi_val:.1f}",
            max_hold_days=hold_days,
            extra={"month": month, "rsi": round(rsi_val, 2)},
        )
    return []


FAMILY_HANDLERS = {
    "trend_pullback": _trend_pullback,
    "breakout_squeeze": _breakout_squeeze,
    "shock_reversion": _shock_reversion,
    "relative_strength": _relative_strength_rotation,
    "gap_reversion": _gap_reversion,
    "macro_regime": _macro_regime,
    "seasonal_bias": _seasonal_bias,
}


STRATEGY_SPECS: tuple[StrategySpec, ...] = (
    StrategySpec("crypto_trend_compression_breakout", "crypto", "breakout_squeeze", tuple(CRYPTO_SYMBOLS), "Momentum continuation after volatility compression in majors and liquid alts.", 42.8, 1.10, {"squeeze_mult": 0.78, "breakout_window": 25, "adx_min": 17, "tp_atr": 2.9, "sl_atr": 1.2, "max_hold_days": 16}),
    StrategySpec("crypto_vwap_proxy_pullback", "crypto", "trend_pullback", tuple(CRYPTO_SYMBOLS), "Trend pullback entry near fast EMA after shallow reset.", 42.8, 1.10, {"ema_fast": 21, "ema_slow": 55, "buffer_pct": 0.04, "rsi_long_min": 34, "rsi_long_max": 56, "tp_atr": 2.4, "sl_atr": 1.2, "max_hold_days": 12}),
    StrategySpec("crypto_relative_strength_rotation", "crypto", "relative_strength", tuple(CRYPTO_SYMBOLS), "Long strongest relative performers and optionally fade laggards.", 42.8, 1.10, {"lookback": 63, "top_count": 1, "allow_short": False, "tp_atr": 2.8, "sl_atr": 1.0, "max_hold_days": 18}),
    StrategySpec("crypto_panic_wick_reclaim", "crypto", "shock_reversion", tuple(CRYPTO_SYMBOLS), "Fade multi-day flushes into high-liquidity crypto names.", 42.8, 1.10, {"return_window": 4, "negative_threshold": -0.15, "rsi_long": 20, "tp_atr": 2.6, "sl_atr": 1.0, "max_hold_days": 7}),
    StrategySpec("crypto_parabolic_exhaustion_fade", "crypto", "shock_reversion", tuple(CRYPTO_SYMBOLS), "Short parabolic daily extensions when momentum runs too hot.", 42.8, 1.10, {"return_window": 4, "positive_threshold": 0.18, "rsi_short": 82, "allow_short": True, "tp_atr": 2.4, "sl_atr": 1.0, "max_hold_days": 6}),
    StrategySpec("crypto_range_break_reclaim", "crypto", "trend_pullback", tuple(CRYPTO_SYMBOLS), "Re-enter crypto leaders after shallow range-break reclaim events to increase pick cadence.", 42.8, 1.10, {"ema_fast": 13, "ema_slow": 34, "buffer_pct": 0.05, "allow_short": False, "rsi_long_min": 32, "rsi_long_max": 60, "volume_min": 0.75, "tp_atr": 2.1, "sl_atr": 1.0, "max_hold_days": 10}),
    StrategySpec("crypto_vol_compression_reversal", "crypto", "breakout_squeeze", tuple(CRYPTO_SYMBOLS), "Capture post-compression reversals with lighter ADX gate to avoid under-trading.", 42.8, 1.10, {"squeeze_mult": 0.88, "breakout_window": 18, "adx_min": 12, "allow_short": True, "tp_atr": 2.2, "sl_atr": 1.0, "max_hold_days": 9}),

    StrategySpec("equity_pead_gap_followthrough", "equity", "gap_reversion", tuple(EQUITY_SYMBOLS), "Exploit post-gap continuation/reversion in liquid US equities.", 45.8, 1.00, {"gap_min": 0.025, "allow_short": True, "rsi_long": 30, "rsi_short": 70, "tp_atr": 2.0, "sl_atr": 0.9, "max_hold_days": 4}),
    StrategySpec("equity_quality_trend_pullback", "equity", "trend_pullback", tuple(EQUITY_SYMBOLS), "Buy shallow pullbacks in persistent equity leaders.", 45.8, 1.00, {"ema_fast": 20, "ema_slow": 60, "buffer_pct": 0.025, "rsi_long_min": 38, "rsi_long_max": 52, "volume_min": 1.0, "tp_atr": 2.6, "sl_atr": 1.0, "max_hold_days": 10}),
    StrategySpec("equity_smallcap_base_breakout", "equity", "breakout_squeeze", ("PLTR", "SNOW", "AMD", "META", "NVDA", "AMZN"), "Breakout bias in higher-beta growth equities with real volume.", 45.8, 1.00, {"squeeze_mult": 0.80, "breakout_window": 30, "adx_min": 16, "volume_min": 1.0, "tp_atr": 2.8, "sl_atr": 1.2, "max_hold_days": 15}),
    StrategySpec("equity_defensive_flush_rebound", "equity", "shock_reversion", ("KO", "JPM", "UNH", "MSFT", "AAPL", "XOM"), "Mean-revert sharp flushes in resilient large caps.", 45.8, 1.00, {"return_window": 4, "negative_threshold": -0.09, "rsi_long": 22, "tp_atr": 2.1, "sl_atr": 0.9, "max_hold_days": 6}),
    StrategySpec("equity_relative_strength_leaders", "equity", "relative_strength", tuple(EQUITY_SYMBOLS), "Ride the strongest stock trend cohort rather than broad beta.", 45.8, 1.00, {"lookback": 63, "top_count": 3, "allow_short": False, "tp_atr": 2.7, "sl_atr": 1.2, "max_hold_days": 16}),
    StrategySpec("equity_high_beta_pullback_rotation", "equity", "relative_strength", ("NVDA", "AMD", "PLTR", "META", "AMZN", "SNOW"), "Increase small/high-beta equity pick count via relative-strength pullback rotation.", 45.8, 1.00, {"lookback": 42, "top_count": 2, "allow_short": True, "bottom_count": 2, "tp_atr": 2.3, "sl_atr": 1.0, "max_hold_days": 11}),
    StrategySpec("equity_breadth_shock_snapback", "equity", "shock_reversion", tuple(EQUITY_SYMBOLS), "Broad-basket snapback strategy targeting low WR streak periods in equities.", 45.8, 1.00, {"return_window": 3, "negative_threshold": -0.07, "positive_threshold": 0.09, "allow_short": True, "rsi_long": 24, "rsi_short": 76, "tp_atr": 1.9, "sl_atr": 1.0, "max_hold_days": 6}),

    StrategySpec("etf_sector_leader_rotation", "etf", "relative_strength", ("XLK", "XLF", "XLV", "XLI", "XLU", "XLP"), "Rotate into leading sectors instead of generic index exposure.", 33.3, 0.19, {"lookback": 63, "top_count": 1, "allow_short": False, "tp_atr": 2.6, "sl_atr": 1.0, "max_hold_days": 20}),
    StrategySpec("etf_volatility_crush_reentry", "etf", "macro_regime", ("SPY", "QQQ", "IWM"), "Re-enter broad-market ETFs after volatility spikes start normalizing.", 33.3, 0.19, {"benchmark_key": "vix", "mode": "fear_bid", "vix_min": 26, "spy_rsi_max": 42, "tp_atr": 2.1, "sl_atr": 1.0, "max_hold_days": 12}),
    StrategySpec("etf_bond_equity_switch", "etf", "macro_regime", ("SPY", "QQQ", "IWM", "TLT"), "Switch between duration and equity beta using SPY trend regime.", 33.3, 0.19, {"mode": "bond_vs_equity", "tp_atr": 2.3, "sl_atr": 1.1, "max_hold_days": 16}),
    StrategySpec("etf_smallcap_gap_snapback", "etf", "gap_reversion", ("IWM", "SPY", "QQQ"), "Fade outsized ETF gaps where broad liquidity usually repairs price.", 33.3, 0.19, {"gap_min": 0.015, "allow_short": True, "rsi_long": 34, "rsi_short": 66, "tp_atr": 1.7, "sl_atr": 1.0, "max_hold_days": 4}),
    StrategySpec("etf_commodity_divergence_breakout", "etf", "breakout_squeeze", ("GLD", "TLT", "XLU", "XLP", "XLK"), "Use defensive/risk-on ETF divergences as a portfolio rotation engine.", 33.3, 0.19, {"squeeze_mult": 0.82, "breakout_window": 22, "adx_min": 15, "tp_atr": 2.4, "sl_atr": 1.1, "max_hold_days": 14}),

    StrategySpec("forex_dxy_breakout_alignment", "forex", "macro_regime", tuple(FOREX_SYMBOLS), "Align major FX pairs with Dollar Index trend direction.", 43.5, 1.00, {"benchmark_key": "dxy", "mode": "dxy_alignment", "allow_short": True, "tp_atr": 2.0, "sl_atr": 1.0, "max_hold_days": 9}),
    StrategySpec("forex_carry_trend_pullback", "forex", "trend_pullback", tuple(FOREX_SYMBOLS), "Blend rate differential bias with pullback entries in majors.", 43.5, 1.00, {"ema_fast": 20, "ema_slow": 50, "buffer_pct": 0.01, "allow_short": False, "rsi_long_min": 39, "rsi_long_max": 54, "tp_atr": 1.9, "sl_atr": 0.9, "max_hold_days": 8}),
    StrategySpec("forex_range_squeeze_breakout", "forex", "breakout_squeeze", tuple(FOREX_SYMBOLS), "Trade compression resolution in lower-volatility FX pairs.", 43.5, 1.00, {"squeeze_mult": 0.75, "breakout_window": 18, "adx_min": 14, "allow_short": True, "tp_atr": 1.9, "sl_atr": 1.0, "max_hold_days": 9}),
    StrategySpec("forex_rsi2_snapback", "forex", "shock_reversion", tuple(FOREX_SYMBOLS), "Fade outsized 3-day FX moves back toward trend equilibrium.", 43.5, 1.00, {"return_window": 3, "negative_threshold": -0.025, "positive_threshold": 0.025, "rsi_long": 22, "rsi_short": 78, "allow_short": True, "tp_atr": 1.7, "sl_atr": 0.9, "max_hold_days": 6}),
    StrategySpec("forex_dollar_exhaustion_fade", "forex", "shock_reversion", ("EURUSD=X", "GBPUSD=X", "AUDUSD=X", "USDCAD=X", "USDJPY=X"), "Fade extreme daily dollar runs when the move is overstretched.", 43.5, 1.00, {"return_window": 5, "negative_threshold": -0.03, "positive_threshold": 0.03, "rsi_long": 24, "rsi_short": 76, "allow_short": True, "tp_atr": 1.8, "sl_atr": 1.0, "max_hold_days": 7}),
    StrategySpec("forex_session_gap_reversion", "forex", "gap_reversion", tuple(FOREX_SYMBOLS), "Fill session dislocations in majors to improve low-pick FX cohorts.", 43.5, 1.00, {"gap_min": 0.004, "allow_short": True, "rsi_long": 32, "rsi_short": 68, "tp_atr": 1.5, "sl_atr": 0.9, "max_hold_days": 3}),
    StrategySpec("forex_macro_strength_rotation", "forex", "relative_strength", tuple(FOREX_SYMBOLS), "Cross-pair relative-strength routing for macro regime transitions.", 43.5, 1.00, {"lookback": 30, "top_count": 2, "bottom_count": 2, "allow_short": True, "tp_atr": 1.9, "sl_atr": 1.0, "max_hold_days": 8}),

    StrategySpec("futures_index_gap_snapback", "futures", "gap_reversion", ("ES=F", "NQ=F", "YM=F", "RTY=F"), "Fade exaggerated overnight gaps in equity index futures.", 6.3, 0.13, {"gap_min": 0.012, "allow_short": True, "rsi_long": 32, "rsi_short": 68, "tp_atr": 1.7, "sl_atr": 1.0, "max_hold_days": 3}),
    StrategySpec("futures_index_trend_pullback", "futures", "trend_pullback", ("ES=F", "NQ=F", "YM=F", "RTY=F"), "Pullback entries for index futures when primary trend remains intact.", 6.3, 0.13, {"ema_fast": 20, "ema_slow": 60, "buffer_pct": 0.02, "allow_short": True, "tp_atr": 2.2, "sl_atr": 1.1, "max_hold_days": 9}),
    StrategySpec("futures_treasury_regime_follow", "futures", "macro_regime", ("ZN=F", "ZB=F"), "Own duration when equity beta breaks down.", 6.3, 0.13, {"mode": "bond_vs_equity", "tp_atr": 2.0, "sl_atr": 1.0, "max_hold_days": 14}),
    StrategySpec("futures_momentum_compression_breakout", "futures", "breakout_squeeze", ("ES=F", "NQ=F", "ZN=F", "ZB=F"), "Breakout futures only after volatility has truly compressed.", 6.3, 0.13, {"squeeze_mult": 0.78, "breakout_window": 20, "adx_min": 16, "allow_short": True, "tp_atr": 2.4, "sl_atr": 1.1, "max_hold_days": 12}),
    StrategySpec("futures_cross_contract_strength", "futures", "relative_strength", ("ES=F", "NQ=F", "YM=F", "RTY=F", "ZN=F", "ZB=F"), "Cross-contract momentum rotation across index and bond futures.", 6.3, 0.13, {"lookback": 42, "top_count": 2, "allow_short": True, "bottom_count": 2, "tp_atr": 2.3, "sl_atr": 1.1, "max_hold_days": 12}),
    StrategySpec("futures_risk_parity_reclaim", "futures", "trend_pullback", ("ES=F", "NQ=F", "ZN=F", "ZB=F"), "Higher-frequency futures pullback engine for low PF / low pick clusters.", 6.3, 0.13, {"ema_fast": 18, "ema_slow": 48, "buffer_pct": 0.03, "allow_short": True, "rsi_long_min": 35, "rsi_long_max": 60, "rsi_short_min": 42, "rsi_short_max": 68, "tp_atr": 2.0, "sl_atr": 1.0, "max_hold_days": 8}),

    StrategySpec("commodity_gold_fear_bid", "commodity", "macro_regime", ("GC=F", "SI=F", "GLD"), "Ride safe-haven demand into precious metals during fear spikes.", 0.0, 0.0, {"benchmark_key": "vix", "mode": "fear_bid", "vix_min": 24, "spy_rsi_max": 42, "tp_atr": 2.2, "sl_atr": 1.0, "max_hold_days": 12}),
    StrategySpec("commodity_crude_crash_rebound", "commodity", "shock_reversion", ("CL=F", "NG=F"), "Fade energy washouts after multi-day liquidations.", 0.0, 0.0, {"return_window": 4, "negative_threshold": -0.09, "positive_threshold": 0.11, "rsi_long": 24, "rsi_short": 78, "allow_short": True, "tp_atr": 2.2, "sl_atr": 1.1, "max_hold_days": 7}),
    StrategySpec("commodity_silver_beta_breakout", "commodity", "breakout_squeeze", ("SI=F", "GC=F", "HG=F"), "Use silver and metals beta when the complex leaves compression.", 0.0, 0.0, {"squeeze_mult": 0.80, "breakout_window": 24, "adx_min": 15, "allow_short": True, "tp_atr": 2.5, "sl_atr": 1.1, "max_hold_days": 13}),
    StrategySpec("commodity_grain_seasonal_rotation", "commodity", "seasonal_bias", ("CORN", "WEAT", "SOYB"), "Seasonal crop-cycle entries in grain ETFs.", 0.0, 0.0, {"buy_months": [3, 4, 10, 11], "sell_months": [6, 7], "rsi_long_max": 60, "rsi_short_min": 42, "allow_short": True, "tp_atr": 1.9, "sl_atr": 1.0, "max_hold_days": 18}),
    StrategySpec("commodity_copper_growth_reversal", "commodity", "trend_pullback", ("HG=F", "GC=F", "SI=F"), "Buy orderly pullbacks in industrial metals when growth proxies stay constructive.", 0.0, 0.0, {"ema_fast": 20, "ema_slow": 55, "buffer_pct": 0.03, "allow_short": True, "tp_atr": 2.3, "sl_atr": 1.1, "max_hold_days": 11}),
)


def evaluate_strategy(
    spec: StrategySpec,
    df: pd.DataFrame,
    symbol: str,
    history: dict[str, pd.DataFrame],
) -> list[dict[str, Any]]:
    handler = FAMILY_HANDLERS[spec.family]
    return handler(df, symbol, spec, history)


def all_symbols() -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for spec in STRATEGY_SPECS:
        for symbol in spec.symbols:
            if symbol not in seen:
                ordered.append(symbol)
                seen.add(symbol)
    for symbol in BENCHMARKS.values():
        if symbol not in seen:
            ordered.append(symbol)
            seen.add(symbol)
    return ordered
