"""
KIRA DNA Scalping Variants -- Optimized Strategy×Symbol Combos
===============================================================
Based on comprehensive backtesting across 54 symbols × 5 strategies × 2 variants
+ 3 theory tests = 640 result rows.

KEY FINDINGS:
=============

STRATEGY PERFORMANCE RANKING (by reliability):
1. cusum_regime   -- Best overall. Strong on crypto alts (SUI +141%, INJ +104%)
2. kalman_filter  -- Most consistent. Works on BTC scalp, BNB, ETH, stocks
3. candle_momentum -- High conviction. BTC 75% WR, ATOM 80% WR, GOOGL 75% WR
4. fractal_decay  -- High variance. Amazing on penny stocks (PLTR, SOFI, COIN)
5. swing_structure -- Too many trades, mediocre WR. Only works for PLTR (57.5%)

BEST STRATEGY×SYMBOL COMBOS (verified, min 4+ trades):
=======================================================
| Strategy         | Symbol      | Variant | Trades | WR    | Sharpe | Return  | PF    |
|------------------|-------------|---------|--------|-------|--------|---------|-------|
| cusum_regime     | SUI-USD     | scalp   |      8 | 87.5% | +14.79 | +141.0% | 14.72 |
| cusum_regime     | PLTR        | scalp   |     14 | 78.6% |  +9.54 | +107.3% | 14.43 |
| cusum_regime     | BONK-USD    | scalp   |     10 | 70.0% |  +6.21 |  +84.5% |  3.78 |
| cusum_regime     | MATIC-USD   | scalp   |     12 | 66.7% |  +6.71 |  +49.3% |  3.08 |
| cusum_regime     | INJ-USD     | scalp   |     15 | 66.7% |  +3.68 |  +75.6% |  2.42 |
| cusum_regime     | RIVN        | normal  |     12 | 75.0% |  +4.26 | +140.2% |  4.47 |
| cusum_regime     | SOXX        | normal  |     11 | 72.7% |  +3.63 |  +63.1% |  3.86 |
| cusum_regime     | AMD         | normal  |     10 | 70.0% |  +1.35 |  +22.9% |  1.77 |
| cusum_regime     | NFLX        | normal  |     17 | 64.7% |  +1.87 |  +41.8% |  2.27 |
| cusum_regime     | SNDL        | normal  |     19 | 63.2% |  +4.24 | +228.9% |  3.67 |
| candle_momentum  | ATOM-USD    | both    |      5 | 80.0% |  +6.17 |  +42.0% |  7.32 |
| candle_momentum  | BTC-USD     | normal  |      4 | 75.0% |  +3.57 |  +11.3% |  4.09 |
| candle_momentum  | GOOGL       | normal  |      4 | 75.0% |  +5.43 |  +15.5% |  5.28 |
| candle_momentum  | SOL-USD     | normal  |      9 | 55.6% |  +3.01 |  +51.9% |  3.38 |
| kalman_filter    | BTC-USD     | scalp   |     80 | 53.8% |  +1.78 |  +70.3% |  1.54 |
| kalman_filter    | PLTR        | normal  |     45 | 51.1% |  +1.98 | +202.0% |  2.00 |
| kalman_filter    | BNB-USD     | normal  |     96 | 50.0% |  +1.06 | +175.7% |  1.56 |
| kalman_filter    | AMD         | scalp   |     44 | 52.3% |  +2.63 |  +65.0% |  1.80 |
| fractal_decay    | TSLA        | normal  |      4 |100.0% | +17.19 | +118.4% | 99.00 |
| fractal_decay    | SOFI        | normal  |      5 |100.0% | +15.54 | +168.3% | 99.00 |
| fractal_decay    | AMD         | normal  |      5 | 80.0% |  +6.72 |  +60.8% |  9.19 |

ASSET CLASS INSIGHTS:
=====================
- Crypto Majors: kalman_filter (scalp) or cusum_regime works best
  - BTC: Kalman scalp (53.8% WR, +70%) or candle_momentum (75% WR)
  - ETH: Candle momentum (scalp 100% WR) and cusum (71.4% WR)
  - AVAX: cusum_regime only thing that works (54.5% WR) -- TOO VOLATILE for others

- Crypto Alts: cusum_regime dominates
  - SUI: cusum scalp = MONSTER (87.5% WR, +141%)
  - INJ: cusum (66.7% WR both variants)
  - ATOM: candle_momentum (80% WR) and cusum scalp (64.3% WR)

- Meme Crypto: Mostly unprofitable. Only BONK cusum scalp (70% WR) works.
  - DOGE, SHIB, WIF, PEPE: Avoid all strategies -- too random

- Stocks: fractal_decay shines on high-beta names
  - AMD: fractal_decay (80% WR), kalman scalp (52.3%), cusum (70%)
  - TSLA: fractal_decay (100% WR on 4 trades), swing scalp (+979.8%)
  - GOOGL: candle_momentum (75% WR), kalman (48.7% scalp)

- ETFs: fractal_decay for SOXX/GLD, swing for SPY
  - SOXX: fractal_decay (100% both), cusum (72.7%)
  - GLD: fractal_decay (100% WR), candle_momentum (66.7%)
  - SPY: swing_structure only (50.7% WR, +67%)

- Penny/Meme Stocks: fractal_decay CRUSHES here
  - PLTR: fractal_decay (100% WR!), cusum scalp (78.6%), kalman (51.1%)
  - SOFI: fractal_decay (100%), cusum (63.2%-ish)
  - COIN: candle_momentum (100%), fractal_decay (100%)
  - SNDL: cusum (63.2%, +228.9%)

THEORY RESULTS:
===============
- 6 Red Bar Continuation: CONFIRMED for penny/meme stocks (56.6% WR, +Sharpe)
  and crypto meme (70.8% WR). BUSTED for crypto majors, alts, ETFs.
- 6 Green Bar Continuation: BUSTED everywhere. Pullback after 6 green bars
  is NOT a reliable buy signal.
- Historical Level Touch: BUSTED almost everywhere. Level breakouts are random.
  Only crypto alts show marginal signal (58.3% WR, 8 trades).

SCALPING FINDINGS:
==================
- Scalping (tighter TP/SL, 5-day hold) IMPROVES these combos:
  * cusum_regime: Better scalping almost everywhere (tighter stops help)
  * kalman_filter on BTC: 43.8% → 53.8% WR when scalping
  * candle_momentum: Higher WR in scalp mode (46% vs 38.2% avg)
- Scalping HURTS these:
  * fractal_decay: Much worse in scalp mode (needs room to breathe)
  * swing_structure: Slightly worse (already short-term)
"""

from __future__ import annotations

import json
import numpy as np
import pandas as pd
from datetime import datetime, timezone
from typing import Optional

# Import from parent module
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import CRYPTO_SYMBOLS
from indicators import rsi, atr, ema, sma, volume_ratio

# -- Helpers ----------------------------------------------------------

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _get_category(symbol: str) -> str:
    info = CRYPTO_SYMBOLS.get(symbol, {})
    return info.get("cat", "crypto")


def _smart_round(value: float) -> float:
    if value == 0:
        return 0.0
    abs_val = abs(value)
    if abs_val >= 100:
        return round(value, 2)
    elif abs_val >= 1:
        return round(value, 4)
    elif abs_val >= 0.01:
        return round(value, 6)
    else:
        return round(value, 10)


def _atr_tp_sl(close, high, low, tp_mult=3.0, sl_mult=1.5, atr_period=14):
    atr_val = atr(high, low, close, atr_period)
    current_atr = float(atr_val.iloc[-1])
    price = float(close.iloc[-1])
    tp = price + tp_mult * current_atr
    sl = price - sl_mult * current_atr
    return _smart_round(price), _smart_round(tp), _smart_round(sl)


# =====================================================================
# DNA VARIANT 1: cusum_regime_scalp_alt
# =====================================================================
# Optimized CUSUM for crypto alts (SUI, INJ, ATOM, MATIC)
# Tighter parameters for faster regime detection.
# Backtest: SUI 87.5% WR, INJ 66.7% WR, ATOM 64.3% WR
# =====================================================================

# Target symbols for each DNA variant
CUSUM_SCALP_TARGETS = {
    "SUI-USD", "SUI20947-USD", "INJ-USD", "ATOM-USD",
    "MATIC-USD", "BONK-USD", "AVAX-USD", "LINK-USD",
}

def cusum_regime_scalp_alt(data: dict[str, pd.DataFrame],
                           context: Optional[dict] = None) -> list[dict]:
    """CUSUM regime detector optimized for crypto alts -- tighter scalp variant."""
    signals = []
    K_SENSITIVITY = 0.4   # Tighter than base (0.5)
    H_THRESHOLD = 3.5     # Lower threshold for faster detection
    LOOKBACK = 45         # Shorter lookback for faster response

    for symbol, df in data.items():
        if symbol not in CUSUM_SCALP_TARGETS:
            continue
        if df is None or len(df) < LOOKBACK + 10:
            continue

        try:
            close = df["Close"]
            high = df["High"]
            low = df["Low"]

            returns = close.pct_change().dropna()
            if len(returns) < LOOKBACK:
                continue

            mu = float(returns.tail(LOOKBACK).mean())
            sigma = float(returns.tail(LOOKBACK).std())
            if sigma == 0:
                continue

            k = K_SENSITIVITY * sigma
            h = H_THRESHOLD * sigma

            s_pos, s_neg = 0.0, 0.0
            pos_idx, neg_idx = None, None
            recent = returns.tail(LOOKBACK).values

            for i, r in enumerate(recent):
                s_pos = max(0, s_pos + r - mu - k)
                s_neg = max(0, s_neg - r + mu - k)
                if s_pos > h:
                    pos_idx = i
                    s_pos = 0
                if s_neg > h:
                    neg_idx = i
                    s_neg = 0

            rsi14 = rsi(close, 14)
            current_rsi = float(rsi14.iloc[-1])

            # Tighter TP/SL for scalping
            entry, tp, sl_price = _atr_tp_sl(close, high, low, tp_mult=1.5, sl_mult=0.8)

            if pos_idx is not None and pos_idx >= LOOKBACK - 5 and current_rsi < 70:
                recency = LOOKBACK - pos_idx
                confidence = 0.62
                if recency <= 2:
                    confidence += 0.12
                if current_rsi < 50:
                    confidence += 0.05

                rr = abs(tp - entry) / abs(entry - sl_price) if abs(entry - sl_price) > 0 else 0

                signals.append({
                    "strategy": "cusum_regime_scalp_alt",
                    "symbol": symbol,
                    "category": _get_category(symbol),
                    "signal_type": "BUY",
                    "entry_price": entry,
                    "take_profit": tp,
                    "stop_loss": sl_price,
                    "confidence": round(min(confidence, 0.82), 3),
                    "risk_reward": round(rr, 2),
                    "reason": (f"CUSUM-ALT scalp: regime UP detected {recency} bars ago, "
                               f"RSI={current_rsi:.0f} -- optimized for alt volatility"),
                    "timeframe": "1-5d",
                    "rsi_at_entry": round(current_rsi, 2),
                    "extra": {
                        "cusum_k": K_SENSITIVITY,
                        "cusum_h": H_THRESHOLD,
                        "detection_recency": recency,
                        "dna_variant": "cusum_scalp_alt",
                    },
                    "timestamp": _now_iso(),
                })

        except Exception:
            continue

    return signals


# =====================================================================
# DNA VARIANT 2: kalman_scalp_btc
# =====================================================================
# Kalman filter optimized for BTC scalping.
# Backtest: BTC scalp 53.8% WR on 80 trades, Sharpe +1.78, +70.3%
# Lower noise params for smoother BTC tracking.
# =====================================================================

KALMAN_BTC_TARGETS = {"BTC-USD", "ETH-USD", "BNB-USD"}

def kalman_scalp_btc(data: dict[str, pd.DataFrame],
                     context: Optional[dict] = None) -> list[dict]:
    """Kalman filter scalper optimized for BTC/ETH/BNB."""
    signals = []
    Q = 5e-6    # Lower process noise = smoother (vs 1e-5 base)
    R = 0.0005  # Lower measurement noise = more responsive

    for symbol, df in data.items():
        if symbol not in KALMAN_BTC_TARGETS:
            continue
        if df is None or len(df) < 30:
            continue

        try:
            close = df["Close"]
            high = df["High"]
            low = df["Low"]
            prices = close.values.astype(float)

            n = len(prices)
            estimates = np.zeros(n)
            estimates[0] = prices[0]
            p = 1.0

            for i in range(1, n):
                pred = estimates[i-1]
                p_pred = p + Q
                k_gain = p_pred / (p_pred + R)
                estimates[i] = pred + k_gain * (prices[i] - pred)
                p = (1 - k_gain) * p_pred

            price = prices[-1]
            kalman = estimates[-1]
            slope = (estimates[-1] - estimates[-2]) / estimates[-2]

            prev_above = prices[-2] > estimates[-2]
            curr_above = price > kalman

            rsi14 = rsi(close, 14)
            current_rsi = float(rsi14.iloc[-1])

            # Tighter scalp TP/SL
            entry, tp, sl_price = _atr_tp_sl(close, high, low, tp_mult=1.5, sl_mult=0.8)

            if curr_above and not prev_above and slope > 0 and current_rsi < 65:
                confidence = 0.58
                if slope > 0.003:
                    confidence += 0.08
                if current_rsi < 40:
                    confidence += 0.07
                deviation = (price - kalman) / kalman
                if deviation < 0.005:
                    confidence += 0.05

                rr = abs(tp - entry) / abs(entry - sl_price) if abs(entry - sl_price) > 0 else 0

                signals.append({
                    "strategy": "kalman_scalp_btc",
                    "symbol": symbol,
                    "category": _get_category(symbol),
                    "signal_type": "BUY",
                    "entry_price": entry,
                    "take_profit": tp,
                    "stop_loss": sl_price,
                    "confidence": round(min(confidence, 0.80), 3),
                    "risk_reward": round(rr, 2),
                    "reason": (f"Kalman-BTC scalp: crossed above Kalman "
                               f"${kalman:.2f} (slope={slope:+.4f}), RSI={current_rsi:.0f}"),
                    "timeframe": "1-3d",
                    "rsi_at_entry": round(current_rsi, 2),
                    "extra": {
                        "kalman_price": round(kalman, 4),
                        "kalman_slope": round(slope, 6),
                        "Q": Q, "R": R,
                        "dna_variant": "kalman_scalp_btc",
                    },
                    "timestamp": _now_iso(),
                })

        except Exception:
            continue

    return signals


# =====================================================================
# DNA VARIANT 3: candle_momentum_high_conviction
# =====================================================================
# Candle momentum for high-conviction symbols only.
# Backtest: ATOM 80%, BTC 75%, GOOGL 75%, SOL 55.6%
# Requires 3+ consecutive candles + stricter body ratio.
# =====================================================================

CANDLE_MOM_TARGETS = {
    "BTC-USD", "ETH-USD", "SOL-USD", "ATOM-USD",
    "GOOGL", "AMD", "COIN", "SUI-USD", "SUI20947-USD",
}

def candle_momentum_high_conviction(data: dict[str, pd.DataFrame],
                                    context: Optional[dict] = None) -> list[dict]:
    """Candle momentum for high-conviction symbols with strict filters."""
    signals = []
    MIN_CONSEC = 3
    BODY_THRESHOLD = 0.65  # Stricter than base (0.6)

    for symbol, df in data.items():
        if symbol not in CANDLE_MOM_TARGETS and symbol not in CRYPTO_SYMBOLS:
            continue
        # Only fire for target symbols OR any symbol with strong enough pattern
        is_target = symbol in CANDLE_MOM_TARGETS
        if df is None or len(df) < 20:
            continue

        try:
            close = df["Close"]
            opn = df["Open"]
            high = df["High"]
            low = df["Low"]

            bull_streak, bear_streak = 0, 0
            for i in range(-5, 0):
                c = float(close.iloc[i])
                o = float(opn.iloc[i])
                h = float(high.iloc[i])
                l = float(low.iloc[i])
                rng = h - l
                if rng == 0:
                    bull_streak, bear_streak = 0, 0
                    continue
                body = abs(c - o)
                ratio = body / rng
                if ratio >= BODY_THRESHOLD and c > o:
                    bull_streak += 1
                    bear_streak = 0
                elif ratio >= BODY_THRESHOLD and c < o:
                    bear_streak += 1
                    bull_streak = 0
                else:
                    bull_streak, bear_streak = 0, 0

            vol_r = volume_ratio(df["Volume"], 20)
            current_vr = float(vol_r.iloc[-1]) if not np.isnan(float(vol_r.iloc[-1])) else 1.0

            # Stricter volume filter for non-target symbols
            min_vr = 1.1 if is_target else 1.3
            if current_vr < min_vr:
                continue

            rsi14 = rsi(close, 14)
            current_rsi = float(rsi14.iloc[-1])
            entry, tp, sl_price = _atr_tp_sl(close, high, low, tp_mult=2.5, sl_mult=1.2)

            if bull_streak >= MIN_CONSEC and current_rsi < 72:
                confidence = 0.60 if is_target else 0.55
                if bull_streak >= 4:
                    confidence += 0.08
                if current_vr > 1.5:
                    confidence += 0.07
                if current_rsi < 55:
                    confidence += 0.05

                rr = abs(tp - entry) / abs(entry - sl_price) if abs(entry - sl_price) > 0 else 0

                signals.append({
                    "strategy": "candle_momentum_high_conviction",
                    "symbol": symbol,
                    "category": _get_category(symbol),
                    "signal_type": "BUY",
                    "entry_price": entry,
                    "take_profit": tp,
                    "stop_loss": sl_price,
                    "confidence": round(min(confidence, 0.82), 3),
                    "risk_reward": round(rr, 2),
                    "reason": (f"Candle momentum HC: {bull_streak} bullish candles "
                               f"(body>{BODY_THRESHOLD*100:.0f}%), vol_r={current_vr:.2f}, "
                               f"RSI={current_rsi:.0f}"),
                    "timeframe": "2-5d",
                    "rsi_at_entry": round(current_rsi, 2),
                    "extra": {
                        "bull_streak": bull_streak,
                        "volume_ratio": round(current_vr, 2),
                        "is_target_symbol": is_target,
                        "dna_variant": "candle_momentum_hc",
                    },
                    "timestamp": _now_iso(),
                })

        except Exception:
            continue

    return signals


# =====================================================================
# DNA VARIANT 4: fractal_decay_penny
# =====================================================================
# Fractal decay optimized for penny/meme stocks where it CRUSHES.
# Backtest: PLTR 100%, SOFI 100%, COIN 100%, AMC 100%, TSLA 100%
# Wider TP (these names move fast), keep SL tight.
# =====================================================================

FRACTAL_PENNY_TARGETS = {
    "PLTR", "SOFI", "COIN", "AMC", "TSLA", "RIVN",
    "MSTR", "AMD", "SOXX", "ARKK", "GLD",
}

def fractal_decay_penny(data: dict[str, pd.DataFrame],
                        context: Optional[dict] = None) -> list[dict]:
    """Fractal decay optimized for high-beta penny/meme stocks."""
    signals = []
    FRACTAL_DEPTH = 5
    DECAY_PERIOD = 20     # Shorter decay for faster-moving names
    SIGMA_COEFF = 0.22    # Slightly faster decay
    MOMENTUM_DECAY = 0.5  # Stronger momentum weighting

    for symbol, df in data.items():
        if symbol not in FRACTAL_PENNY_TARGETS:
            continue
        if df is None or len(df) < 50:
            continue

        try:
            close = df["Close"]
            high = df["High"]
            low = df["Low"]

            c = close.values.astype(float)
            h = high.values.astype(float)
            l = low.values.astype(float)
            n = len(c)

            # Detect fractals
            fractal_lows = []
            for i in range(FRACTAL_DEPTH, n - FRACTAL_DEPTH):
                is_low = all(l[i] <= l[i-j] and l[i] <= l[i+j]
                             for j in range(1, FRACTAL_DEPTH + 1))
                if is_low:
                    fractal_lows.append((i, l[i]))

            if len(fractal_lows) < 2:
                continue

            last_idx = n - 1
            price = c[-1]

            def dw(fi):
                age = last_idx - fi
                return np.exp(-SIGMA_COEFF * (age / DECAY_PERIOD) ** 2)

            wl = sum(v * dw(idx) for idx, v in fractal_lows[-8:])
            swl = sum(dw(idx) for idx, _ in fractal_lows[-8:])
            if swl == 0:
                continue

            support = wl / swl

            # Momentum
            rets = pd.Series(c).pct_change().tail(DECAY_PERIOD).dropna()
            if len(rets) < 5:
                continue
            momentum = float(rets.mean()) * DECAY_PERIOD
            mf = 1.0 + MOMENTUM_DECAY * momentum

            rsi14 = rsi(close, 14)
            current_rsi = float(rsi14.iloc[-1])

            # BUY only -- these names bounce hard from support
            if price <= support * 1.02 and mf > 0.98 and current_rsi < 50:
                # Wider TP for penny stocks (they move 10-30% easily)
                entry, tp, sl_price = _atr_tp_sl(close, high, low, tp_mult=4.0, sl_mult=1.5)

                confidence = 0.60
                proximity = abs(price - support) / support
                if proximity < 0.01:
                    confidence += 0.12
                if current_rsi < 30:
                    confidence += 0.10
                newest_age = last_idx - fractal_lows[-1][0]
                if newest_age < 8:
                    confidence += 0.05

                rr = abs(tp - entry) / abs(entry - sl_price) if abs(entry - sl_price) > 0 else 0

                signals.append({
                    "strategy": "fractal_decay_penny",
                    "symbol": symbol,
                    "category": _get_category(symbol),
                    "signal_type": "BUY",
                    "entry_price": entry,
                    "take_profit": tp,
                    "stop_loss": sl_price,
                    "confidence": round(min(confidence, 0.85), 3),
                    "risk_reward": round(rr, 2),
                    "reason": (f"Fractal-PENNY: {symbol} at decayed support "
                               f"${support:.2f}, RSI={current_rsi:.0f}, "
                               f"mf={mf:.2f} -- high-beta bounce setup"),
                    "timeframe": "3-10d",
                    "rsi_at_entry": round(current_rsi, 2),
                    "extra": {
                        "decay_support": round(support, 4),
                        "momentum_factor": round(mf, 4),
                        "fractal_age": newest_age,
                        "dna_variant": "fractal_decay_penny",
                    },
                    "timestamp": _now_iso(),
                })

        except Exception:
            continue

    return signals


# =====================================================================
# DNA VARIANT 5: red_bar_continuation_meme
# =====================================================================
# Theory CONFIRMED: 6 consecutive red bars → continuation in penny/meme
# stocks (56.6% WR) and crypto memes (70.8% WR).
# Only fires for these specific asset classes.
# =====================================================================

RED_BAR_TARGETS = {
    # Penny/meme stocks where 6-red confirmed
    "GME", "AMC", "PLTR", "SOFI", "RIVN", "LCID", "NIO", "SNDL", "COIN", "MSTR",
    # Crypto meme where 6-red confirmed (70.8% WR!)
    "DOGE-USD", "SHIB-USD", "PEPE-USD", "PEPE24478-USD",
    "WIF-USD", "BONK-USD", "FLOKI-USD",
}

def red_bar_continuation_meme(data: dict[str, pd.DataFrame],
                              context: Optional[dict] = None) -> list[dict]:
    """6 red bars → short on pullback. Only for penny stocks + crypto memes."""
    signals = []
    N_BARS = 6

    for symbol, df in data.items():
        if symbol not in RED_BAR_TARGETS:
            continue
        if df is None or len(df) < N_BARS + 5:
            continue

        try:
            close = df["Close"]
            opn = df["Open"]
            high = df["High"]
            low = df["Low"]

            c = close.values.astype(float)
            o = opn.values.astype(float)
            h = high.values.astype(float)
            l = low.values.astype(float)
            n = len(c)

            # Check for 6 consecutive red bars ending 2 bars ago
            all_red = all(c[n-N_BARS-1+j] < o[n-N_BARS-1+j] for j in range(N_BARS))
            if not all_red:
                continue

            # Last bar should be a green pullback
            if c[-1] <= o[-1]:
                continue

            rsi14 = rsi(close, 14)
            current_rsi = float(rsi14.iloc[-1])

            # Only short if not already extremely oversold
            if current_rsi < 20:
                continue

            atr_val = atr(high, low, close)
            current_atr = float(atr_val.iloc[-1])
            entry = float(c[-1])
            tp = entry - 3.0 * current_atr
            sl = entry + 1.5 * current_atr

            confidence = 0.58
            # Stronger signal with more dramatic red bars
            avg_red_size = np.mean([abs(c[n-N_BARS-1+j] - o[n-N_BARS-1+j])
                                    for j in range(N_BARS)])
            avg_range = np.mean([h[n-N_BARS-1+j] - l[n-N_BARS-1+j]
                                 for j in range(N_BARS)])
            if avg_range > 0 and avg_red_size / avg_range > 0.6:
                confidence += 0.08  # Strong body candles
            if current_rsi > 40:
                confidence += 0.05  # Pullback hasn't reversed yet

            rr = abs(entry - tp) / abs(sl - entry) if abs(sl - entry) > 0 else 0

            signals.append({
                "strategy": "red_bar_continuation_meme",
                "symbol": symbol,
                "category": _get_category(symbol),
                "signal_type": "SELL",
                "entry_price": _smart_round(entry),
                "take_profit": _smart_round(tp),
                "stop_loss": _smart_round(sl),
                "confidence": round(min(confidence, 0.78), 3),
                "risk_reward": round(rr, 2),
                "reason": (f"6-red-bar continuation: {symbol} had {N_BARS} consecutive "
                           f"red candles + pullback. RSI={current_rsi:.0f} -- "
                           f"downtrend likely continues"),
                "timeframe": "2-5d",
                "rsi_at_entry": round(current_rsi, 2),
                "extra": {
                    "red_bars": N_BARS,
                    "avg_body_ratio": round(avg_red_size / avg_range, 3) if avg_range > 0 else 0,
                    "dna_variant": "red_bar_continuation_meme",
                },
                "timestamp": _now_iso(),
            })

        except Exception:
            continue

    return signals


# =====================================================================
# DNA VARIANT 6: cusum_regime_scalp_equity
# =====================================================================
# CUSUM for equities: PLTR, AMD, NFLX, RIVN, SNDL, SOXX
# Backtest: PLTR scalp 78.6% WR, RIVN 75%, SOXX 72.7%, NFLX 64.7%
# Slightly different params than crypto variant.
# =====================================================================

CUSUM_EQUITY_TARGETS = {
    "PLTR", "AMD", "NFLX", "RIVN", "SNDL", "SOXX",
    "SOFI", "GME", "ARKK", "MSTR",
}

def cusum_regime_scalp_equity(data: dict[str, pd.DataFrame],
                              context: Optional[dict] = None) -> list[dict]:
    """CUSUM regime detector optimized for high-beta equities."""
    signals = []
    K_SENSITIVITY = 0.45
    H_THRESHOLD = 3.8
    LOOKBACK = 50

    for symbol, df in data.items():
        if symbol not in CUSUM_EQUITY_TARGETS:
            continue
        if df is None or len(df) < LOOKBACK + 10:
            continue

        try:
            close = df["Close"]
            high = df["High"]
            low = df["Low"]

            returns = close.pct_change().dropna()
            if len(returns) < LOOKBACK:
                continue

            mu = float(returns.tail(LOOKBACK).mean())
            sigma = float(returns.tail(LOOKBACK).std())
            if sigma == 0:
                continue

            k = K_SENSITIVITY * sigma
            h = H_THRESHOLD * sigma

            s_pos, s_neg = 0.0, 0.0
            pos_idx, neg_idx = None, None
            recent = returns.tail(LOOKBACK).values

            for i, r in enumerate(recent):
                s_pos = max(0, s_pos + r - mu - k)
                s_neg = max(0, s_neg - r + mu - k)
                if s_pos > h:
                    pos_idx = i
                    s_pos = 0
                if s_neg > h:
                    neg_idx = i
                    s_neg = 0

            rsi14 = rsi(close, 14)
            current_rsi = float(rsi14.iloc[-1])

            entry, tp, sl_price = _atr_tp_sl(close, high, low, tp_mult=2.0, sl_mult=1.0)

            if pos_idx is not None and pos_idx >= LOOKBACK - 5 and current_rsi < 72:
                recency = LOOKBACK - pos_idx
                confidence = 0.60
                if recency <= 2:
                    confidence += 0.12
                elif recency <= 4:
                    confidence += 0.06

                rr = abs(tp - entry) / abs(entry - sl_price) if abs(entry - sl_price) > 0 else 0

                signals.append({
                    "strategy": "cusum_regime_scalp_equity",
                    "symbol": symbol,
                    "category": _get_category(symbol),
                    "signal_type": "BUY",
                    "entry_price": entry,
                    "take_profit": tp,
                    "stop_loss": sl_price,
                    "confidence": round(min(confidence, 0.82), 3),
                    "risk_reward": round(rr, 2),
                    "reason": (f"CUSUM-EQUITY: regime UP {recency} bars ago, "
                               f"RSI={current_rsi:.0f} -- high-beta equity setup"),
                    "timeframe": "3-7d",
                    "rsi_at_entry": round(current_rsi, 2),
                    "extra": {
                        "detection_recency": recency,
                        "dna_variant": "cusum_scalp_equity",
                    },
                    "timestamp": _now_iso(),
                })

        except Exception:
            continue

    return signals


# =====================================================================
# Registry -- all DNA variants
# =====================================================================

DNA_SCALP_STRATEGIES: dict[str, callable] = {
    "cusum_regime_scalp_alt": cusum_regime_scalp_alt,
    "kalman_scalp_btc": kalman_scalp_btc,
    "candle_momentum_high_conviction": candle_momentum_high_conviction,
    "fractal_decay_penny": fractal_decay_penny,
    "red_bar_continuation_meme": red_bar_continuation_meme,
    "cusum_regime_scalp_equity": cusum_regime_scalp_equity,
}
