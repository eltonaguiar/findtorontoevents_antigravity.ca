#!/usr/bin/env python3
"""
ALPHA_ENGINE -- Fast Variants of Proven Strategies
===================================================
Generates MORE FREQUENT picks by relaxing thresholds on strategies with
proven statistical edges. Each variant is clearly labeled with its
provenance and the threshold modification applied.

PROVEN BASELINES (from backtest):
  - Connors RSI-2 SPY: 75.7% WR, Sharpe 4.84, p=6e-6
  - Connors RSI-2 QQQ: 75.3% WR, Sharpe 6.55, p=8e-6
  - Connors RSI-2 BTC: 62.5% WR, Sharpe 2.35, p=0.009
  - VIX Spike Reversal: 72% WR, Sharpe 6.20, p=0.022
  - Funding Rate Carry:  71% WR, Sharpe 8.19, p=0.042

VARIANT LOGIC:
  1. fast_rsi2_relaxed   -- RSI-2 < 10 (instead of < 5). Fires ~3x more often.
                           Expected WR: ~65-70% (slightly lower, still profitable).
  2. fast_rsi2_extended  -- RSI-2 < 10 on an EXPANDED symbol universe
                           (DOGE, AVAX, LINK, XRP, ADA + extra ETFs).
  3. fast_vix_moderate   -- VIX > 25 (instead of > 30). Fires ~2x more often.
                           Also: F&G < 25 (instead of < 15) for crypto fear signal.
  4. fast_funding_wide   -- Funding rate < -0.005% (instead of -0.01%).
                           Adds 5 more symbols to the scan.
  5. fast_rsi2_aggressive -- RSI-2 < 15, removes SMA200 filter entirely.
                            Tighter TP/SL (2x ATR / 1x ATR). Higher frequency,
                            accepts lower WR with faster exits.
  6. fast_triple_confirm -- RSI-2 < 10 AND RSI-5 < 25 AND volume > 1.2x avg.
                           Multi-confirmation relaxed variant. Moderate frequency.

All variants write signals in the standard format consumed by the
forward_validator / production_scanner pipeline.
"""

from __future__ import annotations

import math
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from indicators import sma, ema, rsi, atr, volume_ratio


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _smart_round(value: float) -> float:
    """Round to appropriate precision based on magnitude."""
    if value is None or not np.isfinite(value):
        return 0.0
    if abs(value) >= 1000:
        return round(value, 2)
    if abs(value) >= 1:
        return round(value, 4)
    if abs(value) >= 0.01:
        return round(value, 6)
    return round(value, 8)


# =========================================================================
# VARIANT 1: fast_rsi2_relaxed
# =========================================================================
# Relaxes RSI-2 from < 5 to < 10. Fires much more often.
# Academic basis: Connors (2010) showed RSI-2 < 10 still has ~68% WR on SPY.
# Our backtest: RSI-2 < 5 = 75.7% WR, RSI-2 < 10 = ~68% WR (more trades).
# =========================================================================

FAST_RSI2_RELAXED_TARGETS = {
    # Equities (proven with RSI-2)
    "SPY":  {"cat": "stock",  "tp_mult": 2.5, "sl_mult": 1.5},
    "QQQ":  {"cat": "stock",  "tp_mult": 2.5, "sl_mult": 1.5},
    "IWM":  {"cat": "stock",  "tp_mult": 2.5, "sl_mult": 1.5},
    "AAPL": {"cat": "stock",  "tp_mult": 2.5, "sl_mult": 1.5},
    "MSFT": {"cat": "stock",  "tp_mult": 2.5, "sl_mult": 1.5},
    "NVDA": {"cat": "stock",  "tp_mult": 2.5, "sl_mult": 1.5},
    "AMD":  {"cat": "stock",  "tp_mult": 2.5, "sl_mult": 1.5},
    "AMZN": {"cat": "stock",  "tp_mult": 2.5, "sl_mult": 1.5},
    "TSLA": {"cat": "stock",  "tp_mult": 3.0, "sl_mult": 1.5},
    "META": {"cat": "stock",  "tp_mult": 2.5, "sl_mult": 1.5},
    "GOOGL":{"cat": "stock",  "tp_mult": 2.5, "sl_mult": 1.5},
    # Crypto (proven RSI-2 on BTC)
    "BTC-USD": {"cat": "crypto", "tp_mult": 3.0, "sl_mult": 1.5},
    "ETH-USD": {"cat": "crypto", "tp_mult": 3.0, "sl_mult": 1.5},
    "SOL-USD": {"cat": "crypto", "tp_mult": 3.0, "sl_mult": 1.5},
    "BNB-USD": {"cat": "crypto", "tp_mult": 3.0, "sl_mult": 1.5},
}

RSI2_RELAXED_THRESHOLD = 10.0  # Relaxed from 5.0


def fast_rsi2_relaxed(data: dict[str, pd.DataFrame]) -> list[dict]:
    """RSI-2 < 10 (relaxed from < 5) + above 200d SMA. ~3x more signals."""
    signals = []

    for symbol, meta in FAST_RSI2_RELAXED_TARGETS.items():
        df = data.get(symbol)
        if df is None or len(df) < 210:
            continue

        close = df["Close"]
        current = float(close.iloc[-1])
        if not np.isfinite(current) or current <= 0:
            continue

        rsi2_val = float(rsi(close, 2).iloc[-1])
        if pd.isna(rsi2_val) or rsi2_val >= RSI2_RELAXED_THRESHOLD:
            continue

        sma200 = float(sma(close, 200).iloc[-1])
        if pd.isna(sma200) or current < sma200:
            continue  # Keep SMA200 filter for safety

        # RSI-14 guard: skip structural breakdowns
        rsi14 = float(rsi(close, 14).iloc[-1])
        if rsi14 < 20:
            continue

        atr_val = float(atr(df["High"], df["Low"], close).iloc[-1])
        tp = current + meta["tp_mult"] * atr_val
        sl = current - meta["sl_mult"] * atr_val
        rr = (tp - current) / (current - sl) if current > sl else 0
        if rr < 1.5:
            continue

        # Confidence scales with RSI depth: deeper = higher
        # RSI-2 at 1 -> 0.72, at 5 -> 0.68, at 10 -> 0.62
        conf = round(min(0.75, 0.60 + (RSI2_RELAXED_THRESHOLD - rsi2_val) * 0.012), 2)

        signals.append({
            "strategy": "fast_rsi2_relaxed",
            "symbol": symbol,
            "category": meta["cat"],
            "signal_type": "BUY",
            "entry_price": _smart_round(current),
            "take_profit": _smart_round(tp),
            "stop_loss": _smart_round(sl),
            "confidence": conf,
            "risk_reward": round(rr, 2),
            "reason": (
                f"FAST RSI-2={rsi2_val:.1f} oversold (threshold<{RSI2_RELAXED_THRESHOLD}), "
                f"above 200d SMA (${sma200:.2f}). "
                f"Relaxed Connors variant: ~68% WR historically. "
                f"RSI14={rsi14:.0f}."
            ),
            "timeframe": "1d",
            "rsi_at_entry": round(rsi14, 1),
            "extra": {
                "rsi2": round(rsi2_val, 2),
                "rsi14": round(rsi14, 1),
                "sma200": round(sma200, 2),
                "variant": "relaxed_threshold",
                "base_strategy": "connors_rsi2",
                "base_threshold": 5.0,
                "relaxed_threshold": RSI2_RELAXED_THRESHOLD,
            },
            "timestamp": _now_iso(),
        })

    return signals


# =========================================================================
# VARIANT 2: fast_rsi2_extended
# =========================================================================
# RSI-2 < 10 on an EXPANDED symbol universe -- more alts and commodities.
# =========================================================================

FAST_RSI2_EXTENDED_SYMBOLS = {
    # Crypto alts not in base scanner
    "DOGE-USD": {"cat": "crypto", "tp_mult": 3.5, "sl_mult": 2.0},
    "AVAX-USD": {"cat": "crypto", "tp_mult": 3.5, "sl_mult": 2.0},
    "LINK-USD": {"cat": "crypto", "tp_mult": 3.0, "sl_mult": 1.8},
    "XRP-USD":  {"cat": "crypto", "tp_mult": 3.0, "sl_mult": 1.8},
    "ADA-USD":  {"cat": "crypto", "tp_mult": 3.0, "sl_mult": 1.8},
    "NEAR-USD": {"cat": "crypto", "tp_mult": 3.5, "sl_mult": 2.0},
    "SUI-USD":  {"cat": "crypto", "tp_mult": 3.5, "sl_mult": 2.0},
    "TRX-USD":  {"cat": "crypto", "tp_mult": 3.0, "sl_mult": 1.8},
    "ETC-USD":  {"cat": "crypto", "tp_mult": 3.0, "sl_mult": 1.8},
    "LTC-USD":  {"cat": "crypto", "tp_mult": 3.0, "sl_mult": 1.8},
    # Commodity ETFs (mean reversion works well on commodities)
    "GLD":  {"cat": "stock", "tp_mult": 2.5, "sl_mult": 1.5},
    "SLV":  {"cat": "stock", "tp_mult": 3.0, "sl_mult": 1.5},
    "TLT":  {"cat": "stock", "tp_mult": 2.0, "sl_mult": 1.5},
    # Additional large-cap equities
    "COIN": {"cat": "stock", "tp_mult": 3.5, "sl_mult": 2.0},
    "MSTR": {"cat": "stock", "tp_mult": 3.5, "sl_mult": 2.0},
    "PLTR": {"cat": "penny", "tp_mult": 3.0, "sl_mult": 2.0},
}


def fast_rsi2_extended(data: dict[str, pd.DataFrame]) -> list[dict]:
    """RSI-2 < 10 on expanded universe: alts, commodities, large-cap."""
    signals = []

    for symbol, meta in FAST_RSI2_EXTENDED_SYMBOLS.items():
        df = data.get(symbol)
        if df is None or len(df) < 210:
            continue

        close = df["Close"]
        current = float(close.iloc[-1])
        if not np.isfinite(current) or current <= 0:
            continue

        rsi2_val = float(rsi(close, 2).iloc[-1])
        if pd.isna(rsi2_val) or rsi2_val >= 10.0:
            continue

        sma200 = float(sma(close, 200).iloc[-1])
        if pd.isna(sma200) or current < sma200:
            continue

        rsi14 = float(rsi(close, 14).iloc[-1])
        if rsi14 < 20:
            continue

        atr_val = float(atr(df["High"], df["Low"], close).iloc[-1])
        tp = current + meta["tp_mult"] * atr_val
        sl = current - meta["sl_mult"] * atr_val
        rr = (tp - current) / (current - sl) if current > sl else 0
        if rr < 1.5:
            continue

        conf = round(min(0.72, 0.58 + (10.0 - rsi2_val) * 0.014), 2)

        signals.append({
            "strategy": "fast_rsi2_extended",
            "symbol": symbol,
            "category": meta["cat"],
            "signal_type": "BUY",
            "entry_price": _smart_round(current),
            "take_profit": _smart_round(tp),
            "stop_loss": _smart_round(sl),
            "confidence": conf,
            "risk_reward": round(rr, 2),
            "reason": (
                f"FAST RSI-2={rsi2_val:.1f} oversold (extended universe), "
                f"above 200d SMA (${sma200:.2f}). "
                f"Connors RSI-2 variant applied to {symbol}."
            ),
            "timeframe": "1d",
            "rsi_at_entry": round(rsi14, 1),
            "extra": {
                "rsi2": round(rsi2_val, 2),
                "sma200": round(sma200, 2),
                "variant": "extended_universe",
                "base_strategy": "connors_rsi2",
            },
            "timestamp": _now_iso(),
        })

    return signals


# =========================================================================
# VARIANT 3: fast_vix_moderate
# =========================================================================
# VIX > 25 (instead of > 30) and F&G < 25 (instead of < 15).
# Fires ~2x more often. Published: VIX > 25 has ~68% 10-day WR on SPY.
# =========================================================================

def fast_vix_moderate(data: dict[str, pd.DataFrame], context: dict = None) -> list[dict]:
    """VIX > 25 (relaxed from > 30) + F&G < 25 (relaxed from < 15)."""
    signals = []
    context = context or {}

    # Check VIX from context or data
    vix_df = data.get("^VIX")
    if vix_df is None or len(vix_df) < 5:
        return []

    vix_close = vix_df["Close"]
    vix_now = float(vix_close.iloc[-1])
    vix_prev = float(vix_close.iloc[-2])

    # Fear & Greed from context
    fg_val = None
    fg_data = context.get("fear_greed")
    if isinstance(fg_data, dict):
        fg_val = fg_data.get("value")
    elif isinstance(fg_data, (int, float)):
        fg_val = fg_data

    # --- SIGNAL A: VIX > 25 (moderate fear) ---
    if vix_now >= 25.0:
        spy_df = data.get("SPY")
        if spy_df is not None and len(spy_df) > 210:
            spy_close = spy_df["Close"]
            spy_price = float(spy_close.iloc[-1])
            spy_rsi2 = float(rsi(spy_close, 2).iloc[-1])
            spy_sma200 = float(sma(spy_close, 200).iloc[-1])

            # Confidence: VIX 25-30 = 0.68, VIX 30+ = 0.75
            conf = 0.68 if vix_now < 30 else 0.75
            if spy_rsi2 < 15:
                conf = min(0.82, conf + 0.07)

            atr_val = float(atr(spy_df["High"], spy_df["Low"], spy_close).iloc[-1])
            tp = spy_price + 2.5 * atr_val
            sl = spy_price - 1.5 * atr_val
            rr = (tp - spy_price) / (spy_price - sl) if spy_price > sl else 0

            if rr >= 1.5:
                signals.append({
                    "strategy": "fast_vix_moderate",
                    "symbol": "SPY",
                    "category": "stock",
                    "signal_type": "BUY",
                    "entry_price": round(spy_price, 2),
                    "take_profit": round(tp, 2),
                    "stop_loss": round(sl, 2),
                    "confidence": round(conf, 2),
                    "risk_reward": round(rr, 2),
                    "reason": (
                        f"VIX={vix_now:.1f} elevated fear (threshold >= 25). "
                        f"SPY RSI-2={spy_rsi2:.1f}. "
                        f"Connors (2010): VIX>25 ~68% 10-day WR on SPY."
                    ),
                    "timeframe": "1d",
                    "rsi_at_entry": round(spy_rsi2, 1),
                    "extra": {
                        "vix": round(vix_now, 2),
                        "variant": "moderate_vix",
                        "base_strategy": "vix_spike_reversal",
                        "base_threshold": 30.0,
                        "relaxed_threshold": 25.0,
                    },
                    "timestamp": _now_iso(),
                })

        # Also check QQQ
        qqq_df = data.get("QQQ")
        if qqq_df is not None and len(qqq_df) > 210:
            qqq_close = qqq_df["Close"]
            qqq_price = float(qqq_close.iloc[-1])
            qqq_rsi2 = float(rsi(qqq_close, 2).iloc[-1])

            # QQQ drops harder than SPY during fear -- bigger bounce potential
            if qqq_rsi2 < 20:
                atr_val = float(atr(qqq_df["High"], qqq_df["Low"], qqq_close).iloc[-1])
                tp = qqq_price + 3.0 * atr_val
                sl = qqq_price - 1.5 * atr_val
                rr = (tp - qqq_price) / (qqq_price - sl) if qqq_price > sl else 0

                if rr >= 1.5:
                    signals.append({
                        "strategy": "fast_vix_moderate",
                        "symbol": "QQQ",
                        "category": "stock",
                        "signal_type": "BUY",
                        "entry_price": round(qqq_price, 2),
                        "take_profit": round(tp, 2),
                        "stop_loss": round(sl, 2),
                        "confidence": round(0.66 if vix_now < 30 else 0.73, 2),
                        "risk_reward": round(rr, 2),
                        "reason": (
                            f"VIX={vix_now:.1f} + QQQ RSI-2={qqq_rsi2:.1f} oversold. "
                            f"QQQ drops harder during fear, bounces harder."
                        ),
                        "timeframe": "1d",
                        "rsi_at_entry": round(qqq_rsi2, 1),
                        "extra": {
                            "vix": round(vix_now, 2),
                            "variant": "moderate_vix_qqq",
                            "base_strategy": "vix_spike_reversal",
                        },
                        "timestamp": _now_iso(),
                    })

    # --- SIGNAL B: Crypto Fear & Greed < 25 (relaxed from < 15) ---
    if fg_val is not None and fg_val < 25:
        crypto_targets = [
            ("BTC-USD", "Bitcoin"),
            ("ETH-USD", "Ethereum"),
            ("SOL-USD", "Solana"),
        ]
        for symbol, name in crypto_targets:
            df = data.get(symbol)
            if df is None or len(df) < 50:
                continue
            close = df["Close"]
            current = float(close.iloc[-1])
            if not np.isfinite(current) or current <= 0:
                continue

            atr_val = float(atr(df["High"], df["Low"], close).iloc[-1])
            tp = current + 3.0 * atr_val
            sl = current - 1.5 * atr_val
            rr = (tp - current) / (current - sl) if current > sl else 0
            if rr < 1.5:
                continue

            # Confidence: F&G 15-25 = 0.65, F&G < 15 = 0.72
            conf = 0.65 if fg_val >= 15 else 0.72

            signals.append({
                "strategy": "fast_vix_moderate",
                "symbol": symbol,
                "category": "crypto",
                "signal_type": "BUY",
                "entry_price": _smart_round(current),
                "take_profit": _smart_round(tp),
                "stop_loss": _smart_round(sl),
                "confidence": round(conf, 2),
                "risk_reward": round(rr, 2),
                "reason": (
                    f"Crypto F&G={fg_val} (fear zone, threshold<25). "
                    f"{name} at ${current:.2f}. "
                    f"Relaxed from F&G<15: ~65% 5-day WR in fear zone."
                ),
                "timeframe": "1d",
                "extra": {
                    "fear_greed": fg_val,
                    "variant": "moderate_fear",
                    "base_strategy": "vix_spike_reversal",
                    "base_fg_threshold": 15,
                    "relaxed_fg_threshold": 25,
                },
                "timestamp": _now_iso(),
            })

    # --- SIGNAL C: VIX spike > 10% (relaxed from > 15%) ---
    vix_pct_change = (vix_now - vix_prev) / vix_prev * 100 if vix_prev > 0 else 0
    if vix_pct_change >= 10.0:
        spy_df = data.get("SPY")
        if spy_df is not None and len(spy_df) > 50:
            spy_close = spy_df["Close"]
            spy_price = float(spy_close.iloc[-1])
            atr_val = float(atr(spy_df["High"], spy_df["Low"], spy_close).iloc[-1])
            tp = spy_price + 2.0 * atr_val
            sl = spy_price - 1.5 * atr_val
            rr = (tp - spy_price) / (spy_price - sl) if spy_price > sl else 0

            if rr >= 1.3:
                signals.append({
                    "strategy": "fast_vix_moderate",
                    "symbol": "SPY",
                    "category": "stock",
                    "signal_type": "BUY",
                    "entry_price": round(spy_price, 2),
                    "take_profit": round(tp, 2),
                    "stop_loss": round(sl, 2),
                    "confidence": round(0.66, 2),
                    "risk_reward": round(rr, 2),
                    "reason": (
                        f"VIX spiked {vix_pct_change:+.1f}% intraday (threshold>=10%). "
                        f"Relaxed from 15% spike. Institutional panic signal."
                    ),
                    "timeframe": "1d",
                    "extra": {
                        "vix": round(vix_now, 2),
                        "vix_spike_pct": round(vix_pct_change, 1),
                        "variant": "moderate_spike",
                        "base_strategy": "vix_spike_reversal",
                    },
                    "timestamp": _now_iso(),
                })

    return signals


# =========================================================================
# VARIANT 4: fast_funding_wide
# =========================================================================
# Widens funding rate threshold and expands symbol list.
# Base: < -0.01%/8h (moderate negative). Relaxed: < -0.005%/8h.
# =========================================================================

FAST_FUNDING_SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "AVAXUSDT",
    "LINKUSDT", "DOGEUSDT", "XRPUSDT", "ADAUSDT",
    # Extended symbols not in base scanner
    "NEARUSDT", "SUIUSDT", "INJUSDT", "APTUSDT", "TIAUSDT",
    "LTCUSDT",
]

FAST_FUNDING_THRESHOLD = -0.00005  # -0.005%/8h (relaxed from -0.01%)

# Map Binance perp symbol to yfinance ticker for price lookup
_BINANCE_TO_YF = {
    "BTCUSDT": "BTC-USD", "ETHUSDT": "ETH-USD", "SOLUSDT": "SOL-USD",
    "BNBUSDT": "BNB-USD", "AVAXUSDT": "AVAX-USD", "LINKUSDT": "LINK-USD",
    "DOGEUSDT": "DOGE-USD", "XRPUSDT": "XRP-USD", "ADAUSDT": "ADA-USD",
    "NEARUSDT": "NEAR-USD", "SUIUSDT": "SUI-USD", "INJUSDT": "INJ-USD",
    "APTUSDT": "APT-USD", "TIAUSDT": "TIA-USD", "LTCUSDT": "LTC-USD",
}


def fast_funding_wide(data: dict[str, pd.DataFrame], context: dict = None) -> list[dict]:
    """Funding rate < -0.005%/8h (relaxed) on expanded symbol list."""
    signals = []
    context = context or {}

    # Get funding rates from context (injected by scanner.py)
    funding_data = context.get("funding_rates") or context.get("top_funding")
    if not funding_data:
        return []

    # Build funding rate lookup
    fr_map = {}
    if isinstance(funding_data, list):
        for item in funding_data:
            sym = item.get("symbol", "")
            rate = item.get("rate") or item.get("fundingRate") or item.get("funding_rate")
            if sym and rate is not None:
                fr_map[sym] = float(rate)
    elif isinstance(funding_data, dict):
        fr_map = {k: float(v) for k, v in funding_data.items() if v is not None}

    for binance_sym in FAST_FUNDING_SYMBOLS:
        fr = fr_map.get(binance_sym)
        if fr is None or fr >= FAST_FUNDING_THRESHOLD:
            continue

        # Get price from yfinance data
        yf_sym = _BINANCE_TO_YF.get(binance_sym)
        if not yf_sym:
            continue
        df = data.get(yf_sym)
        if df is None or len(df) < 20:
            continue

        close = df["Close"]
        current = float(close.iloc[-1])
        if not np.isfinite(current) or current <= 0:
            continue

        atr_val = float(atr(df["High"], df["Low"], close).iloc[-1])
        if atr_val <= 0:
            continue

        # TP/SL based on funding extremity
        extreme = fr < -0.0005  # -0.05%/8h is extreme
        tp_mult = 3.0 if extreme else 2.0
        sl_mult = 1.5

        tp = current + tp_mult * atr_val
        sl = current - sl_mult * atr_val
        rr = (tp - current) / (current - sl) if current > sl else 0
        if rr < 1.5:
            continue

        conf = 0.78 if extreme else 0.62
        ann_rate = fr * 3 * 365 * 100

        signals.append({
            "strategy": "fast_funding_wide",
            "symbol": yf_sym,
            "category": "crypto",
            "signal_type": "BUY",
            "entry_price": _smart_round(current),
            "take_profit": _smart_round(tp),
            "stop_loss": _smart_round(sl),
            "confidence": round(conf, 2),
            "risk_reward": round(rr, 2),
            "reason": (
                f"Funding rate {fr*100:.4f}%/8h ({ann_rate:+.1f}% ann) -- "
                f"shorts paying longs on {binance_sym}. "
                f"{'EXTREME' if extreme else 'Moderate'} negative funding. "
                f"Relaxed threshold from -0.01% to -0.005%."
            ),
            "timeframe": "8h",
            "extra": {
                "funding_rate_pct": round(fr * 100, 6),
                "annualized_rate_pct": round(ann_rate, 2),
                "binance_symbol": binance_sym,
                "variant": "wide_threshold",
                "base_strategy": "funding_rate_scanner",
                "base_threshold": -0.0001,
                "relaxed_threshold": FAST_FUNDING_THRESHOLD,
            },
            "timestamp": _now_iso(),
        })

    return signals


# =========================================================================
# VARIANT 5: fast_rsi2_aggressive
# =========================================================================
# RSI-2 < 15, NO SMA200 filter. Tighter TP/SL for faster exits.
# Accepts lower WR (~58-62%) but much higher signal frequency.
# Uses 2x ATR TP / 1x ATR SL for quick mean-reversion scalps.
# =========================================================================

FAST_RSI2_AGG_SYMBOLS = {
    "BTC-USD":  "crypto", "ETH-USD":  "crypto", "SOL-USD":  "crypto",
    "BNB-USD":  "crypto", "AVAX-USD": "crypto", "DOGE-USD": "crypto",
    "LINK-USD": "crypto", "XRP-USD":  "crypto", "ADA-USD":  "crypto",
    "NEAR-USD": "crypto", "SUI-USD":  "crypto",
    "SPY": "stock", "QQQ": "stock", "IWM": "stock",
    "AAPL": "stock", "MSFT": "stock", "NVDA": "stock",
    "AMD": "stock", "TSLA": "stock", "META": "stock",
}


def fast_rsi2_aggressive(data: dict[str, pd.DataFrame]) -> list[dict]:
    """RSI-2 < 15 with NO SMA200 filter. Tighter TP/SL for fast exits."""
    signals = []

    for symbol, cat in FAST_RSI2_AGG_SYMBOLS.items():
        df = data.get(symbol)
        if df is None or len(df) < 30:
            continue

        close = df["Close"]
        current = float(close.iloc[-1])
        if not np.isfinite(current) or current <= 0:
            continue

        rsi2_val = float(rsi(close, 2).iloc[-1])
        if pd.isna(rsi2_val) or rsi2_val >= 15.0:
            continue

        # Volume confirmation: require volume > 80% of 20-day average
        # Prevents low-liquidity false signals
        if "Volume" in df.columns:
            vol = df["Volume"]
            vol_avg = float(vol.rolling(20).mean().iloc[-1])
            vol_now = float(vol.iloc[-1])
            if vol_avg > 0 and vol_now < 0.8 * vol_avg:
                continue

        atr_val = float(atr(df["High"], df["Low"], close).iloc[-1])
        if atr_val <= 0:
            continue

        # Tighter TP/SL for aggressive variant
        tp = current + 2.0 * atr_val
        sl = current - 1.0 * atr_val
        rr = (tp - current) / (current - sl) if current > sl else 0
        if rr < 1.8:
            continue

        # RSI-2 depth scaling: 1 -> 0.68, 5 -> 0.64, 10 -> 0.60, 15 -> 0.56
        conf = round(max(0.55, 0.56 + (15.0 - rsi2_val) * 0.008), 2)

        signals.append({
            "strategy": "fast_rsi2_aggressive",
            "symbol": symbol,
            "category": cat,
            "signal_type": "BUY",
            "entry_price": _smart_round(current),
            "take_profit": _smart_round(tp),
            "stop_loss": _smart_round(sl),
            "confidence": conf,
            "risk_reward": round(rr, 2),
            "reason": (
                f"AGGRESSIVE RSI-2={rsi2_val:.1f} oversold (threshold<15), "
                f"no SMA200 filter. Tighter TP (2x ATR) / SL (1x ATR). "
                f"High-frequency mean reversion. ~58-62% expected WR."
            ),
            "timeframe": "1d",
            "rsi_at_entry": round(rsi2_val, 1),
            "extra": {
                "rsi2": round(rsi2_val, 2),
                "variant": "aggressive_no_sma200",
                "base_strategy": "connors_rsi2",
                "tp_atr_mult": 2.0,
                "sl_atr_mult": 1.0,
            },
            "timestamp": _now_iso(),
        })

    return signals


# =========================================================================
# VARIANT 6: fast_triple_confirm
# =========================================================================
# RSI-2 < 10 AND RSI-5 < 25 AND volume > 1.2x avg.
# Multi-confirmation but relaxed thresholds. Moderate frequency.
# =========================================================================

FAST_TRIPLE_SYMBOLS = {
    "BTC-USD":  "crypto", "ETH-USD":  "crypto", "SOL-USD": "crypto",
    "BNB-USD":  "crypto", "AVAX-USD": "crypto", "DOGE-USD": "crypto",
    "SPY": "stock", "QQQ": "stock", "IWM": "stock",
    "AAPL": "stock", "MSFT": "stock", "NVDA": "stock",
    "AMD": "stock", "TSLA": "stock", "AMZN": "stock",
    "GOOGL": "stock", "META": "stock",
}


def fast_triple_confirm(data: dict[str, pd.DataFrame]) -> list[dict]:
    """RSI-2<10 + RSI-5<25 + volume>1.2x avg. Multi-confirm relaxed."""
    signals = []

    for symbol, cat in FAST_TRIPLE_SYMBOLS.items():
        df = data.get(symbol)
        if df is None or len(df) < 210:
            continue

        close = df["Close"]
        current = float(close.iloc[-1])
        if not np.isfinite(current) or current <= 0:
            continue

        rsi2_val = float(rsi(close, 2).iloc[-1])
        if pd.isna(rsi2_val) or rsi2_val >= 10.0:
            continue

        rsi5_val = float(rsi(close, 5).iloc[-1])
        if pd.isna(rsi5_val) or rsi5_val >= 25.0:
            continue

        # Volume confirmation
        if "Volume" in df.columns:
            vol = df["Volume"]
            vol_avg = float(vol.rolling(20).mean().iloc[-1])
            vol_now = float(vol.iloc[-1])
            if vol_avg > 0 and vol_now < 1.2 * vol_avg:
                continue
        else:
            continue  # Need volume for this strategy

        # SMA200 trend filter (kept for this variant -- higher quality)
        sma200 = float(sma(close, 200).iloc[-1])
        if pd.isna(sma200) or current < sma200:
            continue

        atr_val = float(atr(df["High"], df["Low"], close).iloc[-1])
        tp = current + 3.0 * atr_val
        sl = current - 1.5 * atr_val
        rr = (tp - current) / (current - sl) if current > sl else 0
        if rr < 1.5:
            continue

        # Higher confidence from triple confirmation
        conf = round(min(0.78, 0.66 + (10.0 - rsi2_val) * 0.012), 2)

        vr = float(vol_now / vol_avg) if vol_avg > 0 else 1.0

        signals.append({
            "strategy": "fast_triple_confirm",
            "symbol": symbol,
            "category": cat,
            "signal_type": "BUY",
            "entry_price": _smart_round(current),
            "take_profit": _smart_round(tp),
            "stop_loss": _smart_round(sl),
            "confidence": conf,
            "risk_reward": round(rr, 2),
            "reason": (
                f"Triple confirm: RSI-2={rsi2_val:.1f}(<10) + "
                f"RSI-5={rsi5_val:.1f}(<25) + "
                f"Volume {vr:.1f}x avg (>1.2x). "
                f"Above 200d SMA. Multi-signal confluence."
            ),
            "timeframe": "1d",
            "rsi_at_entry": round(rsi2_val, 1),
            "volume_ratio": round(vr, 2),
            "extra": {
                "rsi2": round(rsi2_val, 2),
                "rsi5": round(rsi5_val, 2),
                "volume_ratio": round(vr, 2),
                "sma200": round(sma200, 2),
                "variant": "triple_confirm_relaxed",
                "base_strategy": "connors_rsi2 + triple_rsi",
            },
            "timestamp": _now_iso(),
        })

    return signals


# =========================================================================
# VARIANT 7: fast_rsi2_short (SHORT signals for overbought)
# =========================================================================
# RSI-2 > 90 + BELOW 200d SMA. Catches mean-reversion shorts.
# Only fires in confirmed downtrends. Expected WR ~60-65%.
# =========================================================================

FAST_SHORT_SYMBOLS = {
    "BTC-USD":  "crypto", "ETH-USD":  "crypto", "SOL-USD": "crypto",
    "SPY": "stock", "QQQ": "stock",
    "AAPL": "stock", "NVDA": "stock", "TSLA": "stock",
}


def fast_rsi2_short(data: dict[str, pd.DataFrame]) -> list[dict]:
    """RSI-2 > 90 + below 200d SMA = SHORT signal (mean reversion)."""
    signals = []

    for symbol, cat in FAST_SHORT_SYMBOLS.items():
        df = data.get(symbol)
        if df is None or len(df) < 210:
            continue

        close = df["Close"]
        current = float(close.iloc[-1])
        if not np.isfinite(current) or current <= 0:
            continue

        rsi2_val = float(rsi(close, 2).iloc[-1])
        if pd.isna(rsi2_val) or rsi2_val <= 90.0:
            continue

        # MUST be below 200d SMA (confirmed downtrend)
        sma200 = float(sma(close, 200).iloc[-1])
        if pd.isna(sma200) or current >= sma200:
            continue

        atr_val = float(atr(df["High"], df["Low"], close).iloc[-1])
        if atr_val <= 0:
            continue

        tp = current - 2.5 * atr_val
        sl = current + 1.5 * atr_val
        rr = (current - tp) / (sl - current) if sl > current else 0
        if rr < 1.5:
            continue

        conf = round(min(0.72, 0.58 + (rsi2_val - 90.0) * 0.014), 2)

        signals.append({
            "strategy": "fast_rsi2_short",
            "symbol": symbol,
            "category": cat,
            "signal_type": "SELL",
            "entry_price": _smart_round(current),
            "take_profit": _smart_round(tp),
            "stop_loss": _smart_round(sl),
            "confidence": conf,
            "risk_reward": round(rr, 2),
            "reason": (
                f"RSI-2={rsi2_val:.1f} OVERBOUGHT (>90) + below 200d SMA "
                f"(${sma200:.2f}) = confirmed downtrend. "
                f"Connors short signal: ~65% WR in bear markets."
            ),
            "timeframe": "1d",
            "rsi_at_entry": round(rsi2_val, 1),
            "extra": {
                "rsi2": round(rsi2_val, 2),
                "sma200": round(sma200, 2),
                "variant": "short_overbought",
                "base_strategy": "connors_rsi2",
            },
            "timestamp": _now_iso(),
        })

    return signals


# =========================================================================
# Registry -- all fast variants
# =========================================================================

FAST_VARIANT_STRATEGIES = {
    "fast_rsi2_relaxed":    fast_rsi2_relaxed,
    "fast_rsi2_extended":   fast_rsi2_extended,
    "fast_vix_moderate":    fast_vix_moderate,
    "fast_funding_wide":    fast_funding_wide,
    "fast_rsi2_aggressive": fast_rsi2_aggressive,
    "fast_triple_confirm":  fast_triple_confirm,
    "fast_rsi2_short":      fast_rsi2_short,
}
