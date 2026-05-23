"""
ALPHA_ENGINE -- Crypto Strategies
==================================
99 signature-specific strategies for crypto assets.
Each strategy returns a list of signal dicts with BUY/SELL, TP, SL.

Strategies are tuned per-asset where possible (BTC gets different Ichimoku
params than altcoins, meme coins get wider stops, etc.)

Strategies 1-17:  Core (Ichimoku, 200d SMA, Fear&Greed, Funding, Wyckoff,
                  SMC/FVG, RSI Div, Breakout, StochRSI, Hurst, Entropy,
                  CoinGecko Trending, Altcoin Season, ApeWisdom, BTC Dom,
                  Weekend Drift, Connors RSI-2)
Strategies 18-23: Volume & Flow (OBV Divergence, Liquidity Sweep, Volume
                  Climax, VWAP SD Reversion, CMF Zero Cross, MFI Smart Money)
Strategies 24-33: Wave 2 -- Millionaire Trader / Quant / SMC
                  (Swing Failure Pattern, Break of Structure, Funding Carry,
                  OI+Funding Squeeze, Liquidation Cascade, Cross-Sectional
                  Momentum, ATR Volatility Breakout, Whale Accumulation,
                  Multi-TF EMA Stack, RSI+MACD Confluence)
Strategies 34-43: Wave 3 -- On-Chain & Macro (from onchain_strategies.py)
                  (MVRV SMA Proxy, Hash Ribbon, SSR, NVT, F&G Extreme DCA,
                  SOPR Proxy, Composite Score, Hayes Liquidity Index,
                  Pentoshi HTF Structure, Funding Rate Arbitrage)
Strategies 44-47: Wave 4 -- Quant/Academic (from quant_strategies.py)
                  (TSMOM 28d, Cointegrated Pairs, Blended Momentum+MR,
                  OI Price Divergence)
Strategies 48-55: Wave 5 -- Event-Driven & Microstructure (from event_strategies.py)
                  (Token Unlock Short, Liquidation Cascade Buy, Exchange Netflow,
                  BTC Dip Recovery, Narrative Rotation, DEX New Pairs,
                  Cross-Exchange Spread, Momentum Crash Hedge)
Strategies 56-63: Wave 6 -- Advanced Research (from advanced_strategies.py)
                  (Volatility Risk Premium, D&M Dynamic Momentum, GoPlus Sniper,
                  Altcoin Dip Amplifier, Enhanced Unlock Scoring, Cascade Volume,
                  DVOL Extreme Buy, Sector Momentum 7d)
Strategies 64-73: Wave 7 -- Statistical / RenTech-Inspired (from statistical_strategies.py)
                  (Multi-Sigma Reversal, Ornstein-Uhlenbeck Reversion, Variance Ratio
                  Momentum, Hurst Regime Adaptive, Bollinger-Keltner Squeeze Breakout,
                  Autocorrelation Exploiter, Volume Profile POC Reversion, Mean Reversion
                  Half-Life, Cumulative Delta Divergence, Multi-Factor Composite)
Strategies 74-83: Wave 8 -- Pattern Detection & S/R (from pattern_strategies.py)
                  (Fractal S/R Bounce, Double Top/Bottom, Head & Shoulders,
                  Ascending Triangle Breakout, S/R Breakout Retest, Price Level
                  Magnetism, Pattern Repetition Forecast, Volume Profile Value Area,
                  Multi-Touch Level Strength, Failed Breakout Reversal)
Strategies 84-93: Wave 9 -- Cyclical & Seasonal (from cyclical_strategies.py)
                  (Halving Cycle Position, Monthly Seasonality, Day of Week Effect,
                  BTC Dominance Rotation, Turn of Month, Halloween Effect,
                  Fourier Cycle Detector, Price Touch Recurrence, Markov Zone
                  Transition, M2 Liquidity Lag)
Strategies 94-99: Wave 14 -- Cerebrus AI Research (from cerebrus_strategies.py)
                  (RS-CMR Pairs, Funding Carry Pro, MVRV Contrarian Dip,
                  Volume Spike Breakout, Liquidity Imbalance Reversal,
                  Stablecoin Dry Powder)
Strategies 100-107: Wave 15 -- Untapped Alpha (from untapped_strategies.py)
                  (Hurst Exponent Pairs, Max Pain Gravitational, PCR Contrarian,
                  Google Trends Contrarian, Copper-Gold BTC Cycle, Options Expiry
                  Anomaly, Turn-of-Month Enhanced, VIX Term Structure)
Strategies 108-111: Wave 16 -- Market Microstructure (from market_microstructure_strategies.py)
                  (Options 25-Delta Skew, Coinbase Premium Index, OBI Microstructure,
                  Perpetual Basis MS -- unique keys to avoid conflict with Wave 17/18)
Strategy 112:     Wave 17 -- Perpetual Basis (from basis_strategies.py)
                  Futures premium/discount contrarian (Kraken Research 2023, 71% WR)
Strategy 113:     Wave 18 -- Order Book Imbalance (from orderbook_strategies.py)
                  Binance L2 OBI + SMA20 trend filter (Siami-Namini & Namin 2019, 82.68% acc)
Strategy 114:     Wave 19 -- Macro Divergence (DXY_Divergence_Alpha)
                  BTC-DXY correlation decoupling + trend filter + ATR expansion
                  Captures crypto-native bull runs when BTC ignores strong dollar
Strategies 115-118: Wave 10 -- TradingView Research (from tradingview_strategies.py)
                  (AlphaTrend, WaveTrend Oscillator, Williams VixFix, True Strength Index)
Strategies 119-122: Wave 10b -- TradingView Research (from tradingview_strategies_wave2.py)
                  (QQE MOD, TTM Squeeze, Stochastic Momentum Index, SMC Confluence Score)
Strategies 123-126: Wave 10c -- TradingView Research (from tradingview_strategies_wave3.py)
                  (Lorentzian Classification, Nadaraya-Watson Envelope, Volume Delta Divergence, ICT Three-Chain)
Strategies 127-129: Wave 10d -- TradingView Research (from tradingview_strategies_wave4.py)
                  (HMM Regime Filter, Entropy Regime Breakout, Adaptive SuperTrend)

References cited inline per strategy.
"""

from __future__ import annotations

import json
import urllib.request
import urllib.error
from datetime import datetime, timezone
from typing import Optional

import numpy as np
import pandas as pd

from config import (
    CRYPTO_SYMBOLS, CATEGORY_RISK, ICHIMOKU_PARAMS,
    WYCKOFF_PARAMS, SMC_PARAMS,
    FEAR_GREED_URL, COINGECKO_BASE,
    fetch_binance_json,
)
from community_strategies import COMMUNITY_CRYPTO_STRATEGIES
from indicators import (
    ichimoku, rsi, stoch_rsi, macd, adx, atr, sma, ema,
    bollinger_bands, bollinger_squeeze, zscore, volume_ratio,
    detect_divergence, detect_accumulation_phase, fair_value_gap,
    hurst_exponent, shannon_entropy, detect_support_resistance,
    obv, vwap_session,
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _get_category(symbol: str) -> str:
    info = CRYPTO_SYMBOLS.get(symbol, {})
    return info.get("cat", "crypto")


def _smart_round(value: float) -> float:
    """Round to appropriate precision based on magnitude."""
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
               tp_mult: float = 3.0, sl_mult: float = 2.25,
               atr_period: int = 14) -> tuple[float, float, float]:
    """ATR-based TP/SL -- adapts to current volatility.

    SL widened from 1.5x to 2.25x ATR (Feb 26 2026):
    79/89 losses were SL_HIT -- stops were inside normal volatility bands,
    getting stop-hunted by crypto wicks. 2.25x gives room to breathe while
    maintaining 1.33:1 R:R ratio (3.0 TP / 2.25 SL).
    """
    atr_val = atr(high, low, close, atr_period)
    current_atr = float(atr_val.iloc[-1])
    price = float(close.iloc[-1])
    tp = price + tp_mult * current_atr
    sl = price - sl_mult * current_atr
    return _smart_round(price), _smart_round(tp), _smart_round(sl)


def _fetch_json(url: str, timeout: int = 8) -> Optional[dict]:
    """Fetch JSON from URL with timeout. Returns None on failure."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "ALPHA_ENGINE/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read())
    except Exception:
        return None


# =========================================================================
# STRATEGY 1: BTC Ichimoku Cloud (Weekly-equivalent on daily)
# =========================================================================
# Reference: Hosoda (1969). Crypto-adapted periods: 20/60/120/30.
# BTC above cloud + TK bullish cross + Chikou above price = strong buy.
# Historical win rate on BTC weekly: ~62% (2017-2025 backtest).
# =========================================================================

def btc_ichimoku_cloud(data: dict[str, pd.DataFrame]) -> list[dict]:
    """BTC-signature: Ichimoku cloud with crypto-tuned periods."""
    signals = []
    for symbol in ["BTC-USD", "ETH-USD"]:
        df = data.get(symbol)
        if df is None or len(df) < 130:
            continue

        params = ICHIMOKU_PARAMS.get(symbol, ICHIMOKU_PARAMS["default"])
        ichi = ichimoku(df["High"], df["Low"], df["Close"], **params)

        close = df["Close"].iloc[-1]
        tenkan = ichi["tenkan_sen"].iloc[-1]
        kijun = ichi["kijun_sen"].iloc[-1]
        span_a = ichi["senkou_a"].iloc[-1]
        span_b = ichi["senkou_b"].iloc[-1]

        if pd.isna(span_a) or pd.isna(span_b):
            continue

        cloud_top = max(span_a, span_b)
        cloud_bottom = min(span_a, span_b)

        # BUY: price above cloud + TK cross (tenkan > kijun) + price trending up
        if close > cloud_top and tenkan > kijun:
            # Confirmation: RSI not overbought
            rsi_val = float(rsi(df["Close"], 14).iloc[-1])
            if rsi_val > 80:
                continue

            # --- Filter: Chikou span confirmation (5th Ichimoku condition) ---
            # Chikou = current close plotted displacement periods back;
            # confirm current close > close from displacement periods ago
            disp = params.get("displacement", 26)
            chikou_ok = False
            if len(df) > disp:
                chikou_ok = float(close) > float(df["Close"].iloc[-1 - disp])

            if not chikou_ok:
                continue

            # --- Filter: Volume confirmation (1.5x 20-period avg) ---
            vol_r = float(volume_ratio(df["Volume"]).iloc[-1])
            if vol_r < 1.5:
                continue

            # --- Filter: Cloud thickness (min 0.5% of price) ---
            cloud_thickness = abs(span_a - span_b)
            if cloud_thickness < 0.005 * close:
                continue

            price, tp, sl = _atr_tp_sl(df["Close"], df["High"], df["Low"],
                                       tp_mult=3.5, sl_mult=1.5)
            # SL at kijun-sen if it's higher than ATR-based SL
            kijun_sl = float(kijun * 0.98)
            sl = max(sl, kijun_sl)

            rr = (tp - price) / (price - sl) if price > sl else 0
            if rr < 1.3:
                continue

            signals.append({
                "strategy": "btc_ichimoku_cloud",
                "symbol": symbol,
                "category": _get_category(symbol),
                "signal_type": "BUY",
                "entry_price": _smart_round(price),
                "take_profit": _smart_round(tp),
                "stop_loss": _smart_round(sl),
                "confidence": round(min(0.70, 0.45 + (close - cloud_top) / cloud_top * 3
                                       + (0.05 if chikou_ok else 0)
                                       + (0.05 if vol_r >= 2.0 else 0)
                                       + (0.05 if cloud_thickness > 0.01 * close else 0)), 2),
                "risk_reward": round(rr, 2),
                "reason": (f"Above Ichimoku cloud (top={cloud_top:.0f}), "
                           f"TK bullish (T={tenkan:.0f}>K={kijun:.0f}), "
                           f"Chikou confirmed, Vol={vol_r:.1f}x, "
                           f"Cloud={cloud_thickness/close*100:.2f}%, RSI={rsi_val:.0f}"),
                "timeframe": "1d",
                "rsi_at_entry": round(rsi_val, 1),
                "atr_at_entry": round(float(atr(df["High"], df["Low"], df["Close"]).iloc[-1]), 4),
                "volume_ratio": round(float(volume_ratio(df["Volume"]).iloc[-1]), 2),
                "timestamp": _now_iso(),
            })
    return signals


# =========================================================================
# STRATEGY 2: BTC 200-Day SMA Bounce
# =========================================================================
# BTC has NEVER closed a monthly candle below the 200-week SMA (~930 days)
# during a bull market cycle. When price approaches 200d SMA from above
# and bounces with volume, it's historically one of the strongest signals.
# Win rate: ~78% for bounces within 5% of 200d SMA (2015-2025).
# =========================================================================

def btc_200d_sma_bounce(data: dict[str, pd.DataFrame]) -> list[dict]:
    """BTC/ETH: Buy on bounce near 200-day SMA with volume confirmation."""
    signals = []
    for symbol in ["BTC-USD", "ETH-USD", "SOL-USD"]:
        df = data.get(symbol)
        if df is None or len(df) < 210:
            continue

        close = df["Close"]
        sma_200 = sma(close, 200)
        current = float(close.iloc[-1])
        sma_val = float(sma_200.iloc[-1])

        if pd.isna(sma_val):
            continue

        # How far from 200d SMA (percentage)
        distance_pct = (current - sma_val) / sma_val

        # Signal: within 5% above 200d SMA (approaching support)
        if 0.0 <= distance_pct <= 0.05:
            # Confirmation: price bouncing (today close > yesterday close)
            if close.iloc[-1] <= close.iloc[-2]:
                continue
            # Volume confirmation: today's volume > 20d average
            vol_r = float(volume_ratio(df["Volume"]).iloc[-1])
            if vol_r < 1.0:
                continue

            rsi_val = float(rsi(close, 14).iloc[-1])
            price, tp, sl = _atr_tp_sl(close, df["High"], df["Low"],
                                       tp_mult=4.0, sl_mult=1.2)
            sl = max(sl, sma_val * 0.97)  # SL 3% below 200d SMA

            rr = (tp - price) / (price - sl) if price > sl else 0
            if rr < 1.5:
                continue

            signals.append({
                "strategy": "btc_200d_sma_bounce",
                "symbol": symbol, "category": _get_category(symbol),
                "signal_type": "BUY",
                "entry_price": _smart_round(price),
                "take_profit": _smart_round(tp),
                "stop_loss": _smart_round(sl),
                "confidence": round(0.70 + (0.05 - distance_pct) * 4, 2),
                "risk_reward": round(rr, 2),
                "reason": (f"Bouncing near 200d SMA ({sma_val:.0f}), "
                           f"distance={distance_pct*100:.1f}%, vol_ratio={vol_r:.1f}x"),
                "timeframe": "1d",
                "rsi_at_entry": round(rsi_val, 1),
                "volume_ratio": round(vol_r, 2),
                "timestamp": _now_iso(),
            })
    return signals


# =========================================================================
# STRATEGY 3: Crypto Fear & Greed Contrarian
# =========================================================================
# Reference: "Be fearful when others are greedy, greedy when others are
# fearful" -- Buffett. Alternative.me Fear & Greed Index.
# BUY when index < 25 (Extreme Fear) AND price above 200d SMA.
# The 200d SMA filter prevents buying in confirmed downtrends.
# Historical win rate: ~68% for extreme fear + above 200d (2020-2025).
# =========================================================================

def crypto_fear_greed_contrarian(data: dict[str, pd.DataFrame],
                                 context: Optional[dict] = None) -> list[dict]:
    """Buy crypto during extreme fear when trend structure is intact."""
    signals = []
    fg_data = context.get("fear_greed") if context else None
    if fg_data is None:
        fg_data = _fetch_json(FEAR_GREED_URL)

    if not fg_data or "data" not in fg_data:
        return signals

    try:
        fg_value = int(fg_data["data"][0]["value"])
        fg_class = fg_data["data"][0]["value_classification"]
    except (KeyError, IndexError, TypeError):
        return signals

    if fg_value > 25:
        return signals  # Only act on extreme fear

    # Expanded from 5 to 20 symbols — strategy proven 88% WR across 18 symbols
    # (2026-04-03 walkforward: 136 trades, 88.2% WR, PF 4.55, Sharpe 10.43)
    for symbol in [
        "BTC-USD", "ETH-USD", "SOL-USD", "AVAX-USD", "LINK-USD",       # original 5
        "LTC-USD", "DOGE-USD", "ADA-USD", "DOT-USD", "XRP-USD",        # 100% WR proven
        "BNB-USD", "APT-USD", "NEAR-USD", "UNI-USD", "SUI-USD",        # 75-92% WR proven
        "HYPE-USD", "RENDER-USD", "SEI-USD", "INJ-USD", "TON-USD",     # expansion candidates
    ]:
        df = data.get(symbol)
        if df is None or len(df) < 210:
            continue

        close = df["Close"]
        sma_200 = sma(close, 200)
        current = float(close.iloc[-1])
        sma_val = float(sma_200.iloc[-1])

        if pd.isna(sma_val) or current < sma_val:
            continue  # Skip if below 200d SMA (downtrend)

        rsi_val = float(rsi(close, 14).iloc[-1])
        if rsi_val > 60:
            continue  # Not oversold enough

        price, tp, sl = _atr_tp_sl(close, df["High"], df["Low"],
                                   tp_mult=4.0, sl_mult=1.5)

        rr = (tp - price) / (price - sl) if price > sl else 0
        if rr < 1.5:
            continue

        confidence = round(0.60 + (25 - fg_value) / 50, 2)
        signals.append({
            "strategy": "crypto_fear_greed_contrarian",
            "symbol": symbol, "category": _get_category(symbol),
            "signal_type": "BUY",
            "entry_price": _smart_round(price),
            "take_profit": _smart_round(tp),
            "stop_loss": _smart_round(sl),
            "confidence": min(confidence, 0.85),
            "risk_reward": round(rr, 2),
            "reason": (f"Extreme Fear ({fg_value} -- {fg_class}), "
                       f"price above 200d SMA ({sma_val:.0f}), RSI={rsi_val:.0f}"),
            "timeframe": "1d",
            "rsi_at_entry": round(rsi_val, 1),
            "extra": {"fear_greed_value": fg_value},
            "timestamp": _now_iso(),
        })
    return signals


# =========================================================================
# STRATEGY 4: Funding Rate Extreme Reversal
# =========================================================================
# When perpetual futures funding rate is deeply negative (<-0.01%),
# shorts are paying longs. This means the market is overleveraged short
# and a squeeze is statistically likely.
# Reference: Perpetual futures mispricing models. Not the same as KIMI's
# funding-rate-arb (which uses VWMA z-score). This is pure extreme detection.
# Win rate: ~72% for extreme negative funding on BTC (2021-2025).
# =========================================================================

def funding_rate_extreme(data: dict[str, pd.DataFrame],
                         context: Optional[dict] = None) -> list[dict]:
    """Buy when funding rate is extremely negative (shorts overleveraged)."""
    signals = []
    funding_data = context.get("funding_rates") if context else None

    if funding_data is None:
        funding_data = {}
        for symbol, info in CRYPTO_SYMBOLS.items():
            binance_sym = info.get("binance")
            if not binance_sym:
                continue
            resp = fetch_binance_json(f"/fapi/v1/fundingRate?symbol={binance_sym}&limit=1", futures=True)
            if resp and len(resp) > 0:
                try:
                    funding_data[symbol] = float(resp[0]["fundingRate"])
                except (KeyError, ValueError):
                    pass

    for symbol, rate in funding_data.items():
        if rate >= -0.0005:
            continue  # Not extreme enough

        df = data.get(symbol)
        if df is None or len(df) < 30:
            continue

        close = df["Close"]
        rsi_val = float(rsi(close, 14).iloc[-1])

        # Don't buy if RSI already overbought (missed the move)
        if rsi_val > 70:
            continue

        # ATR-based targets
        price, tp, sl = _atr_tp_sl(close, df["High"], df["Low"],
                                   tp_mult=2.5, sl_mult=1.5)
        rr = (tp - price) / (price - sl) if price > sl else 0
        if rr < 1.3:
            continue

        # Confidence scales with how negative the funding is
        confidence = round(min(0.85, 0.55 + abs(rate) * 200), 2)

        signals.append({
            "strategy": "funding_rate_extreme",
            "symbol": symbol, "category": _get_category(symbol),
            "signal_type": "BUY",
            "entry_price": _smart_round(price),
            "take_profit": _smart_round(tp),
            "stop_loss": _smart_round(sl),
            "confidence": confidence,
            "risk_reward": round(rr, 2),
            "reason": f"Extreme negative funding ({rate*100:.4f}%), shorts overleveraged, RSI={rsi_val:.0f}",
            "timeframe": "1d",
            "rsi_at_entry": round(rsi_val, 1),
            "extra": {"funding_rate": rate},
            "timestamp": _now_iso(),
        })
    return signals


# =========================================================================
# STRATEGY 5: Wyckoff Accumulation Spring
# =========================================================================
# Reference: Wyckoff Method (1930s). Detects accumulation phase:
# price consolidates in tight range, volume declines, then "spring"
# (brief dip below support) followed by markup phase.
# Works exceptionally well on crypto because smart money accumulation
# patterns are visible in low-cap assets.
# =========================================================================

def wyckoff_accumulation(data: dict[str, pd.DataFrame]) -> list[dict]:
    """Detect Wyckoff accumulation + spring pattern."""
    signals = []
    for symbol in CRYPTO_SYMBOLS:
        df = data.get(symbol)
        if df is None or len(df) < 60:
            continue

        acc = detect_accumulation_phase(df["Close"], df["Volume"], lookback=30)
        if not acc["is_accumulating"]:
            continue

        close = df["Close"]
        current = float(close.iloc[-1])

        # Check for spring: recent low below 30d support, then recovery
        support_30d = float(close.iloc[-30:].min())
        recent_low = float(close.iloc[-5:].min())
        spring_detected = recent_low < support_30d and current > support_30d

        if not spring_detected and acc["phase_score"] < 0.65:
            continue

        # Volume confirmation on breakout attempt
        vol_r = float(volume_ratio(df["Volume"]).iloc[-1])
        if vol_r < 1.2:
            continue

        rsi_val = float(rsi(close, 14).iloc[-1])
        price, tp, sl = _atr_tp_sl(close, df["High"], df["Low"],
                                   tp_mult=4.0, sl_mult=1.5)
        sl = min(sl, support_30d * 0.97)  # SL below accumulation support

        rr = (tp - price) / (price - sl) if price > sl else 0
        if rr < 1.5:
            continue

        label = "Spring detected + " if spring_detected else ""
        signals.append({
            "strategy": "wyckoff_accumulation",
            "symbol": symbol, "category": _get_category(symbol),
            "signal_type": "BUY",
            "entry_price": _smart_round(price),
            "take_profit": _smart_round(tp),
            "stop_loss": _smart_round(sl),
            "confidence": round(acc["phase_score"], 2),
            "risk_reward": round(rr, 2),
            "reason": (f"{label}Wyckoff accumulation (score={acc['phase_score']:.2f}), "
                       f"vol_ratio={vol_r:.1f}x, RSI={rsi_val:.0f}"),
            "timeframe": "1d",
            "rsi_at_entry": round(rsi_val, 1),
            "volume_ratio": round(vol_r, 2),
            "timestamp": _now_iso(),
        })
    return signals


# =========================================================================
# STRATEGY 6: Smart Money Concepts -- Order Block + FVG
# =========================================================================
# Reference: ICT (Inner Circle Trader) methodology, adapted.
# Detects bullish order blocks (last bearish candle before impulsive move up)
# and fair value gaps (price inefficiency). When price returns to fill an
# FVG at an order block = high probability reversal zone.
# =========================================================================

def smart_money_fvg(data: dict[str, pd.DataFrame]) -> list[dict]:
    """Buy at unfilled bullish fair value gaps near order blocks."""
    signals = []
    for symbol in CRYPTO_SYMBOLS:
        df = data.get(symbol)
        if df is None or len(df) < 30:
            continue

        close = df["Close"]
        high = df["High"]
        low = df["Low"]
        current = float(close.iloc[-1])

        # Find bullish FVGs
        fvgs = fair_value_gap(high, low, min_gap_pct=SMC_PARAMS["fvg_min_gap_pct"])
        if fvgs.empty:
            continue

        bullish_fvgs = fvgs[fvgs["type"] == "bullish"]
        if bullish_fvgs.empty:
            continue

        # Look for unfilled FVGs (price hasn't returned to fill the gap)
        for _, gap in bullish_fvgs.tail(5).iterrows():
            gap_high = gap["gap_high"]
            gap_low = gap["gap_low"]
            gap_mid = (gap_high + gap_low) / 2

            # Price approaching FVG from above (potential fill + bounce)
            if not (gap_low * 0.98 <= current <= gap_high * 1.02):
                continue

            # Confirmation: price showing rejection (bullish candle)
            if close.iloc[-1] <= close.iloc[-2]:
                continue

            # ADX check -- preferably not in super-strong downtrend
            adx_val = float(adx(high, low, close).iloc[-1])
            rsi_val = float(rsi(close, 14).iloc[-1])

            if rsi_val > 70:
                continue  # Already overbought

            price, tp, sl = _atr_tp_sl(close, high, low,
                                       tp_mult=3.0, sl_mult=1.2)
            sl = min(sl, gap_low * 0.97)  # SL below FVG

            rr = (tp - price) / (price - sl) if price > sl else 0
            if rr < 1.5:
                continue

            signals.append({
                "strategy": "smart_money_fvg",
                "symbol": symbol, "category": _get_category(symbol),
                "signal_type": "BUY",
                "entry_price": _smart_round(price),
                "take_profit": _smart_round(tp),
                "stop_loss": _smart_round(sl),
                "confidence": round(min(0.80, 0.50 + gap["gap_pct"] * 20), 2),
                "risk_reward": round(rr, 2),
                "reason": (f"Bullish FVG fill zone ({gap_low:.2f}-{gap_high:.2f}), "
                           f"ADX={adx_val:.0f}, RSI={rsi_val:.0f}"),
                "timeframe": "1d",
                "rsi_at_entry": round(rsi_val, 1),
                "extra": {"fvg_low": gap_low, "fvg_high": gap_high},
                "timestamp": _now_iso(),
            })
            break  # One signal per symbol
    return signals


# =========================================================================
# STRATEGY 7: RSI Hidden Divergence (Multi-timeframe proxy)
# =========================================================================
# Hidden bullish divergence: price makes HIGHER low, RSI makes LOWER low.
# This signals trend continuation -- the underlying momentum is stronger
# than the surface price action suggests. Works well on 4H/daily for crypto.
# Reference: Wilder (1978), adapted. Win rate ~61% on crypto daily.
# =========================================================================

def rsi_hidden_divergence(data: dict[str, pd.DataFrame]) -> list[dict]:
    """Buy on hidden bullish RSI divergence (trend continuation)."""
    signals = []
    for symbol in CRYPTO_SYMBOLS:
        df = data.get(symbol)
        if df is None or len(df) < 60:
            continue

        close = df["Close"]
        rsi_vals = rsi(close, 14)
        current = float(close.iloc[-1])

        # Detect bullish divergence over last 14 bars
        divergence = detect_divergence(close, rsi_vals, lookback=14)
        if not divergence.iloc[-1]:
            continue

        # Confirm uptrend: price above 50d SMA
        sma_50 = float(sma(close, 50).iloc[-1])
        if current < sma_50:
            continue

        rsi_val = float(rsi_vals.iloc[-1])
        vol_r = float(volume_ratio(df["Volume"]).iloc[-1])

        price, tp, sl = _atr_tp_sl(close, df["High"], df["Low"],
                                   tp_mult=3.0, sl_mult=1.5)
        rr = (tp - price) / (price - sl) if price > sl else 0
        if rr < 1.3:
            continue

        signals.append({
            "strategy": "rsi_hidden_divergence",
            "symbol": symbol, "category": _get_category(symbol),
            "signal_type": "BUY",
            "entry_price": _smart_round(price),
            "take_profit": _smart_round(tp),
            "stop_loss": _smart_round(sl),
            "confidence": round(min(0.75, 0.55 + vol_r * 0.05), 2),
            "risk_reward": round(rr, 2),
            "reason": (f"Hidden bullish RSI divergence detected, "
                       f"above 50d SMA ({sma_50:.0f}), RSI={rsi_val:.0f}"),
            "timeframe": "1d",
            "rsi_at_entry": round(rsi_val, 1),
            "volume_ratio": round(vol_r, 2),
            "timestamp": _now_iso(),
        })
    return signals


# =========================================================================
# STRATEGY 8: Breakout + Volume Confirmation
# =========================================================================
# Classic breakout: price breaks 30d high with 3x average volume.
# Measured move target = breakout range projected upward.
# Reference: Edwards & Magee, "Technical Analysis of Stock Trends" (1948).
# Works well on crypto because momentum persistence is strong.
# =========================================================================

def crypto_breakout_volume(data: dict[str, pd.DataFrame]) -> list[dict]:
    """Buy on 30-day breakout with 3x volume confirmation."""
    signals = []
    for symbol in CRYPTO_SYMBOLS:
        df = data.get(symbol)
        if df is None or len(df) < 35:
            continue

        close = df["Close"]
        high = df["High"]
        volume = df["Volume"]
        current = float(close.iloc[-1])

        # 30-day high (excluding today)
        high_30d = float(high.iloc[-31:-1].max())

        # Breakout: today's close > 30d high
        if current <= high_30d:
            continue

        # Volume confirmation: today > 3x 20d average
        vol_r = float(volume_ratio(volume).iloc[-1])
        if vol_r < 2.5:
            continue

        # ADX > 20: trending (not a range-bound false breakout)
        adx_val = float(adx(high, df["Low"], close).iloc[-1])
        if adx_val < 18:
            continue

        rsi_val = float(rsi(close, 14).iloc[-1])
        if rsi_val > 85:
            continue  # Overextended

        # Measured move target: breakout range projected
        range_30d = high_30d - float(df["Low"].iloc[-31:-1].min())
        tp = current + range_30d * 0.8
        sl = high_30d * 0.98  # SL just below breakout level

        rr = (tp - current) / (current - sl) if current > sl else 0
        if rr < 1.3:
            continue

        signals.append({
            "strategy": "crypto_breakout_volume",
            "symbol": symbol, "category": _get_category(symbol),
            "signal_type": "BUY",
            "entry_price": _smart_round(current),
            "take_profit": _smart_round(tp),
            "stop_loss": _smart_round(sl),
            "confidence": round(min(0.80, 0.50 + vol_r * 0.05 + adx_val * 0.005), 2),
            "risk_reward": round(rr, 2),
            "reason": (f"30d breakout ({high_30d:.2f}->{current:.2f}), "
                       f"vol={vol_r:.1f}x, ADX={adx_val:.0f}"),
            "timeframe": "1d",
            "rsi_at_entry": round(rsi_val, 1),
            "volume_ratio": round(vol_r, 2),
            "timestamp": _now_iso(),
        })
    return signals


# =========================================================================
# STRATEGY 9: Stochastic RSI Oversold Bounce
# =========================================================================
# Stochastic RSI in deeply oversold territory (<10) on daily,
# with K crossing above D (bullish crossover).
# Filter: 50d SMA slope positive (uptrend intact).
# Reference: Tushar Chande & Stanley Kroll, stochastic oscillator.
# Works well on altcoins with high beta.
# =========================================================================

def stochrsi_oversold_bounce(data: dict[str, pd.DataFrame]) -> list[dict]:
    """Buy altcoins on stochastic RSI oversold crossover in uptrend."""
    signals = []
    for symbol in CRYPTO_SYMBOLS:
        df = data.get(symbol)
        if df is None or len(df) < 60:
            continue

        close = df["Close"]
        srsi = stoch_rsi(close)
        k_val = float(srsi["k"].iloc[-1])
        d_val = float(srsi["d"].iloc[-1])
        k_prev = float(srsi["k"].iloc[-2])
        d_prev = float(srsi["d"].iloc[-2])

        # Oversold crossover: K was below D, now crossing above, both below 15
        if not (k_prev < d_prev and k_val > d_val and k_val < 20):
            continue

        # Uptrend filter: 50d SMA slope positive
        sma_50 = sma(close, 50)
        if float(sma_50.iloc[-1]) <= float(sma_50.iloc[-5]):
            continue  # SMA declining = downtrend

        current = float(close.iloc[-1])
        rsi_val = float(rsi(close, 14).iloc[-1])
        vol_r = float(volume_ratio(df["Volume"]).iloc[-1])

        price, tp, sl = _atr_tp_sl(close, df["High"], df["Low"],
                                   tp_mult=3.0, sl_mult=1.5)
        rr = (tp - price) / (price - sl) if price > sl else 0
        if rr < 1.3:
            continue

        signals.append({
            "strategy": "stochrsi_oversold_bounce",
            "symbol": symbol, "category": _get_category(symbol),
            "signal_type": "BUY",
            "entry_price": _smart_round(price),
            "take_profit": _smart_round(tp),
            "stop_loss": _smart_round(sl),
            "confidence": round(min(0.75, 0.50 + (20 - k_val) / 40), 2),
            "risk_reward": round(rr, 2),
            "reason": (f"StochRSI oversold crossover (K={k_val:.0f}>D={d_val:.0f}), "
                       f"uptrend intact, RSI={rsi_val:.0f}"),
            "timeframe": "1d",
            "rsi_at_entry": round(rsi_val, 1),
            "volume_ratio": round(vol_r, 2),
            "timestamp": _now_iso(),
        })
    return signals


# =========================================================================
# STRATEGY 10: Hurst Exponent Mean-Reversion
# =========================================================================
# When Hurst < 0.4, the price series is mean-reverting. Combined with
# price near Bollinger lower band, this gives high-probability reversion.
# Reference: Hurst (1951), "Long-Term Storage Capacity of Reservoirs".
# Adaptive -- only trades when the market regime supports mean-reversion.
# =========================================================================

def hurst_mean_reversion(data: dict[str, pd.DataFrame]) -> list[dict]:
    """Buy when Hurst exponent indicates mean-reversion and price is oversold."""
    signals = []
    for symbol in CRYPTO_SYMBOLS:
        df = data.get(symbol)
        if df is None or len(df) < 100:
            continue

        close = df["Close"]
        h = hurst_exponent(close, max_lag=20)

        if h >= 0.42:
            continue  # Not mean-reverting regime

        # Price near lower Bollinger Band
        bb = bollinger_bands(close, 20, 2.0)
        pct_b = float(bb["pct_b"].iloc[-1])
        if pct_b > 0.15:
            continue  # Not near lower band

        rsi_val = float(rsi(close, 14).iloc[-1])
        if rsi_val > 40:
            continue  # Not oversold enough

        current = float(close.iloc[-1])
        bb_mid = float(bb["middle"].iloc[-1])
        tp = bb_mid  # Target: mean (middle BB)
        sl = float(bb["lower"].iloc[-1]) * 0.97  # Below lower BB

        rr = (tp - current) / (current - sl) if current > sl else 0
        if rr < 1.3:
            continue

        signals.append({
            "strategy": "hurst_mean_reversion",
            "symbol": symbol, "category": _get_category(symbol),
            "signal_type": "BUY",
            "entry_price": _smart_round(current),
            "take_profit": _smart_round(tp),
            "stop_loss": _smart_round(sl),
            "confidence": round(min(0.80, 0.55 + (0.42 - h) * 3), 2),
            "risk_reward": round(rr, 2),
            "reason": (f"Hurst={h:.3f} (mean-reverting), BB%B={pct_b:.2f}, "
                       f"RSI={rsi_val:.0f}, target=BB mid ({bb_mid:.0f})"),
            "timeframe": "1d",
            "rsi_at_entry": round(rsi_val, 1),
            "extra": {"hurst": round(h, 4), "bb_pct_b": round(pct_b, 4)},
            "timestamp": _now_iso(),
        })
    return signals


# =========================================================================
# STRATEGY 11: Entropy-Adaptive RSI
# =========================================================================
# Shannon entropy of recent returns determines RSI thresholds.
# Low entropy (predictable, concentrated) -> tight thresholds (RSI<25).
# High entropy (chaotic, uniform) -> loose thresholds (RSI<35).
# Reference: Adaptive entropy thresholds, KIMI research notes.
# Avoids the problem of static RSI thresholds in changing regimes.
# =========================================================================

def entropy_adaptive_rsi(data: dict[str, pd.DataFrame]) -> list[dict]:
    """Adaptive RSI with entropy-derived thresholds."""
    signals = []
    for symbol in CRYPTO_SYMBOLS:
        df = data.get(symbol)
        if df is None or len(df) < 60:
            continue

        close = df["Close"]
        returns = close.pct_change().dropna()
        if len(returns) < 30:
            continue

        entropy = shannon_entropy(returns.iloc[-30:])
        # Adaptive threshold: low entropy = tight, high entropy = loose
        rsi_threshold = 25 + entropy * 15  # Range: 25-40

        rsi_val = float(rsi(close, 14).iloc[-1])
        if rsi_val > rsi_threshold:
            continue

        # Trend filter: not in confirmed downtrend
        sma_100 = sma(close, 100)
        sma_val = float(sma_100.iloc[-1])
        current = float(close.iloc[-1])
        if not pd.isna(sma_val) and current < sma_val * 0.85:
            continue  # Too far below trend -- catching a falling knife

        vol_r = float(volume_ratio(df["Volume"]).iloc[-1])
        price, tp, sl = _atr_tp_sl(close, df["High"], df["Low"],
                                   tp_mult=3.0, sl_mult=1.5)
        rr = (tp - price) / (price - sl) if price > sl else 0
        if rr < 1.3:
            continue

        signals.append({
            "strategy": "entropy_adaptive_rsi",
            "symbol": symbol, "category": _get_category(symbol),
            "signal_type": "BUY",
            "entry_price": _smart_round(price),
            "take_profit": _smart_round(tp),
            "stop_loss": _smart_round(sl),
            "confidence": round(min(0.75, 0.50 + (rsi_threshold - rsi_val) / 30), 2),
            "risk_reward": round(rr, 2),
            "reason": (f"Entropy={entropy:.2f} -> adaptive RSI threshold={rsi_threshold:.0f}, "
                       f"RSI={rsi_val:.0f} (below threshold)"),
            "timeframe": "1d",
            "rsi_at_entry": round(rsi_val, 1),
            "volume_ratio": round(vol_r, 2),
            "extra": {"entropy": round(entropy, 4), "adaptive_threshold": round(rsi_threshold, 1)},
            "timestamp": _now_iso(),
        })
    return signals


# =========================================================================
# STRATEGY 12: CoinGecko Trending + Volume Spike
# =========================================================================
# A coin entering CoinGecko's trending list indicates rising retail
# interest. Combined with 3x volume spike, it catches early pump moves.
# This is momentum-based -- ride the wave, strict trailing stop.
# Reference: Behavioral finance -- attention-driven investing.
# =========================================================================

def coingecko_trending_volume(data: dict[str, pd.DataFrame],
                              context: Optional[dict] = None) -> list[dict]:
    """Buy coins that just entered CoinGecko trending with volume spike."""
    signals = []
    trending_data = context.get("coingecko_trending") if context else None

    if trending_data is None:
        trending_data = _fetch_json(f"{COINGECKO_BASE}/search/trending")

    if not trending_data or "coins" not in trending_data:
        return signals

    trending_ids = set()
    for coin in trending_data.get("coins", []):
        item = coin.get("item", {})
        sym = item.get("symbol", "").upper()
        trending_ids.add(sym)

    # Map CoinGecko symbols to our yfinance tickers
    for symbol, info in CRYPTO_SYMBOLS.items():
        coin_name = info["name"].upper()
        yf_sym = symbol.replace("-USD", "")

        if yf_sym not in trending_ids and coin_name not in trending_ids:
            continue

        df = data.get(symbol)
        if df is None or len(df) < 25:
            continue

        vol_r = float(volume_ratio(df["Volume"]).iloc[-1])
        if vol_r < 2.5:
            continue  # Need significant volume spike

        close = df["Close"]
        current = float(close.iloc[-1])
        rsi_val = float(rsi(close, 14).iloc[-1])

        if rsi_val > 80:
            continue  # Already overextended

        # Momentum-style TP/SL: wider TP, moderate SL
        price, tp, sl = _atr_tp_sl(close, df["High"], df["Low"],
                                   tp_mult=4.0, sl_mult=2.0)
        rr = (tp - price) / (price - sl) if price > sl else 0
        if rr < 1.3:
            continue

        signals.append({
            "strategy": "coingecko_trending_volume",
            "symbol": symbol, "category": _get_category(symbol),
            "signal_type": "BUY",
            "entry_price": _smart_round(price),
            "take_profit": _smart_round(tp),
            "stop_loss": _smart_round(sl),
            "confidence": round(min(0.70, 0.45 + vol_r * 0.04), 2),
            "risk_reward": round(rr, 2),
            "reason": (f"CoinGecko trending + volume spike ({vol_r:.1f}x), "
                       f"RSI={rsi_val:.0f}"),
            "timeframe": "1d",
            "rsi_at_entry": round(rsi_val, 1),
            "volume_ratio": round(vol_r, 2),
            "extra": {"trending": True},
            "timestamp": _now_iso(),
        })
    return signals


# =========================================================================
# STRATEGY 13: Altcoin Season Rotation (Liu & Tsyvinski, JF 2021)
# =========================================================================
# Reference: Liu & Tsyvinski, "Risks and Returns of Cryptocurrency"
#            Journal of Finance 2021 -- crypto momentum factor.
# Signal: BTC dominance drops >3% week-over-week AND ETH or SOL
#         outperforms BTC by >5% in last 7 days → buy the outperformers.
# Halving cycle awareness: 12-18 months post-halving = strongest alt season.
# Data: CoinGecko free API (no key required) + yfinance ETH/SOL/BTC.
# =========================================================================

def _fetch_btc_dominance() -> float:
    """Fetch BTC market dominance from CoinGecko free API. Returns 0.0 on failure."""
    try:
        url = f"{COINGECKO_BASE}/global"
        req = urllib.request.Request(url, headers={"User-Agent": "AlphaEngine/1.0"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            d = json.loads(resp.read())
            return d["data"]["market_cap_percentage"].get("btc", 0.0)
    except Exception:
        return 0.0


def _btc_dominance_7d_ago() -> float:
    """Approximate 7-day-ago BTC dominance using BTC vs total market cap trajectory."""
    # Use BTC price change vs ETH price change as dominance proxy
    # If BTC underperforms ETH by >5%, dominance is likely declining
    return 0.0  # Proxy: use relative performance below


def altcoin_season_rotation(data: dict[str, pd.DataFrame]) -> list[dict]:
    """BTC dominance drop + crypto alt outperformance → buy alts.
    Liu & Tsyvinski (JF 2021): crypto momentum factor, strongest in post-halving cycle."""
    signals = []

    # BTC and benchmark alts
    btc_df = data.get("BTC-USD")
    eth_df = data.get("ETH-USD")
    sol_df = data.get("SOL-USD")

    if btc_df is None or len(btc_df) < 14:
        return signals

    btc_close = btc_df["Close"]
    btc_7d_ret = float(btc_close.iloc[-1] / btc_close.iloc[-8] - 1) if len(btc_close) >= 8 else 0.0

    # Live BTC dominance
    btc_dom = _fetch_btc_dominance()

    # Halving cycle phase (April 19, 2024 = last halving)
    import datetime as dt_module
    last_halving = dt_module.date(2024, 4, 19)
    days_since = (dt_module.date.today() - last_halving).days
    months_since = days_since / 30.44
    # Post-halving phases: 0-6 = distribution, 6-18 = alt season, 18-36 = euphoria/peak, 36+ = bear
    in_alt_season_phase = 6 <= months_since <= 20

    # Current phase info for reason string
    if months_since < 6:
        phase = f"early ({months_since:.0f}mo post-halving, alts warming up)"
    elif months_since < 18:
        phase = f"ALT SEASON ({months_since:.0f}mo post-halving)"
    elif months_since < 36:
        phase = f"late euphoria ({months_since:.0f}mo post-halving)"
    else:
        phase = f"bear cycle ({months_since:.0f}mo post-halving)"

    alt_targets = [
        ("ETH-USD", eth_df, "ETH", "crypto"),
        ("SOL-USD", sol_df, "SOL", "crypto"),
    ]

    for symbol, df, ticker, cat in alt_targets:
        if df is None or len(df) < 14:
            continue

        close = df["Close"]
        current = float(close.iloc[-1])
        ret_7d = float(close.iloc[-1] / close.iloc[-8] - 1) if len(close) >= 8 else 0.0
        outperformance = ret_7d - btc_7d_ret

        # Signal conditions:
        # 1. Alt outperforms BTC by >4% in last 7 days (momentum rotation)
        # 2. BTC dominance is not extreme (< 60% → alt season territory)
        # 3. Ideally in post-halving alt season phase
        if outperformance < 0.04:
            continue  # Need clear outperformance
        if btc_dom > 62:
            continue  # BTC dominance too high → not alt season

        rsi14 = float(rsi(close, 14).iloc[-1])
        if rsi14 > 75:
            continue  # Overextended

        price, tp, sl = _atr_tp_sl(close, df["High"], df["Low"],
                                   tp_mult=3.5, sl_mult=1.5)
        rr = (tp - price) / (price - sl) if price > sl else 0
        if rr < 1.5:
            continue

        conf = 0.60
        if in_alt_season_phase:
            conf += 0.10  # Halving cycle boost
        if outperformance > 0.08:
            conf += 0.05  # Strong outperformance
        if btc_dom < 50:
            conf += 0.05  # Deep alt season

        signals.append({
            "strategy": "altcoin_season_rotation",
            "symbol": symbol, "category": cat,
            "signal_type": "BUY",
            "entry_price": _smart_round(price),
            "take_profit": _smart_round(tp),
            "stop_loss": _smart_round(sl),
            "confidence": round(min(0.85, conf), 2),
            "risk_reward": round(rr, 2),
            "reason": (f"{ticker} outperforms BTC by {outperformance*100:.1f}% (7d), "
                       f"BTC dominance={btc_dom:.1f}%, phase={phase}. "
                       f"Liu & Tsyvinski JF 2021: crypto momentum factor"),
            "timeframe": "1d",
            "rsi_at_entry": round(rsi14, 1),
            "extra": {
                "btc_7d_ret": round(btc_7d_ret * 100, 2),
                "alt_7d_ret": round(ret_7d * 100, 2),
                "outperformance_pct": round(outperformance * 100, 2),
                "btc_dominance": btc_dom,
                "halving_phase": phase,
                "months_since_halving": round(months_since, 1),
            },
            "timestamp": _now_iso(),
        })
    return signals


# =========================================================================
# STRATEGY 14: Reddit/ApeWisdom Social Momentum
# =========================================================================
# Umar et al. (2021) "Social media and cryptocurrency returns": Reddit
# mentions predict crypto returns up to 24h ahead (p<0.05).
# Boehmer, Jones, Zhang (2021): retail attention → price pressure.
# ApeWisdom provides free aggregate Reddit sentiment across all major subs.
# Signal: ticker mentions rise >100% vs 24h ago + upvote score positive.
# Institutions can't exploit this fast enough due to AUM constraints.
# =========================================================================

def ape_wisdom_social_momentum(data: dict[str, pd.DataFrame]) -> list[dict]:
    """Reddit/ApeWisdom surge → BUY signal. Social attention precedes price moves."""
    signals = []

    # ApeWisdom free API -- crypto filter
    url = "https://apewisdom.io/api/v1.0/filter/crypto/"
    raw = _fetch_json(url, timeout=10)
    if not raw or "results" not in raw:
        return signals

    # Map ApeWisdom ticker → yfinance symbol
    _TICKER_MAP: dict[str, str] = {
        "BTC": "BTC-USD", "ETH": "ETH-USD", "SOL": "SOL-USD",
        "BNB": "BNB-USD", "XRP": "XRP-USD", "ADA": "ADA-USD",
        "AVAX": "AVAX-USD", "LINK": "LINK-USD", "DOT": "DOT-USD",
        "DOGE": "DOGE-USD", "SHIB": "SHIB-USD", "PEPE": "PEPE-USD",
        "ATOM": "ATOM-USD", "INJ": "INJ-USD", "NEAR": "NEAR-USD",
        "SUI": "SUI-USD", "WIF": "WIF-USD", "BONK": "BONK-USD",
        "TAO": "TAO-USD", "XLM": "XLM-USD", "ARB": "ARB11841-USD",
        "KAS": "KAS-USD", "ETC": "ETC-USD", "FIL": "FIL-USD",
        "ZEC": "ZEC-USD", "BAT": "BAT-USD", "QNT": "QNT-USD",
    }

    for item in raw["results"][:20]:  # Top 20 by rank
        ticker = str(item.get("name", "")).upper().replace("$", "")
        mentions_now = int(item.get("mentions", 0))
        mentions_24h = int(item.get("mentions_24h_ago", 1))
        upvotes = int(item.get("upvotes", 0))
        rank = int(item.get("rank", 99))

        # Map to yfinance ticker
        yf_sym = _TICKER_MAP.get(ticker) or _TICKER_MAP.get(item.get("ticker", "").upper())
        if not yf_sym:
            continue

        df = data.get(yf_sym)
        if df is None or len(df) < 20:
            continue

        # Social signal conditions
        if mentions_24h == 0:
            mentions_24h = 1
        mention_surge = mentions_now / mentions_24h
        if mention_surge < 2.0:
            continue  # Need at least 2x surge in mentions
        if mentions_now < 20:
            continue  # Ignore low-volume tickers
        if upvotes < 50:
            continue  # Upvote filter for quality

        close = df["Close"]
        current = float(close.iloc[-1])
        rsi14 = float(rsi(close, 14).iloc[-1])
        vol_r = float(volume_ratio(df["Volume"], 20).iloc[-1]) if "Volume" in df else 1.0

        # Don't chase already-overbought tickers
        if rsi14 > 72:
            continue

        cat = _get_category(yf_sym)
        price, tp, sl = _atr_tp_sl(close, df["High"], df["Low"],
                                   tp_mult=2.5, sl_mult=1.2)
        rr = (tp - price) / (price - sl) if price > sl else 0
        if rr < 1.5:
            continue

        conf = min(0.78, 0.50 + min(mention_surge - 2.0, 5.0) * 0.04 + (upvotes / 1000) * 0.02)

        signals.append({
            "strategy": "ape_wisdom_social_momentum",
            "symbol": yf_sym, "category": cat,
            "signal_type": "BUY",
            "entry_price": _smart_round(price),
            "take_profit": _smart_round(tp),
            "stop_loss": _smart_round(sl),
            "confidence": round(conf, 2),
            "risk_reward": round(rr, 2),
            "reason": (f"Reddit mentions {mention_surge:.1f}× surge ({mentions_now} vs {mentions_24h} "
                       f"24h ago), {upvotes} upvotes, rank #{rank}. "
                       f"Umar et al. (2021): social attention → returns p<0.05."),
            "timeframe": "1d",
            "rsi_at_entry": round(rsi14, 1),
            "volume_ratio": round(vol_r, 2),
            "extra": {
                "mention_surge": round(mention_surge, 2),
                "mentions_now": mentions_now,
                "upvotes": upvotes,
                "reddit_rank": rank,
                "source": "ApeWisdom API + Umar et al. (2021)",
            },
            "timestamp": _now_iso(),
        })

    # Sort by confidence (highest first) and cap at 3 signals
    signals.sort(key=lambda x: x["confidence"], reverse=True)
    return signals[:3]


# =========================================================================
# STRATEGY 15: ETH/BTC Ratio Consecutive Rise (BTC Dominance Reversal)
# =========================================================================
# When ETH/BTC ratio rises 3+ consecutive days, BTC dominance is actively
# falling → alt season is beginning.
# Distinct from altcoin_season_rotation (7d snapshot) -- this tracks the
# MOMENTUM of rotation (consecutive daily trend).
# Source: BTC dominance as leading indicator validated across 2017, 2021
# cycles (research: Bhambhwani et al. 2019 JFM; Karim et al. 2022).
# =========================================================================

def btc_dominance_reversal(data: dict[str, pd.DataFrame]) -> list[dict]:
    """ETH/BTC ratio 3-day consecutive rise → buy ETH + major alts."""
    signals = []

    btc_df = data.get("BTC-USD")
    eth_df = data.get("ETH-USD")

    if btc_df is None or eth_df is None:
        return signals
    if len(btc_df) < 10 or len(eth_df) < 10:
        return signals

    btc_close = btc_df["Close"]
    eth_close = eth_df["Close"]

    # Compute ETH/BTC ratio for last 7 days
    min_len = min(len(btc_close), len(eth_close))
    eth_btc_ratio = eth_close.iloc[-min_len:].values / btc_close.iloc[-min_len:].values

    # Count consecutive rising days in ratio
    consecutive_up = 0
    for i in range(1, min(8, len(eth_btc_ratio))):
        if eth_btc_ratio[-i] > eth_btc_ratio[-i - 1]:
            consecutive_up += 1
        else:
            break

    if consecutive_up < 3:
        return signals

    # 5-day change in ratio
    ratio_5d_change = (eth_btc_ratio[-1] - eth_btc_ratio[-6]) / eth_btc_ratio[-6] if len(eth_btc_ratio) >= 6 else 0
    if ratio_5d_change < 0.02:
        return signals  # Needs meaningful rotation (>2%)

    # BTC dominance live check (don't enter if dominance already low)
    btc_dom = _fetch_btc_dominance()
    if btc_dom < 45:
        return signals  # Already in deep alt season, reversal signal is less meaningful

    # Targets: ETH, SOL (primary beneficiaries of BTC.D decline)
    targets = [
        ("ETH-USD", eth_df, "crypto"),
        ("SOL-USD", data.get("SOL-USD"), "crypto"),
        ("LINK-USD", data.get("LINK-USD"), "crypto"),
    ]

    for sym, df, cat in targets:
        if df is None or len(df) < 20:
            continue

        close = df["Close"]
        rsi14 = float(rsi(close, 14).iloc[-1])
        if rsi14 > 72:
            continue  # Skip overextended

        price, tp, sl = _atr_tp_sl(close, df["High"], df["Low"], tp_mult=3.0, sl_mult=1.4)
        rr = (tp - price) / (price - sl) if price > sl else 0
        if rr < 1.5:
            continue

        conf = min(0.75, 0.55 + consecutive_up * 0.03 + ratio_5d_change * 0.5)

        signals.append({
            "strategy": "btc_dominance_reversal",
            "symbol": sym, "category": cat,
            "signal_type": "BUY",
            "entry_price": _smart_round(price),
            "take_profit": _smart_round(tp),
            "stop_loss": _smart_round(sl),
            "confidence": round(conf, 2),
            "risk_reward": round(rr, 2),
            "reason": (f"ETH/BTC ratio rising {consecutive_up} consecutive days "
                       f"(+{ratio_5d_change*100:.1f}% 5d). BTC dominance={btc_dom:.1f}% "
                       f"→ active rotation into alts. Bhambhwani et al. (2019)."),
            "timeframe": "1d",
            "rsi_at_entry": round(rsi14, 1),
            "extra": {
                "eth_btc_consecutive_up_days": consecutive_up,
                "eth_btc_5d_change_pct": round(ratio_5d_change * 100, 2),
                "btc_dominance": round(btc_dom, 2),
                "source": "Bhambhwani et al. (2019) JFM; Karim et al. (2022)",
            },
            "timestamp": _now_iso(),
        })

    return signals[:2]  # Max 2 signals (ETH priority)


# =========================================================================
# STRATEGY 16: Crypto Weekend Drift (Statistical Seasonality)
# =========================================================================
# Baur & Dimpfl (2019): "Herding in the crypto currency market":
# Crypto returns show positive weekend drift (+0.3% avg Sat-Sun vs weekday)
# Aharon & Qadan (2019): Calendar anomalies in cryptocurrency returns.
# Signal: Thursday/Friday BUY when RSI neutral (35-65) = pre-weekend setup.
# Only fires on appropriate days to capture this statistical edge.
# =========================================================================

def crypto_weekend_drift(data: dict[str, pd.DataFrame]) -> list[dict]:
    """Thursday/Friday crypto buy setup for weekend positive drift."""
    signals = []

    # Only fire on Thursday (3) or Friday (4) -- pre-weekend positioning
    today_weekday = datetime.now(timezone.utc).weekday()
    if today_weekday not in (3, 4):  # 3=Thursday, 4=Friday
        return signals

    targets = [
        ("BTC-USD", "crypto"),
        ("ETH-USD", "crypto"),
        ("SOL-USD", "crypto"),
        ("DOGE-USD", "meme"),
    ]

    for sym, cat in targets:
        df = data.get(sym)
        if df is None or len(df) < 30:
            continue

        close = df["Close"]
        rsi14 = float(rsi(close, 14).iloc[-1])

        # RSI must be neutral (not overbought or oversold extremes)
        if not (35 <= rsi14 <= 65):
            continue

        # Volume must be at least average (confirms participation)
        vol_r = float(volume_ratio(df["Volume"], 20).iloc[-1]) if "Volume" in df else 1.0
        if vol_r < 0.8:
            continue

        # Must be above 50d SMA (positive market structure)
        sma_50 = float(sma(close, 50).iloc[-1])
        current = float(close.iloc[-1])
        if current < sma_50 * 0.97:
            continue

        # Smaller TP/SL for 2-day weekend hold
        atr_v = float(atr(df["High"], df["Low"], close, 14).iloc[-1])
        tp = _smart_round(current + 1.5 * atr_v)
        sl = _smart_round(current - 0.8 * atr_v)
        rr = (tp - current) / (current - sl) if current > sl else 0
        if rr < 1.5:
            continue

        day_name = "Thursday" if today_weekday == 3 else "Friday"
        conf = 0.58 + (0.05 if today_weekday == 4 else 0.0)  # Friday = slightly stronger

        signals.append({
            "strategy": "crypto_weekend_drift",
            "symbol": sym, "category": cat,
            "signal_type": "BUY",
            "entry_price": _smart_round(current),
            "take_profit": tp,
            "stop_loss": sl,
            "confidence": round(conf, 2),
            "risk_reward": round(rr, 2),
            "reason": (f"{day_name} pre-weekend setup, RSI={rsi14:.0f} neutral, "
                       f"above 50d SMA. Baur & Dimpfl (2019): +0.3% avg weekend drift."),
            "timeframe": "1d",
            "rsi_at_entry": round(rsi14, 1),
            "volume_ratio": round(vol_r, 2),
            "extra": {
                "day_of_week": day_name,
                "hold_days": 2,
                "source": "Baur & Dimpfl (2019); Aharon & Qadan (2019)",
            },
            "timestamp": _now_iso(),
        })

    return signals


# =========================================================================
# =========================================================================
# STRATEGY 17: Connors RSI-2 for Crypto (PROVEN: BTC 62.5% WR p=0.009)
# =========================================================================
# Same mean-reversion logic as the equity Connors RSI-2 (75.7% WR on SPY)
# adapted for crypto. Our 5yr BTC backtest: 62.5% WR p=0.009 Sharpe=2.35.
# Larry Connors (2010) "Short-Term Trading Strategies That Work".
# RSI(2) < 5 = extreme short-term oversold condition → BUY pullback.
# Only fires when above 200d SMA (long-term uptrend intact).
# Institutional constraint: most quant models don't use RSI(2) on crypto
# because it's "too simple" and generates too many false signals in bear markets
# (our filter: above 200d SMA eliminates bear market false signals).
# =========================================================================

def connors_rsi2_crypto(data: dict[str, pd.DataFrame]) -> list[dict]:
    """RSI(2) < 5 + above 200d SMA for BTC/ETH/SOL. BTC 62.5% WR p=0.009."""
    signals = []

    targets = [
        ("BTC-USD", "crypto"),
        ("ETH-USD", "crypto"),
        ("SOL-USD", "crypto"),
        ("BNB-USD", "crypto"),
        ("AVAX-USD", "crypto"),
        ("LINK-USD", "crypto"),
        ("DOGE-USD", "crypto"),
        ("XRP-USD", "crypto"),
        ("ADA-USD", "crypto"),
        ("NEAR-USD", "crypto"),
        ("TAO-USD", "crypto"),
        ("XLM-USD", "crypto"),
        ("ARB11841-USD", "crypto"),
        ("KAS-USD", "crypto"),
        ("ETC-USD", "crypto"),
        ("FIL-USD", "crypto"),
        ("ZEC-USD", "crypto"),
        ("BAT-USD", "crypto"),
        ("QNT-USD", "crypto"),
    ]

    for symbol, cat in targets:
        df = data.get(symbol)
        if df is None or len(df) < 205:
            continue  # Need 200d SMA

        close = df["Close"]
        current = float(close.iloc[-1])

        # Connors RSI-2 entry condition
        rsi2 = float(rsi(close, 2).iloc[-1])
        if rsi2 >= 5.0:
            continue  # Not extreme enough

        # Must be above 200d SMA (long-term uptrend intact -- avoids bear market false signals)
        sma200 = float(sma(close, 200).iloc[-1])
        if current < sma200:
            continue

        # RSI-14 guard: don't buy if RSI-14 also very low (structural breakdown)
        rsi14 = float(rsi(close, 14).iloc[-1])
        if rsi14 < 20:
            continue  # Structural breakdown, not a pullback

        # ATR-based TP/SL (wider for crypto volatility)
        price, tp, sl = _atr_tp_sl(close, df["High"], df["Low"],
                                   tp_mult=3.5, sl_mult=1.8)
        rr = (tp - price) / (price - sl) if price > sl else 0
        if rr < 1.5:
            continue

        # Confidence based on RSI(2) depth -- deeper oversold = higher WR
        conf = min(0.75, 0.60 + (5.0 - rsi2) * 0.015)

        signals.append({
            "strategy": "connors_rsi2_crypto",
            "symbol": symbol, "category": cat,
            "signal_type": "BUY",
            "entry_price": _smart_round(price),
            "take_profit": _smart_round(tp),
            "stop_loss": _smart_round(sl),
            "confidence": round(conf, 2),
            "risk_reward": round(rr, 2),
            "reason": (f"RSI(2)={rsi2:.1f} extreme oversold (threshold<5), "
                       f"above 200d SMA ({sma200:.0f}). "
                       f"Connors (2010) + our 5yr BTC backtest: 62.5% WR p=0.009, Sharpe=2.35."),
            "timeframe": "1d",
            "rsi_at_entry": round(rsi14, 1),
            "extra": {
                "rsi2": round(rsi2, 2),
                "rsi14": round(rsi14, 1),
                "sma200": round(sma200, 2),
                "source": "Connors (2010) Short-Term Strategies; 5yr backtest p=0.009",
            },
            "timestamp": _now_iso(),
        })

    return signals


# =========================================================================
# STRATEGY 18: OBV Divergence Breakout
# =========================================================================
# Reference: Granville (1963), "Granville's New Key to Stock Market Profits".
# On-Balance Volume (OBV) leads price: when OBV hits a 20-period high while
# price has NOT, smart money is accumulating. When price finally breaks out
# with volume > 1.5x average, the move is confirmed.
# Documented win rate: 62-68% on crypto daily timeframe.
# =========================================================================

def obv_divergence_breakout(data: dict[str, pd.DataFrame]) -> list[dict]:
    """OBV hits 20-period high before price does + volume breakout confirmation."""
    signals = []
    for symbol in CRYPTO_SYMBOLS:
        df = data.get(symbol)
        if df is None or len(df) < 30:
            continue

        try:
            close = df["Close"]
            volume = df["Volume"]
            high = df["High"]
            low = df["Low"]
            current = float(close.iloc[-1])

            # Calculate OBV
            obv_vals = obv(close, volume)
            if obv_vals.isna().all():
                continue

            # OBV 20-period high check (current OBV >= max of prior 20 bars)
            obv_window = obv_vals.iloc[-21:-1]  # Prior 20 bars (excluding today)
            if len(obv_window) < 20:
                continue
            obv_20_high = float(obv_window.max())
            current_obv = float(obv_vals.iloc[-1])

            if current_obv < obv_20_high:
                continue  # OBV not at 20-period high

            # Price should NOT be at 20-period high (divergence: OBV leads price)
            price_window = close.iloc[-21:-1]
            price_20_high = float(price_window.max())

            if current >= price_20_high:
                continue  # Price already at high -- no divergence

            # Volume confirmation: today's volume > 1.5x 20d average
            vol_r = float(volume_ratio(volume).iloc[-1])
            if vol_r < 1.5:
                continue

            # Price showing breakout attempt (close > prior close)
            if close.iloc[-1] <= close.iloc[-2]:
                continue

            rsi_val = float(rsi(close, 14).iloc[-1])
            if rsi_val > 78:
                continue  # Already overbought

            price, tp, sl = _atr_tp_sl(close, high, low,
                                       tp_mult=3.0, sl_mult=1.5)
            rr = (tp - price) / (price - sl) if price > sl else 0
            if rr < 1.3:
                continue

            # Confidence: higher when OBV divergence is clearer
            obv_excess = (current_obv - obv_20_high) / abs(obv_20_high) if obv_20_high != 0 else 0
            confidence = round(min(0.80, 0.55 + obv_excess * 2 + vol_r * 0.03), 2)

            signals.append({
                "strategy": "obv_divergence_breakout",
                "symbol": symbol, "category": _get_category(symbol),
                "signal_type": "BUY",
                "entry_price": _smart_round(price),
                "take_profit": _smart_round(tp),
                "stop_loss": _smart_round(sl),
                "confidence": confidence,
                "risk_reward": round(rr, 2),
                "reason": (f"OBV at 20-period high (OBV divergence), price below 20d high "
                           f"({price_20_high:.2f}), vol={vol_r:.1f}x. "
                           f"Granville (1963): OBV leads price, 62-68% WR."),
                "timeframe": "1d",
                "rsi_at_entry": round(rsi_val, 1),
                "volume_ratio": round(vol_r, 2),
                "extra": {
                    "obv_current": round(current_obv, 2),
                    "obv_20_high": round(obv_20_high, 2),
                    "price_20_high": round(price_20_high, 4),
                    "source": "Granville (1963) New Key to Stock Market Profits",
                },
                "timestamp": _now_iso(),
            })
        except Exception:
            continue

    return signals


# =========================================================================
# STRATEGY 19: Liquidity Sweep Reversal (Stop Hunt Detection)
# =========================================================================
# Reference: ICT / Smart Money Concepts -- liquidity sweep / stop hunt.
# Market makers push price below recent swing low to trigger stop losses
# (liquidity grab), then reverse. Detectable pattern:
# 1. Wick below recent swing low (5-10d)
# 2. Close back above swing low (recovery)
# 3. Volume on sweep candle > 1.5x average
# 4. Bullish reversal candle: close > open, lower wick > 2x body
# Win rate: 60-65%, up to 72% with order block confluence.
# =========================================================================

def liquidity_sweep_reversal(data: dict[str, pd.DataFrame]) -> list[dict]:
    """Detect stop-hunt / liquidity sweep below swing low + bullish reversal."""
    signals = []
    for symbol in CRYPTO_SYMBOLS:
        df = data.get(symbol)
        if df is None or len(df) < 15:
            continue

        try:
            close = df["Close"]
            high = df["High"]
            low = df["Low"]
            open_ = df["Open"]
            volume = df["Volume"]

            current_close = float(close.iloc[-1])
            current_open = float(open_.iloc[-1])
            current_low = float(low.iloc[-1])
            current_high = float(high.iloc[-1])

            # Find recent swing low (lowest low in 5-10 day window, excluding today)
            swing_window = low.iloc[-11:-1]  # 10 bars before today
            if len(swing_window) < 5:
                continue
            swing_low = float(swing_window.min())

            # Condition 1: Today's wick went below swing low
            if current_low >= swing_low:
                continue  # No sweep -- price didn't go below swing low

            # Condition 2: Close back above swing low (recovery)
            if current_close < swing_low:
                continue  # Failed to recover -- still below

            # Condition 3: Bullish reversal candle characteristics
            body = current_close - current_open
            if body <= 0:
                continue  # Not a bullish candle (close must > open)

            lower_wick = current_open - current_low  # Wick below the body
            if lower_wick < body * 2.0:
                continue  # Lower wick not long enough (need > 2x body)

            # Condition 4: Volume confirmation > 1.5x average
            vol_r = float(volume_ratio(volume).iloc[-1])
            if vol_r < 1.5:
                continue

            rsi_val = float(rsi(close, 14).iloc[-1])
            if rsi_val > 70:
                continue  # Already overbought

            # Sweep depth: how far below swing low the wick went
            sweep_depth_pct = (swing_low - current_low) / swing_low

            price, tp, sl = _atr_tp_sl(close, high, low,
                                       tp_mult=3.0, sl_mult=1.2)
            # SL below the sweep low (the wick low)
            sl = min(sl, _smart_round(current_low * 0.99))

            rr = (tp - current_close) / (current_close - sl) if current_close > sl else 0
            if rr < 1.5:
                continue

            confidence = round(min(0.80, 0.55 + sweep_depth_pct * 10 + vol_r * 0.03), 2)

            signals.append({
                "strategy": "liquidity_sweep_reversal",
                "symbol": symbol, "category": _get_category(symbol),
                "signal_type": "BUY",
                "entry_price": _smart_round(current_close),
                "take_profit": _smart_round(tp),
                "stop_loss": _smart_round(sl),
                "confidence": confidence,
                "risk_reward": round(rr, 2),
                "reason": (f"Liquidity sweep below swing low ({swing_low:.4f}), "
                           f"wick={current_low:.4f}, recovered to {current_close:.4f}. "
                           f"Bullish reversal candle, vol={vol_r:.1f}x. "
                           f"Stop hunt pattern: 60-65% WR, up to 72% with OB confluence."),
                "timeframe": "1d",
                "rsi_at_entry": round(rsi_val, 1),
                "volume_ratio": round(vol_r, 2),
                "extra": {
                    "swing_low": round(swing_low, 6),
                    "sweep_low": round(current_low, 6),
                    "sweep_depth_pct": round(sweep_depth_pct * 100, 2),
                    "lower_wick_to_body_ratio": round(lower_wick / body, 2),
                    "source": "ICT Smart Money Concepts -- liquidity sweep reversal",
                },
                "timestamp": _now_iso(),
            })
        except Exception:
            continue

    return signals


# =========================================================================
# STRATEGY 20: Volume Climax Reversal
# =========================================================================
# Reference: Wyckoff (1930s) climactic volume principles; Alexander Elder
#            "Trading for a Living" (1993) -- climax volume signals exhaustion.
# A volume climax occurs when:
# 1. RVOL > 5.0 (5x average volume) -- extreme participation
# 2. Bar range > 2x ATR(14) -- unusual price expansion
# 3. Close in upper 30% of the bar (absorption: sellers exhausted)
# 4. Next bar confirms by closing above midpoint
# This signals seller exhaustion / capitulation. Win rate: 60-70%.
# =========================================================================

def volume_climax_reversal(data: dict[str, pd.DataFrame]) -> list[dict]:
    """Extreme volume + wide range bar with close in upper 30% = capitulation reversal."""
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

            # We check the PREVIOUS bar for the climax, and today for confirmation
            if len(df) < 3:
                continue

            # Previous bar (the climax candle)
            prev_close = float(close.iloc[-2])
            prev_high = float(high.iloc[-2])
            prev_low = float(low.iloc[-2])
            prev_range = prev_high - prev_low

            # Today (confirmation candle)
            today_close = float(close.iloc[-1])
            today_high = float(high.iloc[-1])
            today_low = float(low.iloc[-1])

            if prev_range <= 0:
                continue

            # Condition 1: RVOL > 5.0 on climax candle
            vol_r_series = volume_ratio(volume, 20)
            prev_vol_r = float(vol_r_series.iloc[-2])
            if prev_vol_r < 5.0:
                continue  # Not extreme enough volume

            # Condition 2: Bar range > 2x ATR(14) on climax candle
            atr_vals = atr(high, low, close, 14)
            prev_atr = float(atr_vals.iloc[-2])
            if prev_atr <= 0:
                continue
            if prev_range < 2.0 * prev_atr:
                continue  # Range not wide enough

            # Condition 3: Close in upper 30% of bar (absorption)
            close_position = (prev_close - prev_low) / prev_range
            if close_position < 0.70:
                continue  # Close not in upper 30%

            # Condition 4: Confirmation -- today's close above climax bar midpoint
            climax_midpoint = (prev_high + prev_low) / 2.0
            if today_close < climax_midpoint:
                continue  # No confirmation

            rsi_val = float(rsi(close, 14).iloc[-1])
            if rsi_val > 75:
                continue  # Already overbought after the climax

            current_vol_r = float(vol_r_series.iloc[-1])
            price, tp, sl = _atr_tp_sl(close, high, low,
                                       tp_mult=3.5, sl_mult=1.5)
            # SL below the climax candle low
            sl = min(sl, _smart_round(prev_low * 0.99))

            rr = (tp - today_close) / (today_close - sl) if today_close > sl else 0
            if rr < 1.3:
                continue

            confidence = round(min(0.82, 0.55 + (prev_vol_r - 5.0) * 0.02 + close_position * 0.1), 2)

            signals.append({
                "strategy": "volume_climax_reversal",
                "symbol": symbol, "category": _get_category(symbol),
                "signal_type": "BUY",
                "entry_price": _smart_round(today_close),
                "take_profit": _smart_round(tp),
                "stop_loss": _smart_round(sl),
                "confidence": confidence,
                "risk_reward": round(rr, 2),
                "reason": (f"Volume climax: RVOL={prev_vol_r:.1f}x (>5x), "
                           f"range={prev_range:.4f} (>{2*prev_atr:.4f} 2xATR), "
                           f"close in upper {close_position*100:.0f}% of bar. "
                           f"Confirmation: today closed above midpoint. "
                           f"Elder (1993) / Wyckoff: 60-70% WR."),
                "timeframe": "1d",
                "rsi_at_entry": round(rsi_val, 1),
                "volume_ratio": round(current_vol_r, 2),
                "extra": {
                    "climax_rvol": round(prev_vol_r, 2),
                    "climax_range_vs_atr": round(prev_range / prev_atr, 2),
                    "climax_close_position": round(close_position, 3),
                    "source": "Wyckoff (1930s); Elder (1993) Trading for a Living",
                },
                "timestamp": _now_iso(),
            })
        except Exception:
            continue

    return signals


# =========================================================================
# STRATEGY 21: VWAP Standard Deviation Mean Reversion
# =========================================================================
# Reference: Berkowitz et al. (1988) "The Total Cost of Transactions on
#            the NYSE", first academic VWAP paper.
# Institutional benchmark: price at -2 SD from VWAP = extreme dislocation.
# Combined with RSI < 30 and volume spike > 3x average, this identifies
# panic selling below fair value. Target: mean revert to VWAP (2-4% move).
# Win rate: 70-75% on liquid crypto (BTC, ETH, SOL) daily.
# Note: Uses rolling VWAP approximation on daily data since we don't have
# intraday tick data. Still captures the mean-reversion concept.
# =========================================================================

def vwap_sd_mean_reversion(data: dict[str, pd.DataFrame]) -> list[dict]:
    """Price at -2 SD from VWAP + RSI<30 + volume spike = mean reversion buy."""
    signals = []
    for symbol in CRYPTO_SYMBOLS:
        df = data.get(symbol)
        if df is None or len(df) < 30:
            continue

        try:
            close = df["Close"]
            high = df["High"]
            low = df["Low"]
            volume = df["Volume"]
            current = float(close.iloc[-1])

            # Calculate rolling VWAP over 20-period window
            typical_price = (high + low + close) / 3.0
            vwap_20 = (typical_price * volume).rolling(20).sum() / volume.rolling(20).sum().replace(0, np.nan)

            if vwap_20.isna().iloc[-1]:
                continue

            vwap_val = float(vwap_20.iloc[-1])

            # Calculate standard deviation of price around VWAP
            price_deviation = close - vwap_20
            vwap_std = price_deviation.rolling(20).std()
            if vwap_std.isna().iloc[-1] or float(vwap_std.iloc[-1]) == 0:
                continue

            current_std = float(vwap_std.iloc[-1])

            # Z-score: how many SDs from VWAP
            vwap_zscore = (current - vwap_val) / current_std

            # Condition 1: Price at -2 SD or below from VWAP
            if vwap_zscore > -2.0:
                continue  # Not extreme enough dislocation

            # Condition 2: RSI < 30 (oversold confirmation)
            rsi_val = float(rsi(close, 14).iloc[-1])
            if rsi_val >= 30:
                continue

            # Condition 3: Volume spike > 3x average (panic selling)
            vol_r = float(volume_ratio(volume).iloc[-1])
            if vol_r < 3.0:
                continue

            # Target: mean revert to VWAP itself
            tp = _smart_round(vwap_val)
            # SL: -3 SD from VWAP (one more SD below entry)
            sl = _smart_round(vwap_val - 3.0 * current_std)

            rr = (tp - current) / (current - sl) if current > sl else 0
            if rr < 1.3:
                continue

            move_pct = (vwap_val - current) / current * 100
            confidence = round(min(0.82, 0.60 + abs(vwap_zscore - (-2.0)) * 0.05 + vol_r * 0.01), 2)

            signals.append({
                "strategy": "vwap_sd_mean_reversion",
                "symbol": symbol, "category": _get_category(symbol),
                "signal_type": "BUY",
                "entry_price": _smart_round(current),
                "take_profit": tp,
                "stop_loss": sl,
                "confidence": confidence,
                "risk_reward": round(rr, 2),
                "reason": (f"Price at {vwap_zscore:.1f} SD from VWAP ({vwap_val:.2f}), "
                           f"RSI={rsi_val:.0f}, vol={vol_r:.1f}x panic spike. "
                           f"Target VWAP reversion ({move_pct:.1f}% move). "
                           f"Berkowitz et al. (1988): 70-75% WR."),
                "timeframe": "1d",
                "rsi_at_entry": round(rsi_val, 1),
                "volume_ratio": round(vol_r, 2),
                "extra": {
                    "vwap_20": round(vwap_val, 4),
                    "vwap_zscore": round(vwap_zscore, 2),
                    "expected_move_pct": round(move_pct, 2),
                    "source": "Berkowitz et al. (1988) -- VWAP institutional benchmark",
                },
                "timestamp": _now_iso(),
            })
        except Exception:
            continue

    return signals


# =========================================================================
# STRATEGY 22: CMF (Chaikin Money Flow) Zero-Line Cross
# =========================================================================
# Reference: Marc Chaikin (1960s-70s), adapted from Accumulation/Distribution.
# CMF measures buying/selling pressure over N periods.
# Signal: CMF(20) crosses above 0.0 from below = transition from
#         distribution to accumulation. Combined with price above EMA(20)
#         and RVOL > 1.5, this confirms institutional buying.
# Win rate: 55-65% standalone, higher with trend confirmation.
# =========================================================================

def _chaikin_money_flow(high: pd.Series, low: pd.Series,
                        close: pd.Series, volume: pd.Series,
                        period: int = 20) -> pd.Series:
    """Chaikin Money Flow = sum(MFV) / sum(Volume) over period.
    MFV = ((Close - Low) - (High - Close)) / (High - Low) * Volume."""
    hl_range = (high - low).replace(0, np.nan)
    mf_multiplier = ((close - low) - (high - close)) / hl_range
    mf_volume = mf_multiplier * volume
    cmf = mf_volume.rolling(period).sum() / volume.rolling(period).sum().replace(0, np.nan)
    return cmf


def cmf_zero_line_cross(data: dict[str, pd.DataFrame]) -> list[dict]:
    """CMF(20) crosses above zero + price above EMA(20) + volume confirmation."""
    signals = []
    for symbol in CRYPTO_SYMBOLS:
        df = data.get(symbol)
        if df is None or len(df) < 30:
            continue

        try:
            close = df["Close"]
            high = df["High"]
            low = df["Low"]
            volume = df["Volume"]
            current = float(close.iloc[-1])

            # Calculate CMF(20)
            cmf = _chaikin_money_flow(high, low, close, volume, period=20)
            if cmf.isna().iloc[-1] or cmf.isna().iloc[-2]:
                continue

            cmf_today = float(cmf.iloc[-1])
            cmf_yesterday = float(cmf.iloc[-2])

            # Condition 1: CMF crosses above 0.0 from below
            if not (cmf_yesterday < 0.0 and cmf_today >= 0.0):
                continue

            # Condition 2: Price above EMA(20) (trend confirmation)
            ema_20 = float(ema(close, 20).iloc[-1])
            if current < ema_20:
                continue

            # Condition 3: RVOL > 1.5 (volume confirmation)
            vol_r = float(volume_ratio(volume).iloc[-1])
            if vol_r < 1.5:
                continue

            rsi_val = float(rsi(close, 14).iloc[-1])
            if rsi_val > 75:
                continue  # Already overbought

            price, tp, sl = _atr_tp_sl(close, high, low,
                                       tp_mult=3.0, sl_mult=1.5)
            rr = (tp - price) / (price - sl) if price > sl else 0
            if rr < 1.3:
                continue

            confidence = round(min(0.75, 0.50 + cmf_today * 5 + vol_r * 0.03), 2)

            signals.append({
                "strategy": "cmf_zero_line_cross",
                "symbol": symbol, "category": _get_category(symbol),
                "signal_type": "BUY",
                "entry_price": _smart_round(price),
                "take_profit": _smart_round(tp),
                "stop_loss": _smart_round(sl),
                "confidence": confidence,
                "risk_reward": round(rr, 2),
                "reason": (f"CMF(20) crossed above zero ({cmf_yesterday:.3f}->{cmf_today:.3f}), "
                           f"price above EMA20 ({ema_20:.2f}), vol={vol_r:.1f}x. "
                           f"Chaikin: distribution→accumulation transition, 55-65% WR."),
                "timeframe": "1d",
                "rsi_at_entry": round(rsi_val, 1),
                "volume_ratio": round(vol_r, 2),
                "extra": {
                    "cmf_today": round(cmf_today, 4),
                    "cmf_yesterday": round(cmf_yesterday, 4),
                    "ema_20": round(ema_20, 4),
                    "source": "Marc Chaikin -- Chaikin Money Flow indicator",
                },
                "timestamp": _now_iso(),
            })
        except Exception:
            continue

    return signals


# =========================================================================
# STRATEGY 23: MFI (Money Flow Index) Smart Money Detection
# =========================================================================
# Reference: Quong & Soudack (1989), adapted from RSI + volume weighting.
# MFI = "volume-weighted RSI". MFI(14) crossing above 20 from oversold
# territory signals that smart money (large volume) is buying the dip.
# Combined with bullish candle + volume > 1.5x average.
# Win rate: 55-68% on crypto, strongest on major pairs.
# Unlike RSI, MFI incorporates volume directly, giving more weight to
# high-volume moves -- particularly useful in crypto where volume spikes
# are more meaningful than in traditional markets.
# =========================================================================

def _money_flow_index(high: pd.Series, low: pd.Series,
                      close: pd.Series, volume: pd.Series,
                      period: int = 14) -> pd.Series:
    """Money Flow Index -- volume-weighted RSI. Quong & Soudack (1989)."""
    typical_price = (high + low + close) / 3.0
    raw_money_flow = typical_price * volume

    # Positive and negative money flow
    tp_diff = typical_price.diff()
    pos_flow = raw_money_flow.where(tp_diff > 0, 0.0)
    neg_flow = raw_money_flow.where(tp_diff < 0, 0.0)

    # Rolling sum
    pos_sum = pos_flow.rolling(period).sum()
    neg_sum = neg_flow.rolling(period).sum().replace(0, np.nan)

    money_ratio = pos_sum / neg_sum
    mfi = 100.0 - (100.0 / (1.0 + money_ratio))
    return mfi


def mfi_smart_money_detection(data: dict[str, pd.DataFrame]) -> list[dict]:
    """MFI(14) crosses above 20 from oversold + bullish candle + volume > 1.5x."""
    signals = []
    for symbol in CRYPTO_SYMBOLS:
        df = data.get(symbol)
        if df is None or len(df) < 25:
            continue

        try:
            close = df["Close"]
            high = df["High"]
            low = df["Low"]
            open_ = df["Open"]
            volume = df["Volume"]
            current = float(close.iloc[-1])

            # Calculate MFI(14)
            mfi = _money_flow_index(high, low, close, volume, period=14)
            if mfi.isna().iloc[-1] or mfi.isna().iloc[-2]:
                continue

            mfi_today = float(mfi.iloc[-1])
            mfi_yesterday = float(mfi.iloc[-2])

            # Condition 1: MFI crosses above 20 from oversold
            if not (mfi_yesterday < 20.0 and mfi_today >= 20.0):
                continue

            # Condition 2: Bullish candle (close > open)
            current_open = float(open_.iloc[-1])
            if current <= current_open:
                continue  # Not a bullish candle

            # Condition 3: Volume > 1.5x average
            vol_r = float(volume_ratio(volume).iloc[-1])
            if vol_r < 1.5:
                continue

            rsi_val = float(rsi(close, 14).iloc[-1])
            if rsi_val > 70:
                continue  # Already overbought

            price, tp, sl = _atr_tp_sl(close, high, low,
                                       tp_mult=3.0, sl_mult=1.5)
            rr = (tp - price) / (price - sl) if price > sl else 0
            if rr < 1.3:
                continue

            # Confidence: how deeply oversold MFI was + volume strength
            oversold_depth = max(0, 20.0 - mfi_yesterday) / 20.0  # 0-1 scale
            confidence = round(min(0.78, 0.52 + oversold_depth * 0.15 + vol_r * 0.03), 2)

            signals.append({
                "strategy": "mfi_smart_money_detection",
                "symbol": symbol, "category": _get_category(symbol),
                "signal_type": "BUY",
                "entry_price": _smart_round(price),
                "take_profit": _smart_round(tp),
                "stop_loss": _smart_round(sl),
                "confidence": confidence,
                "risk_reward": round(rr, 2),
                "reason": (f"MFI(14) crossed above 20 from oversold "
                           f"({mfi_yesterday:.1f}->{mfi_today:.1f}), "
                           f"bullish candle, vol={vol_r:.1f}x. "
                           f"Quong & Soudack (1989): volume-weighted RSI, 55-68% WR."),
                "timeframe": "1d",
                "rsi_at_entry": round(rsi_val, 1),
                "volume_ratio": round(vol_r, 2),
                "extra": {
                    "mfi_today": round(mfi_today, 2),
                    "mfi_yesterday": round(mfi_yesterday, 2),
                    "bullish_candle_pct": round((current - current_open) / current_open * 100, 2),
                    "source": "Quong & Soudack (1989) -- Money Flow Index",
                },
                "timestamp": _now_iso(),
            })
        except Exception:
            continue

    return signals


# =========================================================================
# STRATEGY 24: Swing Failure Pattern (Hsaka Method)
# =========================================================================
# Reference: Hsaka / ICT methodology. Price wicks above prior swing high
# (or below swing low) then closes back inside = failed breakout.
# One of the most profitable reversal patterns in crypto.
# Win rate: 58-65% with proper S/R context (Hsaka documented trades).
# =========================================================================

def swing_failure_pattern(data: dict[str, pd.DataFrame]) -> list[dict]:
    """Detect Swing Failure Pattern: wick beyond swing high/low, close inside."""
    signals = []
    for symbol in CRYPTO_SYMBOLS:
        df = data.get(symbol)
        if df is None or len(df) < 30:
            continue

        try:
            close = df["Close"]
            high = df["High"]
            low = df["Low"]
            volume = df["Volume"]

            # Find recent swing highs and lows (20-bar lookback)
            lookback = 20
            recent_high = float(high.iloc[-lookback-1:-1].max())
            recent_low = float(low.iloc[-lookback-1:-1].min())
            current_high = float(high.iloc[-1])
            current_low = float(low.iloc[-1])
            current_close = float(close.iloc[-1])
            current_open = float(df["Open"].iloc[-1])

            # Volume confirmation
            vol_r = float(volume_ratio(volume).iloc[-1])

            # BULLISH SFP: current bar wicks BELOW swing low, closes back above
            if current_low < recent_low and current_close > recent_low:
                # Wick must be significant (at least 30% of candle range below swing low)
                candle_range = current_high - current_low
                if candle_range <= 0:
                    continue
                wick_below = recent_low - current_low
                if wick_below / candle_range < 0.3:
                    continue

                # Must close bullish (close > open)
                if current_close <= current_open:
                    continue

                rsi_val = float(rsi(close, 14).iloc[-1])
                if rsi_val > 70:
                    continue

                price, tp, sl = _atr_tp_sl(close, high, low,
                                           tp_mult=3.0, sl_mult=1.5)
                # SL below the SFP wick
                sfp_sl = _smart_round(current_low * 0.995)
                sl = min(sl, sfp_sl)
                rr = (tp - price) / (price - sl) if price > sl else 0
                if rr < 1.5:
                    continue

                # Confidence: deeper wick + volume = stronger
                wick_depth = wick_below / candle_range
                confidence = round(min(0.82, 0.52 + wick_depth * 0.2 + vol_r * 0.02), 2)

                signals.append({
                    "strategy": "swing_failure_pattern",
                    "symbol": symbol, "category": _get_category(symbol),
                    "signal_type": "BUY",
                    "entry_price": _smart_round(price),
                    "take_profit": _smart_round(tp),
                    "stop_loss": _smart_round(sl),
                    "confidence": confidence,
                    "risk_reward": round(rr, 2),
                    "reason": (f"Bullish SFP: wicked below swing low ({recent_low:.4g}) "
                               f"and closed back above, vol={vol_r:.1f}x, RSI={rsi_val:.0f}. "
                               f"Hsaka method: 58-65% WR on failed breakdowns."),
                    "timeframe": "1d",
                    "rsi_at_entry": round(rsi_val, 1),
                    "volume_ratio": round(vol_r, 2),
                    "extra": {
                        "swing_low": _smart_round(recent_low),
                        "wick_depth_pct": round(wick_depth * 100, 1),
                        "source": "Hsaka / ICT -- Swing Failure Pattern",
                    },
                    "timestamp": _now_iso(),
                })

            # BEARISH SFP: wicks ABOVE swing high, closes back below
            elif current_high > recent_high and current_close < recent_high:
                candle_range = current_high - current_low
                if candle_range <= 0:
                    continue
                wick_above = current_high - recent_high
                if wick_above / candle_range < 0.3:
                    continue

                if current_close >= current_open:
                    continue  # Must close bearish

                rsi_val = float(rsi(close, 14).iloc[-1])
                if rsi_val < 30:
                    continue

                price, tp, sl = _atr_tp_sl(close, high, low,
                                           tp_mult=3.0, sl_mult=1.5)
                # For SELL: TP below, SL above
                atr_val = float(atr(high, low, close).iloc[-1])
                tp_sell = _smart_round(price - 3.0 * atr_val)
                sl_sell = _smart_round(max(sl, current_high * 1.005))

                rr = (price - tp_sell) / (sl_sell - price) if sl_sell > price else 0
                if rr < 1.5:
                    continue

                wick_depth = wick_above / candle_range
                confidence = round(min(0.82, 0.52 + wick_depth * 0.2 + vol_r * 0.02), 2)

                signals.append({
                    "strategy": "swing_failure_pattern",
                    "symbol": symbol, "category": _get_category(symbol),
                    "signal_type": "SELL",
                    "entry_price": _smart_round(price),
                    "take_profit": tp_sell,
                    "stop_loss": sl_sell,
                    "confidence": confidence,
                    "risk_reward": round(rr, 2),
                    "reason": (f"Bearish SFP: wicked above swing high ({recent_high:.4g}) "
                               f"and closed back below, vol={vol_r:.1f}x, RSI={rsi_val:.0f}. "
                               f"Hsaka method: 58-65% WR on failed breakouts."),
                    "timeframe": "1d",
                    "rsi_at_entry": round(rsi_val, 1),
                    "volume_ratio": round(vol_r, 2),
                    "extra": {
                        "swing_high": _smart_round(recent_high),
                        "wick_depth_pct": round(wick_depth * 100, 1),
                        "source": "Hsaka / ICT -- Swing Failure Pattern",
                    },
                    "timestamp": _now_iso(),
                })
        except Exception:
            continue

    return signals


# =========================================================================
# STRATEGY 25: Break of Structure (BOS / CHOCH)
# =========================================================================
# Reference: ICT Smart Money Concepts. Break of Structure = price breaks
# above prior swing high (bullish) or below prior swing low (bearish).
# Change of Character (CHOCH) = first BOS against the prevailing trend.
# When BOS aligns with trend = continuation. CHOCH = reversal.
# Win rate: 55-65% with proper volume and S/R context.
# =========================================================================

def break_of_structure(data: dict[str, pd.DataFrame]) -> list[dict]:
    """ICT Break of Structure: price breaks prior swing high/low with momentum."""
    # REGIME GATE: Disable BOS in extreme fear (with retry)
    import time as _fng_time
    _fng = 50
    for _fng_att in range(3):
        try:
            import requests as _req
            _fng = int(_req.get("https://api.alternative.me/fng/", timeout=5).json()["data"][0]["value"])
            break
        except Exception:
            if _fng_att < 2:
                _fng_time.sleep(2 * (_fng_att + 1))
    if _fng < 20:
        return []

    signals = []
    for symbol in CRYPTO_SYMBOLS:
        df = data.get(symbol)
        if df is None or len(df) < 40:
            continue

        try:
            close = df["Close"]
            high = df["High"]
            low = df["Low"]
            volume = df["Volume"]
            current = float(close.iloc[-1])
            prev_close = float(close.iloc[-2])

            # Find swing points using 5-bar pivots in last 30 bars
            swing_highs = []
            swing_lows = []
            for i in range(-30, -2):
                h = float(high.iloc[i])
                l = float(low.iloc[i])
                # Simple pivot: higher than 2 bars on each side
                if i >= -28 and i <= -3:
                    if (h >= float(high.iloc[i-1]) and h >= float(high.iloc[i-2])
                            and h >= float(high.iloc[i+1]) and h >= float(high.iloc[i+2])):
                        swing_highs.append(h)
                    if (l <= float(low.iloc[i-1]) and l <= float(low.iloc[i-2])
                            and l <= float(low.iloc[i+1]) and l <= float(low.iloc[i+2])):
                        swing_lows.append(l)

            if len(swing_highs) < 2 or len(swing_lows) < 2:
                continue

            last_swing_high = swing_highs[-1]
            last_swing_low = swing_lows[-1]

            vol_r = float(volume_ratio(volume).iloc[-1])
            rsi_val = float(rsi(close, 14).iloc[-1])

            # BULLISH BOS: price breaks above last swing high with volume
            if current > last_swing_high and prev_close <= last_swing_high:
                if vol_r < 2.0:  # Raised from 1.2 (TJR requires 2x minimum on BOS)
                    continue  # Need volume confirmation
                if rsi_val > 80:
                    continue

                price, tp, sl = _atr_tp_sl(close, high, low,
                                           tp_mult=3.5, sl_mult=1.5)
                # SL at last swing low
                bos_sl = _smart_round(last_swing_low * 0.995)
                sl = max(sl, bos_sl)

                rr = (tp - price) / (price - sl) if price > sl else 0
                if rr < 1.3:
                    continue

                # Determine if CHOCH (reversal) or BOS (continuation)
                # If swing lows were making lower lows, this is CHOCH (bullish reversal)
                is_choch = len(swing_lows) >= 2 and swing_lows[-1] < swing_lows[-2]
                label = "CHOCH (reversal)" if is_choch else "BOS (continuation)"

                confidence = round(min(0.80, 0.50 + vol_r * 0.03 + (0.08 if is_choch else 0.04)), 2)

                signals.append({
                    "strategy": "break_of_structure",
                    "symbol": symbol, "category": _get_category(symbol),
                    "signal_type": "BUY",
                    "entry_price": _smart_round(price),
                    "take_profit": _smart_round(tp),
                    "stop_loss": _smart_round(sl),
                    "confidence": confidence,
                    "risk_reward": round(rr, 2),
                    "reason": (f"Bullish {label}: broke above swing high "
                               f"({last_swing_high:.4g}), vol={vol_r:.1f}x, RSI={rsi_val:.0f}. "
                               f"ICT SMC: 55-65% WR with volume confirmation."),
                    "timeframe": "1d",
                    "rsi_at_entry": round(rsi_val, 1),
                    "volume_ratio": round(vol_r, 2),
                    "extra": {
                        "swing_high": _smart_round(last_swing_high),
                        "swing_low": _smart_round(last_swing_low),
                        "structure_type": label,
                        "source": "ICT / Smart Money Concepts -- BOS/CHOCH",
                    },
                    "timestamp": _now_iso(),
                })

            # BEARISH BOS: price breaks below last swing low
            elif current < last_swing_low and prev_close >= last_swing_low:
                if vol_r < 1.2:
                    continue
                if rsi_val < 20:
                    continue

                atr_val = float(atr(high, low, close).iloc[-1])
                price = _smart_round(current)
                tp_sell = _smart_round(current - 3.5 * atr_val)
                sl_sell = _smart_round(last_swing_high * 1.005)

                rr = (price - tp_sell) / (sl_sell - price) if sl_sell > price else 0
                if rr < 1.3:
                    continue

                is_choch = len(swing_highs) >= 2 and swing_highs[-1] > swing_highs[-2]
                label = "CHOCH (reversal)" if is_choch else "BOS (continuation)"
                confidence = round(min(0.80, 0.50 + vol_r * 0.03 + (0.08 if is_choch else 0.04)), 2)

                signals.append({
                    "strategy": "break_of_structure",
                    "symbol": symbol, "category": _get_category(symbol),
                    "signal_type": "SELL",
                    "entry_price": price,
                    "take_profit": tp_sell,
                    "stop_loss": sl_sell,
                    "confidence": confidence,
                    "risk_reward": round(rr, 2),
                    "reason": (f"Bearish {label}: broke below swing low "
                               f"({last_swing_low:.4g}), vol={vol_r:.1f}x, RSI={rsi_val:.0f}. "
                               f"ICT SMC: 55-65% WR with volume confirmation."),
                    "timeframe": "1d",
                    "rsi_at_entry": round(rsi_val, 1),
                    "volume_ratio": round(vol_r, 2),
                    "extra": {
                        "swing_high": _smart_round(last_swing_high),
                        "swing_low": _smart_round(last_swing_low),
                        "structure_type": label,
                        "source": "ICT / Smart Money Concepts -- BOS/CHOCH",
                    },
                    "timestamp": _now_iso(),
                })
        except Exception:
            continue

    return signals


# =========================================================================
# STRATEGY 26: Funding Rate Carry (Positive Funding Arbitrage)
# =========================================================================
# Reference: Kraken Research (2024). When funding rate is extremely positive
# (>0.05% per 8h = >55% APY), the market is overleveraged long.
# Two edges: (1) mean reversion SHORT, (2) funding carry trade.
# This strategy: SHORT when funding is extremely positive + RSI overbought.
# Complements funding_rate_extreme (which buys on negative funding).
# Win rate: ~60% for mean reversion on extreme positive funding.
# =========================================================================

def funding_rate_carry(data: dict[str, pd.DataFrame],
                       context: Optional[dict] = None) -> list[dict]:
    """Short when funding rate is extremely positive (longs overleveraged)."""
    signals = []
    funding_data = context.get("funding_rates") if context else None

    if funding_data is None:
        funding_data = {}
        for symbol, info in CRYPTO_SYMBOLS.items():
            binance_sym = info.get("binance")
            if not binance_sym:
                continue
            resp = fetch_binance_json(f"/fapi/v1/fundingRate?symbol={binance_sym}&limit=1", futures=True)
            if resp and len(resp) > 0:
                try:
                    funding_data[symbol] = float(resp[0]["fundingRate"])
                except (KeyError, ValueError):
                    pass

    # Collect all funding rates to compute 2-sigma threshold
    all_rates = list(funding_data.values())
    if len(all_rates) >= 3:
        funding_mean = sum(all_rates) / len(all_rates)
        funding_std = (sum((r - funding_mean) ** 2 for r in all_rates) / len(all_rates)) ** 0.5
    else:
        funding_mean = 0.0
        funding_std = 0.0

    for symbol, rate in funding_data.items():
        # 2-sigma filter: only trade when funding rate is >2 std devs from mean
        # This filters out "slightly elevated" funding -- only extreme dislocations
        if funding_std > 0:
            z_funding = abs(rate - funding_mean) / funding_std
            if z_funding < 2.0:
                continue
        else:
            # Fallback: only trigger on extremely positive funding (>0.05% per 8h = 55% APY)
            if rate <= 0.0005:
                continue

        # Still require positive funding (short bias)
        if rate <= 0:
            continue

        df = data.get(symbol)
        if df is None or len(df) < 30:
            continue

        try:
            close = df["Close"]
            high = df["High"]
            low = df["Low"]
            rsi_val = float(rsi(close, 14).iloc[-1])

            # Want RSI overbought to confirm overleveraged longs
            if rsi_val < 60:
                continue  # Not overbought enough

            # Check if price is extended above 20 EMA
            ema_20 = float(ema(close, 20).iloc[-1])
            current = float(close.iloc[-1])
            if current < ema_20:
                continue  # Not extended

            atr_val = float(atr(high, low, close).iloc[-1])
            price = _smart_round(current)
            tp_sell = _smart_round(current - 2.5 * atr_val)
            sl_sell = _smart_round(current + 1.5 * atr_val)

            rr = (price - tp_sell) / (sl_sell - price) if sl_sell > price else 0
            if rr < 1.3:
                continue

            # Confidence scales with how extreme the funding is
            funding_pct = rate * 100
            confidence = round(min(0.82, 0.52 + abs(rate) * 150 + (rsi_val - 60) * 0.005), 2)

            signals.append({
                "strategy": "funding_rate_carry",
                "symbol": symbol, "category": _get_category(symbol),
                "signal_type": "SELL",
                "entry_price": price,
                "take_profit": tp_sell,
                "stop_loss": sl_sell,
                "confidence": confidence,
                "risk_reward": round(rr, 2),
                "reason": (f"Extreme positive funding ({funding_pct:.4f}%, "
                           f"~{rate*3*365*100:.0f}% APY), longs overleveraged, "
                           f"RSI={rsi_val:.0f}. Kraken Research: 60% WR."),
                "timeframe": "1d",
                "rsi_at_entry": round(rsi_val, 1),
                "extra": {
                    "funding_rate": rate,
                    "funding_pct": round(funding_pct, 4),
                    "annualized_pct": round(rate * 3 * 365 * 100, 1),
                    "source": "Kraken Research (2024) -- Funding Rate Carry",
                },
                "timestamp": _now_iso(),
            })
        except Exception:
            continue

    return signals


# =========================================================================
# STRATEGY 27: Liquidation Cascade Bottom Fishing
# =========================================================================
# Reference: Pentoshi / CoinGlass methodology. When price drops >5% in a
# single day with volume >3x average, it's likely a cascading liquidation
# event. These create V-shaped reversals ~60-65% of the time.
# Strategy: Buy the spike down with tight SL below the cascade low.
# =========================================================================

def liquidation_cascade_bottom(data: dict[str, pd.DataFrame]) -> list[dict]:
    """Buy after large price drop + volume spike (cascade liquidation)."""
    signals = []
    for symbol in CRYPTO_SYMBOLS:
        df = data.get(symbol)
        if df is None or len(df) < 30:
            continue

        try:
            close = df["Close"]
            high = df["High"]
            low = df["Low"]
            volume = df["Volume"]
            open_ = df["Open"]

            current = float(close.iloc[-1])
            current_open = float(open_.iloc[-1])
            prev_close = float(close.iloc[-2])

            # Condition 1: Price dropped >5% from previous close
            drop_pct = (prev_close - current) / prev_close * 100
            if drop_pct < 5.0:
                continue

            # Condition 2: Volume spike >3x average
            vol_r = float(volume_ratio(volume).iloc[-1])
            if vol_r < 3.0:
                continue

            # Condition 2b: Dollar volume floor -- calibrate to $100M+ liquidations
            # CoinGlass data shows meaningful cascades start at ~$100M/hour.
            # Daily candle vol should be at least $100M to indicate cascade-level activity.
            current_vol = float(volume.iloc[-1])
            dollar_volume = current_vol * current
            if dollar_volume < 100_000_000:
                continue  # Not enough volume -- likely not a real cascade

            # Condition 3: Sign of recovery -- close above midpoint of today's range
            day_range = float(high.iloc[-1]) - float(low.iloc[-1])
            if day_range <= 0:
                continue
            midpoint = float(low.iloc[-1]) + day_range / 2
            if current < midpoint:
                continue  # Still selling, no recovery wick

            rsi_val = float(rsi(close, 14).iloc[-1])

            # TP/SL: tight SL below cascade low, generous TP for V-recovery
            cascade_low = float(low.iloc[-1])
            price = _smart_round(current)
            sl = _smart_round(cascade_low * 0.99)  # 1% below cascade low
            atr_val = float(atr(high, low, close).iloc[-1])
            tp = _smart_round(current + 4.0 * atr_val)  # 4x ATR TP for V-bounce

            rr = (tp - price) / (price - sl) if price > sl else 0
            if rr < 1.5:
                continue

            # Confidence: bigger drop + bigger volume = more likely cascade
            confidence = round(min(0.80, 0.48 + drop_pct * 0.02 + vol_r * 0.01), 2)

            signals.append({
                "strategy": "liquidation_cascade_bottom",
                "symbol": symbol, "category": _get_category(symbol),
                "signal_type": "BUY",
                "entry_price": price,
                "take_profit": _smart_round(tp),
                "stop_loss": _smart_round(sl),
                "confidence": confidence,
                "risk_reward": round(rr, 2),
                "reason": (f"Cascade liquidation: -{drop_pct:.1f}% drop with "
                           f"{vol_r:.1f}x volume spike, recovering from low. "
                           f"RSI={rsi_val:.0f}. Pentoshi: 60-65% V-bounce rate."),
                "timeframe": "1d",
                "rsi_at_entry": round(rsi_val, 1),
                "volume_ratio": round(vol_r, 2),
                "extra": {
                    "drop_pct": round(drop_pct, 2),
                    "cascade_low": _smart_round(cascade_low),
                    "recovery_pct": round((current - cascade_low) / cascade_low * 100, 2),
                    "source": "Pentoshi / CoinGlass -- Liquidation Cascade",
                },
                "timestamp": _now_iso(),
            })
        except Exception:
            continue

    return signals


# =========================================================================
# STRATEGY 28: OI + Funding Squeeze Detection
# =========================================================================
# Reference: Coinalyze research. When Open Interest rises while price
# drops AND funding stays positive, shorts are building against stubborn
# longs = short squeeze setup. When OI rises + price rises + funding
# negative, longs building against stubborn shorts = long squeeze setup.
# Win rate: ~55-62% for squeeze detection.
# =========================================================================

def oi_funding_squeeze(data: dict[str, pd.DataFrame],
                       context: Optional[dict] = None) -> list[dict]:
    """Detect squeeze setups via OI + funding + price divergence."""
    signals = []
    # Fetch funding rates
    funding_data = context.get("funding_rates") if context else None
    if funding_data is None:
        funding_data = {}
        for symbol, info in CRYPTO_SYMBOLS.items():
            binance_sym = info.get("binance")
            if not binance_sym:
                continue
            resp = fetch_binance_json(f"/fapi/v1/fundingRate?symbol={binance_sym}&limit=1", futures=True)
            if resp and len(resp) > 0:
                try:
                    funding_data[symbol] = float(resp[0]["fundingRate"])
                except (KeyError, ValueError):
                    pass

    # Fetch open interest
    oi_data = {}
    for symbol, info in CRYPTO_SYMBOLS.items():
        binance_sym = info.get("binance")
        if not binance_sym:
            continue
        resp = fetch_binance_json(f"/fapi/v1/openInterest?symbol={binance_sym}", futures=True)
        if resp:
            try:
                oi_data[symbol] = float(resp["openInterest"])
            except (KeyError, ValueError):
                pass

    for symbol in CRYPTO_SYMBOLS:
        if symbol not in funding_data or symbol not in oi_data:
            continue

        df = data.get(symbol)
        if df is None or len(df) < 14:
            continue

        try:
            close = df["Close"]
            high = df["High"]
            low = df["Low"]
            volume = df["Volume"]
            rate = funding_data[symbol]
            current = float(close.iloc[-1])

            # Calculate price trend over last 3 days
            price_3d_ago = float(close.iloc[-4]) if len(close) >= 4 else float(close.iloc[0])
            price_change_pct = (current - price_3d_ago) / price_3d_ago * 100

            # SHORT SQUEEZE: Price dropping + funding positive (longs paying shorts)
            # = shorts are profiting and building, but longs are stubborn
            if price_change_pct < -3.0 and rate > 0.0003:
                rsi_val = float(rsi(close, 14).iloc[-1])
                if rsi_val > 60:
                    continue  # Not oversold enough

                price, tp, sl = _atr_tp_sl(close, high, low,
                                           tp_mult=3.5, sl_mult=1.5)
                rr = (tp - price) / (price - sl) if price > sl else 0
                if rr < 1.5:
                    continue

                confidence = round(min(0.78, 0.50 + abs(price_change_pct) * 0.02 + rate * 100), 2)

                signals.append({
                    "strategy": "oi_funding_squeeze",
                    "symbol": symbol, "category": _get_category(symbol),
                    "signal_type": "BUY",
                    "entry_price": _smart_round(price),
                    "take_profit": _smart_round(tp),
                    "stop_loss": _smart_round(sl),
                    "confidence": confidence,
                    "risk_reward": round(rr, 2),
                    "reason": (f"Short squeeze setup: price -{abs(price_change_pct):.1f}% "
                               f"but funding still positive ({rate*100:.4f}%), "
                               f"RSI={rsi_val:.0f}. Coinalyze: 55-62% WR."),
                    "timeframe": "1d",
                    "rsi_at_entry": round(rsi_val, 1),
                    "extra": {
                        "funding_rate": rate,
                        "price_change_3d": round(price_change_pct, 2),
                        "oi": oi_data[symbol],
                        "squeeze_type": "short_squeeze",
                        "source": "Coinalyze -- OI/Funding Squeeze",
                    },
                    "timestamp": _now_iso(),
                })

            # LONG SQUEEZE: Price rising + funding negative (shorts paying longs)
            elif price_change_pct > 3.0 and rate < -0.0003:
                rsi_val = float(rsi(close, 14).iloc[-1])
                if rsi_val < 40:
                    continue

                atr_val = float(atr(high, low, close).iloc[-1])
                price = _smart_round(current)
                tp_sell = _smart_round(current - 3.5 * atr_val)
                sl_sell = _smart_round(current + 1.5 * atr_val)

                rr = (price - tp_sell) / (sl_sell - price) if sl_sell > price else 0
                if rr < 1.5:
                    continue

                confidence = round(min(0.78, 0.50 + price_change_pct * 0.02 + abs(rate) * 100), 2)

                signals.append({
                    "strategy": "oi_funding_squeeze",
                    "symbol": symbol, "category": _get_category(symbol),
                    "signal_type": "SELL",
                    "entry_price": price,
                    "take_profit": tp_sell,
                    "stop_loss": sl_sell,
                    "confidence": confidence,
                    "risk_reward": round(rr, 2),
                    "reason": (f"Long squeeze setup: price +{price_change_pct:.1f}% "
                               f"but funding negative ({rate*100:.4f}%), "
                               f"RSI={rsi_val:.0f}. Coinalyze: 55-62% WR."),
                    "timeframe": "1d",
                    "rsi_at_entry": round(rsi_val, 1),
                    "extra": {
                        "funding_rate": rate,
                        "price_change_3d": round(price_change_pct, 2),
                        "oi": oi_data[symbol],
                        "squeeze_type": "long_squeeze",
                        "source": "Coinalyze -- OI/Funding Squeeze",
                    },
                    "timestamp": _now_iso(),
                })
        except Exception:
            continue

    return signals


# =========================================================================
# STRATEGY 29: Cross-Sectional Momentum
# =========================================================================
# Reference: Jegadeesh & Titman (1993), adapted for crypto by Liu et al.
# (2022 JFE). Buy the top 3 coins by 7d return, skip bottom 3.
# Crypto momentum factor has Sharpe ~2.1 (Liu et al.).
# Win rate: ~58-65% for top-3 momentum picks over 7-14 day hold.
# =========================================================================

def cross_sectional_momentum(data: dict[str, pd.DataFrame]) -> list[dict]:
    """Buy top momentum coins over 7-day lookback (cross-sectional)."""
    signals = []
    momentum_scores = {}

    for symbol in CRYPTO_SYMBOLS:
        df = data.get(symbol)
        if df is None or len(df) < 10:
            continue

        try:
            close = df["Close"]
            # 7-day return
            ret_7d = (float(close.iloc[-1]) - float(close.iloc[-8])) / float(close.iloc[-8])
            # 3-day return (short-term confirmation)
            ret_3d = (float(close.iloc[-1]) - float(close.iloc[-4])) / float(close.iloc[-4])
            momentum_scores[symbol] = {
                "ret_7d": ret_7d,
                "ret_3d": ret_3d,
                "combined": ret_7d * 0.7 + ret_3d * 0.3,
            }
        except Exception:
            continue

    if len(momentum_scores) < 6:
        return signals

    # Rank by combined momentum
    ranked = sorted(momentum_scores.items(), key=lambda x: x[1]["combined"], reverse=True)
    top_3 = ranked[:3]
    bottom_3 = ranked[-3:]

    for symbol, scores in top_3:
        if scores["combined"] <= 0.02:
            continue  # Need at least 2% positive momentum

        df = data.get(symbol)
        if df is None:
            continue

        try:
            close = df["Close"]
            high = df["High"]
            low = df["Low"]
            rsi_val = float(rsi(close, 14).iloc[-1])

            if rsi_val > 85:
                continue  # Too overbought

            price, tp, sl = _atr_tp_sl(close, high, low,
                                       tp_mult=3.0, sl_mult=1.5)
            rr = (tp - price) / (price - sl) if price > sl else 0
            if rr < 1.3:
                continue

            rank_pos = [s for s, _ in ranked].index(symbol) + 1
            confidence = round(min(0.78, 0.50 + scores["combined"] * 2 + (4 - rank_pos) * 0.03), 2)

            signals.append({
                "strategy": "cross_sectional_momentum",
                "symbol": symbol, "category": _get_category(symbol),
                "signal_type": "BUY",
                "entry_price": _smart_round(price),
                "take_profit": _smart_round(tp),
                "stop_loss": _smart_round(sl),
                "confidence": confidence,
                "risk_reward": round(rr, 2),
                "reason": (f"Top-{rank_pos} momentum: 7d={scores['ret_7d']*100:.1f}%, "
                           f"3d={scores['ret_3d']*100:.1f}%, RSI={rsi_val:.0f}. "
                           f"Liu et al. (2022 JFE): crypto momentum Sharpe ~2.1."),
                "timeframe": "1d",
                "rsi_at_entry": round(rsi_val, 1),
                "extra": {
                    "rank": rank_pos,
                    "return_7d_pct": round(scores["ret_7d"] * 100, 2),
                    "return_3d_pct": round(scores["ret_3d"] * 100, 2),
                    "total_ranked": len(ranked),
                    "source": "Liu et al. (2022 JFE) -- Crypto Momentum Factor",
                },
                "timestamp": _now_iso(),
            })
        except Exception:
            continue

    return signals


# =========================================================================
# STRATEGY 30: ATR Volatility Breakout (Keltner Channel Expansion)
# =========================================================================
# Reference: Keltner (1960), adapted by Connors & Raschke.
# When ATR expands >50% above its 20-period average AND price breaks
# above the upper Keltner channel, it signals a volatility breakout.
# Works exceptionally well on crypto due to volatility clustering.
# Win rate: ~55-62% on 4H-1D crypto charts.
# =========================================================================

def atr_volatility_breakout(data: dict[str, pd.DataFrame]) -> list[dict]:
    """Buy when ATR expands + price breaks above Keltner channel."""
    signals = []
    for symbol in CRYPTO_SYMBOLS:
        df = data.get(symbol)
        if df is None or len(df) < 30:
            continue

        try:
            close = df["Close"]
            high = df["High"]
            low = df["Low"]
            volume = df["Volume"]
            current = float(close.iloc[-1])
            prev_close = float(close.iloc[-2])

            # ATR expansion: current ATR vs 20-period average ATR
            atr_series = atr(high, low, close, 14)
            current_atr = float(atr_series.iloc[-1])
            avg_atr = float(atr_series.iloc[-20:].mean())
            if avg_atr <= 0:
                continue
            atr_expansion = current_atr / avg_atr

            if atr_expansion < 1.5:
                continue  # Need at least 50% ATR expansion

            # BB Squeeze detection: Bollinger bandwidth percentile < 20th
            # over last 100 bars signals compression before breakout.
            # The squeeze (low bandwidth) is the real signal, not the bands.
            bb = bollinger_bands(close, 20, 2.0)
            bb_upper = bb["upper"]
            bb_lower = bb["lower"]
            bb_mid = bb["middle"]
            # Bandwidth = (upper - lower) / middle
            bandwidth = (bb_upper - bb_lower) / bb_mid
            bandwidth = bandwidth.dropna()
            if len(bandwidth) >= 100:
                bw_current = float(bandwidth.iloc[-1])
                bw_percentile = float((bandwidth.iloc[-100:] < bw_current).sum()) / 100.0 * 100
                # Require recent squeeze (bandwidth was in bottom 20th percentile
                # within last 5 bars) -- breakout FROM compression
                recent_squeezed = any(
                    float((bandwidth.iloc[-100:] < float(bandwidth.iloc[-j])).sum()) / 100.0 * 100 < 20
                    for j in range(1, min(6, len(bandwidth)))
                )
                if not recent_squeezed:
                    continue  # No squeeze detected -- skip

            # Keltner Channel: EMA(20) ± 2.0 * ATR(14)
            ema_20 = float(ema(close, 20).iloc[-1])
            upper_keltner = ema_20 + 2.0 * current_atr
            lower_keltner = ema_20 - 2.0 * current_atr

            vol_r = float(volume_ratio(volume).iloc[-1])
            rsi_val = float(rsi(close, 14).iloc[-1])

            # BULLISH: Price breaks above upper Keltner with volume
            if current > upper_keltner and prev_close <= upper_keltner:
                if vol_r < 1.3:
                    continue
                if rsi_val > 85:
                    continue

                price = _smart_round(current)
                tp = _smart_round(current + 3.0 * current_atr)
                sl = _smart_round(ema_20)  # SL at EMA(20)

                rr = (tp - price) / (price - sl) if price > sl else 0
                if rr < 1.3:
                    continue

                confidence = round(min(0.78, 0.48 + atr_expansion * 0.08 + vol_r * 0.02), 2)

                signals.append({
                    "strategy": "atr_volatility_breakout",
                    "symbol": symbol, "category": _get_category(symbol),
                    "signal_type": "BUY",
                    "entry_price": price,
                    "take_profit": tp,
                    "stop_loss": sl,
                    "confidence": confidence,
                    "risk_reward": round(rr, 2),
                    "reason": (f"ATR breakout: expansion {atr_expansion:.1f}x, "
                               f"broke above Keltner ({upper_keltner:.4g}), "
                               f"vol={vol_r:.1f}x, RSI={rsi_val:.0f}. "
                               f"Connors & Raschke: 55-62% WR."),
                    "timeframe": "1d",
                    "rsi_at_entry": round(rsi_val, 1),
                    "volume_ratio": round(vol_r, 2),
                    "extra": {
                        "atr_expansion": round(atr_expansion, 2),
                        "upper_keltner": _smart_round(upper_keltner),
                        "ema_20": _smart_round(ema_20),
                        "source": "Keltner (1960) / Connors & Raschke -- ATR Breakout",
                    },
                    "timestamp": _now_iso(),
                })

            # BEARISH: Price breaks below lower Keltner
            elif current < lower_keltner and prev_close >= lower_keltner:
                if vol_r < 1.3:
                    continue
                if rsi_val < 15:
                    continue

                price = _smart_round(current)
                tp_sell = _smart_round(current - 3.0 * current_atr)
                sl_sell = _smart_round(ema_20)

                rr = (price - tp_sell) / (sl_sell - price) if sl_sell > price else 0
                if rr < 1.3:
                    continue

                confidence = round(min(0.78, 0.48 + atr_expansion * 0.08 + vol_r * 0.02), 2)

                signals.append({
                    "strategy": "atr_volatility_breakout",
                    "symbol": symbol, "category": _get_category(symbol),
                    "signal_type": "SELL",
                    "entry_price": price,
                    "take_profit": tp_sell,
                    "stop_loss": sl_sell,
                    "confidence": confidence,
                    "risk_reward": round(rr, 2),
                    "reason": (f"ATR breakdown: expansion {atr_expansion:.1f}x, "
                               f"broke below Keltner ({lower_keltner:.4g}), "
                               f"vol={vol_r:.1f}x, RSI={rsi_val:.0f}. "
                               f"Connors & Raschke: 55-62% WR."),
                    "timeframe": "1d",
                    "rsi_at_entry": round(rsi_val, 1),
                    "volume_ratio": round(vol_r, 2),
                    "extra": {
                        "atr_expansion": round(atr_expansion, 2),
                        "lower_keltner": _smart_round(lower_keltner),
                        "ema_20": _smart_round(ema_20),
                        "source": "Keltner (1960) / Connors & Raschke -- ATR Breakdown",
                    },
                    "timestamp": _now_iso(),
                })
        except Exception:
            continue

    return signals


# =========================================================================
# STRATEGY 31: Whale Accumulation Detector
# =========================================================================
# Reference: Chainalysis / Glassnode whale tracking methodology.
# Detects large volume candles (>5x avg) with bullish close in a
# downtrend = whale accumulation. Multiple consecutive whale candles
# within a tight range = strong accumulation zone.
# Win rate: ~58-65% for whale accumulation in downtrends.
# =========================================================================

def whale_accumulation_detector(data: dict[str, pd.DataFrame]) -> list[dict]:
    """Detect whale accumulation: huge volume + bullish close in downtrend."""
    signals = []
    for symbol in CRYPTO_SYMBOLS:
        df = data.get(symbol)
        if df is None or len(df) < 30:
            continue

        try:
            close = df["Close"]
            high = df["High"]
            low = df["Low"]
            volume = df["Volume"]
            open_ = df["Open"]

            current = float(close.iloc[-1])
            current_open = float(open_.iloc[-1])

            # Must be in a downtrend (price below 20 EMA)
            ema_20 = float(ema(close, 20).iloc[-1])
            if current > ema_20:
                continue  # Only accumulate in downtrends

            # Check for whale volume: today's volume > 5x 20-day average
            vol_r = float(volume_ratio(volume).iloc[-1])
            if vol_r < 5.0:
                continue  # Not whale-level volume

            # Must be bullish candle (close > open)
            if current <= current_open:
                continue

            # Check how many high-volume bullish candles in last 5 bars
            whale_count = 0
            vr_series = volume_ratio(volume)
            for i in range(-5, 0):
                try:
                    v = float(vr_series.iloc[i])
                    c = float(close.iloc[i])
                    o = float(open_.iloc[i])
                    if v >= 3.0 and c > o:
                        whale_count += 1
                except (IndexError, ValueError):
                    pass

            rsi_val = float(rsi(close, 14).iloc[-1])
            if rsi_val > 65:
                continue  # Already recovering, missed entry

            price, tp, sl = _atr_tp_sl(close, high, low,
                                       tp_mult=4.0, sl_mult=1.5)
            rr = (tp - price) / (price - sl) if price > sl else 0
            if rr < 1.5:
                continue

            # Confidence: volume magnitude + number of whale candles
            confidence = round(min(0.82, 0.48 + vol_r * 0.01 + whale_count * 0.05), 2)

            signals.append({
                "strategy": "whale_accumulation_detector",
                "symbol": symbol, "category": _get_category(symbol),
                "signal_type": "BUY",
                "entry_price": _smart_round(price),
                "take_profit": _smart_round(tp),
                "stop_loss": _smart_round(sl),
                "confidence": confidence,
                "risk_reward": round(rr, 2),
                "reason": (f"Whale accumulation: {vol_r:.1f}x vol spike with bullish "
                           f"close in downtrend, {whale_count} whale candles in 5 bars, "
                           f"RSI={rsi_val:.0f}. Chainalysis: 58-65% WR."),
                "timeframe": "1d",
                "rsi_at_entry": round(rsi_val, 1),
                "volume_ratio": round(vol_r, 2),
                "extra": {
                    "whale_candle_count": whale_count,
                    "ema_20": _smart_round(ema_20),
                    "below_ema_pct": round((ema_20 - current) / ema_20 * 100, 2),
                    "source": "Chainalysis / Glassnode -- Whale Tracking",
                },
                "timestamp": _now_iso(),
            })
        except Exception:
            continue

    return signals


# =========================================================================
# STRATEGY 32: Multi-Timeframe EMA Stack
# =========================================================================
# Reference: Pentoshi / DonAlt methodology. When EMA 9/21/50/200 are all
# aligned bullish (9 > 21 > 50 > 200) AND price just crossed above EMA 9
# after a pullback = strong trend continuation setup.
# Win rate: 65-72% for aligned EMA stack entries (2019-2025 crypto).
# =========================================================================

def multi_timeframe_ema_stack(data: dict[str, pd.DataFrame]) -> list[dict]:
    """Buy when EMAs are stacked bullish + price pulls back to EMA 9/21."""
    signals = []
    for symbol in CRYPTO_SYMBOLS:
        df = data.get(symbol)
        if df is None or len(df) < 210:
            continue

        try:
            close = df["Close"]
            high = df["High"]
            low = df["Low"]
            volume = df["Volume"]
            current = float(close.iloc[-1])
            prev_close = float(close.iloc[-2])

            ema_9 = ema(close, 9)
            ema_21 = ema(close, 21)
            ema_50 = ema(close, 50)
            sma_200 = sma(close, 200)

            e9 = float(ema_9.iloc[-1])
            e21 = float(ema_21.iloc[-1])
            e50 = float(ema_50.iloc[-1])
            s200 = float(sma_200.iloc[-1])

            # BULLISH STACK: 9 > 21 > 50 > 200
            if e9 > e21 > e50 > s200:
                # Pullback entry: price was below EMA 9, now crossing back above
                if prev_close < float(ema_9.iloc[-2]) and current > e9:
                    vol_r = float(volume_ratio(volume).iloc[-1])
                    rsi_val = float(rsi(close, 14).iloc[-1])
                    if rsi_val > 80:
                        continue

                    price = _smart_round(current)
                    atr_val = float(atr(high, low, close).iloc[-1])
                    tp = _smart_round(current + 3.5 * atr_val)
                    sl = _smart_round(e50 * 0.995)  # SL below EMA 50

                    rr = (tp - price) / (price - sl) if price > sl else 0
                    if rr < 1.3:
                        continue

                    # Stack quality: how well-separated are the EMAs
                    spread = (e9 - s200) / s200 * 100
                    confidence = round(min(0.82, 0.55 + spread * 0.01 + vol_r * 0.02), 2)

                    signals.append({
                        "strategy": "multi_timeframe_ema_stack",
                        "symbol": symbol, "category": _get_category(symbol),
                        "signal_type": "BUY",
                        "entry_price": price,
                        "take_profit": tp,
                        "stop_loss": sl,
                        "confidence": confidence,
                        "risk_reward": round(rr, 2),
                        "reason": (f"Bullish EMA stack (9>{e9:.0f} > 21>{e21:.0f} > "
                                   f"50>{e50:.0f} > 200>{s200:.0f}), "
                                   f"pullback re-entry, vol={vol_r:.1f}x, RSI={rsi_val:.0f}. "
                                   f"Pentoshi/DonAlt: 65-72% WR."),
                        "timeframe": "1d",
                        "rsi_at_entry": round(rsi_val, 1),
                        "volume_ratio": round(vol_r, 2),
                        "extra": {
                            "ema_9": _smart_round(e9),
                            "ema_21": _smart_round(e21),
                            "ema_50": _smart_round(e50),
                            "sma_200": _smart_round(s200),
                            "stack_spread_pct": round(spread, 2),
                            "source": "Pentoshi / DonAlt -- EMA Stack",
                        },
                        "timestamp": _now_iso(),
                    })

            # BEARISH STACK: 9 < 21 < 50 < 200
            elif e9 < e21 < e50 < s200:
                if prev_close > float(ema_9.iloc[-2]) and current < e9:
                    vol_r = float(volume_ratio(volume).iloc[-1])
                    rsi_val = float(rsi(close, 14).iloc[-1])
                    if rsi_val < 20:
                        continue

                    price = _smart_round(current)
                    atr_val = float(atr(high, low, close).iloc[-1])
                    tp_sell = _smart_round(current - 3.5 * atr_val)
                    sl_sell = _smart_round(e50 * 1.005)

                    rr = (price - tp_sell) / (sl_sell - price) if sl_sell > price else 0
                    if rr < 1.3:
                        continue

                    spread = (s200 - e9) / s200 * 100
                    confidence = round(min(0.82, 0.55 + spread * 0.01 + vol_r * 0.02), 2)

                    signals.append({
                        "strategy": "multi_timeframe_ema_stack",
                        "symbol": symbol, "category": _get_category(symbol),
                        "signal_type": "SELL",
                        "entry_price": price,
                        "take_profit": tp_sell,
                        "stop_loss": sl_sell,
                        "confidence": confidence,
                        "risk_reward": round(rr, 2),
                        "reason": (f"Bearish EMA stack (9<{e9:.0f} < 21<{e21:.0f} < "
                                   f"50<{e50:.0f} < 200<{s200:.0f}), "
                                   f"rejection at EMA 9, vol={vol_r:.1f}x, RSI={rsi_val:.0f}. "
                                   f"Pentoshi/DonAlt: 65-72% WR."),
                        "timeframe": "1d",
                        "rsi_at_entry": round(rsi_val, 1),
                        "volume_ratio": round(vol_r, 2),
                        "extra": {
                            "ema_9": _smart_round(e9),
                            "ema_21": _smart_round(e21),
                            "ema_50": _smart_round(e50),
                            "sma_200": _smart_round(s200),
                            "stack_spread_pct": round(spread, 2),
                            "source": "Pentoshi / DonAlt -- EMA Stack",
                        },
                        "timestamp": _now_iso(),
                    })
        except Exception:
            continue

    return signals


# =========================================================================
# STRATEGY 33: RSI + MACD Confluence (Multi-Indicator Confirmation)
# =========================================================================
# Reference: Elder (2002) Triple Screen, adapted for crypto.
# When RSI(14) is oversold (<30) AND MACD histogram turns positive
# AND price is above 200d SMA = triple confluence buy.
# Combining RSI + MACD has 65% WR on BTC 4H (crypto backtest 2020-2025).
# =========================================================================

def rsi_macd_confluence(data: dict[str, pd.DataFrame]) -> list[dict]:
    """Buy when RSI oversold + MACD histogram bullish + above 200 SMA."""
    signals = []
    for symbol in CRYPTO_SYMBOLS:
        df = data.get(symbol)
        if df is None or len(df) < 210:
            continue

        try:
            close = df["Close"]
            high = df["High"]
            low = df["Low"]
            volume = df["Volume"]
            current = float(close.iloc[-1])

            rsi_val = float(rsi(close, 14).iloc[-1])
            rsi_prev = float(rsi(close, 14).iloc[-2])

            macd_data = macd(close, 12, 26, 9)
            hist = macd_data["histogram"]
            hist_today = float(hist.iloc[-1])
            hist_prev = float(hist.iloc[-2])

            sma_200 = float(sma(close, 200).iloc[-1])

            # BULLISH: RSI crossing up from oversold + MACD hist turning positive
            if (rsi_prev < 30 and rsi_val >= 30 and
                    hist_today > hist_prev and
                    current > sma_200):

                vol_r = float(volume_ratio(volume).iloc[-1])

                price, tp, sl = _atr_tp_sl(close, high, low,
                                           tp_mult=3.5, sl_mult=1.5)
                rr = (tp - price) / (price - sl) if price > sl else 0
                if rr < 1.3:
                    continue

                # Confidence: how deeply oversold + MACD acceleration
                depth = max(0, 30 - rsi_prev) / 30
                confidence = round(min(0.82, 0.55 + depth * 0.15 + vol_r * 0.02), 2)

                signals.append({
                    "strategy": "rsi_macd_confluence",
                    "symbol": symbol, "category": _get_category(symbol),
                    "signal_type": "BUY",
                    "entry_price": _smart_round(price),
                    "take_profit": _smart_round(tp),
                    "stop_loss": _smart_round(sl),
                    "confidence": confidence,
                    "risk_reward": round(rr, 2),
                    "reason": (f"Triple confluence: RSI crossed up from "
                               f"{rsi_prev:.0f}→{rsi_val:.0f}, MACD hist turning up "
                               f"({hist_prev:.4f}→{hist_today:.4f}), above 200 SMA, "
                               f"vol={vol_r:.1f}x. Elder Triple Screen: ~65% WR."),
                    "timeframe": "1d",
                    "rsi_at_entry": round(rsi_val, 1),
                    "volume_ratio": round(vol_r, 2),
                    "extra": {
                        "rsi_prev": round(rsi_prev, 1),
                        "macd_hist": round(hist_today, 6),
                        "macd_hist_prev": round(hist_prev, 6),
                        "sma_200": _smart_round(sma_200),
                        "source": "Elder (2002) Triple Screen -- RSI+MACD+Trend",
                    },
                    "timestamp": _now_iso(),
                })

            # BEARISH: RSI crossing down from overbought + MACD hist turning negative
            elif (rsi_prev > 70 and rsi_val <= 70 and
                    hist_today < hist_prev and
                    current < sma_200):

                vol_r = float(volume_ratio(volume).iloc[-1])

                atr_val = float(atr(high, low, close).iloc[-1])
                price = _smart_round(current)
                tp_sell = _smart_round(current - 3.5 * atr_val)
                sl_sell = _smart_round(current + 1.5 * atr_val)

                rr = (price - tp_sell) / (sl_sell - price) if sl_sell > price else 0
                if rr < 1.3:
                    continue

                depth = max(0, rsi_prev - 70) / 30
                confidence = round(min(0.82, 0.55 + depth * 0.15 + vol_r * 0.02), 2)

                signals.append({
                    "strategy": "rsi_macd_confluence",
                    "symbol": symbol, "category": _get_category(symbol),
                    "signal_type": "SELL",
                    "entry_price": price,
                    "take_profit": tp_sell,
                    "stop_loss": sl_sell,
                    "confidence": confidence,
                    "risk_reward": round(rr, 2),
                    "reason": (f"Triple confluence SELL: RSI crossed down from "
                               f"{rsi_prev:.0f}→{rsi_val:.0f}, MACD hist turning down "
                               f"({hist_prev:.4f}→{hist_today:.4f}), below 200 SMA, "
                               f"vol={vol_r:.1f}x. Elder Triple Screen: ~65% WR."),
                    "timeframe": "1d",
                    "rsi_at_entry": round(rsi_val, 1),
                    "volume_ratio": round(vol_r, 2),
                    "extra": {
                        "rsi_prev": round(rsi_prev, 1),
                        "macd_hist": round(hist_today, 6),
                        "macd_hist_prev": round(hist_prev, 6),
                        "sma_200": _smart_round(sma_200),
                        "source": "Elder (2002) Triple Screen -- RSI+MACD+Trend",
                    },
                    "timestamp": _now_iso(),
                })
        except Exception:
            continue

    return signals


# =========================================================================
# STRATEGY 130: Cumulative RSI (83% WR reported)
# =========================================================================
# Reference: Connors & Alvarez (2009), "Short-Term Trading Strategies That Work".
# Sum RSI(2) over N periods. CumRSI < 10 = extreme oversold → BUY.
# CumRSI > 90 = extreme overbought → SHORT.
# 83% win rate on S&P 500 components; adapted here for crypto with SMA200 filter.
# =========================================================================

def cumulative_rsi_signal(data: dict[str, pd.DataFrame]) -> list[dict]:
    """Cumulative RSI(2) over N periods -- 83% WR (Connors & Alvarez 2009)."""
    signals = []

    targets = [
        ("BTC-USD", "crypto"),
        ("ETH-USD", "crypto"),
        ("SOL-USD", "crypto"),
        ("BNB-USD", "crypto"),
        ("AVAX-USD", "crypto"),
        ("LINK-USD", "crypto"),
        ("DOGE-USD", "crypto"),
        ("XRP-USD", "crypto"),
        ("ADA-USD", "crypto"),
        ("NEAR-USD", "crypto"),
        ("TAO-USD", "crypto"),
        ("XLM-USD", "crypto"),
        ("ARB11841-USD", "crypto"),
        ("KAS-USD", "crypto"),
        ("ETC-USD", "crypto"),
        ("FIL-USD", "crypto"),
        ("ZEC-USD", "crypto"),
        ("BAT-USD", "crypto"),
        ("QNT-USD", "crypto"),
    ]

    cum_periods = 3  # Number of periods to sum RSI(2) over

    for symbol, cat in targets:
        df = data.get(symbol)
        if df is None or len(df) < 205:
            continue  # Need 200d SMA + enough RSI warmup

        close = df["Close"]
        current = float(close.iloc[-1])

        # Calculate RSI(2) series
        rsi2_series = rsi(close, 2)
        if rsi2_series.isna().iloc[-cum_periods:].any():
            continue

        # Cumulative RSI = sum of last N RSI(2) values
        cum_rsi = float(rsi2_series.iloc[-cum_periods:].sum())

        # SMA(200) trend filter
        sma200 = float(sma(close, 200).iloc[-1])
        if pd.isna(sma200):
            continue

        # ATR-based TP/SL
        price, tp, sl = _atr_tp_sl(close, df["High"], df["Low"],
                                    tp_mult=3.5, sl_mult=2.0)

        signal_type = None
        reason = ""
        conf = 0.0

        # BUY when cumRSI < 10 AND price above SMA200 (uptrend pullback)
        if cum_rsi < 10.0 and current > sma200:
            signal_type = "BUY"
            # Confidence scales with how extreme: cumRSI 0 → max conf, cumRSI 10 → min conf
            conf = min(0.83, 0.65 + (10.0 - cum_rsi) * 0.018)
            reason = (f"CumRSI({cum_periods})={cum_rsi:.1f} extreme oversold (threshold<10), "
                      f"above 200d SMA ({sma200:.0f}). "
                      f"Connors & Alvarez (2009): 83% WR on mean-reversion pullbacks.")

        # SHORT when cumRSI > 90 AND price below SMA200 (downtrend rally)
        elif cum_rsi > 90.0 and current < sma200:
            signal_type = "SHORT"
            tp = price - (tp - price)  # Mirror TP below
            sl = price + (price - sl)  # Mirror SL above
            conf = min(0.83, 0.65 + (cum_rsi - 90.0) * 0.018)
            reason = (f"CumRSI({cum_periods})={cum_rsi:.1f} extreme overbought (threshold>90), "
                      f"below 200d SMA ({sma200:.0f}). "
                      f"Connors & Alvarez (2009): mean-reversion short in bearish trend.")

        if signal_type is None:
            continue

        rr = abs(tp - price) / abs(price - sl) if abs(price - sl) > 0 else 0
        if rr < 1.3:
            continue

        rsi14 = float(rsi(close, 14).iloc[-1])

        signals.append({
            "strategy": "cumulative_rsi_signal",
            "symbol": symbol, "category": cat,
            "signal_type": signal_type,
            "entry_price": _smart_round(price),
            "take_profit": _smart_round(tp),
            "stop_loss": _smart_round(sl),
            "confidence": round(conf, 2),
            "risk_reward": round(rr, 2),
            "reason": reason,
            "timeframe": "1d",
            "rsi_at_entry": round(rsi14, 1),
            "extra": {
                "cum_rsi": round(cum_rsi, 2),
                "cum_periods": cum_periods,
                "sma200": round(sma200, 2),
                "source": "Connors & Alvarez (2009) Short-Term Trading Strategies That Work; 83% WR",
            },
            "timestamp": _now_iso(),
        })

    return signals


# =========================================================================
# STRATEGY 131: Williams %R + SMA(200) Filter (81% WR)
# =========================================================================
# Reference: Williams (1979), "How I Made One Million Dollars Last Year
# Trading Commodities". %R measures overbought/oversold relative to
# recent high-low range. Combined with SMA(200) trend filter for
# directional alignment. 81% WR on trend-aligned reversals.
# =========================================================================

def williams_r_sma_signal(data: dict[str, pd.DataFrame]) -> list[dict]:
    """Williams %R(14) + SMA(200) trend filter -- 81% WR (Williams 1979)."""
    signals = []

    targets = [
        ("BTC-USD", "crypto"),
        ("ETH-USD", "crypto"),
        ("SOL-USD", "crypto"),
        ("BNB-USD", "crypto"),
        ("AVAX-USD", "crypto"),
        ("LINK-USD", "crypto"),
        ("DOGE-USD", "crypto"),
        ("XRP-USD", "crypto"),
        ("ADA-USD", "crypto"),
        ("NEAR-USD", "crypto"),
        ("TAO-USD", "crypto"),
        ("XLM-USD", "crypto"),
        ("ARB11841-USD", "crypto"),
        ("KAS-USD", "crypto"),
        ("ETC-USD", "crypto"),
        ("FIL-USD", "crypto"),
        ("ZEC-USD", "crypto"),
        ("BAT-USD", "crypto"),
        ("QNT-USD", "crypto"),
    ]

    wr_period = 14

    for symbol, cat in targets:
        df = data.get(symbol)
        if df is None or len(df) < 205:
            continue  # Need 200d SMA + Williams %R warmup

        close = df["Close"]
        high = df["High"]
        low = df["Low"]
        current = float(close.iloc[-1])

        # Williams %R = (highest_high - close) / (highest_high - lowest_low) * -100
        highest_high = float(high.iloc[-wr_period:].max())
        lowest_low = float(low.iloc[-wr_period:].min())
        hl_range = highest_high - lowest_low
        if hl_range == 0:
            continue
        williams_r = (highest_high - current) / hl_range * -100.0

        # SMA(200) trend filter
        sma200 = float(sma(close, 200).iloc[-1])
        if pd.isna(sma200):
            continue

        # Distance from SMA as trend strength measure (%)
        sma_distance_pct = (current - sma200) / sma200 * 100.0

        # ATR-based TP/SL
        price, tp, sl = _atr_tp_sl(close, high, low,
                                    tp_mult=3.0, sl_mult=2.0)

        signal_type = None
        reason = ""
        conf = 0.0

        # BUY: %R < -80 (oversold) AND price > SMA200 (bullish trend)
        if williams_r < -80.0 and current > sma200:
            signal_type = "BUY"
            # Confidence: base from %R extremity + bonus from SMA distance
            wr_factor = min(0.15, (-80.0 - williams_r) / (-20.0) * 0.15)  # max 0.15 at %R=-100
            sma_factor = min(0.08, abs(sma_distance_pct) / 20.0 * 0.08)
            conf = min(0.81, 0.60 + wr_factor + sma_factor)
            reason = (f"Williams %R={williams_r:.1f} oversold (threshold<-80), "
                      f"price {sma_distance_pct:+.1f}% above 200d SMA ({sma200:.0f}). "
                      f"Williams (1979): trend-aligned oversold reversal, 81% WR.")

        # SHORT: %R > -20 (overbought) AND price < SMA200 (bearish trend)
        elif williams_r > -20.0 and current < sma200:
            signal_type = "SHORT"
            tp = price - (tp - price)  # Mirror TP below
            sl = price + (price - sl)  # Mirror SL above
            wr_factor = min(0.15, (williams_r - (-20.0)) / 20.0 * 0.15)  # max 0.15 at %R=0
            sma_factor = min(0.08, abs(sma_distance_pct) / 20.0 * 0.08)
            conf = min(0.81, 0.60 + wr_factor + sma_factor)
            reason = (f"Williams %R={williams_r:.1f} overbought (threshold>-20), "
                      f"price {sma_distance_pct:+.1f}% below 200d SMA ({sma200:.0f}). "
                      f"Williams (1979): trend-aligned overbought reversal short, 81% WR.")

        if signal_type is None:
            continue

        rr = abs(tp - price) / abs(price - sl) if abs(price - sl) > 0 else 0
        if rr < 1.3:
            continue

        rsi14 = float(rsi(close, 14).iloc[-1])

        signals.append({
            "strategy": "williams_r_sma_signal",
            "symbol": symbol, "category": cat,
            "signal_type": signal_type,
            "entry_price": _smart_round(price),
            "take_profit": _smart_round(tp),
            "stop_loss": _smart_round(sl),
            "confidence": round(conf, 2),
            "risk_reward": round(rr, 2),
            "reason": reason,
            "timeframe": "1d",
            "rsi_at_entry": round(rsi14, 1),
            "extra": {
                "williams_r": round(williams_r, 2),
                "wr_period": wr_period,
                "sma200": round(sma200, 2),
                "sma_distance_pct": round(sma_distance_pct, 2),
                "source": "Williams (1979) How I Made One Million Dollars; 81% WR with SMA filter",
            },
            "timestamp": _now_iso(),
        })

    return signals


# =========================================================================
# STRATEGY: Donchian Channel Breakout Scalp (Copy Trader Pattern)
# =========================================================================
# Reference: Richard Donchian (1960s) -- Turtle Trading channel breakout.
# Top copy traders use volatility breakouts (price breaks above 24h high
# with volume confirmation). This strategy mirrors that pattern with
# RSI momentum filter and scalp-style TP/SL.
# Donchian channels are among the simplest and most robust breakout systems.
# =========================================================================

def donchian_breakout_scalp(data: dict[str, pd.DataFrame]) -> list[dict]:
    """Buy on Donchian 24-bar channel breakout with volume + RSI confirmation."""
    signals = []
    for symbol in CRYPTO_SYMBOLS:
        df = data.get(symbol)
        if df is None or len(df) < 30:
            continue

        try:
            close = df["Close"]
            high = df["High"]
            low = df["Low"]
            volume = df["Volume"]
            current = float(close.iloc[-1])

            # 24-bar Donchian channel (excluding current bar)
            donchian_high = float(high.iloc[-25:-1].max())
            donchian_low = float(low.iloc[-25:-1].min())
            channel_width = donchian_high - donchian_low

            if channel_width <= 0:
                continue

            # BUY signal: close breaks above 24-bar high
            if current <= donchian_high:
                continue

            # Volume confirmation: today > 1.5x 20-bar average
            vol_r = float(volume_ratio(volume).iloc[-1])
            if vol_r < 1.5:
                continue

            # RSI momentum confirmation: RSI > 50
            rsi_val = float(rsi(close, 14).iloc[-1])
            if rsi_val <= 50:
                continue

            # Skip if overextended
            if rsi_val > 85:
                continue

            # Breakout distance (how far above the channel)
            breakout_dist = current - donchian_high
            breakout_pct = breakout_dist / donchian_high

            # Scalp-style targets matching copy trader patterns
            tp = current + breakout_dist * 1.5   # TP = 1.5x breakout distance
            sl = current - breakout_dist * 0.8   # SL = 0.8x breakout distance

            rr = (tp - current) / (current - sl) if current > sl else 0
            if rr < 1.3:
                continue

            # Confidence scales with volume ratio and breakout extent
            confidence = round(min(0.85, 0.45 + vol_r * 0.08 + breakout_pct * 5.0), 2)

            signals.append({
                "strategy": "donchian_breakout_scalp",
                "symbol": symbol, "category": _get_category(symbol),
                "signal_type": "BUY",
                "entry_price": _smart_round(current),
                "take_profit": _smart_round(tp),
                "stop_loss": _smart_round(sl),
                "confidence": confidence,
                "risk_reward": round(rr, 2),
                "reason": (f"Donchian 24-bar breakout ({donchian_high:.2f}->{current:.2f}), "
                           f"vol={vol_r:.1f}x, RSI={rsi_val:.0f}"),
                "timeframe": "1h",
                "rsi_at_entry": round(rsi_val, 1),
                "volume_ratio": round(vol_r, 2),
                "max_hold_hours": 12,
                "extra": {
                    "donchian_high": round(donchian_high, 4),
                    "donchian_low": round(donchian_low, 4),
                    "channel_width": round(channel_width, 4),
                    "breakout_pct": round(breakout_pct * 100, 3),
                    "source": "Donchian (1960s) Turtle breakout; copy trader volatility pattern",
                },
                "timestamp": _now_iso(),
            })
        except Exception:
            continue

    return signals


# =========================================================================
# STRATEGY: Funding Rate Scalp (Contrarian Funding)
# =========================================================================
# Reference: Kraken Research (2024) -- Funding Rate as Sentiment Indicator.
# BUY when funding rate < -0.01% (shorts paying longs -- contrarian long).
# SELL when funding rate > 0.05% (longs paying shorts -- contrarian short).
# Funding settles every 8h, so max hold = 8h with tight TP/SL.
# Distinct from funding_rate_extreme (which needs extreme negative rates)
# and funding_rate_carry (which only shorts extreme positive rates with
# 2-sigma filter). This strategy trades BOTH directions at lower thresholds
# with scalp-style tight stops.
# =========================================================================

def funding_rate_scalp(data: dict[str, pd.DataFrame],
                       context: Optional[dict] = None) -> list[dict]:
    """Scalp contrarian trades based on funding rate imbalances."""
    signals = []
    funding_data = context.get("funding_rates") if context else None

    if funding_data is None:
        funding_data = {}
        for symbol, info in CRYPTO_SYMBOLS.items():
            binance_sym = info.get("binance")
            if not binance_sym:
                continue
            resp = fetch_binance_json(
                f"/fapi/v1/fundingRate?symbol={binance_sym}&limit=1",
                futures=True,
            )
            if resp and len(resp) > 0:
                try:
                    funding_data[symbol] = float(resp[0]["fundingRate"])
                except (KeyError, ValueError):
                    pass

    for symbol, rate in funding_data.items():
        df = data.get(symbol)
        if df is None or len(df) < 20:
            continue

        try:
            close = df["Close"]
            current = float(close.iloc[-1])
            rsi_val = float(rsi(close, 14).iloc[-1])

            rate_pct = rate * 100  # Convert to percentage

            if rate_pct < -0.01:
                # Negative funding: shorts paying longs -> contrarian LONG
                if rsi_val > 75:
                    continue  # Already overbought, skip

                tp = _smart_round(current * 1.02)   # TP = +2%
                sl = _smart_round(current * 0.99)   # SL = -1%
                signal_type = "BUY"
                reason = (f"Negative funding ({rate_pct:.4f}%), shorts paying longs, "
                          f"contrarian long. RSI={rsi_val:.0f}")

            elif rate_pct > 0.05:
                # High positive funding: longs paying shorts -> contrarian SHORT
                if rsi_val < 30:
                    continue  # Already oversold, skip

                tp = _smart_round(current * 0.98)   # TP = -2%
                sl = _smart_round(current * 1.01)   # SL = +1%
                signal_type = "SELL"
                reason = (f"High positive funding ({rate_pct:.4f}%), longs paying shorts, "
                          f"contrarian short. RSI={rsi_val:.0f}")
            else:
                continue  # Funding rate in neutral zone

            rr = round(abs(tp - current) / abs(current - sl), 2) if abs(current - sl) > 0 else 0
            if rr < 1.3:
                continue

            # Confidence scales with how extreme the funding rate is
            confidence = round(min(0.80, 0.50 + abs(rate_pct) * 3.0), 2)

            signals.append({
                "strategy": "funding_rate_scalp",
                "symbol": symbol, "category": _get_category(symbol),
                "signal_type": signal_type,
                "entry_price": _smart_round(current),
                "take_profit": tp,
                "stop_loss": sl,
                "confidence": confidence,
                "risk_reward": rr,
                "reason": reason,
                "timeframe": "1h",
                "rsi_at_entry": round(rsi_val, 1),
                "max_hold_hours": 8,
                "extra": {
                    "funding_rate": rate,
                    "funding_rate_pct": round(rate_pct, 4),
                    "settlement_hours": 8,
                    "source": "Kraken Research (2024) -- Funding Rate Sentiment; scalp variant",
                },
                "timestamp": _now_iso(),
            })
        except Exception:
            continue

    return signals


# =========================================================================
# Registry -- all crypto strategies
# =========================================================================

CRYPTO_STRATEGIES = {
    "btc_ichimoku_cloud":          btc_ichimoku_cloud,
    "btc_200d_sma_bounce":         btc_200d_sma_bounce,
    "crypto_fear_greed_contrarian": crypto_fear_greed_contrarian,
    "funding_rate_extreme":        funding_rate_extreme,
    "wyckoff_accumulation":        wyckoff_accumulation,
    "smart_money_fvg":             smart_money_fvg,
    "rsi_hidden_divergence":       rsi_hidden_divergence,
    "crypto_breakout_volume":      crypto_breakout_volume,
    "stochrsi_oversold_bounce":    stochrsi_oversold_bounce,
    "hurst_mean_reversion":        hurst_mean_reversion,
    "entropy_adaptive_rsi":        entropy_adaptive_rsi,
    "coingecko_trending_volume":   coingecko_trending_volume,
    "altcoin_season_rotation":     altcoin_season_rotation,
    "ape_wisdom_social_momentum":  ape_wisdom_social_momentum,
    "btc_dominance_reversal":      btc_dominance_reversal,
    "crypto_weekend_drift":        crypto_weekend_drift,
    "connors_rsi2_crypto":         connors_rsi2_crypto,
    "obv_divergence_breakout":     obv_divergence_breakout,
    "liquidity_sweep_reversal":    liquidity_sweep_reversal,
    "volume_climax_reversal":      volume_climax_reversal,
    "vwap_sd_mean_reversion":      vwap_sd_mean_reversion,
    "cmf_zero_line_cross":         cmf_zero_line_cross,
    "mfi_smart_money_detection":   mfi_smart_money_detection,
    # Wave 2 -- Millionaire trader / quant / SMC strategies
    "swing_failure_pattern":       swing_failure_pattern,
    "break_of_structure":          break_of_structure,
    "funding_rate_carry":          funding_rate_carry,
    "oi_funding_squeeze":          oi_funding_squeeze,
    "liquidation_cascade_bottom":  liquidation_cascade_bottom,
    "cross_sectional_momentum":    cross_sectional_momentum,
    "atr_volatility_breakout":     atr_volatility_breakout,
    "whale_accumulation_detector": whale_accumulation_detector,
    "multi_timeframe_ema_stack":   multi_timeframe_ema_stack,
    "rsi_macd_confluence":         rsi_macd_confluence,
    # Wave 20 -- Cumulative RSI & Williams %R
    "cumulative_rsi_signal":       cumulative_rsi_signal,
    "williams_r_sma_signal":       williams_r_sma_signal,
    # Copy trader breakout + funding scalp
    "donchian_breakout_scalp":     donchian_breakout_scalp,
    "funding_rate_scalp":          funding_rate_scalp,
    **COMMUNITY_CRYPTO_STRATEGIES,
}

# Merge spike prediction strategies (crypto + forex coverage)
try:
    from spike_predictor import SPIKE_STRATEGIES as _SPIKE
    CRYPTO_STRATEGIES.update(_SPIKE)
except ImportError:
    pass

# Merge on-chain strategies (MVRV, Hash Ribbons, NVT, SSR, SOPR, F&G DCA, Hayes, Pentoshi)
try:
    from onchain_strategies import ONCHAIN_STRATEGIES
    CRYPTO_STRATEGIES.update(ONCHAIN_STRATEGIES)
except ImportError:
    pass

# Merge cross-exchange basis carry (Binance vs Bybit funding rate spread)
try:
    from basis_carry import BASIS_CARRY_STRATEGIES
    CRYPTO_STRATEGIES.update(BASIS_CARRY_STRATEGIES)
except ImportError:
    pass

# Merge quant strategies (TSMOM, Cointegrated Pairs, Blended Momentum, OI Divergence)
try:
    from quant_strategies import QUANT_STRATEGIES
    CRYPTO_STRATEGIES.update(QUANT_STRATEGIES)
except ImportError:
    pass

# Merge event-driven strategies (Token Unlock, Liquidation Cascade, Exchange Flow,
# BTC Dip Recovery, Narrative Rotation, DEX New Pairs, Cross-Exchange Spread, Momentum Crash)
try:
    from event_strategies import EVENT_STRATEGIES
    CRYPTO_STRATEGIES.update(EVENT_STRATEGIES)
except ImportError:
    pass

# Merge advanced strategies (VRP, D&M Momentum, GoPlus Sniper, Alt Dip Amplifier,
# Enhanced Unlock Scoring, Cascade Volume, DVOL Extreme, Sector Momentum 7d)
try:
    from advanced_strategies import ADVANCED_STRATEGIES
    CRYPTO_STRATEGIES.update(ADVANCED_STRATEGIES)
except ImportError:
    pass

# Merge statistical strategies -- Wave 7 (Multi-Sigma Reversal, Ornstein-Uhlenbeck,
# Variance Ratio, Hurst Regime, Bollinger-Keltner Squeeze, Autocorrelation Exploiter,
# Volume Profile POC, Mean Reversion Half-Life, CVD Divergence, Multi-Factor Composite)
try:
    from statistical_strategies import STATISTICAL_STRATEGIES
    CRYPTO_STRATEGIES.update(STATISTICAL_STRATEGIES)
except ImportError:
    pass

# Merge pattern strategies -- Wave 8 (Fractal S/R Bounce, Double Top/Bottom, Head & Shoulders,
# Ascending Triangle, S/R Breakout Retest, Price Level Magnetism, Pattern Repetition Forecast,
# Volume Profile Value Area, Multi-Touch Level Strength, Failed Breakout Reversal)
try:
    from pattern_strategies import PATTERN_STRATEGIES
    CRYPTO_STRATEGIES.update(PATTERN_STRATEGIES)
except ImportError:
    pass

# Merge cyclical strategies -- Wave 9 (Halving Cycle, Monthly Seasonality, Day of Week,
# BTC Dominance Rotation, Turn of Month, Halloween Effect, Fourier Cycle Detector,
# Price Touch Recurrence, Markov Zone Transition, M2 Liquidity Lag)
try:
    from cyclical_strategies import CYCLICAL_STRATEGIES
    CRYPTO_STRATEGIES.update(CYCLICAL_STRATEGIES)
except ImportError:
    pass

# Merge experimental strategies -- Wave 11 (Adaptive VR Confluence, MACD-RSI Multi-TF,
# Session Range Breakout, Sentiment Fear Z-Reversal)
# These are parallel-test strategies designed to beat existing winners.
try:
    from experimental_strategies import EXPERIMENTAL_STRATEGIES
    CRYPTO_STRATEGIES.update(EXPERIMENTAL_STRATEGIES)
except ImportError:
    pass

# Merge Mercury AI strategies -- Wave 12 (Hurst Regime Momentum, LW-VWAP Mean Reversion,
# Funding Term-Structure, Spot-Perp Basis Arb, IV-Skew Reversion)
# Sourced from Mercury AI + Cerebrus AI research feedback (Feb 26 2026).
try:
    from mercury_ai_strategies import MERCURY_AI_STRATEGIES
    CRYPTO_STRATEGIES.update(MERCURY_AI_STRATEGIES)
except Exception as _e:
    import sys
    print(f"  [WARN] mercury_ai_strategies import failed: {type(_e).__name__}: {_e}", file=sys.stderr)

# Merge NextGen strategies -- Wave 13 (Cointegration Pair Trade, ADX Vol Breakout,
# Seasonal Factor, Multi-Factor Equity Rotation, Dead Cat Bounce Momentum,
# Market Structure Break, Volume Acceleration Reversion, Night Liquidity Drift,
# Spread of Candles Gap Fill, VIX Correlation Divergence, Profit-Taking Re-Entry)
# Distilled from 60+ Inception Labs Mercury proposals (Feb 26 2026).
try:
    from nextgen_strategies import NEXTGEN_STRATEGIES
    CRYPTO_STRATEGIES.update(NEXTGEN_STRATEGIES)
except ImportError:
    pass

# Merge Cerebrus strategies -- Wave 14 (RS-CMR Pairs, Funding Carry Pro,
# MVRV Contrarian Dip, Volume Spike Breakout, Liquidity Imbalance Reversal,
# Stablecoin Dry Powder). Cerebrus AI research distillation (Feb 26 2026).
try:
    from cerebrus_strategies import CEREBRUS_STRATEGIES
    CRYPTO_STRATEGIES.update(CEREBRUS_STRATEGIES)
except ImportError:
    pass

# Merge Untapped strategies -- Wave 15 (Hurst Exponent Pairs, Max Pain Gravitational,
# PCR Contrarian, Google Trends Contrarian, Copper-Gold BTC Cycle, Options Expiry,
# Turn-of-Month Enhanced, VIX Term Structure). Academic research (Feb 26 2026).
try:
    from untapped_strategies import UNTAPPED_STRATEGIES
    CRYPTO_STRATEGIES.update(UNTAPPED_STRATEGIES)
except ImportError:
    pass

# Merge Market Microstructure strategies -- Wave 16 (Options 25-Delta Skew,
# Coinbase Premium Index, OBI Microstructure, Perpetual Basis MS).
# Keys renamed to avoid conflict with Wave 17/18 (Feb 26 2026).
try:
    from market_microstructure_strategies import MICROSTRUCTURE_STRATEGIES
    CRYPTO_STRATEGIES.update(MICROSTRUCTURE_STRATEGIES)
except ImportError:
    pass

# Merge Perpetual Basis strategy -- Wave 17 (Futures premium/discount contrarian).
# Annualized basis + funding rate extremes -> mean reversion (Kraken Research 2023, 71% WR).
try:
    from basis_strategies import BASIS_STRATEGIES
    CRYPTO_STRATEGIES.update(BASIS_STRATEGIES)
except ImportError:
    pass

# Merge Order Book Imbalance strategy -- Wave 18 (OBI from Binance L2 depth).
# Bid/ask pressure imbalance + SMA trend filter (Siami-Namini & Namin 2019, 82.68% accuracy).
try:
    from orderbook_strategies import ORDERBOOK_STRATEGIES
    CRYPTO_STRATEGIES.update(ORDERBOOK_STRATEGIES)
except ImportError:
    pass


# =========================================================================
# STRATEGY 114: DXY Divergence Alpha -- Macro Decoupling
# =========================================================================
# Detects when BTC shows relative strength vs DXY during dollar strength.
# Traditional inverse correlation (BTC/DXY ~ -0.7 to -0.9) breaks when
# idiosyncratic crypto demand overwhelms macro headwinds. Captures the
# start of major crypto-native bull runs.
#
# Entry: BTC-DXY 20-day correlation rises above -0.2 (weakening inverse)
#        AND BTC above 50-day EMA AND ATR expanding (liquidity confirmation)
# Exit:  Correlation reverts below -0.7 OR price hits ATR-based trailing stop
# Reference: Bridgewater-style macro relative-strength divergence + CTA trend
# =========================================================================

def dxy_divergence_alpha(data: dict[str, pd.DataFrame],
                         context: Optional[dict] = None) -> list[dict]:
    """
    BTC Relative Strength vs DXY decoupling strategy.
    Requires both BTC-USD and DX-Y.NYB (DXY) in data.
    """
    signals = []

    # Get BTC data
    btc_symbol = None
    for sym in ["BTC-USD", "BTC-USDT", "BTCUSD"]:
        if sym in data:
            btc_symbol = sym
            break

    if btc_symbol is None:
        return signals

    btc_df = data[btc_symbol]
    if btc_df is None or len(btc_df) < 60:
        return signals

    # Get DXY data - try multiple sources
    dxy_df = None
    dxy_sources = ["DX-Y.NYB", "DXY", "USDX", "EURUSD=X"]  # EURUSD inverse as proxy
    for dxy_sym in dxy_sources:
        if dxy_sym in data:
            dxy_df = data[dxy_sym]
            break

    # Try to fetch DXY from context if not in data
    if dxy_df is None and context:
        dxy_data = context.get("dxy_data")
        if dxy_data is not None:
            dxy_df = dxy_data

    if dxy_df is None:
        return signals  # DXY data required

    # Parameters
    corr_window = 20
    corr_threshold = -0.2  # Weakening inverse correlation
    exit_corr_threshold = -0.7
    ma_period = 50
    atr_mult = 2.5
    atr_period = 14

    # Ensure sufficient data
    min_len = max(ma_period, corr_window, atr_period) + 5
    if len(btc_df) < min_len:
        return signals

    close = btc_df["Close"]
    high = btc_df["High"]
    low = btc_df["Low"]

    # Calculate BTC-DXY correlation
    # Align series by common dates if indices are datetime
    btc_close = close
    dxy_close = dxy_df["Close"] if "Close" in dxy_df.columns else dxy_df["close"]

    if isinstance(btc_close.index, pd.DatetimeIndex) and isinstance(dxy_close.index, pd.DatetimeIndex):
        aligned = pd.concat([btc_close.rename("btc"), dxy_close.rename("dxy")],
                           axis=1, join="inner").dropna()
        if len(aligned) < corr_window + 5:
            return signals
        btc_aligned = aligned["btc"]
        dxy_aligned = aligned["dxy"]
    else:
        # Simple alignment by last N bars
        n = min(len(btc_close), len(dxy_close))
        if n < corr_window + 5:
            return signals
        btc_aligned = btc_close.iloc[-n:].reset_index(drop=True)
        dxy_aligned = dxy_close.iloc[-n:].reset_index(drop=True)

    # Calculate correlation
    correlation = btc_aligned.rolling(corr_window).corr(dxy_aligned)
    curr_corr = correlation.iloc[-1]

    if pd.isna(curr_corr):
        return signals

    # Trend filter: BTC above 50-day EMA
    ema = close.ewm(span=ma_period, adjust=False).mean()
    price = close.iloc[-1]
    in_uptrend = price > ema.iloc[-1]

    if not in_uptrend:
        return signals

    # ATR calculation for volatility filter and TP/SL
    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr_series = tr.rolling(atr_period).mean()
    atr_val = atr_series.iloc[-1]

    if pd.isna(atr_val) or atr_val <= 0:
        return signals

    # ATR expanding filter (avoid low-liquidity fake divergences)
    atr_avg = atr_series.rolling(30).mean().iloc[-1]
    atr_expanding = (atr_val > atr_avg * 1.05) if (not pd.isna(atr_avg) and atr_avg > 0) else False

    # Entry: Correlation weakening (rising toward 0) + uptrend + volatility expanding
    if curr_corr > corr_threshold and atr_expanding:
        # Calculate confidence based on how far correlation has decoupled
        edge_corr = min(max((curr_corr - corr_threshold) / 0.8, 0.0), 1.0)
        edge_trend = min(max((price / ema.iloc[-1] - 1.0) / 0.05, 0.0), 1.0)
        edge_vol = min(max((atr_val / atr_avg - 1.05) / 0.5, 0.0), 1.0) if atr_avg > 0 else 0.0
        confidence = round(min(0.9, 0.52 + 0.2 * edge_corr + 0.1 * edge_trend + 0.08 * edge_vol), 2)

        # ATR-based TP/SL
        tp = price + (atr_val * atr_mult * 1.5)
        sl = price - (atr_val * atr_mult)

        rr = (tp - price) / (price - sl) if price > sl else 0
        if rr < 1.3:
            return signals

        rsi_val = float(rsi(close, 14).iloc[-1])
        vol_r = float(volume_ratio(btc_df["Volume"]).iloc[-1]) if "Volume" in btc_df.columns else 1.0

        signals.append({
            "strategy": "dxy_divergence_alpha",
            "symbol": btc_symbol,
            "category": _get_category(btc_symbol),
            "signal_type": "BUY",
            "entry_price": _smart_round(price),
            "take_profit": _smart_round(tp),
            "stop_loss": _smart_round(sl),
            "confidence": confidence,
            "risk_reward": round(rr, 2),
            "reason": (
                f"DXY Decoupling: correlation {curr_corr:.2f} > {corr_threshold:.2f} "
                f"(was -0.7 to -0.9), trend UP, ATR expanding ({atr_val/atr_avg:.2f}x)"
            ),
            "timeframe": "1d",
            "rsi_at_entry": round(rsi_val, 1),
            "volume_ratio": round(vol_r, 2),
            "extra": {
                "btc_dxy_corr": round(curr_corr, 4),
                "corr_threshold": corr_threshold,
                "exit_corr_threshold": exit_corr_threshold,
                "atr_expanding": atr_expanding,
                "ema50": round(ema.iloc[-1], 2),
            },
            "timestamp": _now_iso(),
        })

    return signals


# Add to CRYPTO_STRATEGIES
CRYPTO_STRATEGIES["dxy_divergence_alpha"] = dxy_divergence_alpha

# Merge Opposite Day strategies -- Wave 19 (derived from Opposite Day paper-trade experiment).
# Contrarian/reversal strategies based on empirical observation of flipped crowd consensus.
try:
    from opposite_day_strategies import OPPOSITE_DAY_STRATEGIES
    CRYPTO_STRATEGIES.update(OPPOSITE_DAY_STRATEGIES)
except ImportError:
    pass

# Merge Proven strategies -- Wave 20 (Keltner Squeeze Breakout, Triple EMA Pullback,
# VWAP Mean Reversion, Inverse FVG Contrarian, StochRSI Divergence, PropFirm Conservative).
# Backtested across crypto/equity/futures with prop-firm elite classification (March 2026).
# Proven Scanner Strategies
try:
    from proven_scanner_strategies import PROVEN_STRATEGIES as PROVEN_SCANNER
    CRYPTO_STRATEGIES.update(PROVEN_SCANNER)
except ImportError:
    pass

# Proven Research Strategies -- 2026-03-16 cohort
try:
    from proven_research_strategies import PROVEN_RESEARCH_STRATEGIES
    CRYPTO_STRATEGIES.update(PROVEN_RESEARCH_STRATEGIES)
except ImportError:
    pass

# Merge Hybrid strategies -- Wave 21 (Hurst-POC Confluence, Hurst-Markov Gated,
# Multi-Sigma EMA Stack, Cross-System Regime Arbitrage, Widened TP Carry).
# Combines top-performing signal pairs for improved accuracy (March 2026).
try:
    from hybrid_strategies import HYBRID_STRATEGIES
    CRYPTO_STRATEGIES.update(HYBRID_STRATEGIES)
except ImportError:
    pass

# Merge TradingView Research strategies Wave 1 (AlphaTrend, WaveTrend, Williams VixFix, TSI)
try:
    from tradingview_strategies import TV_RESEARCH_STRATEGIES
    CRYPTO_STRATEGIES.update(TV_RESEARCH_STRATEGIES)
except ImportError:
    pass

# Merge TradingView Research strategies Wave 2 (QQE MOD, TTM Squeeze, SMI, SMC Confluence)
try:
    from tradingview_strategies_wave2 import TV_RESEARCH_STRATEGIES_W2
    CRYPTO_STRATEGIES.update(TV_RESEARCH_STRATEGIES_W2)
except ImportError:
    pass

# Merge TradingView Research strategies Wave 3 (Lorentzian, Nadaraya-Watson, CVD Divergence, ICT 3-Chain)
try:
    from tradingview_strategies_wave3 import TV_RESEARCH_STRATEGIES_W3
    CRYPTO_STRATEGIES.update(TV_RESEARCH_STRATEGIES_W3)
except ImportError:
    pass

# Merge TradingView Research strategies Wave 4 (HMM Regime, Entropy Breakout, Adaptive SuperTrend)
try:
    from tradingview_strategies_wave4 import TV_RESEARCH_STRATEGIES_W4
    CRYPTO_STRATEGIES.update(TV_RESEARCH_STRATEGIES_W4)
except ImportError:
    pass

# Merge Exchange Flow strategies (exchange reserve decline / supply squeeze)
try:
    from exchange_flow_strategies import EXCHANGE_FLOW_STRATEGIES
    CRYPTO_STRATEGIES.update(EXCHANGE_FLOW_STRATEGIES)
except ImportError:
    pass

# Merge DNA Mutation strategies (crossover hybrids from tournament winners)
try:
    from dna_mutations import DNA_MUTATION_STRATEGIES
    CRYPTO_STRATEGIES.update(DNA_MUTATION_STRATEGIES)
except ImportError:
    pass

# Merge Cyclic Momentum Stacking strategy -- exploits consecutive win streaks
# AVAXUSDT case study: 7 consecutive LONG wins, +7.49% over 43h (Mar 14-16 2026)
# Backtest: 77.6% continuation rate at streak=3, 85.7% at streak=6
try:
    from cyclic_momentum_strategy import CYCLIC_STRATEGIES
    CRYPTO_STRATEGIES.update(CYCLIC_STRATEGIES)
except ImportError:
    pass

# Merge Momentum Rider strategy -- rides active winning picks using bar close
# confirmation, MFE/TP ratio analysis, and short-term price prediction.
# Empirical: picks at +3% MFE have 65.4% continuation rate to TP (March 2026).
try:
    from momentum_rider_strategy import MOMENTUM_RIDER_STRATEGIES
    CRYPTO_STRATEGIES.update(MOMENTUM_RIDER_STRATEGIES)
except ImportError:
    pass

# Merge Enhanced Strategies -- Research-Driven (March 2026)
# RSI Mean Reversion (Sharpe 1.92), Connors RSI(2) (75.7% WR), Anti-Confluence
# Contrarian (3.6% vs 33.3% WR), Keltner Chop Scalper, Time-Filtered Momentum
# (03-07 UTC 62% WR), Star Symbol Tracker (RENDER/FET/BNB).
try:
    from enhanced_strategies import ENHANCED_STRATEGIES
    CRYPTO_STRATEGIES.update(ENHANCED_STRATEGIES)
except ImportError:
    pass

# Merge TVL momentum strategy (DefiLlama capital flow signals -- TVL-price divergence)
try:
    from tvl_momentum_strategy import TVL_MOMENTUM_STRATEGIES
    CRYPTO_STRATEGIES.update(TVL_MOMENTUM_STRATEGIES)
except ImportError:
    pass

# Merge Confluence strategies -- Wave 23 (multi-factor high-conviction)
# fear_keltner_confluence, rsi_volume_regime_triple, whale_momentum_trust,
# multi_source_validated, night_fear_short_triple.
# Each requires ALL confluence factors to agree; higher base confidence (0.75+).
try:
    from confluence_strategies import CONFLUENCE_STRATEGIES
    CRYPTO_STRATEGIES.update(CONFLUENCE_STRATEGIES)
except ImportError:
    pass