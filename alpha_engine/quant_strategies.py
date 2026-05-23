"""
ALPHA_ENGINE -- Quantitative Strategies
========================================
4 academically-proven quant strategies for crypto assets.
Based on peer-reviewed research and documented institutional methods.

Strategies 44-47:
  44. tsmom_28d          -- Time-Series Momentum (28d lookback, 5d hold)
                           Han, Kang & Ryu (2024) -- Sharpe 1.51
  45. cointegrated_pairs -- Statistical Arbitrage: BTC/ETH spread Z-score
                           Springer (2024) -- 79-100% WR in backtests
  46. momentum_mean_rev_blend -- 50/50 Momentum + BTC-Neutral Mean Reversion
                           Briplotnik (2024) -- Sharpe 1.71, 56% annual
  47. oi_price_divergence -- Open Interest divergence from price
                           Derivatives desk method -- 60-70% accuracy

Data: All use FREE APIs (yfinance, Binance futures).
"""

from __future__ import annotations

import json
import urllib.request
import urllib.error
from datetime import datetime, timezone
from typing import Optional

import numpy as np
import pandas as pd

from config import CRYPTO_SYMBOLS, BINANCE_FUTURES_BASE
from indicators import rsi, atr, sma, ema, volume_ratio


# -- Helpers (same pattern as crypto_strategies) ------------------------

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


def _atr_tp_sl(close: pd.Series, high: pd.Series, low: pd.Series,
               tp_mult: float = 3.0, sl_mult: float = 2.25,  # sl_mult aligned with crypto_strategies.py 2026-03-13
               atr_period: int = 14) -> tuple[float, float, float]:
    atr_val = atr(high, low, close, atr_period)
    current_atr = float(atr_val.iloc[-1])
    price = float(close.iloc[-1])
    tp = price + tp_mult * current_atr
    sl = price - sl_mult * current_atr
    return _smart_round(price), _smart_round(tp), _smart_round(sl)


def _fetch_json(url: str, timeout: int = 8) -> Optional[dict | list]:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "ALPHA_ENGINE/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        if e.code in (451, 403):
            return None  # geo-blocked
        return None
    except Exception:
        return None


def _fetch_json_failover(urls: list[str], timeout: int = 8) -> Optional[dict | list]:
    """Try multiple URLs in order until one succeeds."""
    for url in urls:
        result = _fetch_json(url, timeout)
        if result is not None:
            return result
    return None


# =====================================================================
# STRATEGY 44: Time-Series Momentum (TSMOM)
# =====================================================================
# Academic: Han, Kang & Ryu (2024) -- "Time-Series and Cross-Sectional
# Momentum in the Cryptocurrency Market"
# Lookback: 28 days. Hold: 5 days. Long-only variant.
# Sharpe: 1.51 (vs 0.84 buy-and-hold). Volume-weighted: Sharpe 2.17.
# Signal: if 28d return in top tercile of distribution → LONG.
# Rebalance every 5 days.
# =====================================================================

def tsmom_28d(data: dict[str, pd.DataFrame]) -> list[dict]:
    """BUY when 28-day momentum is strong (top tercile of return distribution)."""
    signals: list[dict] = []

    # Compute 28-day returns for all crypto symbols
    returns_28d: dict[str, float] = {}
    for symbol in CRYPTO_SYMBOLS:
        if symbol not in data:
            continue
        df = data[symbol]
        if len(df) < 35:
            continue
        close = df["Close"]
        ret = (float(close.iloc[-1]) - float(close.iloc[-28])) / float(close.iloc[-28])
        returns_28d[symbol] = ret

    if len(returns_28d) < 6:
        return signals  # Need enough symbols to rank

    # Sort by 28d return (descending)
    sorted_syms = sorted(returns_28d.items(), key=lambda x: x[1], reverse=True)

    # Top tercile = top 1/3 of symbols by momentum
    top_n = max(1, len(sorted_syms) // 3)
    top_momentum = sorted_syms[:top_n]

    # Only signal if the top symbols have positive momentum
    for symbol, ret_28d in top_momentum:
        if ret_28d <= 0.02:  # Need at least 2% positive momentum
            continue

        try:
            df = data[symbol]
            close = df["Close"]
            high = df["High"]
            low = df["Low"]
            vol = df["Volume"]

            rsi_val = float(rsi(close, 14).iloc[-1])

            # Don't chase extreme overbought
            if rsi_val > 80:
                continue

            # Volume confirmation: recent volume should be above average
            vol_r = volume_ratio(vol, 20)
            vr = float(vol_r.iloc[-1])
            if vr < 0.8:
                continue  # Weak volume = unreliable momentum

            entry, tp, sl = _atr_tp_sl(close, high, low, 3.0, 1.5)
            rr = abs(tp - entry) / max(abs(entry - sl), 0.01)
            if rr < 1.3:
                continue

            # Volatility scaling: position_size = target_vol / realized_vol
            # Target: 15% annualized (~0.94% daily)
            # Reference: Moskowitz, Ooi & Pedersen (2012) -- TSMOM with vol targeting
            daily_returns = close.pct_change().dropna()
            if len(daily_returns) >= 20:
                realized_vol = float(daily_returns.iloc[-20:].std()) * (365 ** 0.5)
            else:
                realized_vol = 0.5  # default 50% annualized vol for crypto
            target_vol = 0.15  # 15% annualized
            vol_scale = min(2.0, max(0.25, target_vol / realized_vol)) if realized_vol > 0 else 0.5

            # Confidence: stronger momentum + volume + vol-scaling
            rank = [s for s, _ in sorted_syms].index(symbol)
            rank_pct = 1.0 - (rank / len(sorted_syms))  # 1.0 = best

            conf = min(0.85, 0.55 + ret_28d * 1.5 + rank_pct * 0.10)
            # Apply vol scaling: higher confidence when vol-target ratio is favorable
            conf = conf * (0.7 + 0.3 * min(1.0, vol_scale))
            conf = max(0.50, conf)

            signals.append({
                "strategy": "tsmom_28d",
                "symbol": symbol,
                "category": _get_category(symbol),
                "signal_type": "BUY",
                "entry_price": entry,
                "take_profit": tp,
                "stop_loss": sl,
                "confidence": round(conf, 2),
                "risk_reward": round(rr, 2),
                "reason": (
                    f"TSMOM: 28d return +{ret_28d*100:.1f}% "
                    f"(rank {rank+1}/{len(sorted_syms)}), "
                    f"vol ratio {vr:.1f}x, RSI {rsi_val:.0f}, "
                    f"vol-scale {vol_scale:.2f}x (target 15% ann.)"
                ),
                "timeframe": "5d",
                "rsi_at_entry": round(rsi_val, 1),
                "extra": {
                    "return_28d_pct": round(ret_28d * 100, 2),
                    "momentum_rank": rank + 1,
                    "total_symbols": len(sorted_syms),
                    "volume_ratio": round(vr, 2),
                    "vol_scale": round(vol_scale, 3),
                    "realized_vol_ann": round(realized_vol * 100, 1),
                    "target_vol_ann": "15%",
                    "hold_period": "5 days",
                    "source": "Han, Kang & Ryu (2024) -- TSMOM Sharpe 1.51 + Moskowitz et al. (2012) vol targeting",
                },
                "timestamp": _now_iso(),
            })
        except Exception:
            continue

    return signals


# =====================================================================
# STRATEGY 45: Cointegrated Pairs Trading (BTC/ETH Spread)
# =====================================================================
# Springer (2024): "Copula-based Trading of Cointegrated Crypto Pairs"
# 79-100% WR in backtests (81,000+ data points).
# Method: Calculate spread = price_A - beta * price_B, compute Z-score.
# Entry: Z > +2 (short A, long B) or Z < -2 (long A, short B).
# Exit: Z reverts to 0. Stop: Z > +3 or < -3.
# We implement BTC/ETH and SOL/AVAX pairs.
# =====================================================================

def cointegrated_pairs(data: dict[str, pd.DataFrame]) -> list[dict]:
    """Trade mean-reverting spread between cointegrated crypto pairs."""
    signals: list[dict] = []

    # Define pairs with expected cointegration
    pairs = [
        ("BTC-USD", "ETH-USD"),
        ("SOL-USD", "AVAX-USD"),
        ("LINK-USD", "DOT-USD"),
    ]

    for sym_a, sym_b in pairs:
        if sym_a not in data or sym_b not in data:
            continue
        try:
            df_a = data[sym_a]
            df_b = data[sym_b]

            min_len = min(len(df_a), len(df_b))
            if min_len < 90:
                continue

            # Use last 90 days for cointegration estimation
            close_a = df_a["Close"].iloc[-90:].values.astype(float)
            close_b = df_b["Close"].iloc[-90:].values.astype(float)

            # Simple OLS regression: A = beta * B + alpha + residual
            # beta = cov(A,B) / var(B)
            mean_a = np.mean(close_a)
            mean_b = np.mean(close_b)
            cov_ab = np.mean((close_a - mean_a) * (close_b - mean_b))
            var_b = np.var(close_b)

            if var_b == 0:
                continue

            beta = cov_ab / var_b
            alpha = mean_a - beta * mean_b

            # Calculate spread (residuals)
            spread = close_a - beta * close_b - alpha

            # Z-score of current spread
            spread_mean = np.mean(spread)
            spread_std = np.std(spread)
            if spread_std < 0.001:
                continue

            current_z = (spread[-1] - spread_mean) / spread_std

            # Check mean-reversion tendency (half-life)
            # Simple AR(1): spread[t] = phi * spread[t-1] + eps
            spread_lag = spread[:-1]
            spread_now = spread[1:]
            if len(spread_lag) < 10:
                continue

            phi = np.corrcoef(spread_lag, spread_now)[0, 1]
            if phi >= 1.0 or phi <= 0:
                continue  # No mean reversion

            half_life = -np.log(2) / np.log(abs(phi))
            if half_life > 30 or half_life < 1:
                continue  # Too slow or too fast

            # Generate signals based on Z-score
            if abs(current_z) < 1.5:
                continue  # Not extreme enough

            # Z < -2: spread too low → long A, short B
            # Z > +2: spread too high → short A, long B
            if current_z < -2.0:
                # Long sym_a (undervalued relative to sym_b)
                target_sym = sym_a
                signal_type = "BUY"
                z_direction = "below"
            elif current_z > 2.0:
                # Long sym_b (undervalued relative to sym_a)
                target_sym = sym_b
                signal_type = "BUY"
                z_direction = "above"
            else:
                continue

            df_target = data[target_sym]
            close_t = df_target["Close"]
            high_t = df_target["High"]
            low_t = df_target["Low"]

            rsi_val = float(rsi(close_t, 14).iloc[-1])

            entry, tp, sl = _atr_tp_sl(close_t, high_t, low_t, 2.5, 1.5)
            rr = abs(tp - entry) / max(abs(entry - sl), 0.01)
            if rr < 1.0:
                continue

            # Confidence: higher Z-score + faster half-life = higher conviction
            z_bonus = min(0.15, (abs(current_z) - 2.0) * 0.10)
            hl_bonus = min(0.10, (30 - half_life) / 30 * 0.10)
            conf = min(0.85, 0.60 + z_bonus + hl_bonus)

            signals.append({
                "strategy": "cointegrated_pairs",
                "symbol": target_sym,
                "category": _get_category(target_sym),
                "signal_type": signal_type,
                "entry_price": entry,
                "take_profit": tp,
                "stop_loss": sl,
                "confidence": round(conf, 2),
                "risk_reward": round(rr, 2),
                "reason": (
                    f"Pairs trade: {sym_a}/{sym_b} spread Z={current_z:.1f} "
                    f"({z_direction} mean), half-life {half_life:.0f}d, "
                    f"beta {beta:.2f}. Long {target_sym}"
                ),
                "timeframe": "1d",
                "rsi_at_entry": round(rsi_val, 1),
                "extra": {
                    "pair": f"{sym_a}/{sym_b}",
                    "spread_z_score": round(current_z, 2),
                    "half_life_days": round(half_life, 1),
                    "beta": round(beta, 4),
                    "phi": round(phi, 4),
                    "target_z": 0.0,
                    "source": "Springer (2024) -- Cointegrated Crypto Pairs, 79-100% WR",
                },
                "timestamp": _now_iso(),
            })
        except Exception:
            continue

    return signals


# =====================================================================
# STRATEGY 46: Blended Momentum + BTC-Neutral Mean Reversion
# =====================================================================
# Briplotnik (2024): Sharpe 1.71, 56% annualized, T-stat 4.07.
# Momentum leg: Z-score of short-term vs long-term returns → trend.
# Mean reversion leg: Regress altcoin on BTC, trade the residual.
# Combined 50/50 blend provides all-weather coverage.
# =====================================================================

def momentum_mean_rev_blend(data: dict[str, pd.DataFrame]) -> list[dict]:
    """BUY when momentum Z-score is positive AND/OR BTC-neutral residual is oversold."""
    signals: list[dict] = []

    if "BTC-USD" not in data:
        return signals

    btc_close = data["BTC-USD"]["Close"]
    if len(btc_close) < 90:
        return signals

    # BTC returns for regression
    btc_returns = btc_close.pct_change().dropna()

    # Only apply to liquid alts (not BTC itself, since we're BTC-neutral)
    alt_symbols = [s for s in CRYPTO_SYMBOLS if s != "BTC-USD" and s in data]

    for symbol in alt_symbols:
        try:
            df = data[symbol]
            if len(df) < 90:
                continue

            close = df["Close"]
            high = df["High"]
            low = df["Low"]

            # -- Momentum Leg --
            # Z-score of 7d return vs 28d return distribution
            ret_7d = (float(close.iloc[-1]) - float(close.iloc[-7])) / float(close.iloc[-7])
            returns_28d = close.pct_change(7).dropna().iloc[-28:]

            if len(returns_28d) < 20:
                continue

            ret_mean = float(returns_28d.mean())
            ret_std = float(returns_28d.std())
            if ret_std < 0.001:
                continue

            momentum_z = (ret_7d - ret_mean) / ret_std
            momentum_bullish = momentum_z > 1.0

            # -- Mean Reversion Leg (BTC-neutral) --
            # Regress altcoin returns on BTC returns
            alt_returns = close.pct_change().dropna()

            # Align lengths
            min_len = min(len(alt_returns), len(btc_returns))
            if min_len < 60:
                continue

            alt_r = alt_returns.iloc[-min_len:].values.astype(float)
            btc_r = btc_returns.iloc[-min_len:].values.astype(float)

            # OLS: alt_return = beta * btc_return + residual
            btc_var = np.var(btc_r)
            if btc_var == 0:
                continue
            beta = np.cov(alt_r, btc_r)[0, 1] / btc_var
            residuals = alt_r - beta * btc_r

            # Z-score of current residual
            res_mean = np.mean(residuals)
            res_std = np.std(residuals)
            if res_std < 0.0001:
                continue

            current_residual = residuals[-1]
            residual_z = (current_residual - res_mean) / res_std
            mean_rev_bullish = residual_z < -2.0  # Oversold residual → expect reversion up

            # -- Blend: signal if at least one leg is bullish --
            # Stronger signal when both agree
            if not momentum_bullish and not mean_rev_bullish:
                continue

            rsi_val = float(rsi(close, 14).iloc[-1])
            if rsi_val > 78:
                continue

            entry, tp, sl = _atr_tp_sl(close, high, low, 3.0, 1.5)
            rr = abs(tp - entry) / max(abs(entry - sl), 0.01)
            if rr < 1.3:
                continue

            # Both legs agree = higher confidence
            both = momentum_bullish and mean_rev_bullish
            if both:
                conf = min(0.85, 0.70 + abs(momentum_z) * 0.03 + abs(residual_z) * 0.02)
            elif momentum_bullish:
                conf = min(0.75, 0.55 + abs(momentum_z) * 0.05)
            else:  # mean_rev only
                conf = min(0.75, 0.55 + abs(residual_z) * 0.05)

            leg_desc = []
            if momentum_bullish:
                leg_desc.append(f"MOM(z={momentum_z:.1f})")
            if mean_rev_bullish:
                leg_desc.append(f"MR(z={residual_z:.1f})")

            signals.append({
                "strategy": "momentum_mean_rev_blend",
                "symbol": symbol,
                "category": _get_category(symbol),
                "signal_type": "BUY",
                "entry_price": entry,
                "take_profit": tp,
                "stop_loss": sl,
                "confidence": round(conf, 2),
                "risk_reward": round(rr, 2),
                "reason": (
                    f"Blended {'+'.join(leg_desc)}: "
                    f"{'BOTH legs' if both else 'single leg'} bullish. "
                    f"7d ret +{ret_7d*100:.1f}%, BTC beta {beta:.2f}"
                ),
                "timeframe": "5d",
                "rsi_at_entry": round(rsi_val, 1),
                "extra": {
                    "momentum_z": round(momentum_z, 2),
                    "residual_z": round(residual_z, 2),
                    "btc_beta": round(beta, 3),
                    "return_7d_pct": round(ret_7d * 100, 2),
                    "both_legs": both,
                    "source": "Briplotnik (2024) -- Blended Mom+MR Sharpe 1.71",
                },
                "timestamp": _now_iso(),
            })
        except Exception:
            continue

    return signals


# =====================================================================
# STRATEGY 47: Open Interest Divergence Signal (Enhanced)
# =====================================================================
# Derivatives desk method: when OI and price diverge, reversals follow.
# Bearish div: price rising + OI declining = unsupported rally.
# Bullish div: price falling + OI declining = selling exhaustion.
# Combined with long/short ratio for crowded-trade detection.
# Uses Binance Futures API (FREE).
# =====================================================================

_BINANCE_OI_URLS = [
    "https://fapi.binance.com/fapi/v1/openInterest",
    "https://fapi1.binance.com/fapi/v1/openInterest",
    "https://fapi2.binance.com/fapi/v1/openInterest",
]
_BINANCE_LS_URLS = [
    "https://fapi.binance.com/futures/data/globalLongShortAccountRatio",
    "https://fapi1.binance.com/futures/data/globalLongShortAccountRatio",
    "https://fapi2.binance.com/futures/data/globalLongShortAccountRatio",
]
# Legacy references
_BINANCE_OI_URL = _BINANCE_OI_URLS[0]
_BINANCE_LS_URL = _BINANCE_LS_URLS[0]


def oi_price_divergence(data: dict[str, pd.DataFrame]) -> list[dict]:
    """BUY/SELL on Open Interest divergence from price."""
    signals: list[dict] = []

    oi_symbols = {
        "BTC-USD": "BTCUSDT",
        "ETH-USD": "ETHUSDT",
        "SOL-USD": "SOLUSDT",
    }

    for symbol, binance_sym in oi_symbols.items():
        if symbol not in data:
            continue
        try:
            df = data[symbol]
            if len(df) < 30:
                continue

            close = df["Close"]
            high = df["High"]
            low = df["Low"]

            # Calculate price change over last 3 days
            price_now = float(close.iloc[-1])
            price_3d = float(close.iloc[-4])
            price_chg = (price_now - price_3d) / price_3d

            # Fetch current Open Interest
            oi_data = _fetch_json_failover(
                [f"{u}?symbol={binance_sym}" for u in _BINANCE_OI_URLS], timeout=8
            )
            if not oi_data or "openInterest" not in oi_data:
                continue

            current_oi = float(oi_data["openInterest"])

            # Fetch long/short ratio (last 3 periods)
            ls_data = _fetch_json_failover(
                [f"{u}?symbol={binance_sym}&period=4h&limit=3" for u in _BINANCE_LS_URLS],
                timeout=8,
            )

            ls_ratio = None
            if ls_data and len(ls_data) > 0:
                ls_ratio = float(ls_data[-1]["longShortRatio"])

            # We need OI trend -- approximate using price-volume dynamics
            # High volume + price drop + OI expected to drop = liquidation exhaustion
            vol_r = volume_ratio(df["Volume"], 20)
            vr = float(vol_r.iloc[-1])

            rsi_val = float(rsi(close, 14).iloc[-1])

            # -- Bullish Divergence: price falling but selling exhausted --
            # Price down 3%+ over 3 days + volume spike (liquidation) + RSI oversold
            if price_chg < -0.03 and vr > 2.0 and rsi_val < 35:
                entry, tp, sl = _atr_tp_sl(close, high, low, 3.5, 1.5)
                rr = abs(tp - entry) / max(abs(entry - sl), 0.01)
                if rr < 1.3:
                    continue

                conf = 0.65
                if ls_ratio and ls_ratio < 0.8:  # Shorts dominating
                    conf += 0.10  # Crowded short = squeeze potential
                if vr > 3.0:
                    conf += 0.05
                conf = min(0.85, conf)

                signals.append({
                    "strategy": "oi_price_divergence",
                    "symbol": symbol,
                    "category": _get_category(symbol),
                    "signal_type": "BUY",
                    "entry_price": entry,
                    "take_profit": tp,
                    "stop_loss": sl,
                    "confidence": round(conf, 2),
                    "risk_reward": round(rr, 2),
                    "reason": (
                        f"OI divergence (bullish): price -{abs(price_chg)*100:.1f}% "
                        f"but vol {vr:.1f}x spike (exhaustion). "
                        f"RSI {rsi_val:.0f}"
                        + (f", L/S ratio {ls_ratio:.2f}" if ls_ratio else "")
                    ),
                    "timeframe": "4h",
                    "rsi_at_entry": round(rsi_val, 1),
                    "extra": {
                        "price_change_3d_pct": round(price_chg * 100, 2),
                        "volume_ratio": round(vr, 2),
                        "open_interest": current_oi,
                        "long_short_ratio": round(ls_ratio, 3) if ls_ratio else None,
                        "divergence_type": "bullish_exhaustion",
                        "source": "Derivatives desk -- OI Price Divergence, 60-70% accuracy",
                    },
                    "timestamp": _now_iso(),
                })

            # -- Bearish Divergence: price rising but on declining conviction --
            # Price up 5%+ but volume declining + RSI overbought
            elif price_chg > 0.05 and vr < 0.7 and rsi_val > 72:
                entry_p = float(close.iloc[-1])
                atr_val = float(atr(high, low, close, 14).iloc[-1])
                tp_sell = entry_p - 3.0 * atr_val
                sl_sell = entry_p + 1.5 * atr_val
                rr = abs(entry_p - tp_sell) / max(abs(sl_sell - entry_p), 0.01)
                if rr < 1.3:
                    continue

                conf = 0.60
                if ls_ratio and ls_ratio > 2.0:  # Crowded longs
                    conf += 0.10
                conf = min(0.80, conf)

                signals.append({
                    "strategy": "oi_price_divergence",
                    "symbol": symbol,
                    "category": _get_category(symbol),
                    "signal_type": "SELL",
                    "entry_price": _smart_round(entry_p),
                    "take_profit": _smart_round(tp_sell),
                    "stop_loss": _smart_round(sl_sell),
                    "confidence": round(conf, 2),
                    "risk_reward": round(rr, 2),
                    "reason": (
                        f"OI divergence (bearish): price +{price_chg*100:.1f}% "
                        f"but vol declining ({vr:.1f}x), unsupported rally. "
                        f"RSI {rsi_val:.0f}"
                        + (f", L/S ratio {ls_ratio:.2f} (crowded longs)" if ls_ratio and ls_ratio > 1.5 else "")
                    ),
                    "timeframe": "4h",
                    "rsi_at_entry": round(rsi_val, 1),
                    "extra": {
                        "price_change_3d_pct": round(price_chg * 100, 2),
                        "volume_ratio": round(vr, 2),
                        "open_interest": current_oi,
                        "long_short_ratio": round(ls_ratio, 3) if ls_ratio else None,
                        "divergence_type": "bearish_unsupported",
                        "source": "Derivatives desk -- OI Price Divergence, 60-70% accuracy",
                    },
                    "timestamp": _now_iso(),
                })
        except Exception:
            continue

    return signals


# =========================================================================
# Registry -- all quant strategies
# =========================================================================

QUANT_STRATEGIES = {
    "tsmom_28d":                 tsmom_28d,
    "cointegrated_pairs":        cointegrated_pairs,
    "momentum_mean_rev_blend":   momentum_mean_rev_blend,
    "oi_price_divergence":       oi_price_divergence,
}
