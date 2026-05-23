#!/usr/bin/env python3
"""
Antigravity Mutations — Audit-Informed Edge Exploiters
======================================================

Created: 2026-03-14 by Antigravity AI
Context: Full system audit revealed only 7/94 systems have positive edge.
         These mutations are designed to exploit SPECIFIC patterns found
         in the audit data from the proven winning systems.

COMPLEMENTARY to Claude's 5 super mutations (keltner_rsi_confluence_v2,
consensus_deep_value_hybrid, genesis_momentum_blend, ml_keltner_adaptive,
multi_system_conviction_filter). Zero overlap.

Mutations:
  AG1: battleground_elite_dual — Only fires when BOTH BTC and SOL Keltner
       (the two ROBUST walk-forward systems) agree on direction.
  AG2: volatility_regime_switch — ATR regime detection: mean-reversion in
       low vol, breakout in high vol. Adapts strategy to market conditions.
  AG3: volume_exhaustion_reversal — Price making new lows while volume
       declining = selling exhaustion. Contrarian buy at capitulation.
  AG4: multi_timeframe_alignment — Requires signal alignment across 1h AND
       4h timeframes before entering. Filters false signals.
  AG5: drawdown_sniper_v2 — Targets coins in -5% to -15% drawdown from
       recent high with volume capitulation. Based on audit finding that
       flash crash reversions have highest conviction.

All mutations follow the same interface as dna_winner_mutations.py:
  - Input: dict[symbol -> DataFrame]
  - Output: list[dict] (standard pick format)
  - Uses _base_signal() for consistent output
  - SANDBOX tier (0.3 weight) until forward-tested

Data Sources: Binance API (klines), Fear & Greed index
"""

from __future__ import annotations

import json
import math
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

# ── Inline indicators (self-contained, no external deps) ─────────────────

def _sma(series: pd.Series, period: int) -> pd.Series:
    return series.rolling(period).mean()

def _ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()

def _rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss.replace(0, np.nan)
    return (100 - 100 / (1 + rs)).fillna(50.0)

def _atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    tr = pd.concat([
        high - low,
        (high - close.shift(1)).abs(),
        (low - close.shift(1)).abs()
    ], axis=1).max(axis=1)
    return tr.rolling(period).mean()

def _keltner_channels(high: pd.Series, low: pd.Series, close: pd.Series,
                      ema_period: int = 20, atr_period: int = 14,
                      atr_mult: float = 2.0) -> tuple:
    """Returns (upper, mid, lower) Keltner Channels."""
    mid = _ema(close, ema_period)
    atr_val = _atr(high, low, close, atr_period)
    upper = mid + atr_mult * atr_val
    lower = mid - atr_mult * atr_val
    return upper, mid, lower


# ── Helpers ──────────────────────────────────────────────────────────────

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def _smart_round(value: float) -> float:
    if value is None or not np.isfinite(value):
        return 0.0
    if abs(value) >= 1000:
        return round(value, 2)
    if abs(value) >= 1:
        return round(value, 4)
    if abs(value) >= 0.01:
        return round(value, 6)
    return round(value, 8)

def _base_signal(strategy: str, symbol: str, signal_type: str, entry: float,
                 tp: float, sl: float, confidence: float, reason: str,
                 parent_system: str, mutation_type: str, **extra) -> dict:
    """Create standardized signal dict with mutation metadata."""
    rr = 0.0
    if signal_type == "BUY" and entry > sl:
        rr = (tp - entry) / (entry - sl)
    elif signal_type == "SELL" and sl > entry:
        rr = (entry - tp) / (sl - entry)

    sig = {
        "strategy": strategy,
        "symbol": symbol,
        "signal_type": signal_type,
        "entry_price": _smart_round(entry),
        "take_profit": _smart_round(tp),
        "stop_loss": _smart_round(sl),
        "confidence": round(min(0.85, confidence), 4),
        "risk_reward": round(max(0, rr), 2),
        "reason": reason,
        "timestamp": _now_iso(),
        "category": "crypto",
        "trust_tier": "SANDBOX",
        "trust_weight": 0.3,
        "parent_system": parent_system,
        "mutation_type": mutation_type,
        "mutation_source": "antigravity_v96_audit",
    }
    sig.update(extra)
    return sig


# ── Data Fetching ────────────────────────────────────────────────────────

BINANCE_MIRRORS = [
    "https://api.binance.com", "https://api1.binance.com",
    "https://api2.binance.com", "https://api3.binance.com",
    "https://data-api.binance.vision",
]

def fetch_binance_klines(symbol: str, interval: str = "1h", limit: int = 300) -> pd.DataFrame:
    """Fetch OHLCV from Binance with mirror rotation."""
    for base in BINANCE_MIRRORS:
        url = f"{base}/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "AntigravityMutations/1.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode())
            if data and isinstance(data, list) and len(data) > 20:
                df = pd.DataFrame(data, columns=[
                    "open_time", "Open", "High", "Low", "Close", "Volume",
                    "close_time", "qav", "num_trades", "taker_buy_base",
                    "taker_buy_quote", "ignore"
                ])
                for col in ["Open", "High", "Low", "Close", "Volume"]:
                    df[col] = pd.to_numeric(df[col], errors="coerce")
                df["open_time"] = pd.to_datetime(df["open_time"], unit="ms")
                df.set_index("open_time", inplace=True)
                return df
        except Exception:
            continue
    return pd.DataFrame()


# ═══════════════════════════════════════════════════════════════════════════
# AG1: BATTLEGROUND ELITE DUAL — Crown Jewel Confluence
# ═══════════════════════════════════════════════════════════════════════════
#
# Audit insight: Walk-forward validation (2026-03-13) proved that ONLY
# BTC Keltner (+5.8% WR improvement OOS) and SOL Keltner (-12.9% but
# still 62.1% test WR) are ROBUST. ETH/XRP Keltner collapsed -50%/-65%.
#
# This mutation only fires when BOTH BTC and SOL Keltner agree on
# direction. Ultra-high conviction, low frequency.
# ═══════════════════════════════════════════════════════════════════════════

ELITE_DUAL_SYMBOLS = {
    "BTCUSDT": {"ema": 20, "atr_mult": 2.0},  # Walk-forward ROBUST
    "SOLUSDT": {"ema": 20, "atr_mult": 2.0},  # Walk-forward ROBUST
}

# Symbols to trade when dual confluence fires
ELITE_TRADE_UNIVERSE = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
    "ADAUSDT", "AVAXUSDT", "LINKUSDT",
]


def battleground_elite_dual(data: dict) -> list[dict]:
    """
    AG1: Only enters when BOTH BTC and SOL Keltner signals agree.

    Logic:
      1. Compute Keltner Channels for BTC and SOL
      2. Detect compression→expansion breakout on both
      3. If both signal same direction → TRADE (ultra-high conviction)
      4. Apply to full trade universe (not just BTC/SOL)

    Walk-forward evidence:
      - BTC Keltner: 69.2% train → 75.0% test (+5.8%) ✅ ROBUST
      - SOL Keltner: 75.0% train → 62.1% test (-12.9%) ✅ ROBUST
      - Combined conviction: expected WR ~65-70% with 2.5+ PF

    Expected: Very low frequency (2-5 signals/week), very high WR
    """
    signals = []

    # Step 1: Get BTC and SOL Keltner signals
    anchor_signals = {}

    for anchor_sym, params in ELITE_DUAL_SYMBOLS.items():
        df = data.get(anchor_sym)
        if df is None or len(df) < 80:
            return signals  # Need BOTH anchors

        close = df["Close"]
        high = df["High"]
        low = df["Low"]
        volume = df["Volume"]
        current = float(close.iloc[-1])

        # Keltner Channels
        kc_upper, kc_mid, kc_lower = _keltner_channels(
            high, low, close,
            ema_period=params["ema"], atr_period=14,
            atr_mult=params["atr_mult"]
        )

        if pd.isna(kc_upper.iloc[-1]) or pd.isna(kc_lower.iloc[-1]):
            return signals

        kc_u = float(kc_upper.iloc[-1])
        kc_l = float(kc_lower.iloc[-1])
        kc_m = float(kc_mid.iloc[-1])

        # Compression detection: current bandwidth vs 20-bar avg bandwidth
        bandwidth = (kc_upper - kc_lower) / kc_mid
        bw_current = float(bandwidth.iloc[-1])
        bw_avg = float(bandwidth.rolling(20).mean().iloc[-1])

        if pd.isna(bw_avg) or bw_avg <= 0:
            return signals

        # Expansion: current bandwidth > 1.1x average (channels widening)
        is_expanding = bw_current > bw_avg * 1.1

        # Direction from price vs Keltner midline + expansion direction
        rsi_14 = float(_rsi(close, 14).iloc[-1])

        if current > kc_u and is_expanding:
            anchor_signals[anchor_sym] = {
                "direction": "BUY",
                "strength": (current - kc_u) / (kc_u - kc_m) if kc_u != kc_m else 0,
                "rsi": rsi_14,
                "bw_ratio": bw_current / bw_avg,
            }
        elif current < kc_l and is_expanding:
            anchor_signals[anchor_sym] = {
                "direction": "SELL",
                "strength": (kc_l - current) / (kc_m - kc_l) if kc_m != kc_l else 0,
                "rsi": rsi_14,
                "bw_ratio": bw_current / bw_avg,
            }

    # Step 2: Check if BOTH anchors agree
    if len(anchor_signals) < 2:
        return signals

    btc_sig = anchor_signals.get("BTCUSDT")
    sol_sig = anchor_signals.get("SOLUSDT")

    if btc_sig is None or sol_sig is None:
        return signals

    if btc_sig["direction"] != sol_sig["direction"]:
        return signals  # Disagreement — no trade

    agreed_direction = btc_sig["direction"]
    combined_strength = (btc_sig["strength"] + sol_sig["strength"]) / 2

    # Step 3: Apply to trade universe
    for symbol in ELITE_TRADE_UNIVERSE:
        df = data.get(symbol)
        if df is None or len(df) < 50:
            continue

        close = df["Close"]
        current = float(close.iloc[-1])
        if current <= 0:
            continue

        atr_val = float(_atr(df["High"], df["Low"], close).iloc[-1])
        if pd.isna(atr_val) or atr_val <= 0:
            continue

        rsi_14 = float(_rsi(close, 14).iloc[-1])

        # RSI guard: don't enter overbought for BUY or oversold for SELL
        if agreed_direction == "BUY" and rsi_14 > 78:
            continue
        if agreed_direction == "SELL" and rsi_14 < 22:
            continue

        # TP/SL: wider targets for high-conviction trades
        if agreed_direction == "BUY":
            tp = current + 3.0 * atr_val
            sl = current - 1.5 * atr_val
        else:
            tp = current - 3.0 * atr_val
            sl = current + 1.5 * atr_val

        # High base confidence due to dual-anchor confluence
        conf = min(0.85, 0.65 + combined_strength * 0.15 +
                   (btc_sig["bw_ratio"] + sol_sig["bw_ratio"] - 2) * 0.05)

        signals.append(_base_signal(
            "ag_elite_dual_mut", symbol, agreed_direction, current, tp, sl, conf,
            f"AG1 Elite Dual: BTC+SOL Keltner agree {agreed_direction}, "
            f"BTC strength={btc_sig['strength']:.2f}, SOL strength={sol_sig['strength']:.2f}, "
            f"combined bw_ratio={(btc_sig['bw_ratio'] + sol_sig['bw_ratio'])/2:.2f}",
            parent_system="battleground",
            mutation_type="elite_confluence",
            btc_direction=btc_sig["direction"],
            sol_direction=sol_sig["direction"],
            combined_strength=round(combined_strength, 3),
            rsi_14=round(rsi_14, 1),
            timeframe="1h",
        ))

    return signals


# ═══════════════════════════════════════════════════════════════════════════
# AG2: VOLATILITY REGIME SWITCH — Adaptive Strategy Selection
# ═══════════════════════════════════════════════════════════════════════════
#
# Audit insight: Some systems (Keltner) excel in trending markets,
# others (Bollinger mean-rev) in ranging markets. The problem is we
# run ALL systems ALL the time regardless of regime.
#
# This mutation detects the volatility regime and applies the
# appropriate strategy: mean-reversion in low vol, breakout in high vol.
# ═══════════════════════════════════════════════════════════════════════════

REGIME_SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
    "ADAUSDT", "AVAXUSDT", "DOGEUSDT", "LINKUSDT", "NEARUSDT",
]


def volatility_regime_switch(data: dict) -> list[dict]:
    """
    AG2: Detects volatility regime and applies appropriate strategy.

    Regime Detection:
      - ATR percentile over 50 bars determines regime
      - Low vol (ATR < 30th pctile): Mean-reversion (buy at BB lower, sell at upper)
      - High vol (ATR > 70th pctile): Breakout (buy above Keltner upper, sell below lower)
      - Medium vol: No signal (avoid chop)

    This is an anti-"one-size-fits-all" approach. The audit showed that
    systems fail because they apply trending logic in ranging markets
    and vice versa. This mutation adapts.

    Expected: Moderate frequency, WR ~55-60%
    """
    signals = []

    for symbol in REGIME_SYMBOLS:
        df = data.get(symbol)
        if df is None or len(df) < 80:
            continue

        close = df["Close"]
        high = df["High"]
        low = df["Low"]
        volume = df["Volume"]
        current = float(close.iloc[-1])
        if current <= 0:
            continue

        # Compute ATR and its percentile rank over 50 bars
        atr_series = _atr(high, low, close, 14)
        atr_val = float(atr_series.iloc[-1])
        if pd.isna(atr_val) or atr_val <= 0:
            continue

        atr_window = atr_series.iloc[-50:]
        atr_pctile = float((atr_window < atr_val).sum() / len(atr_window))

        rsi_14 = float(_rsi(close, 14).iloc[-1])
        if pd.isna(rsi_14):
            continue

        vol_avg = float(volume.rolling(20).mean().iloc[-1])
        vol_ratio = float(volume.iloc[-1]) / vol_avg if vol_avg > 0 else 1.0

        # ── LOW VOLATILITY REGIME: Mean-Reversion ──
        if atr_pctile < 0.30:
            # Bollinger mean-reversion: buy at lower band, sell at upper
            sma_20 = float(close.rolling(20).mean().iloc[-1])
            std_20 = float(close.rolling(20).std().iloc[-1])
            if pd.isna(sma_20) or pd.isna(std_20) or std_20 <= 0:
                continue

            bb_lower = sma_20 - 2 * std_20
            bb_upper = sma_20 + 2 * std_20

            if current <= bb_lower * 1.005 and rsi_14 < 38:
                tp = sma_20  # Target: revert to mean
                sl = current - 1.5 * atr_val
                conf = min(0.78, 0.55 + (38 - rsi_14) / 100 + (vol_ratio - 1.0) * 0.03)

                signals.append(_base_signal(
                    "ag_regime_meanrev_mut", symbol, "BUY", current, tp, sl, conf,
                    f"AG2 Low-Vol Mean-Rev: ATR pctile={atr_pctile:.0%} (<30%), "
                    f"price at BB lower, RSI={rsi_14:.1f}, target=SMA20",
                    parent_system="battleground",
                    mutation_type="regime_adaptive",
                    regime="low_vol_meanrev",
                    atr_percentile=round(atr_pctile, 2),
                    rsi_14=round(rsi_14, 1),
                    volume_ratio=round(vol_ratio, 2),
                    timeframe="1h",
                ))

            elif current >= bb_upper * 0.995 and rsi_14 > 62:
                tp = sma_20  # Target: revert to mean
                sl = current + 1.5 * atr_val
                conf = min(0.78, 0.55 + (rsi_14 - 62) / 100 + (vol_ratio - 1.0) * 0.03)

                signals.append(_base_signal(
                    "ag_regime_meanrev_mut", symbol, "SELL", current, tp, sl, conf,
                    f"AG2 Low-Vol Mean-Rev: ATR pctile={atr_pctile:.0%} (<30%), "
                    f"price at BB upper, RSI={rsi_14:.1f}, target=SMA20",
                    parent_system="battleground",
                    mutation_type="regime_adaptive",
                    regime="low_vol_meanrev",
                    atr_percentile=round(atr_pctile, 2),
                    rsi_14=round(rsi_14, 1),
                    volume_ratio=round(vol_ratio, 2),
                    timeframe="1h",
                ))

        # ── HIGH VOLATILITY REGIME: Keltner Breakout ──
        elif atr_pctile > 0.70:
            kc_upper, kc_mid, kc_lower = _keltner_channels(
                high, low, close, ema_period=20, atr_period=14, atr_mult=2.0
            )
            kc_u = float(kc_upper.iloc[-1])
            kc_l = float(kc_lower.iloc[-1])

            if pd.isna(kc_u) or pd.isna(kc_l):
                continue

            # Volume must confirm the breakout
            if vol_ratio < 1.2:
                continue

            if current > kc_u and rsi_14 < 78:
                tp = current + 2.5 * atr_val
                sl = current - 1.5 * atr_val
                conf = min(0.80, 0.58 + (current - kc_u) / (atr_val + 0.001) * 0.08 +
                           (vol_ratio - 1.2) * 0.04)

                signals.append(_base_signal(
                    "ag_regime_breakout_mut", symbol, "BUY", current, tp, sl, conf,
                    f"AG2 High-Vol Breakout: ATR pctile={atr_pctile:.0%} (>70%), "
                    f"price above Keltner upper, RSI={rsi_14:.1f}, vol={vol_ratio:.1f}x",
                    parent_system="battleground",
                    mutation_type="regime_adaptive",
                    regime="high_vol_breakout",
                    atr_percentile=round(atr_pctile, 2),
                    rsi_14=round(rsi_14, 1),
                    volume_ratio=round(vol_ratio, 2),
                    timeframe="1h",
                ))

            elif current < kc_l and rsi_14 > 22:
                tp = current - 2.5 * atr_val
                sl = current + 1.5 * atr_val
                conf = min(0.80, 0.58 + (kc_l - current) / (atr_val + 0.001) * 0.08 +
                           (vol_ratio - 1.2) * 0.04)

                signals.append(_base_signal(
                    "ag_regime_breakout_mut", symbol, "SELL", current, tp, sl, conf,
                    f"AG2 High-Vol Breakout: ATR pctile={atr_pctile:.0%} (>70%), "
                    f"price below Keltner lower, RSI={rsi_14:.1f}, vol={vol_ratio:.1f}x",
                    parent_system="battleground",
                    mutation_type="regime_adaptive",
                    regime="high_vol_breakout",
                    atr_percentile=round(atr_pctile, 2),
                    rsi_14=round(rsi_14, 1),
                    volume_ratio=round(vol_ratio, 2),
                    timeframe="1h",
                ))

    return signals


# ═══════════════════════════════════════════════════════════════════════════
# AG3: VOLUME EXHAUSTION REVERSAL — Capitulation Detection
# ═══════════════════════════════════════════════════════════════════════════
#
# Audit insight: KIMI flash crash reversal (drawdown + low RSI + volume)
# is one of the most consistently profitable patterns. But KIMI's
# implementation is broken (18.2% WR, dead system).
#
# This mutation reimplements the CONCEPT with better execution: looks
# for volume DECLINING during price drops (exhaustion) rather than
# volume spikes (which can signal continuation).
# ═══════════════════════════════════════════════════════════════════════════

EXHAUSTION_SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
    "ADAUSDT", "AVAXUSDT", "DOGEUSDT", "LINKUSDT", "NEARUSDT",
    "SUIUSDT", "APTUSDT", "INJUSDT",
]


def volume_exhaustion_reversal(data: dict) -> list[dict]:
    """
    AG3: Detects selling exhaustion — price dropping on declining volume.

    Classic Wyckoff pattern: when sellers are exhausted (volume dries up
    during a decline), the selloff is ending and a reversal is imminent.

    Entry conditions:
      1. Price in declining trend (5-bar close change < -2%)
      2. Volume DECLINING over same period (3-bar vol < 5-bar avg vol)
      3. RSI < 35 (oversold but not extreme panic)
      4. No extreme volume (< 2x avg — avoids panic dumps)

    This is the OPPOSITE of volume spike = buy signals. Volume exhaustion
    is a more reliable reversal indicator.

    Expected: Low-medium frequency (3-8 signals/week), WR ~58-64%
    """
    signals = []

    for symbol in EXHAUSTION_SYMBOLS:
        df = data.get(symbol)
        if df is None or len(df) < 30:
            continue

        close = df["Close"]
        volume = df["Volume"]
        high = df["High"]
        low = df["Low"]
        current = float(close.iloc[-1])
        if current <= 0:
            continue

        # 1. Price declining: 5-bar close change < -2%
        price_5bar = float(close.pct_change(5).iloc[-1]) if len(close) > 5 else 0
        if price_5bar >= -0.02:
            continue  # Not declining enough

        # 2. Volume DECLINING: recent 3 bars avg < prior 5-bar avg
        if len(volume) < 10:
            continue
        vol_recent_3 = float(volume.iloc[-3:].mean())
        vol_prior_5 = float(volume.iloc[-8:-3].mean())
        if vol_prior_5 <= 0:
            continue

        vol_decay_ratio = vol_recent_3 / vol_prior_5
        if vol_decay_ratio >= 0.85:
            continue  # Volume not declining enough

        # 3. Current volume not extreme (< 2x 20-bar avg)
        vol_avg_20 = float(volume.rolling(20).mean().iloc[-1])
        vol_ratio = float(volume.iloc[-1]) / vol_avg_20 if vol_avg_20 > 0 else 1.0
        if vol_ratio > 2.0:
            continue  # Panic dump, not exhaustion

        # 4. RSI oversold but not extreme panic
        rsi_14 = float(_rsi(close, 14).iloc[-1])
        if pd.isna(rsi_14) or rsi_14 >= 35 or rsi_14 < 10:
            continue

        # 5. Confirmed: drawdown from 10-bar high
        rolling_high = float(high.rolling(10).max().iloc[-1])
        drawdown_pct = (current - rolling_high) / rolling_high

        atr_val = float(_atr(high, low, close).iloc[-1])
        if pd.isna(atr_val) or atr_val <= 0:
            continue

        # TP: expect reversal to 50% of the drop (conservative)
        recovery_target = current + abs(rolling_high - current) * 0.5
        tp = max(recovery_target, current + 2.0 * atr_val)
        sl = current - 1.5 * atr_val

        # Confidence: deeper exhaustion + lower RSI = higher conviction
        exhaustion_depth = min(1.0, (0.85 - vol_decay_ratio) / 0.35)
        rsi_depth = (35 - rsi_14) / 25
        conf = min(0.82, 0.52 + 0.15 * exhaustion_depth + 0.12 * rsi_depth)

        signals.append(_base_signal(
            "ag_vol_exhaustion_mut", symbol, "BUY", current, tp, sl, conf,
            f"AG3 Vol Exhaustion: price {price_5bar:.1%} (5-bar), "
            f"vol decay={vol_decay_ratio:.2f} (<0.85), RSI={rsi_14:.1f}, "
            f"drawdown={drawdown_pct:.1%} — selling exhaustion detected",
            parent_system="battleground",
            mutation_type="exhaustion_reversal",
            price_5bar_pct=round(price_5bar * 100, 2),
            vol_decay_ratio=round(vol_decay_ratio, 3),
            drawdown_pct=round(drawdown_pct * 100, 2),
            rsi_14=round(rsi_14, 1),
            timeframe="1h",
        ))

    return signals


# ═══════════════════════════════════════════════════════════════════════════
# AG4: MULTI-TIMEFRAME ALIGNMENT — 1h + 4h Confluence
# ═══════════════════════════════════════════════════════════════════════════
#
# Audit insight: Single-timeframe signals generate too much noise.
# When 1h and 4h signals agree, the conviction is much higher.
#
# This mutation requires EMA trend + RSI + MACD alignment across
# BOTH timeframes before entering.
# ═══════════════════════════════════════════════════════════════════════════

MTF_SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
    "ADAUSDT", "AVAXUSDT", "LINKUSDT",
]


def multi_timeframe_alignment(data: dict, data_4h: dict = None) -> list[dict]:
    """
    AG4: Requires alignment across 1h and 4h timeframes.

    For each symbol, checks:
      - 1h: EMA(9) > EMA(21), MACD histogram > 0, RSI 35-65
      - 4h: EMA(9) > EMA(21), price > EMA(50), RSI 40-65

    Both timeframes must agree on direction. This is a strict filter
    that eliminates most false signals.

    If 4h data is not provided, synthesizes from 1h data by resampling.

    Expected: Low frequency (1-3 signals/week), WR ~62-68%
    """
    signals = []

    for symbol in MTF_SYMBOLS:
        df_1h = data.get(symbol)
        if df_1h is None or len(df_1h) < 100:
            continue

        close_1h = df_1h["Close"]
        high_1h = df_1h["High"]
        low_1h = df_1h["Low"]
        current = float(close_1h.iloc[-1])
        if current <= 0:
            continue

        # ── 1h Analysis ──
        ema_9_1h = float(_ema(close_1h, 9).iloc[-1])
        ema_21_1h = float(_ema(close_1h, 21).iloc[-1])
        rsi_1h = float(_rsi(close_1h, 14).iloc[-1])

        # MACD on 1h
        macd_1h = _ema(close_1h, 12) - _ema(close_1h, 26)
        macd_signal_1h = _ema(macd_1h, 9)
        macd_hist_1h = float((macd_1h - macd_signal_1h).iloc[-1])

        if pd.isna(ema_9_1h) or pd.isna(ema_21_1h) or pd.isna(rsi_1h):
            continue

        # ── 4h Analysis (synthesize by resampling 1h data) ──
        if data_4h and symbol in data_4h:
            df_4h = data_4h[symbol]
        else:
            # Resample 1h to 4h
            try:
                df_4h = df_1h.resample("4h").agg({
                    "Open": "first", "High": "max",
                    "Low": "min", "Close": "last",
                    "Volume": "sum"
                }).dropna()
            except Exception:
                continue

        if len(df_4h) < 30:
            continue

        close_4h = df_4h["Close"]
        ema_9_4h = float(_ema(close_4h, 9).iloc[-1])
        ema_21_4h = float(_ema(close_4h, 21).iloc[-1])
        ema_50_4h = float(_ema(close_4h, 50).iloc[-1]) if len(close_4h) > 50 else float(_ema(close_4h, 21).iloc[-1])
        rsi_4h = float(_rsi(close_4h, 14).iloc[-1])

        if pd.isna(ema_9_4h) or pd.isna(ema_21_4h) or pd.isna(rsi_4h):
            continue

        # ── Check BUY alignment ──
        buy_1h = (ema_9_1h > ema_21_1h and macd_hist_1h > 0 and 35 < rsi_1h < 65)
        buy_4h = (ema_9_4h > ema_21_4h and current > ema_50_4h and 40 < rsi_4h < 65)

        # ── Check SELL alignment ──
        sell_1h = (ema_9_1h < ema_21_1h and macd_hist_1h < 0 and 35 < rsi_1h < 65)
        sell_4h = (ema_9_4h < ema_21_4h and current < ema_50_4h and 35 < rsi_4h < 60)

        atr_val = float(_atr(high_1h, low_1h, close_1h).iloc[-1])
        if pd.isna(atr_val) or atr_val <= 0:
            continue

        if buy_1h and buy_4h:
            tp = current + 2.5 * atr_val
            sl = current - 1.5 * atr_val
            conf = min(0.82, 0.60 + (rsi_1h - 35) / 150 + (rsi_4h - 40) / 150)

            signals.append(_base_signal(
                "ag_mtf_aligned_mut", symbol, "BUY", current, tp, sl, conf,
                f"AG4 MTF Aligned BUY: 1h EMA9>21+MACD>0+RSI={rsi_1h:.0f}, "
                f"4h EMA9>21+price>EMA50+RSI={rsi_4h:.0f} — dual timeframe confluence",
                parent_system="battleground",
                mutation_type="multi_timeframe",
                rsi_1h=round(rsi_1h, 1),
                rsi_4h=round(rsi_4h, 1),
                macd_hist_1h=round(macd_hist_1h, 4),
                timeframe="1h+4h",
            ))

        elif sell_1h and sell_4h:
            tp = current - 2.5 * atr_val
            sl = current + 1.5 * atr_val
            conf = min(0.82, 0.60 + (65 - rsi_1h) / 150 + (60 - rsi_4h) / 150)

            signals.append(_base_signal(
                "ag_mtf_aligned_mut", symbol, "SELL", current, tp, sl, conf,
                f"AG4 MTF Aligned SELL: 1h EMA9<21+MACD<0+RSI={rsi_1h:.0f}, "
                f"4h EMA9<21+price<EMA50+RSI={rsi_4h:.0f} — dual timeframe confluence",
                parent_system="battleground",
                mutation_type="multi_timeframe",
                rsi_1h=round(rsi_1h, 1),
                rsi_4h=round(rsi_4h, 1),
                macd_hist_1h=round(macd_hist_1h, 4),
                timeframe="1h+4h",
            ))

    return signals


# ═══════════════════════════════════════════════════════════════════════════
# AG5: DRAWDOWN SNIPER V2 — Precision Capitulation Entry
# ═══════════════════════════════════════════════════════════════════════════
#
# Audit insight: The audit data shows that coins in -5% to -15% drawdown
# from their recent high, WITH specific volume and RSI patterns, tend
# to snap back. This is the flash crash reversal concept done RIGHT.
#
# Key difference from KIMI's flash crash (which has 18.2% WR):
#   - KIMI required volume SPIKE (>2x) — often catches panicking sellers
#     who are RIGHT to sell (continuation, not reversal)
#   - This mutation requires volume NORMALIZATION (vol returning to
#     average after spike) — confirms panic is subsiding
# ═══════════════════════════════════════════════════════════════════════════

SNIPER_SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
    "ADAUSDT", "AVAXUSDT", "DOGEUSDT", "LINKUSDT", "NEARUSDT",
    "SUIUSDT", "APTUSDT", "INJUSDT", "SEIUSDT", "JUPUSDT",
]


def drawdown_sniper_v2(data: dict) -> list[dict]:
    """
    AG5: Precision entry at capitulation with volume normalization.

    Entry conditions:
      1. Drawdown from 20-bar high between -5% and -15%
      2. RSI(14) between 20-35 (deeply oversold)
      3. Volume normalizing: current vol between 0.7x-1.3x of 20-bar avg
         (not too quiet = dead, not too high = panic still ongoing)
      4. Bullish candle: current bar's close > open (buying pressure emerging)
      5. Previous bar was bearish (i.e., we're seeing the TURN)

    Why this works:
      - -5% to -15% is the sweet spot: enough pain to cause capitulation
        but not enough to be a structural breakdown
      - Volume normalizing = panic is over, smart money accumulating
      - Bullish candle after bearish = the actual turn candle
      - RSI 20-35 = deeply oversold but not locked in freefall (RSI < 20)

    Expected: Low-medium frequency (2-6 signals/week), WR ~60-66%
    """
    signals = []

    for symbol in SNIPER_SYMBOLS:
        df = data.get(symbol)
        if df is None or len(df) < 30:
            continue

        close = df["Close"]
        open_price = df["Open"]
        high = df["High"]
        low = df["Low"]
        volume = df["Volume"]
        current = float(close.iloc[-1])
        if current <= 0:
            continue

        # 1. Drawdown from 20-bar high: between -5% and -15%
        rolling_high = float(high.rolling(20).max().iloc[-1])
        if rolling_high <= 0:
            continue
        drawdown = (current - rolling_high) / rolling_high

        if drawdown > -0.05 or drawdown < -0.15:
            continue  # Outside sweet spot

        # 2. RSI deeply oversold but not freefall
        rsi_14 = float(_rsi(close, 14).iloc[-1])
        if pd.isna(rsi_14) or rsi_14 < 20 or rsi_14 > 35:
            continue

        # 3. Volume normalizing (0.7x to 1.3x of avg)
        vol_avg = float(volume.rolling(20).mean().iloc[-1])
        if vol_avg <= 0:
            continue
        vol_ratio = float(volume.iloc[-1]) / vol_avg
        if vol_ratio < 0.7 or vol_ratio > 1.3:
            continue

        # 4. Current candle is bullish (close > open)
        current_open = float(open_price.iloc[-1])
        if current <= current_open:
            continue

        # 5. Previous candle was bearish
        if len(close) < 2 or len(open_price) < 2:
            continue
        prev_close = float(close.iloc[-2])
        prev_open = float(open_price.iloc[-2])
        if prev_close >= prev_open:
            continue  # Previous candle wasn't bearish

        # All conditions met — high conviction entry
        atr_val = float(_atr(high, low, close).iloc[-1])
        if pd.isna(atr_val) or atr_val <= 0:
            continue

        # TP: recovery to 40-60% of the drop
        recovery_40 = current + abs(rolling_high - current) * 0.40
        recovery_60 = current + abs(rolling_high - current) * 0.60
        tp = max(recovery_40, current + 2.0 * atr_val)
        sl = current - 1.5 * atr_val

        # Confidence: deeper drawdown in sweet spot + lower RSI = higher
        dd_quality = 1.0 - abs(drawdown + 0.10) / 0.05  # peaks at -10%
        dd_quality = max(0, min(1, dd_quality))
        rsi_quality = (35 - rsi_14) / 15  # 0 at 35, 1 at 20
        candle_body = (current - current_open) / current  # bullish candle size

        conf = min(0.84, 0.58 + 0.12 * dd_quality + 0.10 * rsi_quality +
                   min(candle_body * 20, 0.05))

        signals.append(_base_signal(
            "ag_dd_sniper_v2_mut", symbol, "BUY", current, tp, sl, conf,
            f"AG5 DD Sniper: drawdown={drawdown:.1%} (sweet spot -5% to -15%), "
            f"RSI={rsi_14:.1f}, vol normalizing={vol_ratio:.2f}x, "
            f"bullish candle after bearish — capitulation reversal",
            parent_system="battleground",
            mutation_type="drawdown_sniper",
            drawdown_pct=round(drawdown * 100, 2),
            rsi_14=round(rsi_14, 1),
            volume_ratio=round(vol_ratio, 2),
            candle_body_pct=round(candle_body * 100, 3),
            timeframe="1h",
        ))

    return signals


# ═══════════════════════════════════════════════════════════════════════════
# RUNNER: Fetch data + run all 5 mutations
# ═══════════════════════════════════════════════════════════════════════════

ALL_ANTIGRAVITY_MUTATIONS = {
    "ag_elite_dual": battleground_elite_dual,
    "ag_regime_switch": volatility_regime_switch,
    "ag_vol_exhaustion": volume_exhaustion_reversal,
    "ag_mtf_aligned": multi_timeframe_alignment,
    "ag_dd_sniper_v2": drawdown_sniper_v2,
}

ALL_SYMBOLS = list(set(
    list(ELITE_DUAL_SYMBOLS.keys()) + ELITE_TRADE_UNIVERSE +
    REGIME_SYMBOLS + EXHAUSTION_SYMBOLS + MTF_SYMBOLS + SNIPER_SYMBOLS
))


def run_all_mutations(data: dict = None) -> list[dict]:
    """
    Run all 5 Antigravity mutations and return combined signals.

    If data is not provided, fetches from Binance.
    """
    # Fetch data if not provided
    if data is None:
        data = {}
        print(f"Fetching data for {len(ALL_SYMBOLS)} symbols...")
        for symbol in ALL_SYMBOLS:
            df = fetch_binance_klines(symbol, interval="1h", limit=300)
            if not df.empty:
                data[symbol] = df
                print(f"  ✓ {symbol}: {len(df)} bars")
            else:
                print(f"  ✗ {symbol}: failed")

    all_signals = []
    for name, func in ALL_ANTIGRAVITY_MUTATIONS.items():
        try:
            signals = func(data)
            all_signals.extend(signals)
            print(f"  {name}: {len(signals)} signals")
        except Exception as e:
            print(f"  {name}: ERROR — {e}")

    return all_signals


def save_picks(signals: list[dict], output_path: str = None) -> str:
    """Save signals to JSON file."""
    if output_path is None:
        output_path = str(Path(__file__).resolve().parent.parent / "data" / "antigravity_mutation_picks.json")

    output = {
        "generated_at": _now_iso(),
        "mutation_source": "antigravity_v96_audit",
        "total_signals": len(signals),
        "mutations_run": list(ALL_ANTIGRAVITY_MUTATIONS.keys()),
        "signals": signals,
    }

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2, default=str)

    return output_path


# ── CLI Entry Point ──────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("ANTIGRAVITY MUTATIONS — Audit-Informed Edge Exploiters")
    print("=" * 60)
    print()

    signals = run_all_mutations()

    print()
    print(f"Total signals: {len(signals)}")
    if signals:
        path = save_picks(signals)
        print(f"Saved to: {path}")
        print()
        print("Top signals:")
        for i, sig in enumerate(sorted(signals, key=lambda x: x["confidence"], reverse=True)[:10], 1):
            print(f"  {i}. {sig['symbol']} {sig['signal_type']} @ {sig['entry_price']} "
                  f"conf={sig['confidence']:.2f} RR={sig['risk_reward']:.1f} "
                  f"({sig['strategy']})")
    else:
        print("No signals generated this run (normal — strategies are selective)")
