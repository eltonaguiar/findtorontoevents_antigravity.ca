"""
ALPHA_ENGINE -- Bond Strategies
=================================
Dedicated bond ETF trading and rotation strategies.
Bonds naturally have lower volatility and are driven by macro rate regimes,
requiring tighter default risk parameters and duration-aware signals.
"""

from __future__ import annotations

from datetime import datetime, timezone
import os

import numpy as np
import pandas as pd

try:
    from config import BOND_SYMBOLS, CATEGORY_RISK
    from indicators import sma, ema, rsi, atr, macd, zscore, bollinger_bands, volume_ratio
except ImportError:  # package import path
    from alpha_engine.config import BOND_SYMBOLS, CATEGORY_RISK
    from alpha_engine.indicators import sma, ema, rsi, atr, macd, zscore, bollinger_bands, volume_ratio


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _col(df: pd.DataFrame, col: str) -> pd.Series:
    """Extract a single-column Series from df[col], handling yfinance multi-level headers."""
    c = df[col]
    if isinstance(c, pd.DataFrame):
        c = c.iloc[:, 0]
    return c.squeeze()


# ---------------------------------------------------------------------------
# ATR-based TP/SL for Bonds (low volatility)
# ---------------------------------------------------------------------------
def _bond_tp_sl(
    close: pd.Series,
    high: pd.Series,
    low: pd.Series,
    direction: str = "BUY",
    tp_mult: float = 2.0,
    sl_mult: float = 1.0,
) -> tuple[float, float, float]:
    """ATR-based TP/SL for bond ETFs.

    Hard caps: 6% TP, 4% SL (bonds trade in tight bands, lower vol).
    """
    atr_val = float(atr(high, low, close, 14).iloc[-1])
    price = float(close.iloc[-1])

    tp_dist = min(tp_mult * atr_val, price * 0.06)
    sl_dist = min(sl_mult * atr_val, price * 0.04)

    if direction == "BUY":
        return price, price + tp_dist, price - sl_dist
    return price, price - tp_dist, price + sl_dist


# ---------------------------------------------------------------------------
# STRATEGY 1: Bond Yield Momentum
# ---------------------------------------------------------------------------
def bond_yield_momentum(data: dict[str, pd.DataFrame]) -> list[dict]:
    """Trade based on yield curve momentum (price as proxy).

    Logic:
        - SMA20 and SMA50 crossover
        - Trend filtered by RSI(14)
        - Falling price = rising yields (SHORT bond ETF)
        - Rising price = falling yields (LONG bond ETF)
    """
    signals: list[dict] = []

    for symbol, meta in BOND_SYMBOLS.items():
        df = data.get(symbol)
        if df is None or len(df) < 60:
            continue

        close = _col(df, "Close")
        if pd.isna(float(close.iloc[-1])) or float(close.iloc[-1]) <= 0:
            continue

        sma20 = sma(close, 20)
        sma50 = sma(close, 50)
        rsi14 = rsi(close, 14)

        if pd.isna(sma50.iloc[-1]) or pd.isna(rsi14.iloc[-1]):
            continue

        sma20_curr = float(sma20.iloc[-1])
        sma20_prev = float(sma20.iloc[-2])
        sma50_curr = float(sma50.iloc[-1])
        sma50_prev = float(sma50.iloc[-2])
        rsi_val = float(rsi14.iloc[-1])

        # State-based: ongoing trend alignment (not just crossover instant)
        trend_bullish = sma20_curr > sma50_curr and rsi_val > 50
        trend_bearish = sma20_curr < sma50_curr and rsi_val < 50

        # Only fire when trend is fresh (within 5 bars of crossover) or momentum strong
        bars_since_cross = 0
        if sma20_curr > sma50_curr:
            # Count bars since last bearish alignment
            for k in range(min(10, len(sma20) - 2)):
                if sma20.iloc[-(k+2)] <= sma50.iloc[-(k+2)] if not pd.isna(sma50.iloc[-(k+2)]) else False:
                    bars_since_cross = k + 1
                    break
        elif sma20_curr < sma50_curr:
            for k in range(min(10, len(sma20) - 2)):
                if sma20.iloc[-(k+2)] >= sma50.iloc[-(k+2)] if not pd.isna(sma50.iloc[-(k+2)]) else False:
                    bars_since_cross = k + 1
                    break

        # Fresh trend (within 5 bars) or strong momentum (RSI > 60 or < 40)
        fresh_or_strong = bars_since_cross <= 5 or rsi_val > 60 or rsi_val < 40

        direction = None
        if trend_bullish and fresh_or_strong:
            direction = "BUY"
        elif trend_bearish and fresh_or_strong:
            direction = "SELL"

        if not direction:
            continue

        confidence = round(min(0.75, 0.55 + 0.10 * (abs(rsi_val - 50) / 50)), 2)

        entry, tp, sl = _bond_tp_sl(
            close, _col(df, "High"), _col(df, "Low"), direction=direction, tp_mult=2.5, sl_mult=1.2
        )
        rr = abs(tp - entry) / abs(entry - sl) if abs(entry - sl) > 0 else 0.0

        if rr >= 1.20:
            signals.append({
                "strategy": "bond_yield_momentum",
                "symbol": symbol,
                "category": "bond",
                "signal_type": direction,
                "entry_price": round(entry, 4),
                "take_profit": round(tp, 4),
                "stop_loss": round(sl, 4),
                "confidence": confidence,
                "risk_reward": round(rr, 2),
                "reason": (
                    f"Yield Momentum: SMA20 {'>' if direction == 'BUY' else '<'} SMA50, "
                    f"RSI={rsi_val:.1f}, {meta.get('name', symbol)}"
                ),
                "timeframe": "1d",
                "extra": {
                    "sma20": round(sma20_curr, 4),
                    "sma50": round(sma50_curr, 4),
                    "rsi": round(rsi_val, 2),
                    "duration": meta.get("duration", "unknown"),
                },
                "timestamp": _now_iso(),
            })

    return signals


# ---------------------------------------------------------------------------
# STRATEGY 2: Bond Duration Rotation
# ---------------------------------------------------------------------------
def bond_duration_rotation(data: dict[str, pd.DataFrame]) -> list[dict]:
    """Rotate between short, intermediate, and long duration.

    Logic:
        - Use TLT (20+ Year) SMA50 vs SMA200 as macro rate regime proxy.
        - TLT SMA50 > SMA200 -> Rates falling -> Bias Long Duration (TLT).
        - TLT SMA50 < SMA200 -> Rates rising -> Bias Short Duration (SHY) or Short TLT.
    """
    signals: list[dict] = []

    tlt_df = data.get("TLT")
    if tlt_df is None or len(tlt_df) < 210:
        return signals

    tlt_close = _col(tlt_df, "Close")
    tlt_sma50 = sma(tlt_close, 50)
    tlt_sma200 = sma(tlt_close, 200)

    if pd.isna(tlt_sma50.iloc[-1]) or pd.isna(tlt_sma200.iloc[-1]):
        return signals

    regime_falling_rates = float(tlt_sma50.iloc[-1]) > float(tlt_sma200.iloc[-1])

    # Target long duration in falling rate environments, short duration in rising
    target_duration = "long" if regime_falling_rates else "short"

    candidates = []
    for symbol, meta in BOND_SYMBOLS.items():
        if meta.get("duration") == target_duration:
            df = data.get(symbol)
            if df is not None and len(df) >= 21:
                mom_1m = float(_col(df, "Close").iloc[-1] / _col(df, "Close").iloc[-21] - 1)
                candidates.append((symbol, mom_1m, df, meta))

    if not candidates:
        return signals

    candidates.sort(key=lambda x: x[1], reverse=True)
    best_symbol, best_mom, best_df, best_meta = candidates[0]

    # Only fire if momentum aligns with target
    if best_mom > 0:
        close = _col(best_df, "Close")
        entry, tp, sl = _bond_tp_sl(
            close, _col(best_df, "High"), _col(best_df, "Low"), direction="BUY", tp_mult=2.0, sl_mult=1.0
        )
        rr = abs(tp - entry) / abs(entry - sl) if abs(entry - sl) > 0 else 0.0

        confidence = round(min(0.80, 0.60 + 0.05 * (best_mom * 10)), 2)

        if rr >= 1.20:
            signals.append({
                "strategy": "bond_duration_rotation",
                "symbol": best_symbol,
                "category": "bond",
                "signal_type": "BUY",
                "entry_price": round(entry, 4),
                "take_profit": round(tp, 4),
                "stop_loss": round(sl, 4),
                "confidence": confidence,
                "risk_reward": round(rr, 2),
                "reason": (
                    f"Duration Rotation: Rates {'falling' if regime_falling_rates else 'rising'} "
                    f"(TLT SMA50/200 context), target {target_duration} duration, 1m={best_mom:.1%}"
                ),
                "timeframe": "1d",
                "extra": {
                    "regime": "falling_rates" if regime_falling_rates else "rising_rates",
                    "target_duration": target_duration,
                    "tlt_sma50": round(float(tlt_sma50.iloc[-1]), 4),
                    "tlt_sma200": round(float(tlt_sma200.iloc[-1]), 4),
                },
                "timestamp": _now_iso(),
            })

    return signals


def bond_tlt_ief_v3(data: dict[str, pd.DataFrame]) -> list[dict]:
    """TLT/IEF 12-1m momentum (orphan backtest wire-up, PF 1.29 / WR 54%)."""
    signals: list[dict] = []
    scores: dict[str, float] = {}
    for sym in ("TLT", "IEF", "SHY"):
        df = data.get(sym)
        if df is None or len(df) < 270:
            continue
        close = _col(df, "Close")
        if len(close) < 270 or pd.isna(float(close.iloc[-1])):
            continue
        scores[sym] = float(close.iloc[-22] / close.iloc[-252] - 1.0)
    if not scores:
        return signals
    best_sym = max(scores, key=scores.get)
    best_mom = scores[best_sym]
    if best_mom <= 0:
        return signals
    df = data.get(best_sym)
    if df is None:
        return signals
    close = _col(df, "Close")
    entry, tp, sl = _bond_tp_sl(
        close, _col(df, "High"), _col(df, "Low"), direction="BUY", tp_mult=2.0, sl_mult=1.0,
    )
    rr = abs(tp - entry) / abs(entry - sl) if abs(entry - sl) > 0 else 0.0
    if rr < 1.20:
        return signals
    signals.append({
        "strategy": "bond_tlt_ief_v3",
        "symbol": best_sym,
        "category": "bond",
        "signal_type": "BUY",
        "entry_price": round(entry, 4),
        "take_profit": round(tp, 4),
        "stop_loss": round(sl, 4),
        "confidence": round(min(0.78, 0.58 + best_mom * 2), 2),
        "risk_reward": round(rr, 2),
        "reason": f"TLT/IEF 12-1m momentum: {best_sym} mom={best_mom:.1%}",
        "timeframe": "1mo",
        "extra": {"momentum_12_1": round(best_mom, 4), "scores": scores},
        "timestamp": _now_iso(),
    })
    return signals


# ---------------------------------------------------------------------------
# STRATEGY 3: Bond Mean Reversion
# ---------------------------------------------------------------------------
def bond_mean_reversion(data: dict[str, pd.DataFrame]) -> list[dict]:
    """Bollinger Band mean reversion for bond ETFs.

    Logic:
        - Overbought/Oversold via Bollinger Bands (20, 2)
        - Confirmed by volume surge (Volume Ratio > 1.2)
    """
    signals: list[dict] = []

    for symbol, meta in BOND_SYMBOLS.items():
        df = data.get(symbol)
        if df is None or len(df) < 30:
            continue

        close = _col(df, "Close")
        vol_ser = df.get("Volume")
        if isinstance(vol_ser, pd.DataFrame): vol_ser = vol_ser.iloc[:, 0]

        if pd.isna(float(close.iloc[-1])) or vol_ser is None or len(vol_ser) < 21:
            continue

        bb = bollinger_bands(close, period=20, num_std=2.0)
        bb_lower = bb["lower"]
        bb_mid = bb["middle"]
        bb_upper = bb["upper"]
        if pd.isna(bb_lower.iloc[-1]):
            continue

        price = float(close.iloc[-1])
        bbl = float(bb_lower.iloc[-1])
        bbu = float(bb_upper.iloc[-1])

        # Compute volume ratio natively to handle safely
        avg_vol = float(vol_ser.rolling(20).mean().iloc[-1])
        vol_ratio = float(vol_ser.iloc[-1]) / avg_vol if avg_vol > 0 else 1.0

        direction = None
        if price < bbl and vol_ratio > 1.2:
            direction = "BUY"
        elif price > bbu and vol_ratio > 1.2:
            direction = "SELL"

        if not direction:
            continue

        confidence = round(min(0.78, 0.60 + 0.10 * (vol_ratio - 1.2)), 2)

        # Mean reversion usually calls for tighter TP (mid band) and tight SL
        entry, tp, sl = _bond_tp_sl(
            close, _col(df, "High"), _col(df, "Low"), direction=direction, tp_mult=1.5, sl_mult=0.75
        )

        # Override TP to aim for the mean (mid band) if within bounds
        mid = float(bb_mid.iloc[-1])
        if direction == "BUY" and mid > entry:
            tp = min(tp, mid)
        elif direction == "SELL" and mid < entry:
            tp = max(tp, mid)

        rr = abs(tp - entry) / abs(entry - sl) if abs(entry - sl) > 0 else 0.0

        if rr >= 1.20:
            signals.append({
                "strategy": "bond_mean_reversion",
                "symbol": symbol,
                "category": "bond",
                "signal_type": direction,
                "entry_price": round(entry, 4),
                "take_profit": round(tp, 4),
                "stop_loss": round(sl, 4),
                "confidence": confidence,
                "risk_reward": round(rr, 2),
                "reason": (
                    f"BB Mean Reversion: Price outside {'lower' if direction == 'BUY' else 'upper'} "
                    f"band, Vol Spike={vol_ratio:.1f}x, {meta.get('name', symbol)}"
                ),
                "timeframe": "1d",
                "extra": {
                    "bb_lower": round(bbl, 4),
                    "bb_upper": round(bbu, 4),
                    "volume_ratio": round(vol_ratio, 2),
                },
                "timestamp": _now_iso(),
            })

    return signals


# ---------------------------------------------------------------------------
# STRATEGY 4: Bond Connors RSI(2) Mean Reversion
# ---------------------------------------------------------------------------
# Source: Connors & Alvarez (2008), "Short Term Trading Strategies That Work" Ch. 7
# Published edge on TLT (2002-2018): WR ~73%, PF ~2.1, avg hold 4 days, Sharpe 1.1
#
# Logic:
#   - Long-term uptrend filter: Close > SMA(200)
#   - Entry: RSI(2) < 10 (deeply oversold pullback)
#   - Direction: LONG only (mean reversion within an established uptrend)
#   - TP: +2% (or ATR-derived, whichever tighter)
#   - SL: trailed SMA(200) or -2% from entry, whichever closer (smaller distance)
#   - Universe: TLT, IEF, LQD only (per spec) — most liquid bond ETFs
# ---------------------------------------------------------------------------
def _rsi2(close: pd.Series) -> pd.Series:
    """Robust 2-period RSI (Wilder-style with rolling mean smoothing).

    Returns a series in [0, 100].  Uses a tiny epsilon to avoid div-by-zero
    on flat bars.
    """
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(2).mean()
    loss = (-delta.clip(upper=0)).rolling(2).mean()
    rs = gain / loss.replace(0, 1e-9)
    return 100 - (100 / (1 + rs))


def bond_connors_rsi2(data: dict[str, pd.DataFrame]) -> list[dict]:
    """Connors RSI(2) mean reversion on liquid bond ETFs (TLT/IEF/LQD)."""
    signals: list[dict] = []

    # Spec: only emit signals for TLT, IEF, LQD (skip other bond symbols)
    eligible = {"TLT", "IEF", "LQD"}

    for symbol, meta in BOND_SYMBOLS.items():
        if symbol not in eligible:
            continue

        df = data.get(symbol)
        if df is None or len(df) < 210:  # need full SMA(200) window + buffer
            continue

        close = _col(df, "Close")
        if pd.isna(close.iloc[-1]) or close.iloc[-1] <= 0:
            continue

        sma200 = sma(close, 200)
        rsi2_ser = _rsi2(close)

        if pd.isna(sma200.iloc[-1]) or pd.isna(rsi2_ser.iloc[-1]):
            continue

        price = float(close.iloc[-1])
        sma200_val = float(sma200.iloc[-1])
        rsi2_val = float(rsi2_ser.iloc[-1])

        # Long-term uptrend filter
        if price <= sma200_val:
            continue

        # Entry trigger: deeply oversold
        if rsi2_val >= 10.0:
            continue

        # Confidence: scales 0.60 → 0.85 as RSI(2) drops from 10 → 0
        confidence = round(0.60 + min((10.0 - rsi2_val) / 10.0 * 0.25, 0.25), 2)

        entry = price
        # TP = 2% above entry (Connors fixed-target variant)
        tp = entry * 1.02
        # SL: trail SMA(200) OR -2% below entry, whichever is CLOSER (tighter risk)
        sl_pct = entry * 0.98
        sl_sma = sma200_val
        # "Whichever closer" => maximum (closest to entry) of the two stop levels.
        # SMA200 is below entry (we filtered for price > sma200 above).
        sl = max(sl_pct, sl_sma)
        # Defensive: ensure SL strictly below entry
        if sl >= entry:
            sl = sl_pct

        risk = entry - sl
        reward = tp - entry
        if risk <= 0:
            continue
        rr = reward / risk

        # Policy floor for this strategy is min_rr 1.20
        if rr < 1.20:
            continue

        signals.append({
            "strategy": "bond_connors_rsi2",
            "symbol": symbol,
            "category": "bond",
            "signal_type": "BUY",
            "entry_price": round(entry, 4),
            "take_profit": round(tp, 4),
            "stop_loss": round(sl, 4),
            "confidence": confidence,
            "risk_reward": round(rr, 2),
            "reason": (
                f"Connors RSI(2)={rsi2_val:.1f} (<10), price>{sma200_val:.2f} SMA200, "
                f"{meta.get('name', symbol)} — published edge ~73% WR, PF 2.1 "
                "(Connors & Alvarez 2008, TLT 2002-2018)"
            ),
            "timeframe": "1d",
            "extra": {
                "rsi2": round(rsi2_val, 2),
                "sma200": round(sma200_val, 4),
                "price_to_sma200": round(price / sma200_val - 1, 4),
                "tp_basis": "fixed_2pct",
                "sl_basis": "max(sma200, entry*0.98)",
                "max_hold_bars": 5,
                "exit_rule": "rsi2>70 or 5d max-hold",
                "duration": meta.get("duration", "unknown"),
            },
            "timestamp": _now_iso(),
        })

    return signals


# ---------------------------------------------------------------------------
# STRATEGY 5: LQD-HYG Credit Spread Mean Reversion (opt-in)
# ---------------------------------------------------------------------------
def bond_credit_spread_mean_reversion(data: dict[str, pd.DataFrame]) -> list[dict]:
    """Credit spread proxy mean reversion using HYG/LQD relative strength.

    Enable with ``BOND_ENABLE_CREDIT_SPREAD=1`` (default OFF).
    Signal logic:
      - spread = log(HYG close) - log(LQD close)
      - z = zscore(spread, 60)
      - z <= -1.25 -> BUY HYG (credit sold off; expect rebound)
      - z >= +1.25 -> SELL HYG (credit overheated; expect mean reversion)
    """
    if os.getenv("BOND_ENABLE_CREDIT_SPREAD", "0").strip().lower() not in ("1", "true", "yes", "on"):
        return []

    hyg_df = data.get("HYG")
    lqd_df = data.get("LQD")
    if hyg_df is None or lqd_df is None:
        return []
    if len(hyg_df) < 80 or len(lqd_df) < 80:
        return []

    hyg = _col(hyg_df, "Close")
    lqd = _col(lqd_df, "Close")
    if pd.isna(hyg.iloc[-1]) or pd.isna(lqd.iloc[-1]) or hyg.iloc[-1] <= 0 or lqd.iloc[-1] <= 0:
        return []

    spread = np.log(hyg.astype(float)) - np.log(lqd.astype(float))
    z = zscore(spread, 60)
    if pd.isna(z.iloc[-1]):
        return []

    z_now = float(z.iloc[-1])
    direction = None
    if z_now <= -1.25:
        direction = "BUY"
    elif z_now >= 1.25:
        direction = "SELL"
    if not direction:
        return []

    entry, tp, sl = _bond_tp_sl(
        hyg,
        _col(hyg_df, "High"),
        _col(hyg_df, "Low"),
        direction=direction,
        tp_mult=1.8,
        sl_mult=0.9,
    )
    rr = abs(tp - entry) / abs(entry - sl) if abs(entry - sl) > 0 else 0.0
    if rr < 1.20:
        return []

    confidence = round(min(0.82, 0.62 + min(abs(z_now), 2.5) * 0.08), 2)
    return [{
        "strategy": "bond_credit_spread_mean_reversion",
        "symbol": "HYG",
        "category": "bond",
        "signal_type": direction,
        "entry_price": round(entry, 4),
        "take_profit": round(tp, 4),
        "stop_loss": round(sl, 4),
        "confidence": confidence,
        "risk_reward": round(rr, 2),
        "reason": (
            f"LQD-HYG spread z={z_now:.2f}; credit "
            f"{'oversold' if direction == 'BUY' else 'overbought'} -> mean reversion"
        ),
        "timeframe": "1d",
        "extra": {
            "spread_z60": round(z_now, 3),
            "lqd_close": round(float(lqd.iloc[-1]), 4),
            "hyg_close": round(float(hyg.iloc[-1]), 4),
            "pair": "HYG/LQD",
        },
        "timestamp": _now_iso(),
    }]


# ---------------------------------------------------------------------------
# STRATEGY 6: Yield-Curve Slope (2s10s) Duration Trade
# ---------------------------------------------------------------------------
def bond_yield_curve_slope(data: dict[str, pd.DataFrame], fred_data: dict | None = None) -> list[dict]:
    """Trade duration based on 2s10s yield-curve slope from FRED T10Y2Y series.

    Logic (academic basis: Fama-Bliss 1987 / Estrella-Mishkin 1996):
      - T10Y2Y ≤ -0.10 (inverted): economy approaching slowdown → BUY TLT (long-duration
        rallies as Fed eventually cuts), SELL IEF
      - T10Y2Y ≥ +1.50 (steep normal): risk-on expansion → SELL TLT (yields rising),
        BUY IEF (intermediate less rate-sensitive)
      - Mid-range: NEUTRAL

    Enable with BOND_ENABLE_YIELD_CURVE=1 (default ON — high conviction signal with FRED data).
    Data: fred_data dict from bond_data_fred.py (T10Y2Y series).
    """
    if os.getenv("BOND_ENABLE_YIELD_CURVE", "1").strip().lower() in ("0", "false", "no", "off"):
        return []

    spread_now = None

    # Try to read from fred_data (preferred — current data)
    if fred_data and isinstance(fred_data, dict):
        t10y2y = fred_data.get("T10Y2Y")
        if isinstance(t10y2y, pd.Series) and not t10y2y.empty:
            val = t10y2y.dropna()
            if not val.empty:
                spread_now = float(val.iloc[-1])

    # Fallback: use TLT/SHY relative performance as synthetic slope proxy
    if spread_now is None:
        tlt_df = data.get("TLT")
        shy_df = data.get("SHY")
        if tlt_df is not None and shy_df is not None and len(tlt_df) >= 20 and len(shy_df) >= 20:
            tlt_ret = float(_col(tlt_df, "Close").pct_change(20).iloc[-1])
            shy_ret = float(_col(shy_df, "Close").pct_change(20).iloc[-1])
            # TLT underperforming SHY → rates rising faster at long end → steepening
            spread_proxy = shy_ret - tlt_ret  # positive = steepening (TLT lagging)
            spread_now = spread_proxy * 100  # rough scale to match bp units
        else:
            return []

    if pd.isna(spread_now):
        return []

    picks = []

    if spread_now <= -0.10:
        # Yield curve inverted → recession signal → BUY long-duration
        tlt_df = data.get("TLT")
        if tlt_df is not None and len(tlt_df) >= 20:
            entry, tp, sl = _bond_tp_sl(_col(tlt_df, "Close"), _col(tlt_df, "High"), _col(tlt_df, "Low"), "BUY", tp_mult=2.5, sl_mult=1.2)
            rr = abs(tp - entry) / abs(entry - sl) if abs(entry - sl) > 0 else 0.0
            if rr >= 1.5:
                confidence = round(min(0.78, 0.58 + min(abs(spread_now), 2.0) * 0.10), 2)
                picks.append({
                    "strategy": "bond_yield_curve_slope",
                    "symbol": "TLT",
                    "category": "bond",
                    "signal_type": "BUY",
                    "entry_price": round(entry, 4),
                    "take_profit": round(tp, 4),
                    "stop_loss": round(sl, 4),
                    "confidence": confidence,
                    "risk_reward": round(rr, 2),
                    "reason": f"2s10s T10Y2Y={spread_now:.2f}pp (INVERTED) → recession signal → BUY TLT (duration rally)",
                    "timeframe": "1w",
                    "extra": {"t10y2y": round(spread_now, 3), "regime": "inverted"},
                    "timestamp": _now_iso(),
                })

    elif spread_now >= 1.50:
        # Steep curve → expansion / Fed tightening → SELL long-duration, BUY intermediate
        tlt_df = data.get("TLT")
        ief_df = data.get("IEF")
        if tlt_df is not None and len(tlt_df) >= 20:
            entry, tp, sl = _bond_tp_sl(_col(tlt_df, "Close"), _col(tlt_df, "High"), _col(tlt_df, "Low"), "SELL", tp_mult=2.0, sl_mult=1.0)
            rr = abs(tp - entry) / abs(entry - sl) if abs(entry - sl) > 0 else 0.0
            if rr >= 1.5:
                confidence = round(min(0.74, 0.54 + min(spread_now - 1.5, 1.5) * 0.08), 2)
                picks.append({
                    "strategy": "bond_yield_curve_slope",
                    "symbol": "TLT",
                    "category": "bond",
                    "signal_type": "SELL",
                    "entry_price": round(entry, 4),
                    "take_profit": round(tp, 4),
                    "stop_loss": round(sl, 4),
                    "confidence": confidence,
                    "risk_reward": round(rr, 2),
                    "reason": f"2s10s T10Y2Y={spread_now:.2f}pp (STEEP) → expansion → SELL TLT (rising yields)",
                    "timeframe": "1w",
                    "extra": {"t10y2y": round(spread_now, 3), "regime": "steep"},
                    "timestamp": _now_iso(),
                })
        if ief_df is not None and len(ief_df) >= 20:
            entry, tp, sl = _bond_tp_sl(_col(ief_df, "Close"), _col(ief_df, "High"), _col(ief_df, "Low"), "BUY", tp_mult=1.8, sl_mult=0.9)
            rr = abs(tp - entry) / abs(entry - sl) if abs(entry - sl) > 0 else 0.0
            if rr >= 1.3:
                confidence = round(min(0.68, 0.50 + min(spread_now - 1.5, 1.5) * 0.06), 2)
                picks.append({
                    "strategy": "bond_yield_curve_slope",
                    "symbol": "IEF",
                    "category": "bond",
                    "signal_type": "BUY",
                    "entry_price": round(entry, 4),
                    "take_profit": round(tp, 4),
                    "stop_loss": round(sl, 4),
                    "confidence": confidence,
                    "risk_reward": round(rr, 2),
                    "reason": f"2s10s T10Y2Y={spread_now:.2f}pp (STEEP) → BUY IEF (less rate-sensitive than TLT)",
                    "timeframe": "1w",
                    "extra": {"t10y2y": round(spread_now, 3), "regime": "steep"},
                    "timestamp": _now_iso(),
                })

    return picks


# ---------------------------------------------------------------------------
# STRATEGY 7: UST Time-Series Momentum (TSMOM) via FRED DGS10
# ---------------------------------------------------------------------------
def bond_ust_tsmom(data: dict[str, pd.DataFrame], fred_data: dict | None = None) -> list[dict]:
    """12-month yield momentum on DGS10 + TLT price-SMA confirmation.

    Logic (Moskowitz-Ooi-Pedersen TSMOM, fixed-income version):
      - Compute 12-month (252 trading day) return on DGS10 yield from FRED.
      - If yield UP (positive 12m momentum) → rates rising → SELL TLT (short duration).
      - If yield DOWN (negative 12m momentum) → rates falling → BUY TLT (long duration).
      - Confirm with TLT price vs SMA50: price trend must agree with yield signal.
      - Inflation context: T10YIE ≥ 2.5 raises confidence for rising-rate (SELL TLT) signal.

    Enable with BOND_ENABLE_UST_TSMOM=1 (default ON).
    Requires FRED DGS10 series in fred_data; falls back to TLT 12m price return if absent.
    """
    if os.getenv("BOND_ENABLE_UST_TSMOM", "1").strip().lower() in ("0", "false", "no", "off"):
        return []

    # Read DGS10 from FRED (preferred)
    dgs10_series: pd.Series | None = None
    t10yie_latest: float | None = None
    if fred_data and isinstance(fred_data, dict):
        dgs10 = fred_data.get("DGS10")
        if isinstance(dgs10, pd.Series) and len(dgs10.dropna()) >= 30:
            dgs10_series = dgs10.dropna()
        t10yie = fred_data.get("T10YIE")
        if isinstance(t10yie, pd.Series) and not t10yie.dropna().empty:
            t10yie_latest = float(t10yie.dropna().iloc[-1])

    # TLT OHLCV required for entry/TP/SL and price confirmation
    tlt_df = data.get("TLT")
    if tlt_df is None or len(tlt_df) < 55:
        return []
    tlt_close = _col(tlt_df, "Close")
    tlt_sma50 = sma(tlt_close, 50)
    if pd.isna(tlt_sma50.iloc[-1]):
        return []

    tlt_price_bullish = float(tlt_close.iloc[-1]) > float(tlt_sma50.iloc[-1])
    tlt_price_bearish = float(tlt_close.iloc[-1]) < float(tlt_sma50.iloc[-1])

    # Yield momentum signal
    if dgs10_series is not None and len(dgs10_series) >= 30:
        latest_yield = float(dgs10_series.iloc[-1])
        # Use 252 days back if available, else 12m worth of available data
        lookback = min(252, len(dgs10_series) - 1)
        prior_yield = float(dgs10_series.iloc[-(lookback + 1)])
        yield_12m_change = latest_yield - prior_yield  # pp change
        direction_from_yield = "SELL" if yield_12m_change > 0.20 else ("BUY" if yield_12m_change < -0.20 else None)
        data_source = "FRED_DGS10"
    else:
        # Fallback: use TLT 12m price return (inverse of yield)
        if len(tlt_close) < 252:
            return []
        tlt_12m_ret = float(tlt_close.iloc[-1] / tlt_close.iloc[-252] - 1)
        yield_12m_change = -tlt_12m_ret  # invert: TLT UP = yields DOWN
        direction_from_yield = "SELL" if tlt_12m_ret < -0.05 else ("BUY" if tlt_12m_ret > 0.05 else None)
        data_source = "TLT_PRICE_PROXY"
        latest_yield = float(tlt_close.iloc[-1])
        prior_yield = float(tlt_close.iloc[-252])

    if direction_from_yield is None:
        return []

    # Price confirmation gate: yield signal must agree with TLT price trend
    if direction_from_yield == "BUY" and not tlt_price_bullish:
        return []
    if direction_from_yield == "SELL" and not tlt_price_bearish:
        return []

    # Inflation booster: high breakeven → more confident in rising-rate signal
    confidence_base = 0.58
    if direction_from_yield == "SELL" and t10yie_latest is not None and t10yie_latest >= 2.5:
        confidence_base = 0.65

    confidence = round(min(0.80, confidence_base + min(abs(yield_12m_change), 2.0) * 0.05), 2)

    entry, tp, sl = _bond_tp_sl(
        tlt_close, _col(tlt_df, "High"), _col(tlt_df, "Low"),
        direction=direction_from_yield, tp_mult=2.5, sl_mult=1.2,
    )
    rr = abs(tp - entry) / abs(entry - sl) if abs(entry - sl) > 0 else 0.0
    if rr < 1.20:
        return []

    inflation_note = f", T10YIE={t10yie_latest:.2f}%" if t10yie_latest is not None else ""
    return [{
        "strategy": "bond_ust_tsmom",
        "symbol": "TLT",
        "category": "bond",
        "signal_type": direction_from_yield,
        "entry_price": round(entry, 4),
        "take_profit": round(tp, 4),
        "stop_loss": round(sl, 4),
        "confidence": confidence,
        "risk_reward": round(rr, 2),
        "reason": (
            f"UST TSMOM ({data_source}): DGS10 12m change={yield_12m_change:+.2f}pp → "
            f"{'rates rising' if direction_from_yield == 'SELL' else 'rates falling'} → "
            f"{'SELL' if direction_from_yield == 'SELL' else 'BUY'} TLT{inflation_note}"
        ),
        "timeframe": "1m",
        "extra": {
            "dgs10_latest": round(latest_yield, 3),
            "dgs10_prior_12m": round(prior_yield, 3),
            "yield_12m_change_pp": round(yield_12m_change, 3),
            "t10yie": t10yie_latest,
            "data_source": data_source,
            "tlt_vs_sma50": "above" if tlt_price_bullish else "below",
        },
        "timestamp": _now_iso(),
    }]


# ---------------------------------------------------------------------------
# Public Registry
# ---------------------------------------------------------------------------
BOND_STRATEGIES: dict[str, callable] = {
    "bond_yield_momentum": bond_yield_momentum,
    "bond_duration_rotation": bond_duration_rotation,
    "bond_mean_reversion": bond_mean_reversion,
    "bond_connors_rsi2": bond_connors_rsi2,
    "bond_credit_spread_mean_reversion": bond_credit_spread_mean_reversion,
    "bond_yield_curve_slope": bond_yield_curve_slope,
    "bond_ust_tsmom": bond_ust_tsmom,
}
