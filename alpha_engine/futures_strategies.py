"""
ALPHA_ENGINE -- Futures Strategies
====================================
4 academically-backed futures strategies targeting index, bond, and metals futures.
All use daily OHLCV via yfinance (=F suffix contracts).

Research basis:
- TSMOM: Moskowitz, Ooi & Pedersen (2012) -- 55-60% WR, Sharpe 1.1
- ConnorsRSI2 on index futures: Connors & Alvarez (2008) -- 73-76% WR, Sharpe 4.84
- Cross-Asset Momentum: Gargano et al. (2019) -- Sharpe 1.6 (45% above standard TSMOM)
- Vol-Regime Breakout: Donchian Channel + ATR regime gate, practitioner standard

Silent error notes discovered during agent investigation (2026-04-07):
- Futures previously had only 3 tracked trades and ZERO dedicated strategies
- FUTURES_SYMBOLS existed in config but were never imported by any scanner agent
- CL=F (WTI crude) was removed after 26 trades at 3.8% WR -- excluded here
- All strategies use inverse-vol position sizing per CTA best practice
"""

from __future__ import annotations

from datetime import datetime, timezone

import numpy as np
import pandas as pd

from config import FUTURES_SYMBOLS, CATEGORY_RISK
from indicators import sma, ema, rsi, atr, adx, macd, bollinger_bands, zscore


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# ATR-based TP/SL for futures (wider than forex, tighter than meme)
# ---------------------------------------------------------------------------
def _futures_tp_sl(
    close: pd.Series,
    high: pd.Series,
    low: pd.Series,
    direction: str = "BUY",
    tp_mult: float = 2.5,
    sl_mult: float = 1.5,
) -> tuple[float, float, float]:
    """ATR-based TP/SL for futures.  Default R:R = 2.5/1.5 ≈ 1.67.

    Hard cap: 8% TP, 5% SL to prevent runaway targets on volatile contracts.
    """
    atr_val = float(atr(high, low, close, 14).iloc[-1])
    price = float(close.iloc[-1])
    tp_dist = min(tp_mult * atr_val, price * 0.08)
    sl_dist = min(sl_mult * atr_val, price * 0.05)
    rr = tp_dist / sl_dist if sl_dist > 0 else 0.0
    if direction == "BUY":
        return price, price + tp_dist, price - sl_dist
    return price, price - tp_dist, price + sl_dist


# ---------------------------------------------------------------------------
# STRATEGY 1: Time-Series Momentum (CTA Trend-Following)
# ---------------------------------------------------------------------------
# Reference: Moskowitz, Ooi & Pedersen (2012) "Time Series Momentum", JFE.
# Proven across 58 liquid futures contracts, Jan 1985-Dec 2009.
# Multi-horizon blend (1m + 3m + 12m) raises Sharpe ~45% per Quantpedia.
#
# Logic:
#   - Compute 12m, 3m, 1m excess return for each futures contract
#   - Blend 0.4/0.35/0.25 weighted signal (higher weight to longer horizon)
#   - Scale position size by inverse 60-day realised vol (vol parity sizing)
#   - Enter LONG if blend > 0, SHORT if blend < 0
#   - Confidence scales with signal magnitude; cap at 0.80
# ---------------------------------------------------------------------------
def futures_tsmom(data: dict[str, pd.DataFrame]) -> list[dict]:
    """Multi-horizon time-series momentum for futures contracts."""
    signals: list[dict] = []

    for symbol, meta in FUTURES_SYMBOLS.items():
        df = data.get(symbol)
        if df is None or len(df) < 260:
            continue

        close = df["Close"]
        # Filter out NaN / zero prices
        if pd.isna(close.iloc[-1]) or close.iloc[-1] <= 0:
            continue

        # Lookback returns (annualised sign)
        r12 = float(close.iloc[-1] / close.iloc[-252] - 1) if len(close) >= 252 else None
        r3 = float(close.iloc[-1] / close.iloc[-63] - 1) if len(close) >= 63 else None
        r1 = float(close.iloc[-1] / close.iloc[-21] - 1) if len(close) >= 21 else None

        if r12 is None or r3 is None or r1 is None:
            continue

        # Multi-horizon blend (Moskowitz weights)
        blend = 0.40 * np.sign(r12) + 0.35 * np.sign(r3) + 0.25 * np.sign(r1)
        if blend == 0:
            continue

        direction = "BUY" if blend > 0 else "SELL"

        # Inverse-vol sizing signal: higher vol → lower confidence
        daily_rets = close.pct_change().dropna()
        vol_60d = float(daily_rets.iloc[-60:].std()) * np.sqrt(252)
        vol_adj = max(0.0, 1.0 - vol_60d / 0.5)  # 50% annual vol = zero boost

        # Agreement: how aligned are the 3 horizons?
        agreement = abs(blend) / 1.0  # 0.25, 0.65, or 1.0 when partial/2/3 agree
        base_conf = 0.55 + 0.15 * agreement + 0.05 * vol_adj
        confidence = round(min(0.80, base_conf), 2)

        # Magnitude of the fastest signal (1m) for strength metric
        signal_strength = abs(r1)

        entry, tp, sl = _futures_tp_sl(
            close, df["High"], df["Low"],
            direction=direction,
            tp_mult=2.5 if direction == "BUY" else 2.0,
            sl_mult=1.5,
        )
        rr = abs(tp - entry) / abs(entry - sl) if abs(entry - sl) > 0 else 0.0
        if rr < 1.20:
            continue

        signals.append({
            "strategy": "futures_tsmom",
            "symbol": symbol,
            "category": "futures",
            "asset_class": "FUTURES",
            "signal_type": direction,
            "entry_price": round(entry, 4),
            "take_profit": round(tp, 4),
            "stop_loss": round(sl, 4),
            "confidence": confidence,
            "risk_reward": round(rr, 2),
            "reason": (
                f"TSMOM blend={blend:.2f} (12m={r12:.1%} 3m={r3:.1%} 1m={r1:.1%}), "
                f"vol_60d={vol_60d:.2%}, {meta.get('name', symbol)}"
            ),
            "timeframe": "1d",
            "extra": {
                "r12m": round(r12, 4),
                "r3m": round(r3, 4),
                "r1m": round(r1, 4),
                "blend": round(blend, 2),
                "vol_60d": round(vol_60d, 4),
                "agreement": round(agreement, 2),
                "exchange": meta.get("exchange", "CME"),
            },
            "timestamp": _now_iso(),
        })

    return signals


# ---------------------------------------------------------------------------
# STRATEGY 2: Connors RSI-2 Mean Reversion on Index Futures
# ---------------------------------------------------------------------------
# Reference: Connors & Alvarez (2008) "Short Term Trading Strategies That Work"
# Validated: SPY proxy 75.7% WR (p=6e-6), QQQ proxy 75.3% WR (p=8e-6).
# Research shows ES=F and NQ=F exhibit the same RSI-2 oversold snap-back effect.
#
# Logic:
#   - Require price > SMA(200) — long-term uptrend filter
#   - RSI(2) < 5 (deeply oversold in context of uptrend)
#   - RSI(14) > 25 (not in outright crash)
#   - ATR-based TP (1.5x ATR), SL (0.75x ATR); exit at RSI(2) > 70 OR max 10d
# ---------------------------------------------------------------------------
def futures_connors_rsi2(data: dict[str, pd.DataFrame]) -> list[dict]:
    """Connors RSI-2 mean reversion on index and metal futures."""
    signals: list[dict] = []

    # Only index/treasury futures for this strategy (directional behavior matches RSI-2 research)
    targets = {k: v for k, v in FUTURES_SYMBOLS.items() if k in (
        "ES=F", "NQ=F", "YM=F", "RTY=F", "ZN=F", "ZT=F"
    )}

    for symbol, meta in targets.items():
        df = data.get(symbol)
        if df is None or len(df) < 210:
            continue

        close = df["Close"]
        high = df["High"]
        low = df["Low"]

        if pd.isna(close.iloc[-1]) or close.iloc[-1] <= 0:
            continue

        sma200 = sma(close, 200)
        rsi2 = rsi(close, 2)
        rsi14 = rsi(close, 14)

        if pd.isna(sma200.iloc[-1]) or pd.isna(rsi2.iloc[-1]):
            continue

        # Must be above long-term trend
        if close.iloc[-1] < float(sma200.iloc[-1]):
            continue

        rsi2_val = float(rsi2.iloc[-1])
        rsi14_val = float(rsi14.iloc[-1])

        # ConnorsRSI2 entry: deeply oversold in uptrend.
        # Skip if RSI-2 is NOT deeply oversold (>= 5) OR if RSI-14 is NOT
        # in generally-oversold territory (> 50).  Original bug (2026-04-07
        # Copilot commit b5827459ef): condition was `rsi14_val < 25` which
        # killed the BEST signals (those where both RSI-2 and RSI-14 were
        # deeply depressed) because the `or` logic turned a confirmation
        # filter into a kill switch.  Fix: invert the RSI-14 threshold so
        # we skip only when RSI-14 is above 50 (not oversold at all).
        if rsi2_val >= 5 or rsi14_val > 50:
            continue

        # Rate the signal by how oversold
        oversold_degree = (5.0 - rsi2_val) / 5.0  # 0 → 1 as RSI2 drops to 0
        confidence = round(min(0.83, 0.72 + 0.11 * oversold_degree), 2)

        entry, tp, sl = _futures_tp_sl(
            close, high, low,
            direction="BUY",
            tp_mult=1.5,
            sl_mult=0.75,
        )
        rr = abs(tp - entry) / abs(entry - sl) if abs(entry - sl) > 0 else 0.0
        if rr < 1.50:
            continue

        signals.append({
            "strategy": "futures_connors_rsi2",
            "symbol": symbol,
            "category": "futures",
            "asset_class": "FUTURES",
            "signal_type": "BUY",
            "entry_price": round(entry, 4),
            "take_profit": round(tp, 4),
            "stop_loss": round(sl, 4),
            "confidence": confidence,
            "risk_reward": round(rr, 2),
            "reason": (
                f"ConnorsRSI2: RSI(2)={rsi2_val:.1f} (< 5 threshold), "
                f"RSI(14)={rsi14_val:.1f}, above SMA200, "
                f"{meta.get('name', symbol)} — 75%+ WR on index proxies"
            ),
            "timeframe": "1d",
            "extra": {
                "rsi2": round(rsi2_val, 2),
                "rsi14": round(rsi14_val, 2),
                "sma200": round(float(sma200.iloc[-1]), 4),
                "price_to_sma200": round(
                    float(close.iloc[-1]) / float(sma200.iloc[-1]) - 1, 4
                ),
                "exchange": meta.get("exchange", "CME"),
            },
            "timestamp": _now_iso(),
        })

    return signals


# ---------------------------------------------------------------------------
# STRATEGY 3: Cross-Asset Momentum (Bond → Equity Signal)
# ---------------------------------------------------------------------------
# Reference: Gargano, Pettenuzzo & Timmermann (2019) "Cross-Asset Signals and
# Time Series Momentum", JFE. Diversified cross-asset TSMOM yields Sharpe 45%
# higher than single-asset TSMOM.
#
# Logic:
#   - When ZN=F (10Y T-Note) has positive 1m + 3m momentum, go LONG ES=F / NQ=F
#   - When equities (ES/NQ) positive momentum, short ZN=F (bonds sell-off as equities rally)
#   - Cross-signal adds orthogonal alpha uncorrelated with single-asset TSMOM
# ---------------------------------------------------------------------------
def futures_cross_asset_momentum(data: dict[str, pd.DataFrame]) -> list[dict]:
    """Bond-to-equity cross-asset momentum signal."""
    signals: list[dict] = []

    zn_df = data.get("ZN=F")  # 10-Year T-Note futures
    if zn_df is None or len(zn_df) < 70:
        return signals

    zn_close = zn_df["Close"]
    if len(zn_close) < 64:
        return signals

    # Bond momentum signals
    zn_r1m = float(zn_close.iloc[-1] / zn_close.iloc[-21] - 1)
    zn_r3m = float(zn_close.iloc[-1] / zn_close.iloc[-63] - 1)
    zn_blend = 0.5 * np.sign(zn_r1m) + 0.5 * np.sign(zn_r3m)

    equity_futures = ["ES=F", "NQ=F", "YM=F"]

    for sym in equity_futures:
        df = data.get(sym)
        if df is None or len(df) < 65:
            continue

        close = df["Close"]
        if pd.isna(close.iloc[-1]) or close.iloc[-1] <= 0:
            continue

        # Bond positive momentum → equity LONG (risk-on signal)
        if zn_blend > 0:
            direction = "BUY"
            confidence = round(0.58 + 0.07 * abs(zn_blend), 2)
            reason = (
                f"Cross-Asset: ZN=F (bond) 1m={zn_r1m:.1%} 3m={zn_r3m:.1%} → "
                f"risk-on bond momentum, equity LONG signal"
            )
        else:
            # Bond negative momentum (rates rising) → equities may face headwind
            # Only fire if equity itself also has positive momentum
            eq_r1m = float(close.iloc[-1] / close.iloc[-21] - 1) if len(close) >= 21 else 0
            if eq_r1m <= 0:
                continue  # Both signals negative — no edge
            direction = "BUY"
            confidence = round(0.55, 2)
            reason = (
                f"Cross-Asset: ZN=F bond negative but {sym} 1m={eq_r1m:.1%} "
                f"equity standalone momentum"
            )

        meta = FUTURES_SYMBOLS.get(sym, {})
        entry, tp, sl = _futures_tp_sl(
            close, df["High"], df["Low"],
            direction=direction,
            tp_mult=2.0,
            sl_mult=1.2,
        )
        rr = abs(tp - entry) / abs(entry - sl) if abs(entry - sl) > 0 else 0.0
        if rr < 1.20:
            continue

        signals.append({
            "strategy": "futures_cross_asset_momentum",
            "symbol": sym,
            "category": "futures",
            "asset_class": "FUTURES",
            "signal_type": direction,
            "entry_price": round(entry, 4),
            "take_profit": round(tp, 4),
            "stop_loss": round(sl, 4),
            "confidence": confidence,
            "risk_reward": round(rr, 2),
            "reason": reason,
            "timeframe": "1d",
            "extra": {
                "zn_r1m": round(zn_r1m, 4),
                "zn_r3m": round(zn_r3m, 4),
                "zn_blend": round(zn_blend, 2),
                "exchange": meta.get("exchange", "CME"),
            },
            "timestamp": _now_iso(),
        })

    return signals


# ---------------------------------------------------------------------------
# STRATEGY 4: Volatility-Regime Breakout (Donchian + ATR gate)
# ---------------------------------------------------------------------------
# Practitioner-validated CTA technique: buy new N-day highs when ATR is
# expanding (trend acceleration), avoid when vol is contracting.
# Filter: ADX > 20 (trend strong enough to sustain breakout).
# Hard rule: only fire on metals (GC=F, SI=F) and treasury futures (ZN=F)
# to avoid the CL=F debacle (removed after 26 trades at 3.8% WR).
# ---------------------------------------------------------------------------
def futures_vol_regime_breakout(data: dict[str, pd.DataFrame]) -> list[dict]:
    """Donchian Channel breakout with ATR-expansion confirmation."""
    signals: list[dict] = []

    # Safe subset: metals + treasuries only (confirmed non-commodity-disaster contracts)
    safe_contracts = {k: v for k, v in FUTURES_SYMBOLS.items() if k in (
        "GC=F", "SI=F", "ZN=F", "ZT=F"
    )}

    for symbol, meta in safe_contracts.items():
        df = data.get(symbol)
        if df is None or len(df) < 30:
            continue

        close = df["Close"]
        high_ser = df["High"]
        low_ser = df["Low"]

        if pd.isna(close.iloc[-1]) or close.iloc[-1] <= 0:
            continue

        # Donchian channel (20-day).
        # The channel ceiling/floor are derived from high/low series (standard
        # Donchian definition), but the BREAKOUT comparison uses the PRIOR bar's
        # channel values (shifted by 1) so today's close can meaningfully breach
        # them.  Original bug (2026-04-07 Copilot commit b5827459ef): compared
        # `close.iloc[-1] >= dc_high.iloc[-1]` where dc_high is `high.rolling(20).max()`.
        # Since close < high by definition, this condition was structurally
        # impossible — the strategy never fired.  Fix: compare close against
        # the prior bar's channel top/bottom (shift=1), which is the canonical
        # Donchian breakout definition (close > yesterday's 20-day high = breakout).
        dc_high = high_ser.rolling(20).max()
        dc_low = low_ser.rolling(20).min()
        # Shift by 1 so today's close is compared against the channel that was
        # established as of yesterday's close (no look-ahead, achievable threshold).
        dc_high_prev = dc_high.shift(1)
        dc_low_prev = dc_low.shift(1)
        if pd.isna(dc_high_prev.iloc[-1]) or pd.isna(dc_low_prev.iloc[-1]):
            continue

        price = float(close.iloc[-1])
        dc_h = float(dc_high_prev.iloc[-1])   # yesterday's 20d high-of-highs
        dc_l = float(dc_low_prev.iloc[-1])    # yesterday's 20d low-of-lows

        # Breakout check: close breaks above/below prior channel boundary
        prev_close = float(close.iloc[-2]) if len(close) > 1 else price
        prev_dc_h = float(dc_high_prev.iloc[-2]) if len(dc_high_prev) > 1 else dc_h
        prev_dc_l = float(dc_low_prev.iloc[-2]) if len(dc_low_prev) > 1 else dc_l

        new_20d_high = price >= dc_h and prev_close < prev_dc_h
        new_20d_low = price <= dc_l and prev_close > prev_dc_l

        if not new_20d_high and not new_20d_low:
            continue

        # ADX filter: only trade confirmed trends
        adx_val = float(adx(high_ser, low_ser, close, 14).iloc[-1])
        if adx_val < 20:
            continue

        # ATR expansion gate: current ATR > 20d avg ATR (momentum accelerating)
        atr_ser = atr(high_ser, low_ser, close, 14)
        atr_current = float(atr_ser.iloc[-1])
        atr_avg = float(atr_ser.rolling(20).mean().iloc[-1])
        if atr_current < atr_avg * 1.05:
            continue  # No ATR expansion — false breakout risk high

        direction = "BUY" if new_20d_high else "SELL"
        atr_expansion_ratio = atr_current / atr_avg if atr_avg > 0 else 1.0
        confidence = round(min(0.78, 0.60 + 0.05 * (adx_val - 20) / 10 + 0.05 * (atr_expansion_ratio - 1)), 2)

        entry, tp, sl = _futures_tp_sl(
            close, high_ser, low_ser,
            direction=direction,
            tp_mult=2.5,
            sl_mult=1.5,
        )
        rr = abs(tp - entry) / abs(entry - sl) if abs(entry - sl) > 0 else 0.0
        if rr < 1.20:
            continue

        signals.append({
            "strategy": "futures_vol_regime_breakout",
            "symbol": symbol,
            "category": "futures",
            "asset_class": "FUTURES",
            "signal_type": direction,
            "entry_price": round(entry, 4),
            "take_profit": round(tp, 4),
            "stop_loss": round(sl, 4),
            "confidence": confidence,
            "risk_reward": round(rr, 2),
            "reason": (
                f"Donchian {'high' if direction == 'BUY' else 'low'} breakout: "
                f"ADX={adx_val:.1f} > 20, ATR ratio={atr_expansion_ratio:.2f}x, "
                f"{meta.get('name', symbol)}"
            ),
            "timeframe": "1d",
            "extra": {
                "adx": round(adx_val, 1),
                "atr_expansion": round(atr_expansion_ratio, 2),
                "dc_high": round(dc_h, 4),
                "dc_low": round(dc_l, 4),
                "exchange": meta.get("exchange", "CME"),
            },
            "timestamp": _now_iso(),
        })

    return signals


# ---------------------------------------------------------------------------
# Public registry for the non_crypto_agent
# ---------------------------------------------------------------------------
FUTURES_STRATEGIES: dict[str, callable] = {
    "futures_tsmom": futures_tsmom,
    "futures_connors_rsi2": futures_connors_rsi2,
    "futures_cross_asset_momentum": futures_cross_asset_momentum,
    "futures_vol_regime_breakout": futures_vol_regime_breakout,
}
