"""
ALPHA_ENGINE -- Untapped Strategies (Wave 15)
=====================================================
8 research-backed strategies from academic literature.

Strategies:
  1. hurst_exponent_pairs        -- R/S Hurst on crypto pair spreads (mean-reversion)
  2. max_pain_gravitational       -- Options max pain convergence (BTC, ETH)
  3. put_call_ratio_contrarian    -- PCR proxy contrarian (equities + crypto)
  4. google_trends_contrarian     -- Capitulation proxy via RSI + F&G + volume
  5. copper_gold_btc_cycle        -- Copper/Gold ratio RSI as BTC macro cycle proxy
  6. btc_options_expiry_anomaly   -- Weekly/monthly options expiry calendar anomaly
  7. turn_of_month_enhanced       -- Enhanced TOM with RSI + volume + VIX filters
  8. vix_term_structure_signal    -- VIX spike/crush contrarian + crypto overlay

References:
  - Hurst pairs: Guillen et al. (2024) MDPI, Sharpe ~1.0
  - Max pain: Quantpedia, KuCoin Research
  - PCR contrarian: QuantifiedStrategies, 77% 2-week WR
  - Trends contrarian: Zelieska et al. (2024) SSRN
  - Copper/Gold: ainvest.com Jan 2026
  - Options expiry: Quantpedia confirmed anomaly
  - Turn of month: Quantpedia, 60yr backtest, CAGR 7.11%
  - VIX term structure: Quantpedia, PMC 2024

Data sources (all FREE, CI-safe):
  - Binance public klines, CoinGecko, alternative.me (crypto)
  - yfinance (HG=F copper, GC=F gold, ^VIX, SPY, QQQ, BTC-USD, ETH-USD)
  - Calendar logic via datetime stdlib
"""


from __future__ import annotations

import json
import math
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta
from typing import Optional
from itertools import combinations

import numpy as np
import pandas as pd
import yfinance as yf

from config import (
    ALL_SYMBOLS, CRYPTO_SYMBOLS, EQUITY_SYMBOLS, CATEGORY_RISK,
    BINANCE_BASE, FEAR_GREED_URL,
)
from indicators import rsi, sma, ema, atr, bollinger_bands, zscore, volume_ratio


# -- Helpers ----------------------------------------------------------------

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _get_category(symbol: str) -> str:
    info = ALL_SYMBOLS.get(symbol, {})
    cat = info.get("cat", "crypto")
    if info.get("tier") == "meme":
        return "meme"
    return cat


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


def _fetch_json(url: str, timeout: int = 8) -> Optional[dict | list]:
    """Fetch JSON from URL with timeout. Returns None on any failure."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "ALPHA_ENGINE/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read())
    except Exception:
        return None


def _rolling_hurst(series: pd.Series, window: int = 100, max_lag: int = 20) -> pd.Series:
    """
    Rolling Hurst exponent using R/S (rescaled range) analysis.
    H < 0.5 = anti-persistent (mean-reverting)
    H > 0.5 = persistent (trending)
    H ~ 0.5 = random walk
    """
    result = pd.Series(np.nan, index=series.index)
    values = series.values

    for i in range(window, len(values)):
        segment = values[i - window:i]
        if np.any(np.isnan(segment)):
            continue

        lags = range(2, min(max_lag + 1, window // 2))
        log_rs = []
        log_n = []

        for lag in lags:
            subseries_count = window // lag
            if subseries_count < 1:
                continue

            rs_values = []
            for k in range(subseries_count):
                sub = segment[k * lag:(k + 1) * lag]
                mean_sub = np.mean(sub)
                deviations = np.cumsum(sub - mean_sub)
                r = np.max(deviations) - np.min(deviations)
                s = np.std(sub, ddof=1) if len(sub) > 1 else 1e-10
                if s > 1e-10:
                    rs_values.append(r / s)

            if rs_values:
                log_rs.append(np.log(np.mean(rs_values)))
                log_n.append(np.log(lag))

        if len(log_rs) >= 3:
            try:
                poly = np.polyfit(log_n, log_rs, 1)
                result.iloc[i] = poly[0]
            except (np.linalg.LinAlgError, ValueError):
                pass

    return result


def _fetch_fear_greed() -> Optional[int]:
    """Fetch current Fear & Greed index value (0-100)."""
    data = _fetch_json(f"{FEAR_GREED_URL}?limit=1")
    if data and "data" in data and len(data["data"]) > 0:
        try:
            return int(data["data"][0]["value"])
        except (KeyError, ValueError, TypeError):
            pass
    return None


def _fetch_fear_greed_history(days: int = 7) -> Optional[list[int]]:
    """Fetch last N days of Fear & Greed values."""
    data = _fetch_json(f"{FEAR_GREED_URL}?limit={days}")
    if data and "data" in data:
        try:
            return [int(d["value"]) for d in data["data"]]
        except (KeyError, ValueError, TypeError):
            pass
    return None


def _pct_tp_sl(price: float, direction: str,
               tp_pct: float, sl_pct: float) -> tuple[float, float, float]:
    """Fixed-percentage TP/SL. Returns (entry, tp, sl)."""
    if direction == "BUY":
        tp = price * (1.0 + tp_pct)
        sl = price * (1.0 - sl_pct)
    else:
        tp = price * (1.0 - tp_pct)
        sl = price * (1.0 + sl_pct)
    return _smart_round(price), _smart_round(tp), _smart_round(sl)


def _fetch_yf_inline(ticker: str, period: str = "6mo") -> Optional[pd.DataFrame]:
    """Fetch a symbol via yfinance inline if not in data dict. Returns None on failure."""
    try:
        df = yf.download(ticker, period=period, interval="1d",
                         progress=False, auto_adjust=True)
        if df is not None and len(df) > 20:
            return df
    except Exception:
        pass
    return None


# =====================================================================
# STRATEGY 1: Hurst Exponent Pairs Trading (Crypto)
# =====================================================================
# Compute rolling Hurst exponent on log-spread of crypto pairs.
# When Hurst < 0.45 (anti-persistent), the spread is mean-reverting
# and we trade the z-score of the spread.
# Reference: Guillen et al. (2024) MDPI, Sharpe ~1.0
# =====================================================================

def hurst_exponent_pairs(data: dict[str, pd.DataFrame],
                         context: Optional[dict] = None) -> list[dict]:
    """Pairs trading on crypto spreads with Hurst exponent filter."""
    signals: list[dict] = []

    # Select top 10 most liquid crypto symbols that have data
    major_cryptos = [
        "BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD", "XRP-USD",
        "ADA-USD", "AVAX-USD", "LINK-USD", "DOT-USD", "NEAR-USD",
    ]
    available = [s for s in major_cryptos if s in data and len(data[s]) >= 120]

    if len(available) < 2:
        return signals

    # Compute log prices
    log_prices: dict[str, pd.Series] = {}
    for sym in available:
        df = data[sym]
        close = df["Close"]
        if close.iloc[-1] > 0:
            log_prices[sym] = np.log(close)

    if len(log_prices) < 2:
        return signals

    # Evaluate all pair combinations
    for sym_a, sym_b in combinations(sorted(log_prices.keys()), 2):
        try:
            lp_a = log_prices[sym_a]
            lp_b = log_prices[sym_b]

            # Align on common index
            common_idx = lp_a.index.intersection(lp_b.index)
            if len(common_idx) < 120:
                continue

            lp_a_aligned = lp_a.loc[common_idx]
            lp_b_aligned = lp_b.loc[common_idx]

            # Compute spread = log(A) - log(B)
            spread = lp_a_aligned - lp_b_aligned

            # Rolling Hurst on the spread
            hurst = _rolling_hurst(spread, window=100, max_lag=20)
            current_hurst = hurst.iloc[-1]
            if np.isnan(current_hurst) or current_hurst >= 0.45:
                continue  # Not mean-reverting enough

            # Z-score of spread (60-day lookback)
            spread_z = zscore(spread, 60)
            current_z = float(spread_z.iloc[-1])
            if np.isnan(current_z):
                continue

            # Entry conditions
            if abs(current_z) < 2.0:
                continue  # Not far enough from mean

            df_a = data[sym_a]
            df_b = data[sym_b]
            price_a = float(df_a["Close"].iloc[-1])
            price_b = float(df_b["Close"].iloc[-1])
            name_a = CRYPTO_SYMBOLS.get(sym_a, {}).get("name", sym_a)
            name_b = CRYPTO_SYMBOLS.get(sym_b, {}).get("name", sym_b)

            confidence = min(0.85, 0.55 + (abs(current_z) - 2.0) * 0.1
                             + (0.45 - current_hurst) * 0.5)

            if current_z > 2.0:
                # Spread too high: A overvalued relative to B
                # SELL A, BUY B
                sl_a, tp_a, sl_b, tp_b = (
                    _smart_round(price_a * 1.035),  # SL for short A (spread z>3.5)
                    _smart_round(price_a * 0.985),  # TP when z returns to 0.5
                    _smart_round(price_b * 0.965),  # SL for long B
                    _smart_round(price_b * 1.015),  # TP for long B
                )
                signals.append({
                    "symbol": sym_a,
                    "direction": "SELL",
                    "strategy": "hurst_exponent_pairs",
                    "confidence": round(confidence, 2),
                    "entry_price": _smart_round(price_a),
                    "tp_price": tp_a,
                    "sl_price": sl_a,
                    "reason": (f"Hurst pairs: {name_a}/{name_b} spread z={current_z:.2f}, "
                               f"H={current_hurst:.3f} (mean-reverting). "
                               f"{name_a} overvalued vs {name_b}. "
                               f"Ref: Guillen et al. (2024) MDPI"),
                    "generated_at": _now_iso(),
                    "max_hold_days": 14,
                    "pair_leg": f"SHORT {sym_a} / LONG {sym_b}",
                })
                signals.append({
                    "symbol": sym_b,
                    "direction": "BUY",
                    "strategy": "hurst_exponent_pairs",
                    "confidence": round(confidence, 2),
                    "entry_price": _smart_round(price_b),
                    "tp_price": tp_b,
                    "sl_price": sl_b,
                    "reason": (f"Hurst pairs: {name_b}/{name_a} spread z={current_z:.2f}, "
                               f"H={current_hurst:.3f} (mean-reverting). "
                               f"{name_b} undervalued vs {name_a}. "
                               f"Ref: Guillen et al. (2024) MDPI"),
                    "generated_at": _now_iso(),
                    "max_hold_days": 14,
                    "pair_leg": f"LONG {sym_b} / SHORT {sym_a}",
                })

            elif current_z < -2.0:
                # Spread too low: B overvalued relative to A
                # BUY A, SELL B
                sl_a, tp_a, sl_b, tp_b = (
                    _smart_round(price_a * 0.965),
                    _smart_round(price_a * 1.015),
                    _smart_round(price_b * 1.035),
                    _smart_round(price_b * 0.985),
                )
                signals.append({
                    "symbol": sym_a,
                    "direction": "BUY",
                    "strategy": "hurst_exponent_pairs",
                    "confidence": round(confidence, 2),
                    "entry_price": _smart_round(price_a),
                    "tp_price": tp_a,
                    "sl_price": sl_a,
                    "reason": (f"Hurst pairs: {name_a}/{name_b} spread z={current_z:.2f}, "
                               f"H={current_hurst:.3f} (mean-reverting). "
                               f"{name_a} undervalued vs {name_b}. "
                               f"Ref: Guillen et al. (2024) MDPI"),
                    "generated_at": _now_iso(),
                    "max_hold_days": 14,
                    "pair_leg": f"LONG {sym_a} / SHORT {sym_b}",
                })
                signals.append({
                    "symbol": sym_b,
                    "direction": "SELL",
                    "strategy": "hurst_exponent_pairs",
                    "confidence": round(confidence, 2),
                    "entry_price": _smart_round(price_b),
                    "tp_price": tp_b,
                    "sl_price": sl_b,
                    "reason": (f"Hurst pairs: {name_b}/{name_a} spread z={current_z:.2f}, "
                               f"H={current_hurst:.3f} (mean-reverting). "
                               f"{name_b} overvalued vs {name_a}. "
                               f"Ref: Guillen et al. (2024) MDPI"),
                    "generated_at": _now_iso(),
                    "max_hold_days": 14,
                    "pair_leg": f"SHORT {sym_b} / LONG {sym_a}",
                })

        except Exception:
            continue

    return signals


# =====================================================================
# STRATEGY 2: Max Pain Gravitational (Crypto - BTC, ETH)
# =====================================================================
# Fetch Deribit options open interest to find the max pain strike.
# Price gravitates toward max pain near expiry (Friday 08:00 UTC).
# BUY if spot > 3% below max pain within 48h of expiry.
# SELL if spot > 3% above max pain within 48h of expiry.
# Reference: Quantpedia, KuCoin Research
# =====================================================================

def max_pain_gravitational(data: dict[str, pd.DataFrame],
                           context: Optional[dict] = None) -> list[dict]:
    """Trade crypto price convergence toward options max pain near expiry."""
    signals: list[dict] = []
    # BTC/ETH ONLY: Deribit options API only supports BTC and ETH currencies.
    # SOL options exist but with thin liquidity -- max pain less meaningful.
    target_map = {"BTC-USD": "BTC", "ETH-USD": "ETH"}

    now = datetime.now(timezone.utc)

    # Check if within 48h of a Friday 08:00 UTC expiry
    # Find next Friday 08:00 UTC
    days_until_friday = (4 - now.weekday()) % 7  # 4 = Friday
    if days_until_friday == 0 and now.hour >= 8:
        days_until_friday = 7
    next_expiry = now.replace(hour=8, minute=0, second=0, microsecond=0) + timedelta(days=days_until_friday)
    hours_to_expiry = (next_expiry - now).total_seconds() / 3600.0

    if hours_to_expiry > 48:
        return signals  # Too far from expiry, no gravitational pull yet

    for symbol, currency in target_map.items():
        if symbol not in data or len(data[symbol]) < 14:
            continue

        try:
            df = data[symbol]
            spot_price = float(df["Close"].iloc[-1])

            # Fetch Deribit options book summary to find max pain
            url = (f"https://www.deribit.com/api/v2/public/"
                   f"get_book_summary_by_currency?currency={currency}&kind=option")
            api_data = _fetch_json(url, timeout=10)

            if not api_data or "result" not in api_data:
                continue  # API failed, skip (no fake signals)

            # Parse open interest by strike to find max pain
            # Max pain = strike where total OI-weighted losses for option holders is maximized
            strike_oi: dict[float, dict[str, float]] = {}

            for instrument in api_data["result"]:
                inst_name = instrument.get("instrument_name", "")
                oi = instrument.get("open_interest", 0)
                if oi <= 0:
                    continue

                # Parse instrument name: BTC-28FEB26-90000-C or BTC-28FEB26-90000-P
                parts = inst_name.split("-")
                if len(parts) < 4:
                    continue

                try:
                    strike = float(parts[2])
                    opt_type = parts[3]  # C or P
                except (ValueError, IndexError):
                    continue

                if strike not in strike_oi:
                    strike_oi[strike] = {"call_oi": 0.0, "put_oi": 0.0}

                if opt_type == "C":
                    strike_oi[strike]["call_oi"] += oi
                elif opt_type == "P":
                    strike_oi[strike]["put_oi"] += oi

            if not strike_oi:
                continue

            # Calculate max pain: the strike that minimizes total payout
            # At each candidate strike, sum up intrinsic value * OI for all options
            strikes = sorted(strike_oi.keys())
            min_pain = float("inf")
            max_pain_strike = spot_price  # default

            for candidate in strikes:
                total_pain = 0.0
                for strike, oi_data in strike_oi.items():
                    # Call holders lose if strike > candidate (OTM)
                    # Call intrinsic = max(0, candidate - strike)
                    call_intrinsic = max(0, candidate - strike)
                    total_pain += call_intrinsic * oi_data["call_oi"]

                    # Put intrinsic = max(0, strike - candidate)
                    put_intrinsic = max(0, strike - candidate)
                    total_pain += put_intrinsic * oi_data["put_oi"]

                if total_pain < min_pain:
                    min_pain = total_pain
                    max_pain_strike = candidate

            # Calculate divergence from max pain
            divergence_pct = (spot_price - max_pain_strike) / max_pain_strike

            name = CRYPTO_SYMBOLS.get(symbol, {}).get("name", symbol)
            confidence = min(0.80, 0.50 + abs(divergence_pct) * 5.0
                             + (48 - hours_to_expiry) / 48 * 0.15)

            if divergence_pct < -0.03:
                # Spot is > 3% below max pain: expect upward pull
                tp = _smart_round(spot_price * 1.02)
                sl = _smart_round(spot_price * 0.97)
                signals.append({
                    "symbol": symbol,
                    "direction": "BUY",
                    "strategy": "max_pain_gravitational",
                    "confidence": round(confidence, 2),
                    "entry_price": _smart_round(spot_price),
                    "tp_price": tp,
                    "sl_price": sl,
                    "reason": (f"Max pain gravity: {name} spot ${spot_price:,.0f} is "
                               f"{abs(divergence_pct)*100:.1f}% below max pain "
                               f"${max_pain_strike:,.0f}. {hours_to_expiry:.0f}h to expiry. "
                               f"Price tends to converge. Ref: Quantpedia, KuCoin Research"),
                    "generated_at": _now_iso(),
                    "max_hold_days": 3,
                })

            elif divergence_pct > 0.03:
                # Spot is > 3% above max pain: expect downward pull
                tp = _smart_round(spot_price * 0.98)
                sl = _smart_round(spot_price * 1.03)
                signals.append({
                    "symbol": symbol,
                    "direction": "SELL",
                    "strategy": "max_pain_gravitational",
                    "confidence": round(confidence, 2),
                    "entry_price": _smart_round(spot_price),
                    "tp_price": tp,
                    "sl_price": sl,
                    "reason": (f"Max pain gravity: {name} spot ${spot_price:,.0f} is "
                               f"{divergence_pct*100:.1f}% above max pain "
                               f"${max_pain_strike:,.0f}. {hours_to_expiry:.0f}h to expiry. "
                               f"Price tends to converge. Ref: Quantpedia, KuCoin Research"),
                    "generated_at": _now_iso(),
                    "max_hold_days": 3,
                })

        except Exception:
            continue

    return signals


# =====================================================================
# STRATEGY 3: Put-Call Ratio Contrarian (Equities + Crypto)
# =====================================================================
# Uses VIX as a PCR proxy for equities (VIX > 25 ~ high PCR) and
# Fear & Greed Index as PCR proxy for crypto (F&G < 20 ~ high PCR).
# Extreme readings = contrarian entry.
# Reference: QuantifiedStrategies, 77% 2-week WR
# =====================================================================

def put_call_ratio_contrarian(data: dict[str, pd.DataFrame],
                              context: Optional[dict] = None) -> list[dict]:
    """Contrarian signals from PCR proxy extremes (VIX for equities, F&G for crypto)."""
    signals: list[dict] = []

    # -- Equities: VIX-based PCR proxy ------------------------------
    # Use ^VIX data if available, otherwise estimate from SPY realized vol
    equity_targets = ["SPY", "QQQ"]
    vix_level: Optional[float] = None

    # Try to get VIX from data
    if "^VIX" in data and len(data["^VIX"]) >= 5:
        vix_series = data["^VIX"]["Close"]
        vix_level = float(vix_series.rolling(5).mean().iloc[-1])
    else:
        # Estimate VIX from SPY realized vol (annualized)
        if "SPY" in data and len(data["SPY"]) >= 25:
            spy_returns = data["SPY"]["Close"].pct_change().dropna()
            realized_vol = float(spy_returns.iloc[-20:].std() * np.sqrt(252) * 100)
            vix_level = realized_vol  # Rough approximation

    if vix_level is not None:
        for symbol in equity_targets:
            if symbol not in data or len(data[symbol]) < 20:
                continue
            try:
                df = data[symbol]
                price = float(df["Close"].iloc[-1])
                name = EQUITY_SYMBOLS.get(symbol, {}).get("name", symbol)
                cat = _get_category(symbol)
                sl_pct, tp_pct, max_hold = CATEGORY_RISK.get(cat, (-0.06, 0.12, 10))

                if vix_level > 30:
                    # Extreme fear: contrarian BUY
                    confidence = min(0.85, 0.55 + (vix_level - 30) / 40)
                    signals.append({
                        "symbol": symbol,
                        "direction": "BUY",
                        "strategy": "put_call_ratio_contrarian",
                        "confidence": round(confidence, 2),
                        "entry_price": _smart_round(price),
                        "tp_price": _smart_round(price * (1 + tp_pct)),
                        "sl_price": _smart_round(price * (1 + sl_pct)),
                        "reason": (f"PCR contrarian BUY: VIX={vix_level:.1f} (extreme fear). "
                                   f"{name} historically rallies 77% of 2-week windows "
                                   f"after VIX>30. Ref: QuantifiedStrategies"),
                        "generated_at": _now_iso(),
                        "max_hold_days": 14,
                    })
                elif vix_level < 12:
                    # Extreme complacency: contrarian SELL
                    confidence = min(0.75, 0.50 + (12 - vix_level) / 10)
                    signals.append({
                        "symbol": symbol,
                        "direction": "SELL",
                        "strategy": "put_call_ratio_contrarian",
                        "confidence": round(confidence, 2),
                        "entry_price": _smart_round(price),
                        "tp_price": _smart_round(price * (1 + sl_pct)),  # Inverted for short
                        "sl_price": _smart_round(price * (1 + tp_pct)),
                        "reason": (f"PCR contrarian SELL: VIX={vix_level:.1f} (extreme "
                                   f"complacency). {name} vulnerable to correction. "
                                   f"Ref: QuantifiedStrategies"),
                        "generated_at": _now_iso(),
                        "max_hold_days": 14,
                    })
            except Exception:
                continue

    # -- Crypto: Fear & Greed as PCR proxy --------------------------
    # F&G is market-wide -- contrarian signal applies to all liquid crypto
    crypto_targets = ["BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD", "XRP-USD",
                      "ADA-USD", "AVAX-USD", "LINK-USD", "DOT-USD", "DOGE-USD"]

    fg_history = _fetch_fear_greed_history(5)
    if fg_history is None:
        fg_current = _fetch_fear_greed()
        if fg_current is not None:
            fg_history = [fg_current]

    if fg_history and len(fg_history) > 0:
        # 5-day smoothed F&G
        fg_smoothed = sum(fg_history) / len(fg_history)

        for symbol in crypto_targets:
            if symbol not in data or len(data[symbol]) < 20:
                continue
            try:
                df = data[symbol]
                price = float(df["Close"].iloc[-1])
                name = CRYPTO_SYMBOLS.get(symbol, {}).get("name", symbol)
                cat = _get_category(symbol)
                sl_pct, tp_pct, max_hold = CATEGORY_RISK.get(cat, (-0.08, 0.15, 7))

                if fg_smoothed < 15:
                    # Extreme fear: contrarian BUY
                    confidence = min(0.85, 0.55 + (15 - fg_smoothed) / 20)
                    signals.append({
                        "symbol": symbol,
                        "direction": "BUY",
                        "strategy": "put_call_ratio_contrarian",
                        "confidence": round(confidence, 2),
                        "entry_price": _smart_round(price),
                        "tp_price": _smart_round(price * (1 + tp_pct)),
                        "sl_price": _smart_round(price * (1 + sl_pct)),
                        "reason": (f"PCR contrarian BUY: F&G={fg_smoothed:.0f} (extreme fear, "
                                   f"5d avg). {name} at capitulation levels. "
                                   f"77% 2-week win rate historically. "
                                   f"Ref: QuantifiedStrategies"),
                        "generated_at": _now_iso(),
                        "max_hold_days": 14,
                    })
                elif fg_smoothed > 85:
                    # Extreme greed: contrarian SELL
                    confidence = min(0.75, 0.50 + (fg_smoothed - 85) / 20)
                    signals.append({
                        "symbol": symbol,
                        "direction": "SELL",
                        "strategy": "put_call_ratio_contrarian",
                        "confidence": round(confidence, 2),
                        "entry_price": _smart_round(price),
                        "tp_price": _smart_round(price * (1 + sl_pct)),
                        "sl_price": _smart_round(price * (1 + tp_pct)),
                        "reason": (f"PCR contrarian SELL: F&G={fg_smoothed:.0f} (extreme greed, "
                                   f"5d avg). {name} at euphoria levels. "
                                   f"Ref: QuantifiedStrategies"),
                        "generated_at": _now_iso(),
                        "max_hold_days": 14,
                    })
            except Exception:
                continue

    return signals


# =====================================================================
# STRATEGY 4: Google Trends Contrarian (Crypto - BTC only)
# =====================================================================
# Since pytrends is unreliable in CI, we use a capitulation proxy:
# RSI-14 < 25 AND F&G < 20 AND volume > 2x average approximates
# "bitcoin crash" search spikes (extreme fear = capitulation = BUY).
# RSI-14 > 80 AND F&G > 85 = euphoria = SELL.
# Reference: Zelieska et al. (2024) SSRN
# =====================================================================

def google_trends_contrarian(data: dict[str, pd.DataFrame],
                             context: Optional[dict] = None) -> list[dict]:
    """Contrarian BTC signal combining RSI, F&G, and volume as a Google Trends proxy."""
    signals: list[dict] = []

    if "BTC-USD" not in data:
        return signals

    df = data["BTC-USD"]
    if len(df) < 30:
        return signals

    try:
        close = df["Close"]
        vol = df["Volume"]
        price = float(close.iloc[-1])

        # Compute indicators
        rsi_14 = rsi(close, 14)
        current_rsi = float(rsi_14.iloc[-1])
        vol_ratio = volume_ratio(vol, 20)
        current_vol_ratio = float(vol_ratio.iloc[-1])

        # Fetch Fear & Greed
        fg_value = _fetch_fear_greed()
        if fg_value is None:
            return signals  # Cannot evaluate without F&G

        name = CRYPTO_SYMBOLS.get("BTC-USD", {}).get("name", "Bitcoin")

        # Capitulation BUY: RSI < 25 AND F&G < 20 AND volume > 2x avg
        if current_rsi < 25 and fg_value < 20 and current_vol_ratio > 2.0:
            confidence = min(0.90, 0.60
                             + (25 - current_rsi) / 50
                             + (20 - fg_value) / 40
                             + min(0.1, (current_vol_ratio - 2.0) / 10))
            signals.append({
                "symbol": "BTC-USD",
                "direction": "BUY",
                "strategy": "google_trends_contrarian",
                "confidence": round(confidence, 2),
                "entry_price": _smart_round(price),
                "tp_price": _smart_round(price * 1.08),
                "sl_price": _smart_round(price * 0.95),
                "reason": (f"Trends contrarian BUY: {name} capitulation detected. "
                           f"RSI={current_rsi:.1f} (<25), F&G={fg_value} (<20), "
                           f"Vol={current_vol_ratio:.1f}x avg (>2x). "
                           f"Triple-fear confluence = high-probability reversal. "
                           f"Ref: Zelieska et al. (2024) SSRN"),
                "generated_at": _now_iso(),
                "max_hold_days": 10,
            })

        # Euphoria SELL: RSI > 80 AND F&G > 85
        elif current_rsi > 80 and fg_value > 85:
            confidence = min(0.80, 0.55
                             + (current_rsi - 80) / 40
                             + (fg_value - 85) / 30)
            signals.append({
                "symbol": "BTC-USD",
                "direction": "SELL",
                "strategy": "google_trends_contrarian",
                "confidence": round(confidence, 2),
                "entry_price": _smart_round(price),
                "tp_price": _smart_round(price * 0.92),
                "sl_price": _smart_round(price * 1.05),
                "reason": (f"Trends contrarian SELL: {name} euphoria detected. "
                           f"RSI={current_rsi:.1f} (>80), F&G={fg_value} (>85). "
                           f"Extreme greed + overbought = correction likely. "
                           f"Ref: Zelieska et al. (2024) SSRN"),
                "generated_at": _now_iso(),
                "max_hold_days": 10,
            })

    except Exception:
        pass

    return signals


# -- Registry ------------------------------------------------------------


# =====================================================================
# STRATEGY 5: Copper/Gold Ratio BTC Cycle
# =====================================================================
# The Copper/Gold ratio (CGR) is a classic macro indicator.
# Copper = industrial demand proxy, Gold = safe haven proxy.
# CGR rising -> risk-on -> bullish BTC.
# CGR falling -> risk-off -> bearish BTC.
#
# We apply RSI-14 to the CGR and look for oversold/overbought
# reversals to time BTC cycle entries/exits.
#
# Reference: ainvest.com Jan 2026, "Copper-Gold Ratio as BTC Leading Indicator"
# Win rate: ~55-60% (macro cycle, longer-term holds)
# TP: 10%, SL: 6%, Max hold: 21 days
# =====================================================================

def copper_gold_btc_cycle(data: dict[str, pd.DataFrame],
                          context: Optional[dict] = None) -> list[dict]:
    """
    Copper/Gold ratio RSI as a macro cycle proxy for BTC.

    Logic:
      - Compute CGR = copper_close / gold_close
      - RSI-14 of CGR
      - BUY BTC when CGR RSI < 30 and turning up (RSI today > RSI yesterday)
      - SELL BTC when CGR RSI > 70 and turning down
    """
    signals: list[dict] = []

    # Get copper and gold data
    copper_df = data.get("HG=F")
    if copper_df is None or len(copper_df) < 30:
        copper_df = _fetch_yf_inline("HG=F", period="6mo")
    gold_df = data.get("GC=F")
    if gold_df is None or len(gold_df) < 30:
        gold_df = _fetch_yf_inline("GC=F", period="6mo")

    if copper_df is None or gold_df is None:
        return signals
    if len(copper_df) < 30 or len(gold_df) < 30:
        return signals

    # Align on common dates
    copper_close = copper_df["Close"].dropna()
    gold_close = gold_df["Close"].dropna()
    common_idx = copper_close.index.intersection(gold_close.index)
    if len(common_idx) < 30:
        return signals

    copper_close = copper_close.loc[common_idx]
    gold_close = gold_close.loc[common_idx]

    # Compute Copper/Gold ratio
    cgr = copper_close / gold_close.replace(0, np.nan)
    cgr = cgr.dropna()
    if len(cgr) < 20:
        return signals

    # RSI-14 of CGR
    cgr_rsi = rsi(cgr, 14)
    if len(cgr_rsi) < 2 or cgr_rsi.isna().iloc[-1] or cgr_rsi.isna().iloc[-2]:
        return signals

    rsi_today = float(cgr_rsi.iloc[-1])
    rsi_yesterday = float(cgr_rsi.iloc[-2])

    direction = None
    reason_detail = ""

    if rsi_today < 30 and rsi_today > rsi_yesterday:
        direction = "BUY"
        reason_detail = (f"CGR RSI oversold at {rsi_today:.1f} and turning up "
                         f"(prev {rsi_yesterday:.1f}) -- risk-on reversal")
    elif rsi_today > 70 and rsi_today < rsi_yesterday:
        direction = "SELL"
        reason_detail = (f"CGR RSI overbought at {rsi_today:.1f} and turning down "
                         f"(prev {rsi_yesterday:.1f}) -- risk-off reversal")

    if direction is None:
        return signals

    # Apply to BTC
    btc_df = data.get("BTC-USD")
    if btc_df is None or len(btc_df) < 20:
        return signals

    btc_close = btc_df["Close"]
    price = float(btc_close.iloc[-1])
    entry, tp, sl = _pct_tp_sl(price, direction, tp_pct=0.10, sl_pct=0.06)

    # Confidence based on RSI extremity
    if direction == "BUY":
        extremity = max(0, (30 - rsi_today) / 30)  # 0 at 30, 1 at 0
    else:
        extremity = max(0, (rsi_today - 70) / 30)   # 0 at 70, 1 at 100
    confidence = round(0.55 + extremity * 0.15, 2)  # 0.55 to 0.70

    rr = abs(tp - entry) / abs(entry - sl) if abs(entry - sl) > 0 else 0

    signals.append({
        "strategy": "copper_gold_btc_cycle",
        "symbol": "BTC-USD",
        "category": "crypto",
        "direction": direction,
        "confidence": confidence,
        "entry_price": entry,
        "tp_price": tp,
        "sl_price": sl,
        "rr_ratio": round(rr, 2),
        "max_hold_days": 21,
        "reason": (f"Copper/Gold ratio cycle: {reason_detail}. "
                   f"CGR RSI={rsi_today:.1f}. Ref: ainvest.com Jan 2026"),
        "reference": "ainvest.com Jan 2026 -- Copper-Gold ratio as BTC cycle proxy",
        "timestamp": _now_iso(),
    })

    return signals


# =====================================================================
# STRATEGY 6: BTC Options Expiry Anomaly
# =====================================================================
# Weekly options expire every Friday at 08:00 UTC (Deribit/CME).
# Research shows positive returns on expiry day and the day after.
# Monthly expiry (last Friday of month) has a stronger effect
# as max-pain convergence drives price toward strike clusters.
#
# Calendar logic:
#   - Thursday: BUY (front-running Friday expiry)
#   - Wednesday before monthly expiry: stronger BUY
#   - Additional confluence: BTC below 20-SMA (max pain pull more likely)
#
# Reference: Quantpedia confirmed anomaly
# Win rate: ~55-58%
# TP: 2%, SL: 2%, Max hold: 3 days
# =====================================================================

def btc_options_expiry_anomaly(data: dict[str, pd.DataFrame],
                               context: Optional[dict] = None) -> list[dict]:
    """
    Calendar-based BTC options expiry anomaly.

    Fires on Thursdays (day before weekly expiry) with enhanced
    signal near monthly expiry (last Friday of month).
    """
    signals: list[dict] = []
    now = datetime.now(timezone.utc)
    today = now.date()
    weekday = today.weekday()  # 0=Mon ... 4=Fri, 6=Sun

    # Only fire on Wednesday (2) or Thursday (3)
    if weekday not in (2, 3):
        return signals

    # Determine if this is near monthly expiry (last Friday of month)
    # Find last Friday of the current month
    year, month = today.year, today.month
    # Last day of month
    if month == 12:
        next_month_first = datetime(year + 1, 1, 1).date()
    else:
        next_month_first = datetime(year, month + 1, 1).date()
    last_day = next_month_first - timedelta(days=1)
    # Walk back to Friday
    last_friday = last_day
    while last_friday.weekday() != 4:  # 4 = Friday
        last_friday -= timedelta(days=1)

    is_monthly = abs((today - last_friday).days) <= 2
    is_thursday = weekday == 3
    is_wednesday_monthly = weekday == 2 and is_monthly

    if not is_thursday and not is_wednesday_monthly:
        return signals

    # Options expiry affects BTC/ETH most (Deribit liquidity), but SOL also has
    # active options markets. Other alts are affected via correlation.
    target_symbols = ["BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD", "XRP-USD",
                      "ADA-USD", "AVAX-USD", "LINK-USD", "DOT-USD", "DOGE-USD"]

    for symbol in target_symbols:
        df = data.get(symbol)
        if df is None or len(df) < 25:
            continue

        close = df["Close"]
        price = float(close.iloc[-1])

        # Below 20-SMA = stronger convergence signal (price pulled to max pain)
        sma20 = sma(close, 20)
        sma20_val = float(sma20.iloc[-1])
        below_sma = price < sma20_val

        # Build confidence
        base_conf = 0.52
        reason_parts = []

        if is_thursday:
            base_conf += 0.03
            reason_parts.append("Thursday pre-expiry")
        if is_monthly:
            base_conf += 0.06
            reason_parts.append("monthly expiry week (stronger max-pain effect)")
        if below_sma:
            base_conf += 0.04
            reason_parts.append(f"below 20-SMA ({sma20_val:.2f}), max-pain convergence likely")

        confidence = round(min(0.70, base_conf), 2)
        entry, tp, sl = _pct_tp_sl(price, "BUY", tp_pct=0.02, sl_pct=0.02)
        rr = abs(tp - entry) / abs(entry - sl) if abs(entry - sl) > 0 else 0

        signals.append({
            "strategy": "btc_options_expiry_anomaly",
            "symbol": symbol,
            "category": "crypto",
            "direction": "BUY",
            "confidence": confidence,
            "entry_price": entry,
            "tp_price": tp,
            "sl_price": sl,
            "rr_ratio": round(rr, 2),
            "max_hold_days": 3,
            "reason": (f"Options expiry anomaly: {'; '.join(reason_parts)}. "
                       f"Ref: Quantpedia confirmed weekly/monthly expiry effect"),
            "reference": "Quantpedia -- BTC options expiry calendar anomaly",
            "timestamp": _now_iso(),
        })

    return signals


# =====================================================================
# STRATEGY 7: Turn of Month Enhanced
# =====================================================================
# The basic turn-of-month effect (Ariel 1987) is in cyclical_strategies.py.
# This ENHANCED version adds three confirmation filters:
#   1. RSI-14 not overbought (< 75) -- avoid chasing
#   2. Volume above 20d average -- institutional participation
#   3. VIX < 30 -- don't buy into panic
#
# Window: last 4 trading days of month + first 3 of next month
#
# Reference: Quantpedia, 60-year backtest, CAGR 7.11%
# Win rate: ~60-65% (enhanced filters improve basic ~55%)
# TP: 2%, SL: 1.5%, Max hold: 7 days
# =====================================================================

def turn_of_month_enhanced(data: dict[str, pd.DataFrame],
                           context: Optional[dict] = None) -> list[dict]:
    """
    Enhanced Turn-of-Month effect with RSI, volume, and VIX filters.

    BUY SPY/QQQ during the last 4 or first 3 trading days of month,
    but only when RSI < 75, volume > 20d avg, and VIX < 30.
    """
    signals: list[dict] = []
    now = datetime.now(timezone.utc)
    today = now.date()
    day = today.day
    year, month = today.year, today.month

    # Determine last day of month
    if month == 12:
        next_month_first = datetime(year + 1, 1, 1).date()
    else:
        next_month_first = datetime(year, month + 1, 1).date()
    last_day = (next_month_first - timedelta(days=1)).day

    # Check if within TOM window: last 4 days of month OR first 3 days
    in_last_4 = day >= (last_day - 3)
    in_first_3 = day <= 3
    if not in_last_4 and not in_first_3:
        return signals

    # VIX filter
    vix_df = data.get("^VIX")
    if vix_df is None or len(vix_df) < 5:
        vix_df = _fetch_yf_inline("^VIX", period="3mo")

    vix_ok = True
    vix_level = None
    if vix_df is not None and len(vix_df) >= 5:
        vix_level = float(vix_df["Close"].iloc[-1])
        if vix_level >= 30:
            vix_ok = False  # Panic zone -- skip

    if not vix_ok:
        return signals

    # Scan SPY and QQQ
    target_symbols = ["SPY", "QQQ"]

    for symbol in target_symbols:
        df = data.get(symbol)
        if df is None or len(df) < 25:
            continue

        close = df["Close"]
        vol = df["Volume"]
        price = float(close.iloc[-1])

        # RSI filter: not overbought
        rsi14 = rsi(close, 14)
        current_rsi = float(rsi14.iloc[-1])
        if current_rsi >= 75:
            continue

        # Volume filter: above 20d average
        vol_r = volume_ratio(vol, 20)
        current_vol_ratio = float(vol_r.iloc[-1])
        if current_vol_ratio < 1.0:
            continue  # Below-average volume, skip

        # All filters passed -- generate BUY signal
        reason_parts = []
        if in_last_4:
            reason_parts.append(f"last {last_day - day + 1} day(s) of month")
        else:
            reason_parts.append(f"day {day} of month (first 3 days)")

        reason_parts.append(f"RSI={current_rsi:.1f} (not overbought)")
        reason_parts.append(f"vol ratio={current_vol_ratio:.2f}x (above avg)")
        if vix_level is not None:
            reason_parts.append(f"VIX={vix_level:.1f} (< 30 safe)")

        # Confidence: base 0.58, +0.03 for strong volume, +0.02 for low RSI
        conf = 0.58
        if current_vol_ratio > 1.5:
            conf += 0.03
        if current_rsi < 50:
            conf += 0.02
        if in_last_4 and in_first_3:
            conf += 0.02  # Won't happen, but defensive
        confidence = round(min(0.70, conf), 2)

        entry, tp, sl = _pct_tp_sl(price, "BUY", tp_pct=0.02, sl_pct=0.015)
        rr = abs(tp - entry) / abs(entry - sl) if abs(entry - sl) > 0 else 0

        signals.append({
            "strategy": "turn_of_month_enhanced",
            "symbol": symbol,
            "category": "stock",
            "direction": "BUY",
            "confidence": confidence,
            "entry_price": entry,
            "tp_price": tp,
            "sl_price": sl,
            "rr_ratio": round(rr, 2),
            "max_hold_days": 7,
            "reason": (f"Enhanced TOM effect: {'; '.join(reason_parts)}. "
                       f"Ref: Quantpedia 60yr backtest CAGR 7.11%"),
            "reference": "Quantpedia -- Turn of Month enhanced (Ariel 1987)",
            "timestamp": _now_iso(),
        })

    return signals


# =====================================================================
# STRATEGY 8: VIX Term Structure Signal
# =====================================================================
# VIX level vs its 50-day SMA as a fear/complacency regime proxy.
#
# When VIX > 50% above 50d SMA: extreme fear spike -> contrarian BUY SPY
# When VIX > 30% below 50d SMA: extreme complacency -> caution SELL
#
# Crypto overlay (delayed transmission):
#   - VIX spike today + BTC still flat -> prepare to SELL BTC (1-2d lag)
#   - VIX crash from spike + BTC oversold -> BUY BTC (risk-on returning)
#
# Reference: Quantpedia "highly profitable", PMC 2024 validated
# Win rate: ~60-65% on equity, ~55-60% on crypto overlay
# TP/SL: Based on CATEGORY_RISK
# Max hold: 10 days
# =====================================================================

def vix_term_structure_signal(data: dict[str, pd.DataFrame],
                              context: Optional[dict] = None) -> list[dict]:
    """
    VIX spike/crush contrarian strategy for equities + crypto overlay.

    Uses VIX deviation from its 50d SMA as a regime signal.
    """
    signals: list[dict] = []

    # Get VIX data
    vix_df = data.get("^VIX")
    if vix_df is None or len(vix_df) < 55:
        vix_df = _fetch_yf_inline("^VIX", period="6mo")
    if vix_df is None or len(vix_df) < 55:
        return signals

    vix_close = vix_df["Close"]
    # Handle MultiIndex columns from yfinance (returns DataFrame instead of Series)
    if isinstance(vix_close, pd.DataFrame):
        vix_close = vix_close.iloc[:, 0]
    vix_current = float(vix_close.iloc[-1])
    vix_sma50 = sma(vix_close, 50)
    vix_sma50_val = float(vix_sma50.iloc[-1])

    if vix_sma50_val <= 0:
        return signals

    # Compute deviation percentage
    deviation = (vix_current - vix_sma50_val) / vix_sma50_val

    # Check yesterday's deviation for direction of change
    vix_yesterday = float(vix_close.iloc[-2])
    vix_sma50_yesterday = float(vix_sma50.iloc[-2])
    deviation_yesterday = ((vix_yesterday - vix_sma50_yesterday) /
                           vix_sma50_yesterday if vix_sma50_yesterday > 0 else 0)

    vix_rising = deviation > deviation_yesterday
    vix_falling = deviation < deviation_yesterday

    # ---- Equity signals (SPY) ----

    if deviation > 0.50:
        # Extreme fear spike -> contrarian BUY SPY
        spy_df = data.get("SPY")
        if spy_df is not None and len(spy_df) >= 20:
            close = spy_df["Close"]
            price = float(close.iloc[-1])
            sl_pct, tp_pct, max_hold = CATEGORY_RISK.get("stock", (-0.06, 0.12, 10))
            sl_pct = abs(sl_pct)
            entry, tp, sl = _pct_tp_sl(price, "BUY", tp_pct=tp_pct, sl_pct=sl_pct)
            rr = abs(tp - entry) / abs(entry - sl) if abs(entry - sl) > 0 else 0

            conf = 0.58 + min(0.12, (deviation - 0.50) * 0.40)  # Higher spike = more confident
            confidence = round(min(0.75, conf), 2)

            signals.append({
                "strategy": "vix_term_structure_signal",
                "symbol": "SPY",
                "category": "stock",
                "direction": "BUY",
                "confidence": confidence,
                "entry_price": entry,
                "tp_price": tp,
                "sl_price": sl,
                "rr_ratio": round(rr, 2),
                "max_hold_days": max_hold,
                "reason": (f"VIX fear spike: VIX={vix_current:.1f}, "
                           f"50d SMA={vix_sma50_val:.1f}, "
                           f"deviation=+{deviation*100:.0f}% (>50% threshold). "
                           f"Contrarian BUY. Ref: Quantpedia, PMC 2024"),
                "reference": "Quantpedia -- VIX term structure contrarian, PMC 2024",
                "timestamp": _now_iso(),
            })

    elif deviation < -0.30:
        # Extreme complacency -> caution SELL SPY
        spy_df = data.get("SPY")
        if spy_df is not None and len(spy_df) >= 20:
            close = spy_df["Close"]
            price = float(close.iloc[-1])
            sl_pct, tp_pct, max_hold = CATEGORY_RISK.get("stock", (-0.06, 0.12, 10))
            sl_pct = abs(sl_pct)
            entry, tp, sl = _pct_tp_sl(price, "SELL", tp_pct=tp_pct, sl_pct=sl_pct)
            rr = abs(tp - entry) / abs(entry - sl) if abs(entry - sl) > 0 else 0

            conf = 0.53 + min(0.10, (abs(deviation) - 0.30) * 0.30)
            confidence = round(min(0.68, conf), 2)

            signals.append({
                "strategy": "vix_term_structure_signal",
                "symbol": "SPY",
                "category": "stock",
                "direction": "SELL",
                "confidence": confidence,
                "entry_price": entry,
                "tp_price": tp,
                "sl_price": sl,
                "rr_ratio": round(rr, 2),
                "max_hold_days": max_hold,
                "reason": (f"VIX complacency: VIX={vix_current:.1f}, "
                           f"50d SMA={vix_sma50_val:.1f}, "
                           f"deviation={deviation*100:.0f}% (<-30% threshold). "
                           f"Caution SELL. Ref: Quantpedia, PMC 2024"),
                "reference": "Quantpedia -- VIX term structure contrarian, PMC 2024",
                "timestamp": _now_iso(),
            })

    # ---- Crypto overlay (BTC, 1-2 day lag effect) ----

    btc_df = data.get("BTC-USD")
    if btc_df is not None and len(btc_df) >= 25:
        btc_close = btc_df["Close"]
        btc_price = float(btc_close.iloc[-1])
        btc_rsi14 = rsi(btc_close, 14)
        btc_rsi_val = float(btc_rsi14.iloc[-1])

        sl_pct, tp_pct, max_hold = CATEGORY_RISK.get("crypto", (-0.08, 0.15, 7))
        sl_pct = abs(sl_pct)

        # VIX spike + BTC still flat/up -> delayed selloff warning
        if deviation > 0.50 and vix_rising and btc_rsi_val > 45:
            # BTC hasn't reacted to the fear yet -- expect delayed drop
            btc_1d_ret = (btc_price / float(btc_close.iloc[-2])) - 1.0
            if btc_1d_ret > -0.02:  # BTC hasn't dropped much yet
                entry, tp, sl = _pct_tp_sl(btc_price, "SELL",
                                           tp_pct=tp_pct, sl_pct=sl_pct)
                rr = abs(tp - entry) / abs(entry - sl) if abs(entry - sl) > 0 else 0

                signals.append({
                    "strategy": "vix_term_structure_signal",
                    "symbol": "BTC-USD",
                    "category": "crypto",
                    "direction": "SELL",
                    "confidence": 0.55,
                    "entry_price": entry,
                    "tp_price": tp,
                    "sl_price": sl,
                    "rr_ratio": round(rr, 2),
                    "max_hold_days": max_hold,
                    "reason": (f"VIX-BTC lag: VIX spiked +{deviation*100:.0f}% above "
                               f"50d SMA but BTC flat (RSI={btc_rsi_val:.0f}, "
                               f"1d ret={btc_1d_ret*100:+.1f}%). "
                               f"Expect delayed crypto selloff in 1-2 days"),
                    "reference": "VIX-crypto transmission lag (Quantpedia, PMC 2024)",
                    "timestamp": _now_iso(),
                })

        # VIX crashing from spike + BTC oversold -> risk-on BUY
        elif deviation_yesterday > 0.30 and deviation < 0.20 and vix_falling:
            if btc_rsi_val < 40:
                entry, tp, sl = _pct_tp_sl(btc_price, "BUY",
                                           tp_pct=tp_pct, sl_pct=sl_pct)
                rr = abs(tp - entry) / abs(entry - sl) if abs(entry - sl) > 0 else 0

                signals.append({
                    "strategy": "vix_term_structure_signal",
                    "symbol": "BTC-USD",
                    "category": "crypto",
                    "direction": "BUY",
                    "confidence": 0.58,
                    "entry_price": entry,
                    "tp_price": tp,
                    "sl_price": sl,
                    "rr_ratio": round(rr, 2),
                    "max_hold_days": max_hold,
                    "reason": (f"VIX fear unwind: VIX dropped from "
                               f"+{deviation_yesterday*100:.0f}% to "
                               f"+{deviation*100:.0f}% above 50d SMA. "
                               f"BTC oversold (RSI={btc_rsi_val:.0f}). "
                               f"Risk-on returning -- contrarian BUY"),
                    "reference": "VIX-crypto transmission lag (Quantpedia, PMC 2024)",
                    "timestamp": _now_iso(),
                })

    return signals


# =====================================================================
# Registry
# =====================================================================

UNTAPPED_STRATEGIES = {
    # Backtested positive (6 strategies):
    "max_pain_gravitational": max_pain_gravitational,        # 68.4% WR, Sharpe 3.67
    "put_call_ratio_contrarian": put_call_ratio_contrarian,  # 75.0% WR, Sharpe 11.39
    "google_trends_contrarian": google_trends_contrarian,    # 100% WR (rare signal), Sharpe 153
    "btc_options_expiry_anomaly": btc_options_expiry_anomaly,# 53.8% WR, Sharpe 1.79, 104 trades
    "turn_of_month_enhanced": turn_of_month_enhanced,        # 57.1% WR, Sharpe 3.15, 49 trades
    "vix_term_structure_signal": vix_term_structure_signal,  # 83.3% WR, Sharpe 14.79
    # Needs more tuning (disabled for now):
    # "hurst_exponent_pairs": hurst_exponent_pairs,          # 0 trades -- z>2 + Hurst<0.45 too strict
    # "copper_gold_btc_cycle": copper_gold_btc_cycle,        # 42.9% WR, negative PnL -- DISABLED
}
