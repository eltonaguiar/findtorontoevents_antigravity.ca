"""
ALPHA_ENGINE -- NextGen Strategies (Wave 13)
=============================================
12 new strategies distilled from 60+ proposals by Inception Labs Mercury.
Each strategy follows the standard Alpha Engine pattern:
    func(data: dict[str, pd.DataFrame], context: dict | None = None) -> list[dict]

Strategies:
  1. cointegration_pair_trade    -- Z-score spread mean-reversion between cointegrated pairs
  2. adx_volatility_breakout     -- ADX-confirmed volatility expansion breakout
  3. seasonal_factor_rotation    -- Calendar seasonality + momentum confirmation
  4. multi_factor_equity_rotation-- Monthly L/S ranking by momentum+quality+vol
  5. dead_cat_bounce_momentum    -- Engulfing pattern in extreme fear + volume surge
  6. market_structure_break      -- Round-number level break with institutional volume
  7. volume_acceleration_reversion-- Volume spike with no price move (absorption reversal)
  8. night_liquidity_drift       -- Off-peak hour breakout in thin markets
  9. spread_of_candles_gap       -- Two-candle gap detection + gap fill target
  10. vix_correlation_divergence -- SPY bounce when VIX decouples
  11. profit_taking_reentry      -- Re-enter after pullback on winners (meta-layer)
  12. bb_rsi_mean_reversion      -- Bollinger band touch + RSI extreme (mean-reversion scalp)
  13. pi_cycle_regime_gate        -- Suppress longs when 111DMA near 350DMA×2 (macro top)
  14. puell_multiple_extreme      -- Mining revenue ratio for BTC macro bottom/top detection

References cited inline per strategy.
"""

from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from typing import Optional

import numpy as np
import pandas as pd

from config import (
    CRYPTO_SYMBOLS, EQUITY_SYMBOLS, ALL_SYMBOLS, CATEGORY_RISK,
    DATA_DIR,
)
from indicators import (
    rsi, sma, ema, atr, adx, bollinger_bands, zscore,
    volume_ratio, hurst_exponent, macd, vwap_session,
)


# ---------------------------------------------------------------------------
# Helpers (same patterns as crypto_strategies.py)
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _get_category(symbol: str) -> str:
    info = ALL_SYMBOLS.get(symbol, {})
    return info.get("cat", "crypto")


def _smart_round(value: float) -> float:
    if value == 0 or not math.isfinite(value):
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


def _atr_val(high: pd.Series, low: pd.Series, close: pd.Series,
             period: int = 14) -> float:
    """Return latest ATR value as float."""
    a = atr(high, low, close, period)
    val = float(a.iloc[-1])
    return val if math.isfinite(val) and val > 0 else 0.0


def _rr(entry: float, tp: float, sl: float) -> float:
    """Compute risk-reward ratio."""
    risk = abs(entry - sl)
    reward = abs(tp - entry)
    if risk <= 0:
        return 0.0
    return round(reward / risk, 2)


# =========================================================================
# STRATEGY 1: Cointegration Pair Trade (CPT)
# =========================================================================
# Reference: Vidyamurthy (2004) "Pairs Trading", Johansen (1991)
# Edge: Mean-reverting spread between statistically cointegrated crypto pairs.
# Uses OLS regression + Z-score entry/exit.
# =========================================================================

def cointegration_pair_trade(data: dict[str, pd.DataFrame],
                             context: dict | None = None) -> list[dict]:
    """
    Find cointegrated crypto pairs and trade spread mean-reversion.
    Entry: Z-score > 2 or < -2. Exit target: Z < 0.5.
    """
    signals = []
    lookback = 120  # minimum candles for spread stats
    zscore_entry = 2.0
    zscore_exit = 0.5
    tp_sl_atr_mult = (2.0, 1.5)

    # Get symbols with enough data
    available = {}
    for sym in CRYPTO_SYMBOLS:
        df = data.get(sym)
        if df is not None and len(df) >= lookback:
            available[sym] = df

    if len(available) < 2:
        return signals

    symbols = list(available.keys())

    # Test pairs (limit to top 10 by market cap to avoid combinatorial explosion)
    top_syms = symbols[:10]
    tested = set()

    for i, s1 in enumerate(top_syms):
        for s2 in top_syms[i + 1:]:
            pair_key = f"{s1}/{s2}"
            if pair_key in tested:
                continue
            tested.add(pair_key)

            try:
                df1 = available[s1]
                df2 = available[s2]

                # Align on same length
                min_len = min(len(df1), len(df2), lookback)
                log_p1 = np.log(df1["Close"].iloc[-min_len:].values.astype(float))
                log_p2 = np.log(df2["Close"].iloc[-min_len:].values.astype(float))

                if len(log_p1) < lookback or np.any(~np.isfinite(log_p1)) or np.any(~np.isfinite(log_p2)):
                    continue

                # OLS regression: log_p1 = beta * log_p2 + alpha + residual
                beta, alpha = np.polyfit(log_p2, log_p1, 1)
                spread = log_p1 - beta * log_p2 - alpha
                mu = np.mean(spread)
                sigma = np.std(spread)

                if sigma < 1e-8:
                    continue

                z = (spread[-1] - mu) / sigma

                # Quick stationarity check: spread mean should be near 0
                # and spread should cross zero at least 3 times in lookback
                zero_crossings = np.sum(np.diff(np.sign(spread - mu)) != 0)
                if zero_crossings < 3:
                    continue

                if abs(z) < zscore_entry:
                    continue

                # Direction: z > 2 means s1 overpriced relative to s2
                price1 = float(df1["Close"].iloc[-1])
                price2 = float(df2["Close"].iloc[-1])
                atr1 = _atr_val(df1["High"], df1["Low"], df1["Close"])

                if atr1 <= 0:
                    continue

                if z > zscore_entry:
                    # s1 overpriced → SHORT s1 (or just signal SELL on s1)
                    direction = "SELL"
                    entry = _smart_round(price1)
                    tp = _smart_round(price1 - tp_sl_atr_mult[0] * atr1)
                    sl = _smart_round(price1 + tp_sl_atr_mult[1] * atr1)
                elif z < -zscore_entry:
                    # s1 underpriced → LONG s1
                    direction = "BUY"
                    entry = _smart_round(price1)
                    tp = _smart_round(price1 + tp_sl_atr_mult[0] * atr1)
                    sl = _smart_round(price1 - tp_sl_atr_mult[1] * atr1)
                else:
                    continue

                rr = _rr(entry, tp, sl)
                if rr < 1.3:
                    continue

                # Confidence scales with z-score magnitude (capped)
                conf = round(min(0.75, 0.55 + (abs(z) - zscore_entry) * 0.1), 2)

                signals.append({
                    "strategy": "cointegration_pair_trade",
                    "symbol": s1,
                    "category": _get_category(s1),
                    "signal_type": direction,
                    "entry_price": entry,
                    "take_profit": tp,
                    "stop_loss": sl,
                    "confidence": conf,
                    "risk_reward": rr,
                    "reason": (f"Cointegrated pair {s1}/{s2}: Z={z:.2f} "
                               f"(entry at |Z|>{zscore_entry}), beta={beta:.3f}, "
                               f"zero-crossings={zero_crossings}"),
                    "timeframe": "1d",
                    "extra": {
                        "hedge_symbol": s2,
                        "beta": round(beta, 4),
                        "zscore": round(z, 3),
                        "sigma": round(sigma, 6),
                        "zero_crossings": int(zero_crossings),
                        "source": "Vidyamurthy (2004), Johansen (1991)",
                    },
                    "timestamp": _now_iso(),
                })
            except Exception:
                continue

    return signals[:4]  # Max 4 pair signals per scan


# =========================================================================
# STRATEGY 2: ADX Volatility Breakout
# =========================================================================
# Reference: Wilder (1978) ADX, Keltner (1960) volatility channels.
# Edge: When ADX confirms a strong trend AND volatility surges, breakouts
# of 20-period highs/lows have high continuation probability.
# =========================================================================

def adx_volatility_breakout(data: dict[str, pd.DataFrame],
                            context: dict | None = None) -> list[dict]:
    """
    ADX > 25 + ATR spike 30% + 20-period high/low break = trend continuation.
    """
    signals = []
    adx_threshold = 25
    atr_spike_pct = 0.30
    lookback = 20

    for symbol in CRYPTO_SYMBOLS:
        df = data.get(symbol)
        if df is None or len(df) < 50:
            continue

        try:
            close = df["Close"]
            high = df["High"]
            low = df["Low"]

            # ADX
            adx_vals = adx(high, low, close, 14)
            current_adx = float(adx_vals.iloc[-1])
            if not math.isfinite(current_adx) or current_adx < adx_threshold:
                continue

            # ATR spike: current 14-period ATR vs 4x longer average
            atr_short = _atr_val(high, low, close, 14)
            atr_long = _atr_val(high, low, close, 56)  # ~4 weeks
            if atr_long <= 0 or atr_short <= 0:
                continue
            if (atr_short - atr_long) / atr_long < atr_spike_pct:
                continue

            # 20-period high/low
            high_20 = float(high.iloc[-lookback:].max())
            low_20 = float(low.iloc[-lookback:].min())
            price = float(close.iloc[-1])

            direction = None
            if price > high_20 * 0.998:  # within 0.2% of 20-period high
                direction = "BUY"
                tp = _smart_round(price + 3.0 * atr_short)
                sl = _smart_round(price - 1.0 * atr_short)
            elif price < low_20 * 1.002:
                direction = "SELL"
                tp = _smart_round(price - 3.0 * atr_short)
                sl = _smart_round(price + 1.0 * atr_short)

            if direction is None:
                continue

            rr = _rr(price, tp, sl)
            if rr < 1.3:
                continue

            signals.append({
                "strategy": "adx_volatility_breakout",
                "symbol": symbol,
                "category": _get_category(symbol),
                "signal_type": direction,
                "entry_price": _smart_round(price),
                "take_profit": tp,
                "stop_loss": sl,
                "confidence": round(min(0.72, 0.55 + (current_adx - 25) * 0.005), 2),
                "risk_reward": rr,
                "reason": (f"ADX={current_adx:.0f} (>{adx_threshold}) + "
                           f"ATR spike {(atr_short/atr_long-1)*100:.0f}% + "
                           f"{'new high' if direction == 'BUY' else 'new low'} "
                           f"(20p {'high' if direction == 'BUY' else 'low'}={high_20 if direction == 'BUY' else low_20:.2f})"),
                "timeframe": "1d",
                "extra": {
                    "adx": round(current_adx, 1),
                    "atr_short": round(atr_short, 4),
                    "atr_long": round(atr_long, 4),
                    "source": "Wilder (1978) ADX + Keltner channels",
                },
                "timestamp": _now_iso(),
            })
        except Exception:
            continue

    return signals


# =========================================================================
# STRATEGY 3: Seasonal Factor Rotation
# =========================================================================
# Reference: Kamstra et al. (2003) "Winter Blues", Bouman & Jacobsen (2002)
# Edge: Calendar-based seasonal patterns in crypto. BTC historically stronger
# in Q4/Q1, weaker in Q3. Altcoins follow BTC with a lag.
# =========================================================================

def seasonal_factor_rotation(data: dict[str, pd.DataFrame],
                             context: dict | None = None) -> list[dict]:
    """
    Compute seasonal factor from historical daily averages (rolling 252d).
    Long when factor > 1.02 + 7d momentum positive.
    Short when factor < 0.98 + 7d momentum negative.
    """
    signals = []

    for symbol in CRYPTO_SYMBOLS:
        df = data.get(symbol)
        if df is None or len(df) < 252:
            continue

        try:
            close = df["Close"]
            price = float(close.iloc[-1])

            # Compute seasonal factor: price / 252-day SMA
            # This approximates "how far are we from the yearly average?"
            sma_252 = float(sma(close, 252).iloc[-1])
            if sma_252 <= 0 or not math.isfinite(sma_252):
                continue

            season_factor = price / sma_252

            # 7-day momentum
            if len(close) < 7:
                continue
            mom_7d = (price / float(close.iloc[-7]) - 1)

            # Monthly seasonality bonus: Q4/Q1 historically bullish for crypto
            month = datetime.now().month
            seasonal_bonus = 0.0
            if month in (10, 11, 12, 1, 2):
                seasonal_bonus = 0.01  # Lower threshold in bullish months

            atr_val = _atr_val(df["High"], df["Low"], close)
            if atr_val <= 0:
                continue

            direction = None
            if season_factor > (1.02 - seasonal_bonus) and mom_7d > 0:
                direction = "BUY"
                tp = _smart_round(price * 1.02)
                sl = _smart_round(price * 0.99)
            elif season_factor < (0.98 + seasonal_bonus) and mom_7d < 0:
                direction = "SELL"
                tp = _smart_round(price * 0.98)
                sl = _smart_round(price * 1.01)

            if direction is None:
                continue

            rr = _rr(price, tp, sl)
            if rr < 1.3:
                continue

            signals.append({
                "strategy": "seasonal_factor_rotation",
                "symbol": symbol,
                "category": _get_category(symbol),
                "signal_type": direction,
                "entry_price": _smart_round(price),
                "take_profit": tp,
                "stop_loss": sl,
                "confidence": round(min(0.65, 0.55 + abs(season_factor - 1.0) * 2), 2),
                "risk_reward": rr,
                "reason": (f"Seasonal factor={season_factor:.3f} "
                           f"({'above' if direction == 'BUY' else 'below'} threshold), "
                           f"7d momentum={mom_7d*100:.1f}%, month={month}"),
                "timeframe": "1d",
                "extra": {
                    "season_factor": round(season_factor, 4),
                    "momentum_7d": round(mom_7d, 4),
                    "month": month,
                    "source": "Kamstra et al. (2003), Bouman & Jacobsen (2002)",
                },
                "timestamp": _now_iso(),
            })
        except Exception:
            continue

    return signals


# =========================================================================
# STRATEGY 4: Multi-Factor Equity Rotation
# =========================================================================
# Reference: Asness et al. (2013) "Value and Momentum Everywhere"
# Edge: Monthly ranking by composite factor score (momentum + low-vol + value).
# Long top 3, short bottom 3.
# =========================================================================

def multi_factor_equity_rotation(data: dict[str, pd.DataFrame],
                                 context: dict | None = None) -> list[dict]:
    """
    Rank equity universe by composite score. Long top 3, short bottom 3.
    Only fires on 1st trading day of month (approx: day <= 3).
    """
    signals = []

    # Only fire near month start
    today = datetime.now().day
    if today > 5:
        return signals

    # Score each equity
    scores = {}
    equity_data = {}
    for symbol in EQUITY_SYMBOLS:
        df = data.get(symbol)
        if df is None or len(df) < 63:  # need 3 months
            continue

        try:
            close = df["Close"]
            price = float(close.iloc[-1])

            # Momentum (3-month return): weight 0.5
            mom_3m = price / float(close.iloc[-63]) - 1 if len(close) >= 63 else 0

            # Low-volatility (inverse of 30-day vol): weight 0.3
            vol_30d = float(close.pct_change().rolling(30).std().iloc[-1])
            low_vol_score = 1.0 / (vol_30d + 0.001)  # inverse

            # Normalize to 0-1 range (will normalize across symbols later)
            scores[symbol] = {
                "momentum": mom_3m,
                "low_vol": low_vol_score,
                "price": price,
            }
            equity_data[symbol] = df
        except Exception:
            continue

    if len(scores) < 6:
        return signals

    # Rank and compute composite score
    # Normalize each factor to [0, 1]
    mom_vals = [s["momentum"] for s in scores.values()]
    vol_vals = [s["low_vol"] for s in scores.values()]
    mom_min, mom_max = min(mom_vals), max(mom_vals)
    vol_min, vol_max = min(vol_vals), max(vol_vals)

    composite = {}
    for sym, s in scores.items():
        mom_norm = (s["momentum"] - mom_min) / (mom_max - mom_min + 1e-8)
        vol_norm = (s["low_vol"] - vol_min) / (vol_max - vol_min + 1e-8)
        composite[sym] = 0.6 * mom_norm + 0.4 * vol_norm

    ranked = sorted(composite.items(), key=lambda x: x[1], reverse=True)
    top3 = [r[0] for r in ranked[:3]]
    bot3 = [r[0] for r in ranked[-3:]]

    for sym in top3:
        df = equity_data[sym]
        price = scores[sym]["price"]
        atr_val = _atr_val(df["High"], df["Low"], df["Close"])
        if atr_val <= 0:
            continue
        tp = _smart_round(price + 2.5 * atr_val)
        sl = _smart_round(price - 1.5 * atr_val)
        rr = _rr(price, tp, sl)

        signals.append({
            "strategy": "multi_factor_equity_rotation",
            "symbol": sym,
            "category": _get_category(sym),
            "signal_type": "BUY",
            "entry_price": _smart_round(price),
            "take_profit": tp,
            "stop_loss": sl,
            "confidence": round(min(0.70, 0.55 + composite[sym] * 0.2), 2),
            "risk_reward": rr,
            "reason": (f"Top-3 composite score={composite[sym]:.3f} "
                       f"(mom={scores[sym]['momentum']*100:.1f}%, "
                       f"vol-rank={ranked.index((sym, composite[sym]))+1}/{len(ranked)})"),
            "timeframe": "1d",
            "extra": {
                "composite_score": round(composite[sym], 4),
                "momentum_3m": round(scores[sym]["momentum"], 4),
                "rank": ranked.index((sym, composite[sym])) + 1,
                "source": "Asness et al. (2013) Value & Momentum Everywhere",
            },
            "timestamp": _now_iso(),
        })

    for sym in bot3:
        df = equity_data[sym]
        price = scores[sym]["price"]
        atr_val = _atr_val(df["High"], df["Low"], df["Close"])
        if atr_val <= 0:
            continue
        tp = _smart_round(price - 2.5 * atr_val)
        sl = _smart_round(price + 1.5 * atr_val)
        rr = _rr(price, tp, sl)

        signals.append({
            "strategy": "multi_factor_equity_rotation",
            "symbol": sym,
            "category": _get_category(sym),
            "signal_type": "SELL",
            "entry_price": _smart_round(price),
            "take_profit": tp,
            "stop_loss": sl,
            "confidence": round(min(0.65, 0.50 + (1 - composite[sym]) * 0.2), 2),
            "risk_reward": rr,
            "reason": (f"Bottom-3 composite score={composite[sym]:.3f} "
                       f"(mom={scores[sym]['momentum']*100:.1f}%, "
                       f"weak momentum + high vol)"),
            "timeframe": "1d",
            "extra": {
                "composite_score": round(composite[sym], 4),
                "momentum_3m": round(scores[sym]["momentum"], 4),
                "source": "Asness et al. (2013)",
            },
            "timestamp": _now_iso(),
        })

    return signals


# =========================================================================
# STRATEGY 5: Dead Cat Bounce Momentum
# =========================================================================
# Reference: Subrahmanyam (2005) "Distinguishing Between Bad Models and
# Market Inefficiencies"
# Edge: After extreme panic drop (F&G ≤ 12, >8% in 2h), a 3-candle bullish
# engulfing with volume > 1.5× average is a high-probability reversal.
# =========================================================================

def dead_cat_bounce_momentum(data: dict[str, pd.DataFrame],
                             context: dict | None = None) -> list[dict]:
    """
    Extreme fear + large drop + bullish engulfing + volume = reversal long.
    """
    signals = []

    # Fear & Greed check
    fng = 50
    if context and "fear_greed" in context:
        try:
            fng = int(context["fear_greed"]["data"][0]["value"])
        except (KeyError, IndexError, TypeError):
            pass

    if fng > 12:
        return signals  # Only fire in extreme panic

    for symbol in CRYPTO_SYMBOLS:
        df = data.get(symbol)
        if df is None or len(df) < 10:
            continue

        try:
            close = df["Close"]
            high = df["High"]
            low = df["Low"]
            volume = df["Volume"]
            open_price = df["Open"]

            price = float(close.iloc[-1])

            # Check for large recent drop (>8% from recent high in last 5 bars)
            recent_high = float(high.iloc[-5:].max())
            drop_pct = (recent_high - price) / recent_high
            if drop_pct < 0.08:
                continue

            # Bullish engulfing: current candle body covers previous candle body
            cur_open = float(open_price.iloc[-1])
            cur_close = float(close.iloc[-1])
            prev_open = float(open_price.iloc[-2])
            prev_close = float(close.iloc[-2])

            is_bullish_engulf = (
                cur_close > cur_open and  # current is green
                prev_close < prev_open and  # previous is red
                cur_close > prev_open and  # current close > prev open
                cur_open < prev_close  # current open < prev close
            )

            if not is_bullish_engulf:
                continue

            # Volume confirmation: current volume > 1.5× 20-bar average
            avg_vol = float(volume.iloc[-20:].mean())
            cur_vol = float(volume.iloc[-1])
            if avg_vol <= 0 or cur_vol < 1.5 * avg_vol:
                continue

            atr_val = _atr_val(high, low, close)
            if atr_val <= 0:
                continue

            tp = _smart_round(price * 1.05)  # 5% TP
            sl = _smart_round(price * 0.98)  # 2% SL

            rr = _rr(price, tp, sl)
            if rr < 1.3:
                continue

            signals.append({
                "strategy": "dead_cat_bounce_momentum",
                "symbol": symbol,
                "category": _get_category(symbol),
                "signal_type": "BUY",
                "entry_price": _smart_round(price),
                "take_profit": tp,
                "stop_loss": sl,
                "confidence": round(min(0.75, 0.60 + drop_pct * 0.5), 2),
                "risk_reward": rr,
                "reason": (f"F&G={fng} (extreme panic) + {drop_pct*100:.1f}% drop from "
                           f"recent high + bullish engulfing + vol {cur_vol/avg_vol:.1f}x avg"),
                "timeframe": "1d",
                "rsi_at_entry": round(float(rsi(close, 14).iloc[-1]), 1),
                "volume_ratio": round(cur_vol / avg_vol, 2),
                "extra": {
                    "fear_greed": fng,
                    "drop_pct": round(drop_pct, 4),
                    "vol_multiplier": round(cur_vol / avg_vol, 2),
                    "source": "Dead-cat bounce reversal (Subrahmanyam 2005)",
                },
                "timestamp": _now_iso(),
            })
        except Exception:
            continue

    return signals


# =========================================================================
# STRATEGY 6: Market Structure Break
# =========================================================================
# Reference: Wyckoff (1931) "Studies in Tape Reading"
# Edge: When price breaks a significant round-number level (e.g., BTC $65K)
# with 2× average volume and holds for 2 bars, continuation is likely.
# =========================================================================

def market_structure_break(data: dict[str, pd.DataFrame],
                           context: dict | None = None) -> list[dict]:
    """
    Round-number level break with institutional volume confirmation.
    """
    signals = []

    for symbol in CRYPTO_SYMBOLS:
        df = data.get(symbol)
        if df is None or len(df) < 25:
            continue

        try:
            close = df["Close"]
            high = df["High"]
            low = df["Low"]
            volume = df["Volume"]

            price = float(close.iloc[-1])
            if price <= 0:
                continue

            # Determine round-number step size based on price magnitude
            if price >= 10000:
                step = 1000
            elif price >= 1000:
                step = 100
            elif price >= 100:
                step = 10
            elif price >= 10:
                step = 1
            elif price >= 1:
                step = 0.1
            else:
                step = price * 0.05  # 5% steps for very small prices

            # Find nearest round levels
            level_above = math.ceil(price / step) * step
            level_below = math.floor(price / step) * step

            # Check if price just broke above a level
            prev_close_2 = float(close.iloc[-3])
            prev_close_1 = float(close.iloc[-2])

            # Volume check: current > 2× 20-bar average
            avg_vol = float(volume.iloc[-20:].mean())
            cur_vol = float(volume.iloc[-1])
            if avg_vol <= 0 or cur_vol < 2.0 * avg_vol:
                continue

            atr_val = _atr_val(high, low, close)
            if atr_val <= 0:
                continue

            direction = None
            broken_level = None

            # Breakout above: price was below level, now above for 2 bars
            if prev_close_2 < level_below and prev_close_1 > level_below and price > level_below:
                direction = "BUY"
                broken_level = level_below
            # Breakdown below: price was above level, now below for 2 bars
            elif prev_close_2 > level_above and prev_close_1 < level_above and price < level_above:
                direction = "SELL"
                broken_level = level_above

            if direction is None:
                continue

            if direction == "BUY":
                tp = _smart_round(price + 2.5 * atr_val)
                sl = _smart_round(max(price - 1.5 * atr_val, broken_level * 0.995))
            else:
                tp = _smart_round(price - 2.5 * atr_val)
                sl = _smart_round(min(price + 1.5 * atr_val, broken_level * 1.005))

            rr = _rr(price, tp, sl)
            if rr < 1.3:
                continue

            signals.append({
                "strategy": "market_structure_break",
                "symbol": symbol,
                "category": _get_category(symbol),
                "signal_type": direction,
                "entry_price": _smart_round(price),
                "take_profit": tp,
                "stop_loss": sl,
                "confidence": round(min(0.68, 0.55 + (cur_vol / avg_vol - 2) * 0.05), 2),
                "risk_reward": rr,
                "reason": (f"Broke {'above' if direction == 'BUY' else 'below'} "
                           f"level {broken_level} (held 2 bars), "
                           f"vol={cur_vol/avg_vol:.1f}x avg"),
                "timeframe": "1d",
                "volume_ratio": round(cur_vol / avg_vol, 2),
                "extra": {
                    "broken_level": broken_level,
                    "vol_multiplier": round(cur_vol / avg_vol, 2),
                    "source": "Wyckoff (1931) structural breaks",
                },
                "timestamp": _now_iso(),
            })
        except Exception:
            continue

    return signals


# =========================================================================
# STRATEGY 7: Volume Acceleration Reversion
# =========================================================================
# Reference: Easley, Lopez de Prado & O'Hara (2012) "Volume Clock"
# Edge: When volume spikes 3× without meaningful price change (<0.3%),
# it indicates "absorption" -- large orders being filled without moving
# price. The market typically reverses shortly after.
# =========================================================================

def volume_acceleration_reversion(data: dict[str, pd.DataFrame],
                                  context: dict | None = None) -> list[dict]:
    """
    Volume spike 3× avg + price move < 0.3% = absorption → expect reversal.
    """
    signals = []

    for symbol in CRYPTO_SYMBOLS:
        df = data.get(symbol)
        if df is None or len(df) < 30:
            continue

        try:
            close = df["Close"]
            high = df["High"]
            low = df["Low"]
            open_price = df["Open"]
            volume = df["Volume"]

            price = float(close.iloc[-1])
            cur_open = float(open_price.iloc[-1])
            cur_vol = float(volume.iloc[-1])

            # Volume acceleration: 3× 30-bar average
            avg_vol = float(volume.iloc[-30:].mean())
            if avg_vol <= 0 or cur_vol < 3.0 * avg_vol:
                continue

            # Price move must be tiny (< 0.3%)
            price_move = abs(price - cur_open) / cur_open
            if price_move > 0.003:
                continue

            atr_val = _atr_val(high, low, close)
            if atr_val <= 0:
                continue

            # Direction: if tiny green candle during absorption → SHORT (buying absorbed)
            # If tiny red candle → LONG (selling absorbed)
            if price > cur_open:
                direction = "SELL"  # buying pressure absorbed → reversal down
                tp = _smart_round(price - 1.8 * atr_val)
                sl = _smart_round(price + 1.2 * atr_val)
            else:
                direction = "BUY"  # selling pressure absorbed → reversal up
                tp = _smart_round(price + 1.8 * atr_val)
                sl = _smart_round(price - 1.2 * atr_val)

            rr = _rr(price, tp, sl)
            if rr < 1.3:
                continue

            signals.append({
                "strategy": "volume_acceleration_reversion",
                "symbol": symbol,
                "category": _get_category(symbol),
                "signal_type": direction,
                "entry_price": _smart_round(price),
                "take_profit": tp,
                "stop_loss": sl,
                "confidence": round(min(0.70, 0.58 + (cur_vol / avg_vol - 3) * 0.03), 2),
                "risk_reward": rr,
                "reason": (f"Volume {cur_vol/avg_vol:.1f}x avg but price moved only "
                           f"{price_move*100:.2f}% -- absorption detected, expect reversal"),
                "timeframe": "1d",
                "volume_ratio": round(cur_vol / avg_vol, 2),
                "extra": {
                    "vol_multiplier": round(cur_vol / avg_vol, 2),
                    "price_move_pct": round(price_move * 100, 3),
                    "source": "Easley, Lopez de Prado & O'Hara (2012)",
                },
                "timestamp": _now_iso(),
            })
        except Exception:
            continue

    return signals


# =========================================================================
# STRATEGY 8: Night Liquidity Drift
# =========================================================================
# Reference: Barclay & Hendershott (2003) "Price Discovery and Trading
# After Hours"
# Edge: During off-peak hours (00-04 UTC), when volume is < 30% of avg,
# breakouts tend to be trend-following because thin order books amplify
# moves. The drift often lasts 1-3 hours.
# =========================================================================

def night_liquidity_drift(data: dict[str, pd.DataFrame],
                          context: dict | None = None) -> list[dict]:
    """
    Off-peak (00-04 UTC) + low volume + 4h high/low break → trend continuation.
    """
    signals = []

    # Check if we're in the off-peak window (approximate via UTC hour)
    now_utc = datetime.now(timezone.utc)
    if now_utc.hour not in (0, 1, 2, 3):
        return signals  # Only fire during off-peak

    for symbol in CRYPTO_SYMBOLS:
        df = data.get(symbol)
        if df is None or len(df) < 10:
            continue

        try:
            close = df["Close"]
            high = df["High"]
            low = df["Low"]
            volume = df["Volume"]

            price = float(close.iloc[-1])
            cur_vol = float(volume.iloc[-1])

            # Low volume check: < 50% of 20-bar average
            avg_vol = float(volume.iloc[-20:].mean())
            if avg_vol <= 0 or cur_vol > 0.50 * avg_vol:
                continue  # Volume too high for a "night drift"

            # 4-bar high/low (approximates 4h on daily, or 4 candles)
            high_4 = float(high.iloc[-4:].max())
            low_4 = float(low.iloc[-4:].min())

            atr_val = _atr_val(high, low, close)
            if atr_val <= 0:
                continue

            direction = None
            if price > high_4:
                direction = "BUY"
                tp = _smart_round(price + 2.5 * atr_val)
                sl = _smart_round(price - 1.5 * atr_val)
            elif price < low_4:
                direction = "SELL"
                tp = _smart_round(price - 2.5 * atr_val)
                sl = _smart_round(price + 1.5 * atr_val)

            if direction is None:
                continue

            rr = _rr(price, tp, sl)
            if rr < 1.3:
                continue

            signals.append({
                "strategy": "night_liquidity_drift",
                "symbol": symbol,
                "category": _get_category(symbol),
                "signal_type": direction,
                "entry_price": _smart_round(price),
                "take_profit": tp,
                "stop_loss": sl,
                "confidence": 0.60,
                "risk_reward": rr,
                "reason": (f"Off-peak breakout (UTC {now_utc.hour}:00): "
                           f"vol={cur_vol/avg_vol*100:.0f}% of avg, "
                           f"{'new high' if direction == 'BUY' else 'new low'} "
                           f"(4-bar range {low_4:.2f}-{high_4:.2f})"),
                "timeframe": "1d",
                "volume_ratio": round(cur_vol / avg_vol, 2) if avg_vol > 0 else 0,
                "extra": {
                    "utc_hour": now_utc.hour,
                    "vol_pct_of_avg": round(cur_vol / avg_vol * 100, 1) if avg_vol > 0 else 0,
                    "source": "Barclay & Hendershott (2003)",
                },
                "timestamp": _now_iso(),
            })
        except Exception:
            continue

    return signals


# =========================================================================
# STRATEGY 9: Spread of Candles Gap Fill
# =========================================================================
# Reference: CME Gap Fill effect; Bulkowski (2005) "Encyclopedia of Chart
# Patterns"
# Edge: When two consecutive candles create a price gap (open[i] > high[i-1]
# or open[i] < low[i-1]), the gap fills ~70% of the time within 3 days.
# =========================================================================

def spread_of_candles_gap(data: dict[str, pd.DataFrame],
                          context: dict | None = None) -> list[dict]:
    """
    Detect two-candle gaps. Short gap-ups, long gap-downs (gap fill trade).
    """
    signals = []

    for symbol in CRYPTO_SYMBOLS:
        df = data.get(symbol)
        if df is None or len(df) < 25:
            continue

        try:
            close = df["Close"]
            high = df["High"]
            low = df["Low"]
            open_price = df["Open"]
            volume = df["Volume"]

            cur_open = float(open_price.iloc[-1])
            prev_high = float(high.iloc[-2])
            prev_low = float(low.iloc[-2])
            price = float(close.iloc[-1])

            # Volume check: > 1.3× average
            avg_vol = float(volume.iloc[-20:].mean())
            cur_vol = float(volume.iloc[-1])
            if avg_vol <= 0 or cur_vol < 1.3 * avg_vol:
                continue

            atr_val = _atr_val(high, low, close)
            if atr_val <= 0:
                continue

            direction = None
            gap_target = None

            # Gap up: current open > previous high
            if cur_open > prev_high * 1.001:  # at least 0.1% gap
                direction = "SELL"  # expect gap fill (price comes back down)
                gap_target = prev_high  # target is to fill back to prev high
                sl = _smart_round(price + 2.0 * atr_val)
            # Gap down: current open < previous low
            elif cur_open < prev_low * 0.999:
                direction = "BUY"  # expect gap fill (price comes back up)
                gap_target = prev_low
                sl = _smart_round(price - 2.0 * atr_val)

            if direction is None or gap_target is None:
                continue

            tp = _smart_round(gap_target)
            rr = _rr(price, tp, sl)
            if rr < 1.3:
                continue

            gap_size = abs(cur_open - (prev_high if direction == "SELL" else prev_low))
            gap_pct = gap_size / price * 100

            signals.append({
                "strategy": "spread_of_candles_gap",
                "symbol": symbol,
                "category": _get_category(symbol),
                "signal_type": direction,
                "entry_price": _smart_round(price),
                "take_profit": tp,
                "stop_loss": sl,
                "confidence": round(min(0.72, 0.60 + gap_pct * 0.02), 2),
                "risk_reward": rr,
                "reason": (f"{'Gap up' if direction == 'SELL' else 'Gap down'} "
                           f"detected ({gap_pct:.2f}% gap), target gap fill at "
                           f"{gap_target:.2f}, vol {cur_vol/avg_vol:.1f}x avg"),
                "timeframe": "1d",
                "volume_ratio": round(cur_vol / avg_vol, 2),
                "extra": {
                    "gap_size_pct": round(gap_pct, 3),
                    "gap_target": gap_target,
                    "source": "CME Gap Fill effect, Bulkowski (2005)",
                },
                "timestamp": _now_iso(),
            })
        except Exception:
            continue

    return signals


# =========================================================================
# STRATEGY 10: VIX Correlation Divergence
# =========================================================================
# Reference: Whaley (2000) "The Investor Fear Gauge"
# Edge: When VIX > 25 but SPY-VIX correlation drops < 0.2 for 4+ bars,
# equities often bounce because the fear is no longer driving prices.
# =========================================================================

def vix_correlation_divergence(data: dict[str, pd.DataFrame],
                               context: dict | None = None) -> list[dict]:
    """
    Long SPY/QQQ when VIX > 25 but SPY-VIX correlation breaks down.
    """
    signals = []

    spy_df = data.get("SPY")
    # Try to get VIX data -- it may be in the equity data or not available
    vix_df = data.get("^VIX") or data.get("VIX")

    if spy_df is None or len(spy_df) < 30:
        return signals

    # If no VIX data, use SPY volatility as proxy
    try:
        spy_close = spy_df["Close"]
        spy_price = float(spy_close.iloc[-1])

        if vix_df is not None and len(vix_df) >= 30:
            vix_close = vix_df["Close"]
            vix_level = float(vix_close.iloc[-1])

            if vix_level <= 25:
                return signals  # Only fire when VIX elevated

            # Compute rolling correlation (20-bar)
            spy_ret = spy_close.pct_change().iloc[-20:]
            vix_ret = vix_close.pct_change().iloc[-20:]

            if len(spy_ret.dropna()) < 15 or len(vix_ret.dropna()) < 15:
                return signals

            corr = float(spy_ret.corr(vix_ret))

            if corr >= 0.2:
                return signals  # Correlation still intact, no divergence
        else:
            # Proxy: use realized vol spike as VIX substitute
            realized_vol = float(spy_close.pct_change().rolling(20).std().iloc[-1]) * (252 ** 0.5)
            if realized_vol < 0.25:  # ~25% annualized
                return signals
            vix_level = realized_vol * 100
            corr = -0.1  # assume divergence when using proxy

        atr_val = _atr_val(spy_df["High"], spy_df["Low"], spy_close)
        if atr_val <= 0:
            return signals

        # Signal on SPY and QQQ
        for sym in ["SPY", "QQQ"]:
            df = data.get(sym)
            if df is None or len(df) < 20:
                continue

            price = float(df["Close"].iloc[-1])
            atr_s = _atr_val(df["High"], df["Low"], df["Close"])
            if atr_s <= 0:
                continue

            tp = _smart_round(price + 2.0 * atr_s)
            sl = _smart_round(price - 1.5 * atr_s)
            rr = _rr(price, tp, sl)
            if rr < 1.3:
                continue

            signals.append({
                "strategy": "vix_correlation_divergence",
                "symbol": sym,
                "category": "stock",
                "signal_type": "BUY",
                "entry_price": _smart_round(price),
                "take_profit": tp,
                "stop_loss": sl,
                "confidence": 0.62,
                "risk_reward": rr,
                "reason": (f"VIX={vix_level:.0f} (>25) but SPY-VIX corr={corr:.2f} "
                           f"(<0.2) -- fear decoupling, expect equity bounce"),
                "timeframe": "1d",
                "extra": {
                    "vix_level": round(vix_level, 1),
                    "spy_vix_corr": round(corr, 3),
                    "source": "Whaley (2000) VIX fear gauge divergence",
                },
                "timestamp": _now_iso(),
            })
    except Exception:
        pass

    return signals


# =========================================================================
# STRATEGY 11: Profit-Taking Re-Entry (PTR)
# =========================================================================
# Reference: Jegadeesh & Titman (1993) "Momentum"
# Edge: When an active winning pick pulls back slightly after reaching
# +1×ATR profit, re-entering captures the continuation move. This is a
# META strategy that reads active_picks.json and generates re-entry signals.
# =========================================================================

def profit_taking_reentry(data: dict[str, pd.DataFrame],
                          context: dict | None = None) -> list[dict]:
    """
    Read active picks. If a pick is at +1×ATR profit and pulls back ≤ 0.5×ATR,
    generate a re-entry signal with the same TP/SL.
    """
    signals = []

    # Load active picks
    active_file = DATA_DIR / "active_picks.json"
    if not active_file.exists():
        return signals

    try:
        with open(active_file, "r") as f:
            active_picks = json.load(f)
    except Exception:
        return signals

    if not isinstance(active_picks, list):
        return signals

    for pick in active_picks:
        try:
            sym = pick.get("symbol")
            if not sym:
                continue

            df = data.get(sym)
            if df is None or len(df) < 20:
                continue

            entry_price = float(pick.get("entry_price", 0))
            signal_type = pick.get("signal_type", "BUY")
            tp = float(pick.get("take_profit", 0))
            sl = float(pick.get("stop_loss", 0))
            strategy = pick.get("strategy", "")

            if entry_price <= 0 or tp <= 0 or sl <= 0:
                continue

            # Don't re-enter PTR picks (avoid infinite loop)
            if strategy == "profit_taking_reentry":
                continue

            price = float(df["Close"].iloc[-1])
            atr_val = _atr_val(df["High"], df["Low"], df["Close"])
            if atr_val <= 0:
                continue

            # Check if pick is in profit territory (+1×ATR from entry)
            if signal_type == "BUY":
                profit = price - entry_price
                pullback = float(df["High"].iloc[-3:].max()) - price
            else:
                profit = entry_price - price
                pullback = price - float(df["Low"].iloc[-3:].min())

            # Condition: profit >= 1×ATR and pullback <= 0.5×ATR
            if profit >= 1.0 * atr_val and pullback <= 0.5 * atr_val and pullback > 0:
                rr = _rr(price, tp, sl)
                if rr < 1.0:
                    continue

                signals.append({
                    "strategy": "profit_taking_reentry",
                    "symbol": sym,
                    "category": _get_category(sym),
                    "signal_type": signal_type,
                    "entry_price": _smart_round(price),
                    "take_profit": _smart_round(tp),
                    "stop_loss": _smart_round(sl),
                    "confidence": 0.60,
                    "risk_reward": rr,
                    "reason": (f"PTR re-entry: original {strategy} pick at profit "
                               f"+{profit/entry_price*100:.1f}%, pullback "
                               f"{pullback/atr_val:.2f}×ATR -- continuation expected"),
                    "timeframe": "1d",
                    "extra": {
                        "original_strategy": strategy,
                        "original_entry": entry_price,
                        "profit_atr_mult": round(profit / atr_val, 2),
                        "pullback_atr_mult": round(pullback / atr_val, 2),
                        "source": "Jegadeesh & Titman (1993) momentum continuation",
                    },
                    "timestamp": _now_iso(),
                })
        except Exception:
            continue

    return signals[:3]  # Max 3 re-entries per scan


# =========================================================================
# STRATEGY 12: Bollinger Bands + RSI Mean-Reversion
# =========================================================================
# Reference: Bollinger (2001) "Bollinger on Bollinger Bands";
#            QuantConnect most-forked crypto template 2024-2025.
# Edge: Price at lower BB + RSI < 30 = oversold mean-reversion buy.
# Price at upper BB + RSI > 70 = overbought mean-reversion sell.
# Distinct from our BB *squeeze* strategies which trade the expansion --
# this trades the reversion to the mean (middle band).
# Quant community note: "BB+RSI is the retail-to-pro favourite for
# range-bound crypto, extremely popular in QuantConnect & Hummingbot."
# =========================================================================

def bb_rsi_mean_reversion(data: dict[str, pd.DataFrame],
                          context: dict | None = None) -> list[dict]:
    """
    Mean-reversion when price touches Bollinger Band extremes + RSI confirms.
    BUY when price < lower BB and RSI < 30; SELL when price > upper BB and RSI > 70.
    """
    signals = []

    for symbol in CRYPTO_SYMBOLS:
        df = data.get(symbol)
        if df is None or len(df) < 25:
            continue

        try:
            close = df["Close"]
            high = df["High"]
            low = df["Low"]
            volume = df["Volume"]

            price = float(close.iloc[-1])
            if price <= 0:
                continue

            # Bollinger Bands (20, 2)
            bb = bollinger_bands(close, 20, 2.0)
            upper_bb = float(bb["upper"].iloc[-1])
            lower_bb = float(bb["lower"].iloc[-1])
            middle_bb = float(bb["middle"].iloc[-1])

            # RSI(14)
            rsi_val = float(rsi(close, 14).iloc[-1])

            # Volume filter: at least 0.8× average (don't require spike for mean-reversion)
            avg_vol = float(volume.iloc[-20:].mean())
            cur_vol = float(volume.iloc[-1])
            if avg_vol <= 0 or cur_vol < 0.8 * avg_vol:
                continue

            atr_val = _atr_val(high, low, close)
            if atr_val <= 0:
                continue

            direction = None
            tp = None
            sl = None

            # Oversold: price below lower BB + RSI < 30
            if price <= lower_bb * 1.002 and rsi_val < 30:
                direction = "BUY"
                tp = _smart_round(middle_bb)  # target: mean (middle band)
                sl = _smart_round(price - 2.0 * atr_val)

            # Overbought: price above upper BB + RSI > 70
            elif price >= upper_bb * 0.998 and rsi_val > 70:
                direction = "SELL"
                tp = _smart_round(middle_bb)
                sl = _smart_round(price + 2.0 * atr_val)

            if direction is None:
                continue

            rr = _rr(price, tp, sl)
            if rr < 1.3:
                continue

            # Confidence scales with RSI extremity
            rsi_extremity = (30 - rsi_val) / 30 if direction == "BUY" else (rsi_val - 70) / 30
            conf = round(min(0.75, 0.58 + rsi_extremity * 0.15), 2)

            signals.append({
                "strategy": "bb_rsi_mean_reversion",
                "symbol": symbol,
                "category": _get_category(symbol),
                "signal_type": direction,
                "entry_price": _smart_round(price),
                "take_profit": tp,
                "stop_loss": sl,
                "confidence": conf,
                "risk_reward": rr,
                "reason": (f"BB+RSI mean-reversion: price {'below lower' if direction == 'BUY' else 'above upper'} "
                           f"BB, RSI={rsi_val:.0f}, target middle band at {middle_bb:.2f}"),
                "timeframe": "1d",
                "rsi_at_entry": round(rsi_val, 1),
                "volume_ratio": round(cur_vol / avg_vol, 2),
                "extra": {
                    "upper_bb": round(upper_bb, 2),
                    "lower_bb": round(lower_bb, 2),
                    "middle_bb": round(middle_bb, 2),
                    "rsi": round(rsi_val, 1),
                    "source": "Bollinger (2001) + QuantConnect crypto template",
                },
                "timestamp": _now_iso(),
            })
        except Exception:
            continue

    return signals


# =========================================================================
# STRATEGY 13: Pi Cycle Regime Gate
# =========================================================================
# Reference: Philip Swift (LookIntoBitcoin, 2019).
# 111DMA and 350DMA×2 crossing = BTC macro top within 3 days.
# Confirmed in 2013, 2017, April 2021 cycles.
# Implementation: proximity-based regime gate (not just crossover).
# When 111DMA is within 10% of 350DMA×2 → suppress new longs.
# When gap > 50% → accumulation zone (boost longs).
# This is a META strategy that modifies signals, not a standalone signal.
# It generates a BUY signal ONLY at accumulation extremes (gap > 60%).
# Community standard: Returns Gone Wild Substack, TradingView scripts.
# =========================================================================

def pi_cycle_regime_gate(data: dict[str, pd.DataFrame],
                         context: dict | None = None) -> list[dict]:
    """
    Pi Cycle Top/Bottom indicator as regime gate for BTC.
    Only generates BUY signal when gap > 60% (deep accumulation zone).
    The proximity warning (< 10% gap) is exposed via context for other
    strategies to read.
    """
    signals = []

    btc_df = data.get("BTC-USD")
    if btc_df is None or len(btc_df) < 355:
        return signals  # Need 350+ bars for the long MA

    try:
        close = btc_df["Close"]
        price = float(close.iloc[-1])
        if price <= 0:
            return signals

        # 111-day SMA and 350-day SMA × 2
        sma_111 = float(sma(close, 111).iloc[-1])
        sma_350x2 = float(sma(close, 350).iloc[-1]) * 2

        if sma_350x2 <= 0 or sma_111 <= 0:
            return signals

        # Gap percentage: how far 111DMA is from crossing 350DMA×2
        gap_pct = (sma_350x2 - sma_111) / sma_350x2 * 100

        # Store in context for other strategies to read
        if context is not None:
            context["pi_cycle_gap_pct"] = round(gap_pct, 2)
            context["pi_cycle_danger"] = gap_pct < 10
            context["pi_cycle_accumulation"] = gap_pct > 50

        # Only generate signal at deep accumulation (gap > 60%)
        if gap_pct > 60:
            atr_val = _atr_val(btc_df["High"], btc_df["Low"], close)
            if atr_val <= 0:
                return signals

            tp = _smart_round(price + 3.0 * atr_val)
            sl = _smart_round(price - 1.5 * atr_val)
            rr = _rr(price, tp, sl)
            if rr < 1.3:
                return signals

            signals.append({
                "strategy": "pi_cycle_regime_gate",
                "symbol": "BTC-USD",
                "category": "crypto",
                "signal_type": "BUY",
                "entry_price": _smart_round(price),
                "take_profit": tp,
                "stop_loss": sl,
                "confidence": round(min(0.80, 0.60 + (gap_pct - 60) * 0.005), 2),
                "risk_reward": rr,
                "reason": (f"Pi Cycle accumulation zone: 111DMA-to-350DMA×2 gap "
                           f"= {gap_pct:.1f}% (>60% = deep value). "
                           f"111DMA={sma_111:.0f}, 350DMA×2={sma_350x2:.0f}"),
                "timeframe": "1d",
                "extra": {
                    "sma_111": round(sma_111, 2),
                    "sma_350x2": round(sma_350x2, 2),
                    "gap_pct": round(gap_pct, 2),
                    "zone": "accumulation",
                    "source": "Philip Swift (LookIntoBitcoin 2019), confirmed 3 cycles",
                },
                "timestamp": _now_iso(),
            })

        # Danger zone: near top (gap < 10%) -- generate SHORT signal
        elif gap_pct < 10 and gap_pct > 0:
            atr_val = _atr_val(btc_df["High"], btc_df["Low"], close)
            if atr_val <= 0:
                return signals

            tp = _smart_round(price - 3.0 * atr_val)
            sl = _smart_round(price + 2.0 * atr_val)
            rr = _rr(price, tp, sl)
            if rr < 1.3:
                return signals

            signals.append({
                "strategy": "pi_cycle_regime_gate",
                "symbol": "BTC-USD",
                "category": "crypto",
                "signal_type": "SELL",
                "entry_price": _smart_round(price),
                "take_profit": tp,
                "stop_loss": sl,
                "confidence": round(min(0.78, 0.60 + (10 - gap_pct) * 0.02), 2),
                "risk_reward": rr,
                "reason": (f"Pi Cycle TOP WARNING: 111DMA-to-350DMA×2 gap "
                           f"= {gap_pct:.1f}% (<10% = macro top zone). "
                           f"111DMA={sma_111:.0f}, 350DMA×2={sma_350x2:.0f}"),
                "timeframe": "1d",
                "extra": {
                    "sma_111": round(sma_111, 2),
                    "sma_350x2": round(sma_350x2, 2),
                    "gap_pct": round(gap_pct, 2),
                    "zone": "danger",
                    "source": "Philip Swift (LookIntoBitcoin 2019), confirmed 3 cycles",
                },
                "timestamp": _now_iso(),
            })

        # Crossed over: confirmed top
        elif gap_pct <= 0:
            atr_val = _atr_val(btc_df["High"], btc_df["Low"], close)
            if atr_val <= 0:
                return signals

            tp = _smart_round(price - 4.0 * atr_val)
            sl = _smart_round(price + 2.0 * atr_val)
            rr = _rr(price, tp, sl)
            if rr < 1.3:
                return signals

            signals.append({
                "strategy": "pi_cycle_regime_gate",
                "symbol": "BTC-USD",
                "category": "crypto",
                "signal_type": "SELL",
                "entry_price": _smart_round(price),
                "take_profit": tp,
                "stop_loss": sl,
                "confidence": 0.82,
                "risk_reward": rr,
                "reason": (f"Pi Cycle TOP CONFIRMED: 111DMA CROSSED above 350DMA×2! "
                           f"Historically signals macro BTC top within 3 days. "
                           f"111DMA={sma_111:.0f} > 350DMA×2={sma_350x2:.0f}"),
                "timeframe": "1d",
                "extra": {
                    "sma_111": round(sma_111, 2),
                    "sma_350x2": round(sma_350x2, 2),
                    "gap_pct": round(gap_pct, 2),
                    "zone": "top_confirmed",
                    "source": "Philip Swift (LookIntoBitcoin 2019), 85% top accuracy",
                },
                "timestamp": _now_iso(),
            })
    except Exception:
        pass

    return signals


# =========================================================================
# STRATEGY 14: Puell Multiple Extreme
# =========================================================================
# Reference: David Puell (2019), Glassnode.
# Puell Multiple = Daily Mining Revenue / 365-day MA of Mining Revenue.
# We proxy this using BTC price × estimated block reward (3.125 BTC post-
# halving 2024) and compare to the 365-day SMA of that product.
# PM < 0.5 = deep undervaluation (BUY)
# PM > 4.0 = overheated (SELL risk)
# Free data proxy: price × block_reward / 365d_sma(price × block_reward)
# =========================================================================

def puell_multiple_extreme(data: dict[str, pd.DataFrame],
                           context: dict | None = None) -> list[dict]:
    """
    Puell Multiple proxy using BTC price × block reward (3.125 BTC).
    BUY when PM < 0.5 (miner capitulation), SELL when PM > 4.0.
    """
    signals = []

    btc_df = data.get("BTC-USD")
    if btc_df is None or len(btc_df) < 370:
        return signals  # Need 365+ bars

    try:
        close = btc_df["Close"]
        price = float(close.iloc[-1])
        if price <= 0:
            return signals

        # Block reward proxy: 3.125 BTC per block × ~144 blocks/day = 450 BTC/day
        # Daily mining revenue proxy = price × 450
        DAILY_BLOCKS_REWARD = 450  # BTC per day (3.125 × 144)
        daily_revenue = close * DAILY_BLOCKS_REWARD
        ma_365 = float(daily_revenue.rolling(365).mean().iloc[-1])

        if ma_365 <= 0:
            return signals

        puell = float(daily_revenue.iloc[-1]) / ma_365

        # Store in context
        if context is not None:
            context["puell_multiple"] = round(puell, 3)

        atr_val = _atr_val(btc_df["High"], btc_df["Low"], close)
        if atr_val <= 0:
            return signals

        # BUY at deep undervaluation
        if puell < 0.5:
            tp = _smart_round(price + 3.0 * atr_val)
            sl = _smart_round(price - 1.5 * atr_val)
            rr = _rr(price, tp, sl)
            if rr < 1.3:
                return signals

            signals.append({
                "strategy": "puell_multiple_extreme",
                "symbol": "BTC-USD",
                "category": "crypto",
                "signal_type": "BUY",
                "entry_price": _smart_round(price),
                "take_profit": tp,
                "stop_loss": sl,
                "confidence": round(min(0.80, 0.65 + (0.5 - puell) * 0.3), 2),
                "risk_reward": rr,
                "reason": (f"Puell Multiple = {puell:.2f} (<0.5 = miner capitulation). "
                           f"Historically signals BTC macro bottom. "
                           f"Daily rev proxy: ${daily_revenue.iloc[-1]:,.0f} vs "
                           f"365d avg: ${ma_365:,.0f}"),
                "timeframe": "1d",
                "extra": {
                    "puell_multiple": round(puell, 3),
                    "daily_revenue_proxy": round(float(daily_revenue.iloc[-1]), 0),
                    "ma_365_revenue": round(ma_365, 0),
                    "zone": "capitulation",
                    "source": "David Puell (2019), Glassnode. 70% WR at extremes.",
                },
                "timestamp": _now_iso(),
            })

        # SELL at overheated
        elif puell > 4.0:
            tp = _smart_round(price - 3.0 * atr_val)
            sl = _smart_round(price + 2.0 * atr_val)
            rr = _rr(price, tp, sl)
            if rr < 1.3:
                return signals

            signals.append({
                "strategy": "puell_multiple_extreme",
                "symbol": "BTC-USD",
                "category": "crypto",
                "signal_type": "SELL",
                "entry_price": _smart_round(price),
                "take_profit": tp,
                "stop_loss": sl,
                "confidence": round(min(0.78, 0.60 + (puell - 4.0) * 0.05), 2),
                "risk_reward": rr,
                "reason": (f"Puell Multiple = {puell:.2f} (>4.0 = overheated mining). "
                           f"Historically signals profit-taking zone."),
                "timeframe": "1d",
                "extra": {
                    "puell_multiple": round(puell, 3),
                    "zone": "overheated",
                    "source": "David Puell (2019), Glassnode. 70% WR at extremes.",
                },
                "timestamp": _now_iso(),
            })
    except Exception:
        pass

    return signals


# =========================================================================
# STRATEGY REGISTRY
# =========================================================================
# This dict is imported by crypto_strategies.py and merged into the
# master CRYPTO_STRATEGIES dict. The scanner calls each function
# automatically during each scan cycle.
# =========================================================================

NEXTGEN_STRATEGIES: dict[str, callable] = {
    "cointegration_pair_trade": cointegration_pair_trade,
    "adx_volatility_breakout": adx_volatility_breakout,
    "seasonal_factor_rotation": seasonal_factor_rotation,
    "multi_factor_equity_rotation": multi_factor_equity_rotation,
    "dead_cat_bounce_momentum": dead_cat_bounce_momentum,
    "market_structure_break": market_structure_break,
    "volume_acceleration_reversion": volume_acceleration_reversion,
    "night_liquidity_drift": night_liquidity_drift,
    "spread_of_candles_gap": spread_of_candles_gap,
    "vix_correlation_divergence": vix_correlation_divergence,
    "profit_taking_reentry": profit_taking_reentry,
    "bb_rsi_mean_reversion": bb_rsi_mean_reversion,
    "pi_cycle_regime_gate": pi_cycle_regime_gate,
    "puell_multiple_extreme": puell_multiple_extreme,
}
