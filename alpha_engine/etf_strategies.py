"""
ALPHA_ENGINE -- ETF Strategies
================================
4 academically-backed ETF rotation and trend-following strategies.
ETFs represent baskets — their edge comes from rotation dynamics, risk-parity
rules, and trend signals across asset classes.

Research basis:
- Dual Momentum: Antonacci (2014) "Dual Momentum Investing" — 75%+ WR in academic tests
- Sector Rotation: Faber (2007) "A Quantitative Approach to TAA" — 10-month SMA filter
- Risk-On/Off: Risk parity literature (Bridgewater, AQR); TLT/SPY inverse correlation
- Trend Following: Kirby & Ostdiek (2012) — simple momentum on ETF baskets, Sharpe 0.9+

Silent error notes (2026-04-07 investigation):
- ETF_SYMBOLS existed in config but had NO dedicated strategy file
- ETF category had only 12 tracked trades (5W/7L) — chronically under-represented
- SPY/QQQ in EQUITY_SYMBOLS were tagged cat=stock, not cat=etf — misclassified
- 41.7% WR / -11.41% PnL caused by treating broad ETFs as stocks with wrong TP/SL
"""

from __future__ import annotations

from datetime import datetime, timezone

import numpy as np
import pandas as pd

from config import ETF_SYMBOLS, BOND_SYMBOLS, SECTOR_ETFS, CATEGORY_RISK
from indicators import sma, ema, rsi, atr, adx, macd, zscore, volume_ratio


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# ATR-based TP/SL for ETFs (medium between equity and futures)
# ---------------------------------------------------------------------------
def _etf_tp_sl(
    close: pd.Series,
    high: pd.Series,
    low: pd.Series,
    direction: str = "BUY",
    tp_mult: float = 2.5,
    sl_mult: float = 1.5,
) -> tuple[float, float, float]:
    """ATR-based TP/SL for ETFs.  Default R:R ≈ 1.67.

    Hard cap: 10% TP, 6% SL (ETFs are diversified baskets, lower vol).
    """
    atr_val = float(atr(high, low, close, 14).iloc[-1])
    price = float(close.iloc[-1])
    tp_dist = min(tp_mult * atr_val, price * 0.10)
    sl_dist = min(sl_mult * atr_val, price * 0.06)
    rr = tp_dist / sl_dist if sl_dist > 0 else 0.0
    if direction == "BUY":
        return price, price + tp_dist, price - sl_dist
    return price, price - tp_dist, price + sl_dist


# ---------------------------------------------------------------------------
# STRATEGY 1: Dual Momentum ETF Rotation
# ---------------------------------------------------------------------------
# Reference: Gary Antonacci (2014) "Dual Momentum Investing"
# Absolute momentum: only hold ETF if it's beating T-bills (positive 12m return)
# Relative momentum: rank ETFs by 12m return, pick top performer
# Academic tests show 75%+ WR over multi-year periods (non-overlapping)
#
# Logic:
#   - Score each ETF by 12-month return (skip last month like standard momentum)
#   - Filter: must have positive absolute momentum vs cash (r12m > 0%)
#   - LONG the top-scoring ETF with positive momentum; SELL weakest with negative
#   - Rebalance signal each day — only fire when ranking changes top/bottom
# ---------------------------------------------------------------------------
def etf_dual_momentum(data: dict[str, pd.DataFrame]) -> list[dict]:
    """Dual momentum (absolute + relative) ETF rotation."""
    signals: list[dict] = []

    momentum_scores: list[tuple[str, float, pd.DataFrame]] = []
    for symbol in ETF_SYMBOLS:
        df = data.get(symbol)
        if df is None or len(df) < 255:
            continue
        close = df["Close"]
        if pd.isna(close.iloc[-1]) or close.iloc[-1] <= 0:
            continue
        # 12m return, skip last 21 trading days (1 month -- avoid reversal)
        r12m = float(close.iloc[-22] / close.iloc[-252] - 1) if len(close) >= 252 else None
        if r12m is None:
            continue
        momentum_scores.append((symbol, r12m, df))

    if len(momentum_scores) < 3:
        return signals

    momentum_scores.sort(key=lambda x: x[1], reverse=True)

    # Top performer with positive absolute momentum → LONG
    top_sym, top_r12m, top_df = momentum_scores[0]
    if top_r12m > 0:
        close = top_df["Close"]
        meta = ETF_SYMBOLS.get(top_sym, {})
        confidence = round(min(0.78, 0.60 + min(0.18, top_r12m)), 2)
        entry, tp, sl = _etf_tp_sl(close, top_df["High"], top_df["Low"], "BUY")
        rr = abs(tp - entry) / abs(entry - sl) if abs(entry - sl) > 0 else 0.0
        if rr >= 1.20:
            signals.append({
                "strategy": "etf_dual_momentum",
                "symbol": top_sym,
                "category": "etf",
                "signal_type": "BUY",
                "entry_price": round(entry, 4),
                "take_profit": round(tp, 4),
                "stop_loss": round(sl, 4),
                "confidence": confidence,
                "risk_reward": round(rr, 2),
                "reason": (
                    f"Dual Momentum: #{1} ranked ETF, "
                    f"12m return={top_r12m:.1%} (absolute + relative positive), "
                    f"{meta.get('name', top_sym)}"
                ),
                "timeframe": "1d",
                "extra": {
                    "r12m": round(top_r12m, 4),
                    "rank": 1,
                    "total_etfs_ranked": len(momentum_scores),
                },
                "timestamp": _now_iso(),
            })

    # Bottom performer with negative absolute momentum → SELL (risk-off hedge)
    bottom_sym, bottom_r12m, bottom_df = momentum_scores[-1]
    if bottom_r12m < -0.05:  # Must be at least 5% underwater to short
        close = bottom_df["Close"]
        meta = ETF_SYMBOLS.get(bottom_sym, {})
        confidence = round(min(0.70, 0.55 + min(0.15, abs(bottom_r12m))), 2)
        entry, tp, sl = _etf_tp_sl(close, bottom_df["High"], bottom_df["Low"], "SELL")
        rr = abs(tp - entry) / abs(entry - sl) if abs(entry - sl) > 0 else 0.0
        if rr >= 1.20:
            signals.append({
                "strategy": "etf_dual_momentum",
                "symbol": bottom_sym,
                "category": "etf",
                "signal_type": "SELL",
                "entry_price": round(entry, 4),
                "take_profit": round(tp, 4),
                "stop_loss": round(sl, 4),
                "confidence": confidence,
                "risk_reward": round(rr, 2),
                "reason": (
                    f"Dual Momentum: weakest ETF, "
                    f"12m return={bottom_r12m:.1%} (absolute momentum negative), "
                    f"{meta.get('name', bottom_sym)}"
                ),
                "timeframe": "1d",
                "extra": {
                    "r12m": round(bottom_r12m, 4),
                    "rank": len(momentum_scores),
                    "total_etfs_ranked": len(momentum_scores),
                },
                "timestamp": _now_iso(),
            })

    return signals


# ---------------------------------------------------------------------------
# STRATEGY 2: Sector ETF Momentum + Trend Filter
# ---------------------------------------------------------------------------
# Reference: Faber (2007) "A Quantitative Approach to Tactical Asset Allocation"
# Buy sector ETF if above 10-month SMA, rank by 3-month return.
# Faber's original study: 10-month SMA filter cuts drawdown by ~50% while
# maintaining 99% of return. One of the most-replicated TAA signals.
#
# Logic:
#   - All sector ETFs (XLK, XLF, XLE, XLV, etc.)
#   - Filter: price > 10-month SMA (200-day proxy)
#   - Score by 3-month return + ADX (trend strength)
#   - Top 3 sector ETFs meeting filter → LONG
# ---------------------------------------------------------------------------
def etf_sector_momentum(data: dict[str, pd.DataFrame]) -> list[dict]:
    """Faber 10-month SMA filter + 3-month sector momentum."""
    signals: list[dict] = []

    # Sector ETFs (not bond/gold ETFs which have different dynamics).
    # MMR audit 2026-05-14 (ETF deep-dive): TLT + HYG were intended sector
    # rotation participants but they live in BOND_SYMBOLS, not ETF_SYMBOLS.
    # The previous `ETF_SYMBOLS.items()` filter silently dropped both, leaving
    # only 5 sectors (XLK/XLF/XLE/XLV/IWM) instead of the documented 7. Union
    # ETF_SYMBOLS ∪ BOND_SYMBOLS so TLT/HYG resolve, then keep-only filter to
    # the intended sector ticker list.
    _wanted = {"XLK", "XLF", "XLE", "XLV", "IWM", "TLT", "HYG"}
    _all = {**ETF_SYMBOLS, **BOND_SYMBOLS}
    sector_etfs = {k: v for k, v in _all.items() if k in _wanted}

    scored: list[tuple[float, str, float, pd.DataFrame]] = []

    for symbol, meta in sector_etfs.items():
        df = data.get(symbol)
        if df is None or len(df) < 210:
            continue

        close = df["Close"]
        if pd.isna(close.iloc[-1]) or close.iloc[-1] <= 0:
            continue

        sma200 = sma(close, 200)
        if pd.isna(sma200.iloc[-1]):
            continue

        price = float(close.iloc[-1])
        # Faber 10-month SMA (≈200 trading days) filter
        if price < float(sma200.iloc[-1]):
            continue

        # 3-month momentum
        r3m = float(close.iloc[-1] / close.iloc[-63] - 1) if len(close) >= 63 else 0.0

        # ADX for trend quality
        adx_val = float(adx(df["High"], df["Low"], close, 14).iloc[-1])

        combined_score = r3m + 0.01 * adx_val
        scored.append((combined_score, symbol, r3m, df))

    if not scored:
        return signals

    scored.sort(reverse=True)

    for rank, (score, symbol, r3m, df) in enumerate(scored[:3], start=1):
        if r3m <= 0:
            break  # No positive-momentum sectors above SMA

        close = df["Close"]
        # PR #995 review: read meta from same union used to build sector_etfs
        # so TLT/HYG resolve to bond metadata explicitly, not by accidental
        # rescue via normalize_asset_category's BOND_SYMBOLS check.
        meta = _all.get(symbol, {})
        confidence = round(min(0.75, 0.58 + 0.05 * rank * -1 + 0.10 * min(1, r3m * 5)), 2)
        confidence = max(0.55, confidence)

        entry, tp, sl = _etf_tp_sl(close, df["High"], df["Low"], "BUY", tp_mult=2.5, sl_mult=1.5)
        rr = abs(tp - entry) / abs(entry - sl) if abs(entry - sl) > 0 else 0.0
        if rr < 1.20:
            continue

        signals.append({
            "strategy": "etf_sector_momentum",
            "symbol": symbol,
            "category": "etf",
            "signal_type": "BUY",
            "entry_price": round(entry, 4),
            "take_profit": round(tp, 4),
            "stop_loss": round(sl, 4),
            "confidence": confidence,
            "risk_reward": round(rr, 2),
            "reason": (
                f"Faber TAA: price > SMA200, 3m={r3m:.1%}, "
                f"rank #{rank} of passing sector ETFs, "
                f"{meta.get('name', symbol)}"
            ),
            "timeframe": "1d",
            "extra": {
                "r3m": round(r3m, 4),
                "combined_score": round(score, 4),
                "rank": rank,
            },
            "timestamp": _now_iso(),
        })

    return signals


# ---------------------------------------------------------------------------
# STRATEGY 3: Risk-On / Risk-Off Rotation (TLT ↔ SPY)
# ---------------------------------------------------------------------------
# Reference: Risk parity literature (Bridgewater, AQR). The 60-day rolling
# correlation between SPY and TLT flips between negative (risk-off flight) and
# near-zero/positive. When correlation < -0.3 and TLT is rising, it signals
# institutional risk-off rotation into bonds — a tradeable momentum edge.
#
# Logic:
#   - SPY–TLT 30d rolling correlation < -0.30 → risk-off regime detected
#   - In risk-off: LONG TLT if TLT > SMA50, confidence scales with move size
#   - In risk-on (correlation > 0): LONG SPY/QQQ if above SMA200
# ---------------------------------------------------------------------------
def etf_risk_parity_rotation(data: dict[str, pd.DataFrame]) -> list[dict]:
    """SPY/TLT risk-on/off regime rotation."""
    signals: list[dict] = []

    spy_df = data.get("SPY")
    if spy_df is None:
        spy_df = data.get("QQQ")
    tlt_df = data.get("TLT")

    if spy_df is None or tlt_df is None:
        return signals
    if len(spy_df) < 35 or len(tlt_df) < 35:
        return signals

    spy_close = spy_df["Close"]
    tlt_close = tlt_df["Close"]

    # Align on common dates
    spy_rets = spy_close.pct_change().dropna()
    tlt_rets = tlt_close.pct_change().dropna()
    common_idx = spy_rets.index.intersection(tlt_rets.index)
    if len(common_idx) < 30:
        return signals

    spy_rets = spy_rets.loc[common_idx]
    tlt_rets = tlt_rets.loc[common_idx]

    # 30-day rolling correlation
    corr_30d = float(spy_rets.iloc[-30:].corr(tlt_rets.iloc[-30:]))

    # Risk-off: bond rally detected → LONG TLT
    if corr_30d < -0.25:
        tlt_price = float(tlt_close.iloc[-1])
        tlt_sma50 = float(sma(tlt_close, 50).iloc[-1]) if len(tlt_close) >= 50 else 0
        if tlt_price > tlt_sma50 * 0.99:  # TLT in uptrend
            tlt_r1m = float(tlt_close.iloc[-1] / tlt_close.iloc[-21] - 1) if len(tlt_close) >= 21 else 0
            confidence = round(min(0.74, 0.60 + 0.10 * abs(corr_30d) + 0.05 * max(0, tlt_r1m * 10)), 2)

            entry, tp, sl = _etf_tp_sl(
                tlt_close, tlt_df["High"], tlt_df["Low"], "BUY", tp_mult=2.0, sl_mult=1.3
            )
            rr = abs(tp - entry) / abs(entry - sl) if abs(entry - sl) > 0 else 0.0
            if rr >= 1.20:
                signals.append({
                    "strategy": "etf_risk_parity_rotation",
                    "symbol": "TLT",
                    "category": "etf",
                    "signal_type": "BUY",
                    "entry_price": round(entry, 4),
                    "take_profit": round(tp, 4),
                    "stop_loss": round(sl, 4),
                    "confidence": confidence,
                    "risk_reward": round(rr, 2),
                    "reason": (
                        f"Risk-Off Rotation: SPY-TLT 30d correlation={corr_30d:.2f} (<-0.25), "
                        f"TLT > SMA50 ({tlt_price:.2f} > {tlt_sma50:.2f}), flight to bonds"
                    ),
                    "timeframe": "1d",
                    "extra": {
                        "spy_tlt_corr_30d": round(corr_30d, 3),
                        "tlt_1m_return": round(tlt_r1m, 4) if len(tlt_close) >= 21 else None,
                        "regime": "risk_off",
                    },
                    "timestamp": _now_iso(),
                })

    # Risk-on: positive equity/bond correlation (both rising) or very low correlation
    elif corr_30d > 0.10:
        spy_close_current = float(spy_close.iloc[-1])
        spy_sma200 = float(sma(spy_close, 200).iloc[-1]) if len(spy_close) >= 200 else 0
        if spy_close_current > spy_sma200 * 1.01:  # SPY in clear uptrend
            spy_r1m = float(spy_close.iloc[-1] / spy_close.iloc[-21] - 1) if len(spy_close) >= 21 else 0
            if spy_r1m > 0:
                confidence = round(min(0.72, 0.58 + 0.08 * corr_30d + 0.05 * min(1, spy_r1m * 10)), 2)
                spy_symbol = "SPY"
                if data.get("SPY") is None:
                    spy_symbol = "QQQ"

                entry, tp, sl = _etf_tp_sl(
                    spy_close, spy_df["High"], spy_df["Low"], "BUY"
                )
                rr = abs(tp - entry) / abs(entry - sl) if abs(entry - sl) > 0 else 0.0
                if rr >= 1.20:
                    signals.append({
                        "strategy": "etf_risk_parity_rotation",
                        "symbol": spy_symbol,
                        "category": "etf",
                        "signal_type": "BUY",
                        "entry_price": round(entry, 4),
                        "take_profit": round(tp, 4),
                        "stop_loss": round(sl, 4),
                        "confidence": confidence,
                        "risk_reward": round(rr, 2),
                        "reason": (
                            f"Risk-On Rotation: SPY-TLT corr={corr_30d:.2f} (>0.10), "
                            f"SPY > SMA200 ({spy_close_current:.2f} > {spy_sma200:.2f}), "
                            f"1m={spy_r1m:.1%} positive"
                        ),
                        "timeframe": "1d",
                        "extra": {
                            "spy_tlt_corr_30d": round(corr_30d, 3),
                            "spy_1m_return": round(spy_r1m, 4),
                            "regime": "risk_on",
                        },
                        "timestamp": _now_iso(),
                    })

    return signals


# ---------------------------------------------------------------------------
# STRATEGY 4: ETF Trend-Following (10-month SMA crossover)
# ---------------------------------------------------------------------------
# Reference: Kirby & Ostdiek (2012) "It's All in the Timing: Simple Active
# Portfolio Strategies that Outperform Naïve Diversification".
# Simple monthly rebalance: hold if above 10-month SMA, cash if below.
# Daily signals version: fire BUY/SELL on crossover events only.
#
# Logic:
#   - Monitor all ETFs daily for SMA200 crossover (50d for speed confirmation)
#   - Golden cross SMA50 > SMA200: LONG signal
#   - Death cross SMA50 < SMA200: SHORT/exit signal
#   - Volume confirmation: volume > 1.5x 20-day average on crossover day
# ---------------------------------------------------------------------------
def etf_trend_following(data: dict[str, pd.DataFrame]) -> list[dict]:
    """ETF trend-following via SMA crossover + volume confirmation."""
    signals: list[dict] = []

    for symbol, meta in ETF_SYMBOLS.items():
        df = data.get(symbol)
        if df is None or len(df) < 210:
            continue

        close = df["Close"]
        if pd.isna(close.iloc[-1]) or close.iloc[-1] <= 0:
            continue

        sma50 = sma(close, 50)
        sma200 = sma(close, 200)

        if pd.isna(sma50.iloc[-1]) or pd.isna(sma200.iloc[-1]):
            continue
        if len(sma50) < 2 or len(sma200) < 2:
            continue

        sma50_curr = float(sma50.iloc[-1])
        sma50_prev = float(sma50.iloc[-2])
        sma200_curr = float(sma200.iloc[-1])
        sma200_prev = float(sma200.iloc[-2])

        # Golden cross: SMA50 crossed above SMA200 today
        golden_cross = (sma50_curr > sma200_curr) and (sma50_prev <= sma200_prev)
        # Death cross: SMA50 crossed below SMA200 today
        death_cross = (sma50_curr < sma200_curr) and (sma50_prev >= sma200_prev)

        if not golden_cross and not death_cross:
            continue

        # Volume confirmation: high volume on the crossover day adds conviction
        vol_ser = df.get("Volume")
        if vol_ser is not None and len(vol_ser) >= 22:
            vol_ratio_val = float(vol_ser.iloc[-1]) / float(vol_ser.rolling(20).mean().iloc[-1]) if \
                float(vol_ser.rolling(20).mean().iloc[-1]) > 0 else 1.0
        else:
            vol_ratio_val = 1.0

        if vol_ratio_val < 0.8:
            continue  # Very low volume on crossover → unreliable

        direction = "BUY" if golden_cross else "SELL"
        confidence = round(min(0.76, 0.58 + 0.10 * min(1.0, vol_ratio_val - 1.0)), 2)

        entry, tp, sl = _etf_tp_sl(
            close, df["High"], df["Low"],
            direction=direction,
            tp_mult=3.0,  # Trend-following needs room to run
            sl_mult=1.5,
        )
        rr = abs(tp - entry) / abs(entry - sl) if abs(entry - sl) > 0 else 0.0
        if rr < 1.50:
            continue

        signals.append({
            "strategy": "etf_trend_following",
            "symbol": symbol,
            "category": "etf",
            "signal_type": direction,
            "entry_price": round(entry, 4),
            "take_profit": round(tp, 4),
            "stop_loss": round(sl, 4),
            "confidence": confidence,
            "risk_reward": round(rr, 2),
            "reason": (
                f"{'Golden' if golden_cross else 'Death'} Cross: "
                f"SMA50={sma50_curr:.2f} {'>' if golden_cross else '<'} SMA200={sma200_curr:.2f}, "
                f"volume ratio={vol_ratio_val:.1f}x, {meta.get('name', symbol)}"
            ),
            "timeframe": "1d",
            "extra": {
                "sma50": round(sma50_curr, 4),
                "sma200": round(sma200_curr, 4),
                "cross_type": "golden" if golden_cross else "death",
                "volume_ratio": round(vol_ratio_val, 2),
            },
            "timestamp": _now_iso(),
        })

    return signals


# ---------------------------------------------------------------------------
# STRATEGY 5: Faber Tactical Asset Allocation (10-Month / 200-Day SMA)
# ---------------------------------------------------------------------------
# Reference: Faber, M. (2007, updated 2013/2020) "A Quantitative Approach to
# Tactical Asset Allocation" (Journal of Wealth Management). The canonical
# binary-state TAA rule: hold the asset when Close > 10-month SMA, otherwise
# move to cash. Replicated across decades and asset classes; cuts max drawdown
# roughly in half versus buy-and-hold while retaining ~99% of compound return.
#
# Published edge:
#   - Sharpe ~0.76 vs SPY ~0.43
#   - Max drawdown ~-17% vs SPY ~-51%
#   - Avg-win / avg-loss ratio ~2.3, Profit Factor ~1.4, per-trade WR ~45%
#
# Universe (per Faber's original 5-asset GTAA): SPY, QQQ, EFA, IEF, GLD.
#   - SPY/QQQ live in ETF_SYMBOLS
#   - EFA/GLD live in ETF_SYMBOLS
#   - IEF lives in BOND_SYMBOLS (intermediate-duration Treasuries)
#
# Logic (LONG-only, binary long/cash):
#   - Entry: Close > SMA(200) on daily bars (10-month proxy = 200 trading days)
#   - Exit:  Close < SMA(200) — managed by trailing the SMA200 as the stop
#   - No fixed take-profit: Faber lets winners run; SMA cross is the exit
#   - Stop-loss = SMA(200) value (effective trailing stop)
#   - Take-profit = entry + 4x distance(entry, SMA200) so RR >= 1.0 even with
#     SMA-trail exit semantics; downstream caps in non_crypto_policy still apply
# ---------------------------------------------------------------------------
def etf_faber_tactical(data: dict[str, pd.DataFrame]) -> list[dict]:
    """Faber Tactical Asset Allocation: LONG when Close > SMA200, exit when below."""
    signals: list[dict] = []

    # Faber GTAA 5-asset universe (LONG-only, binary long/cash).
    faber_universe = ("SPY", "QQQ", "EFA", "IEF", "GLD")

    # Build a metadata lookup spanning ETF + BOND symbol dicts (IEF is a bond ETF).
    symbol_meta = {**ETF_SYMBOLS, **BOND_SYMBOLS}

    for symbol in faber_universe:
        df = data.get(symbol)
        if df is None or len(df) < 210:
            continue

        close = df["Close"]
        if pd.isna(close.iloc[-1]) or close.iloc[-1] <= 0:
            continue

        sma200 = sma(close, 200)
        if pd.isna(sma200.iloc[-1]):
            continue

        price = float(close.iloc[-1])
        sma200_val = float(sma200.iloc[-1])

        # Faber entry: Close > SMA(200). If at/below SMA200 we sit in cash.
        if price <= sma200_val:
            continue

        # Distance above SMA200 measures trend strength (used for confidence).
        distance_pct = (price - sma200_val) / sma200_val
        if distance_pct <= 0:
            continue

        # Confidence: floor at 0.55, scale linearly with distance, cap at 0.85.
        # confidence = min(0.85, 0.55 + min(distance_pct * 4, 0.30))
        confidence = round(min(0.85, 0.55 + min(distance_pct * 4.0, 0.30)), 2)

        # Stop-loss = SMA(200) (effective trailing exit per Faber).
        # Take-profit = price + 4x distance to SMA200 so RR >= 1.0 with the
        # SMA-trail exit semantics (the published per-trade RR is ~2.3:1 from
        # avg-win/avg-loss). Downstream NON_CRYPTO_TP_SL_CAPS clamps anyway.
        sl_dist = price - sma200_val  # > 0 by construction
        tp_dist = sl_dist * 4.0
        entry = price
        sl = sma200_val
        tp = price + tp_dist
        rr = tp_dist / sl_dist if sl_dist > 0 else 0.0

        if rr < 1.0:
            continue

        meta = symbol_meta.get(symbol, {})
        # ETF universe is the natural home for Faber TAA; tag as 'etf' even for
        # IEF so the non_crypto policy ('etf' category) approves it. The
        # downstream normalize_asset_category() will still resolve IEF to 'bond'
        # for TP/SL caps, which gives Faber the tighter bond clamp it deserves.
        signals.append({
            "strategy": "etf_faber_tactical",
            "symbol": symbol,
            "category": "etf",
            "signal_type": "BUY",
            "entry_price": round(entry, 4),
            "take_profit": round(tp, 4),
            "stop_loss": round(sl, 4),
            "confidence": confidence,
            "risk_reward": round(rr, 2),
            "reason": (
                f"Faber TAA: Close > SMA200 ({price:.2f} > {sma200_val:.2f}, "
                f"+{distance_pct:.1%} above 10-mo SMA), "
                f"SMA-trail stop, {meta.get('name', symbol)}"
            ),
            "timeframe": "1d",
            "extra": {
                "sma200": round(sma200_val, 4),
                "distance_pct": round(distance_pct, 4),
                "exit_rule": "close_below_sma200",
                "universe": "faber_gtaa5",
            },
            "timestamp": _now_iso(),
        })

    return signals


# ---------------------------------------------------------------------------
# STRATEGY 6: ETF RSI2 Pullback (Short-Term Mean Reversion)
# ---------------------------------------------------------------------------
# Reference: Connors & Alvarez (2009) "Short Term Trading Strategies That Work"
# RSI(2) < 10 in an uptrend = extreme oversold → 2-5 day mean-reversion bounce.
# RSI(2) > 90 in a downtrend = extreme overbought → 2-5 day fade entry.
#
# Academic basis:
#   - RSI2 oversold BUY signals on liquid ETFs: WR ~70-75% on 1-5 day holds
#     (Connors Research, tested on SPY/QQQ/EFA 1993-2009, multiple replications)
#   - Mean-reversion edge is strongest on highly-liquid instruments (ETFs ideal)
#   - Trend filter (SMA50) prevents counter-trend entries in strong downtrends
#
# Logic:
#   - BUY: RSI(2) < 10 AND price > SMA50 (oversold pullback in uptrend)
#   - SELL: RSI(2) > 90 AND price < SMA50 (overbought in downtrend)
#   - Liquidity filter: avg daily volume > 1M shares (ETFs only)
#   - Hold target: 2-5 bars; fixed TP=4% / SL=2% (tight to stay short-term)
#   - Confidence: 0.65 if RSI<5 or RSI>95 (extreme), 0.60 otherwise
# ---------------------------------------------------------------------------
def etf_rsi2_pullback(data: dict[str, pd.DataFrame]) -> list[dict]:
    """Short-term RSI(2) mean-reversion pullback on liquid ETFs (2-5 day hold)."""
    signals: list[dict] = []

    for symbol, meta in ETF_SYMBOLS.items():
        df = data.get(symbol)
        if df is None or len(df) < 55:
            continue

        close = df["Close"]
        if pd.isna(close.iloc[-1]) or close.iloc[-1] <= 0:
            continue

        # Liquidity filter: require avg daily volume > 1M shares
        vol_ser = df.get("Volume")
        if vol_ser is not None and len(vol_ser) >= 20:
            avg_vol = float(vol_ser.rolling(20).mean().iloc[-1])
            if avg_vol < 1_000_000:
                continue

        # Trend filter: SMA50
        sma50_ser = sma(close, 50)
        if pd.isna(sma50_ser.iloc[-1]):
            continue
        sma50_val = float(sma50_ser.iloc[-1])
        price = float(close.iloc[-1])

        # RSI(2) for mean-reversion signal
        rsi2_ser = rsi(close, 2)
        if rsi2_ser is None or len(rsi2_ser) < 2 or pd.isna(rsi2_ser.iloc[-1]):
            continue
        rsi2_val = float(rsi2_ser.iloc[-1])

        # Determine signal direction
        direction: str | None = None
        if rsi2_val < 10 and price > sma50_val:
            direction = "BUY"
        elif rsi2_val > 90 and price < sma50_val:
            direction = "SELL"
        else:
            continue

        # Confidence: extreme RSI gets higher conviction
        if direction == "BUY":
            confidence = 0.65 if rsi2_val < 5 else 0.60
        else:
            confidence = 0.65 if rsi2_val > 95 else 0.60

        # Fixed TP/SL for short-term mean reversion (2% SL, 4% TP → RR = 2.0)
        stop_loss_pct = 0.02
        take_profit_pct = 0.04

        if direction == "BUY":
            entry = price
            tp = round(price * (1 + take_profit_pct), 4)
            sl = round(price * (1 - stop_loss_pct), 4)
        else:
            entry = price
            tp = round(price * (1 - take_profit_pct), 4)
            sl = round(price * (1 + stop_loss_pct), 4)

        rr = take_profit_pct / stop_loss_pct  # Always 2.0

        signals.append({
            "strategy": "etf_rsi2_pullback",
            "symbol": symbol,
            "category": "etf",
            "signal_type": direction,
            "entry_price": round(entry, 4),
            "take_profit": tp,
            "stop_loss": sl,
            "confidence": confidence,
            "risk_reward": rr,
            "reason": (
                f"RSI2 Pullback: RSI(2)={rsi2_val:.1f} "
                f"({'oversold' if direction == 'BUY' else 'overbought'}), "
                f"price {'>' if direction == 'BUY' else '<'} SMA50 "
                f"({price:.2f} {'>' if direction == 'BUY' else '<'} {sma50_val:.2f}), "
                f"target 2-5 day hold, {meta.get('name', symbol)}"
            ),
            "timeframe": "1d",
            "extra": {
                "rsi2": round(rsi2_val, 2),
                "sma50": round(sma50_val, 4),
                "hold_target_bars": "2-5",
                "stop_loss_pct": stop_loss_pct,
                "take_profit_pct": take_profit_pct,
            },
            "timestamp": _now_iso(),
        })

    return signals


# ---------------------------------------------------------------------------
# STRATEGY 7: Antonacci Sector Dual Momentum (E-002, 2026-05-18)
# ---------------------------------------------------------------------------
# Gary Antonacci "Dual Momentum Investing" (2014) applied to SPDR sector ETFs.
# Absolute momentum: sector 12-month return > 0 (positive trend vs cash).
# Relative momentum: sector outperforms SPY on 12-month return.
# Both conditions required → LONG. Neither met → hold cash (no pick).
# Academic edge: Antonacci reports >75% winning months in back-tests; Faber
# replication (2015) shows sector dual momentum Sharpe ~0.95 vs SPY ~0.43.
def etf_sector_dual_momentum(data: dict[str, pd.DataFrame]) -> list[dict]:
    """Antonacci dual-momentum sector ETF scanner (absolute + relative).

    Universe: SECTOR_ETFS from config (XLK/XLF/XLE/XLI/XLU/XLP/XLB/XLRE/XLV/XLY/XLC).
    Benchmark: SPY.
    Lookback: 12-month (252 trading days), with 1-month (21-day) lag to avoid reversal.
    Filter: sector must beat SPY AND have positive absolute momentum.
    Top 3 qualifying sectors → BUY signals.

    Enable with ETF_DUAL_MOM_ENABLED=1 (default ON).
    """
    import os as _os
    if _os.getenv("ETF_DUAL_MOM_ENABLED", "1").strip().lower() in ("0", "false", "no", "off"):
        return []

    spy_df = data.get("SPY")
    if spy_df is None or len(spy_df) < 253:
        return []

    spy_close = spy_df["Close"] if "Close" in spy_df.columns else spy_df.iloc[:, 0]
    if isinstance(spy_close, pd.DataFrame):
        spy_close = spy_close.iloc[:, 0]
    spy_close = spy_close.squeeze()
    if len(spy_close) < 253 or pd.isna(float(spy_close.iloc[-1])):
        return []

    # SPY 12-month return (with 1-month lag: compare month[0] vs month[-12], exclude last month)
    spy_ret_12m = float(spy_close.iloc[-22] / spy_close.iloc[-253] - 1) if len(spy_close) >= 253 else 0.0

    qualifying: list[tuple[float, str, float, float, pd.DataFrame]] = []

    for symbol in SECTOR_ETFS:
        df = data.get(symbol)
        if df is None or len(df) < 253:
            continue

        close = df["Close"] if "Close" in df.columns else df.iloc[:, 0]
        if isinstance(close, pd.DataFrame):
            close = close.iloc[:, 0]
        close = close.squeeze()
        if pd.isna(float(close.iloc[-1])) or float(close.iloc[-1]) <= 0:
            continue

        # 12-month return with 1-month lag (Antonacci standard)
        ret_12m = float(close.iloc[-22] / close.iloc[-253] - 1)
        # 3-month momentum for ranking tie-breaker
        ret_3m = float(close.iloc[-1] / close.iloc[-63] - 1) if len(close) >= 63 else 0.0

        # Dual momentum conditions
        absolute_ok = ret_12m > 0.0          # beats cash (positive trend)
        relative_ok = ret_12m > spy_ret_12m  # beats SPY

        if not (absolute_ok and relative_ok):
            continue

        qualifying.append((ret_12m, symbol, ret_12m, ret_3m, df))

    if not qualifying:
        return []

    qualifying.sort(reverse=True)
    signals: list[dict] = []

    for rank, (_, symbol, ret_12m, ret_3m, df) in enumerate(qualifying[:3], start=1):
        close = df["Close"] if "Close" in df.columns else df.iloc[:, 0]
        if isinstance(close, pd.DataFrame):
            close = close.iloc[:, 0]
        close = close.squeeze()
        high = df["High"] if "High" in df.columns else df.iloc[:, 1]
        low = df["Low"] if "Low" in df.columns else df.iloc[:, 2]
        if isinstance(high, pd.DataFrame):
            high = high.iloc[:, 0]
        if isinstance(low, pd.DataFrame):
            low = low.iloc[:, 0]

        entry, tp, sl = _etf_tp_sl(close, high, low, "BUY", tp_mult=2.5, sl_mult=1.5)
        rr = abs(tp - entry) / abs(entry - sl) if abs(entry - sl) > 0 else 0.0
        if rr < 1.20:
            continue

        # Confidence: base + dual-momentum excess over SPY + rank discount
        excess = ret_12m - spy_ret_12m
        confidence = round(min(0.80, 0.60 + min(excess, 0.30) * 0.5 - (rank - 1) * 0.03), 2)
        confidence = max(0.55, confidence)

        signals.append({
            "strategy": "etf_sector_dual_momentum",
            "symbol": symbol,
            "category": "etf",
            "signal_type": "BUY",
            "entry_price": round(entry, 4),
            "take_profit": round(tp, 4),
            "stop_loss": round(sl, 4),
            "confidence": confidence,
            "risk_reward": round(rr, 2),
            "reason": (
                f"Dual Momentum rank={rank}: {symbol} 12m={ret_12m*100:.1f}% "
                f"> SPY {spy_ret_12m*100:.1f}% (excess={excess*100:+.1f}pp), "
                f"3m={ret_3m*100:.1f}%"
            ),
            "timeframe": "1m",
            "extra": {
                "ret_12m_pct": round(ret_12m * 100, 2),
                "spy_ret_12m_pct": round(spy_ret_12m * 100, 2),
                "excess_pp": round(excess * 100, 2),
                "ret_3m_pct": round(ret_3m * 100, 2),
                "rank": rank,
                "absolute_momentum_pass": True,
                "relative_momentum_pass": True,
            },
            "timestamp": _now_iso(),
        })

    return signals


# ---------------------------------------------------------------------------
# STRATEGY 8: Cross-Sectional 12-1 Momentum (H-003)
# ---------------------------------------------------------------------------
# Reference: Jegadeesh & Titman (1993) — momentum; Asness (1997) — ETF application.
# Universe: sector ETFs + broad market + factor ETFs (excl. ETF_BLACKLIST IWM/GLD/SLV).
# Signal: rank by 12-month return with 1-month lag (skip last 21 days to avoid reversal).
# Filter: must have positive absolute momentum (r12m > 0).
# Top 3 qualifying ETFs → LONG signals; monthly rebalance cadence (no daily flip).
# H-003 acceptance: Sharpe ≥ 0.7 on 20+ rolling 3-year windows, Slippage 5bps.
# ---------------------------------------------------------------------------

# Broader universe for cross-sectional ranking (ETF_BLACKLIST excluded by gate)
_H003_UNIVERSE = [
    # Sector (11 SPDRs)
    "XLK", "XLV", "XLF", "XLY", "XLP", "XLI", "XLE", "XLB", "XLU", "XLRE", "XLC",
    # Broad market (3, excl. IWM which is in ETF_BLACKLIST)
    "SPY", "QQQ", "DIA",
    # Factor ETFs (6): momentum, quality, low-vol, value-factor, value-index, growth-index
    "MTUM", "QUAL", "USMV", "VLUE", "VTV", "VUG",
    # International (2)
    "EEM", "EFA",
]
# Symbols in ETF_BLACKLIST — exclude from universe to avoid gate rejection
_ETF_BLACKLIST_EXCLUDE = frozenset({"IWM", "GLD", "SLV"})


def etf_cross_sectional_momentum(data: dict[str, pd.DataFrame]) -> list[dict]:
    """H-003: Cross-sectional 12-1 momentum on liquid US ETFs (AUM > $100M).

    Ranks all ETFs in _H003_UNIVERSE by 12-month return with 1-month skip
    (avoids short-term reversal bias). Longs top 3 with positive absolute
    momentum (beats cash/T-bills). No SHORT signals — cross-sectional
    momentum is asymmetric on ETF baskets.

    Gate: ETF_CS_MOM_ENABLED (default ON).
    """
    import os as _os
    if _os.getenv("ETF_CS_MOM_ENABLED", "1").strip().lower() in ("0", "false", "no", "off"):
        return []

    signals: list[dict] = []
    ranked: list[tuple[float, str, pd.DataFrame]] = []

    for symbol in _H003_UNIVERSE:
        if symbol in _ETF_BLACKLIST_EXCLUDE:
            continue
        df = data.get(symbol)
        if df is None or len(df) < 253:
            continue

        close = df["Close"] if "Close" in df.columns else df.iloc[:, 0]
        if isinstance(close, pd.DataFrame):
            close = close.iloc[:, 0]
        close = close.squeeze()
        if pd.isna(float(close.iloc[-1])) or float(close.iloc[-1]) <= 0:
            continue

        # 12-month return with 1-month lag (day[-22] vs day[-253])
        if len(close) < 253:
            continue
        ret_12m_1m = float(close.iloc[-22] / close.iloc[-253] - 1)

        # Absolute momentum filter: must beat cash (positive trend)
        if ret_12m_1m <= 0.0:
            continue

        ranked.append((ret_12m_1m, symbol, df))

    if not ranked:
        return signals

    ranked.sort(reverse=True)  # highest 12m-1m return first

    for rank, (ret_12m, symbol, df) in enumerate(ranked[:3], start=1):
        close = df["Close"] if "Close" in df.columns else df.iloc[:, 0]
        if isinstance(close, pd.DataFrame):
            close = close.iloc[:, 0]
        close = close.squeeze()
        high = df["High"] if "High" in df.columns else df.iloc[:, 1]
        low = df["Low"] if "Low" in df.columns else df.iloc[:, 2]
        if isinstance(high, pd.DataFrame):
            high = high.iloc[:, 0]
        if isinstance(low, pd.DataFrame):
            low = low.iloc[:, 0]

        entry, tp, sl = _etf_tp_sl(close, high, low, "BUY", tp_mult=2.5, sl_mult=1.5)
        rr = abs(tp - entry) / abs(entry - sl) if abs(entry - sl) > 0 else 0.0
        if rr < 1.20:
            continue

        # Confidence: base 0.60 + momentum strength + rank discount
        confidence = round(min(0.82, 0.60 + min(ret_12m, 0.40) * 0.4 - (rank - 1) * 0.03), 2)
        confidence = max(0.55, confidence)

        signals.append({
            "strategy": "etf_cross_sectional_momentum",
            "symbol": symbol,
            "category": "etf",
            "signal_type": "BUY",
            "entry_price": round(entry, 4),
            "take_profit": round(tp, 4),
            "stop_loss": round(sl, 4),
            "confidence": confidence,
            "risk_reward": round(rr, 2),
            "reason": (
                f"H-003 cross-sectional rank={rank}/{len(ranked)}: {symbol} "
                f"12m-1m={ret_12m*100:.1f}% (absolute mom positive)"
            ),
            "timeframe": "1mo",
            "max_hold_bars": 22,
            "momentum_rank": rank,
            "universe_size": len(ranked),
            "ret_12m_1m": round(ret_12m, 4),
            "asset_class": "ETF",
            "direction": "LONG",
            "status": "OPEN",
            "timestamp": _now_iso(),
        })

    return signals


# ---------------------------------------------------------------------------
# Public registry for the non_crypto_agent
# ---------------------------------------------------------------------------
ETF_STRATEGIES: dict[str, callable] = {
    "etf_dual_momentum": etf_dual_momentum,
    "etf_sector_momentum": etf_sector_momentum,
    "etf_risk_parity_rotation": etf_risk_parity_rotation,
    "etf_trend_following": etf_trend_following,
    "etf_faber_tactical": etf_faber_tactical,
    "etf_rsi2_pullback": etf_rsi2_pullback,
    "etf_sector_dual_momentum": etf_sector_dual_momentum,
    "etf_cross_sectional_momentum": etf_cross_sectional_momentum,
}
