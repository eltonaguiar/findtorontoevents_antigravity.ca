"""
DNA Mutations -- Crossover strategies from tournament winners
============================================================
These are hybrid strategies that combine the entry logic of one proven
strategy with the exit/filter logic of another. Think of it like
breeding: take the best trait from each parent.

Tournament data shows:
- DOT SHORT is the most consistent winner across all rounds
- ConnorsRSI has 75.7% WR on SPY (proven backtest)
- Williams %R + SMA filter has 81% WR (KIMI uses it)
- Mixed direction portfolios (long + short) beat all-one-direction
- TVL inflows from DefiLlama predicted the R3 bounce that killed all shorts

Mutations:
1. connors_williams_hybrid -- ConnorsRSI entry + Williams %R exit timing
2. tvl_weighted_momentum -- Use TVL inflows to decide long vs short
3. anti_consensus_contrarian -- If all signals agree, fade the consensus
"""

from __future__ import annotations

import time
from datetime import datetime, timezone

import numpy as np

try:
    import pandas as pd
except ImportError:
    pd = None

# -- Helpers (same as crypto_strategies.py) --------------------------

def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def _smart_round(price):
    if price >= 1000:
        return round(price, 2)
    elif price >= 1:
        return round(price, 4)
    elif price >= 0.01:
        return round(price, 6)
    return round(price, 8)


def _rsi(close, period=14):
    """Calculate RSI from a pandas Series."""
    delta = close.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_gain = gain.rolling(window=period, min_periods=period).mean()
    avg_loss = loss.rolling(window=period, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, 1e-10)
    return 100.0 - (100.0 / (1.0 + rs))


def _williams_r(high, low, close, period=14):
    """Williams %R: (highest_high - close) / (highest_high - lowest_low) * -100"""
    highest = high.rolling(window=period).max()
    lowest = low.rolling(window=period).min()
    wr = (highest - close) / (highest - lowest).replace(0, 1e-10) * -100
    return wr


def _sma(series, period):
    return series.rolling(window=period).mean()


def _atr(high, low, close, period=14):
    tr = pd.concat([
        high - low,
        (high - close.shift(1)).abs(),
        (low - close.shift(1)).abs()
    ], axis=1).max(axis=1)
    return tr.rolling(window=period).mean()


# =====================================================================
# MUTATION 1: ConnorsRSI Entry + Williams %R Exit
# =====================================================================
# Parent A: ConnorsRSI -- 75.7% WR on SPY. Enters on RSI(2) < 5 oversold.
# Parent B: Williams %R -- 81% WR. Exits when %R crosses back above -20
#           (overbought) or below -80 (oversold).
#
# The mutation: Use ConnorsRSI's extreme-oversold entry (proven to catch
# dips) but ADD Williams %R as a confirmation filter. Only enter if BOTH
# agree the asset is at an extreme.
#
# For LONG: RSI(2) < 10 AND Williams %R < -80 (both say oversold)
# For SHORT: RSI(2) > 90 AND Williams %R > -20 (both say overbought)
# =====================================================================

def connors_williams_hybrid(data: dict) -> list[dict]:
    """Crossover: ConnorsRSI entry + Williams %R confirmation (DNA Mutation 1)."""
    if pd is None:
        return []

    signals = []
    targets = [
        ("BTC-USD", "crypto"), ("ETH-USD", "crypto"), ("SOL-USD", "crypto"),
        ("XRP-USD", "crypto"), ("AVAX-USD", "crypto"), ("LINK-USD", "crypto"),
        ("DOGE-USD", "crypto"), ("DOT-USD", "crypto"), ("ADA-USD", "crypto"),
        ("NEAR-USD", "crypto"), ("INJ-USD", "crypto"), ("TRX-USD", "crypto"),
    ]

    for symbol, cat in targets:
        df = data.get(symbol)
        if df is None or len(df) < 205:
            continue

        close = df["Close"]
        high = df["High"]
        low = df["Low"]
        current = float(close.iloc[-1])

        rsi2 = float(_rsi(close, 2).iloc[-1])
        wr14 = float(_williams_r(high, low, close, 14).iloc[-1])
        sma200 = float(_sma(close, 200).iloc[-1])
        atr14 = float(_atr(high, low, close, 14).iloc[-1])

        if atr14 <= 0 or np.isnan(atr14):
            continue

        signal_type = None
        reason = ""

        # LONG: Both RSI(2) and Williams %R say oversold + above SMA200
        if rsi2 < 10 and wr14 < -80 and current > sma200:
            signal_type = "BUY"
            tp = current + atr14 * 3.0
            sl = current - atr14 * 1.5
            # Confidence scales with how extreme both indicators are
            conf = min(0.85, 0.65 + (10.0 - rsi2) * 0.01 + (-80.0 - wr14) * 0.005)
            reason = (f"DNA Mutation: RSI(2)={rsi2:.1f} + Williams %R={wr14:.1f} "
                      f"BOTH oversold. Above SMA200={sma200:.2f}. Double confirmation buy.")

        # SHORT: Both RSI(2) and Williams %R say overbought + below SMA200
        elif rsi2 > 90 and wr14 > -20 and current < sma200:
            signal_type = "SELL"
            tp = current - atr14 * 3.0
            sl = current + atr14 * 1.5
            conf = min(0.85, 0.65 + (rsi2 - 90.0) * 0.01 + (wr14 + 20.0) * 0.005)
            reason = (f"DNA Mutation: RSI(2)={rsi2:.1f} + Williams %R={wr14:.1f} "
                      f"BOTH overbought. Below SMA200={sma200:.2f}. Double confirmation short.")

        if signal_type is None:
            continue

        rr = abs(tp - current) / abs(current - sl) if abs(current - sl) > 0 else 0
        if rr < 1.2:
            continue

        signals.append({
            "strategy": "connors_williams_hybrid",
            "symbol": symbol,
            "category": cat,
            "signal_type": signal_type,
            "entry_price": _smart_round(current),
            "take_profit": _smart_round(tp),
            "stop_loss": _smart_round(sl),
            "confidence": round(conf, 2),
            "risk_reward": round(rr, 2),
            "reason": reason,
            "timeframe": "1d",
            "rsi_at_entry": round(rsi2, 1),
            "extra": {"williams_r": round(wr14, 1), "sma200": round(sma200, 4)},
            "timestamp": _now_iso(),
        })

    return signals


# =====================================================================
# MUTATION 2: TVL-Weighted Momentum
# =====================================================================
# Uses DefiLlama TVL inflows to decide direction.
#
# The problem in Round 3: all AIs used Fear & Greed (backward-looking
# sentiment) to decide direction. But TVL data (forward-looking capital
# flow) told the opposite story -- money was entering crypto.
#
# This mutation: check TVL momentum FIRST, then use RSI for timing.
# If TVL is rising >2% weekly → bias LONG (money entering)
# If TVL is falling >2% weekly → bias SHORT (money leaving)
# Then use RSI(14) for entry timing within that bias.
# =====================================================================

def tvl_weighted_momentum(data: dict) -> list[dict]:
    """TVL inflow/outflow decides direction, RSI times the entry (DNA Mutation 2)."""
    if pd is None:
        return []

    # Try to get DefiLlama data
    try:
        from defillama_signals import get_chain_tvl_momentum
    except ImportError:
        return []

    signals = []

    # Map symbols to their chain for TVL lookup
    chain_map = {
        "ETH-USD": "Ethereum",
        "SOL-USD": "Solana",
        "AVAX-USD": "Avalanche",
        "NEAR-USD": "Near",
        "INJ-USD": "Injective",
        "DOT-USD": "Polkadot",
        "TRX-USD": "Tron",
    }

    for symbol, chain in chain_map.items():
        df = data.get(symbol)
        if df is None or len(df) < 50:
            continue

        close = df["Close"]
        high = df["High"]
        low = df["Low"]
        current = float(close.iloc[-1])

        # Get TVL momentum for this chain
        try:
            tvl = get_chain_tvl_momentum(chain)
            tvl_pct = tvl.get("momentum_pct", 0)
            tvl_signal = tvl.get("signal", "FLAT")
        except Exception:
            continue

        rsi14 = float(_rsi(close, 14).iloc[-1])
        atr14 = float(_atr(high, low, close, 14).iloc[-1])

        if atr14 <= 0 or np.isnan(atr14):
            continue

        signal_type = None
        reason = ""

        # TVL INFLOW (>2%) + RSI pullback (30-45) = buy the dip
        if tvl_pct > 2.0 and 30 <= rsi14 <= 45:
            signal_type = "BUY"
            tp = current + atr14 * 2.5
            sl = current - atr14 * 1.5
            conf = min(0.80, 0.55 + tvl_pct * 0.02 + (45 - rsi14) * 0.005)
            reason = (f"DNA Mutation: {chain} TVL +{tvl_pct:.1f}% (money entering) "
                      f"+ RSI={rsi14:.0f} pullback = buy the dip. "
                      f"Fear & Greed says fear but capital flows say buy.")

        # TVL OUTFLOW (<-2%) + RSI bounce (55-70) = short the bounce
        elif tvl_pct < -2.0 and 55 <= rsi14 <= 70:
            signal_type = "SELL"
            tp = current - atr14 * 2.5
            sl = current + atr14 * 1.5
            conf = min(0.80, 0.55 + abs(tvl_pct) * 0.02 + (rsi14 - 55) * 0.005)
            reason = (f"DNA Mutation: {chain} TVL {tvl_pct:.1f}% (money leaving) "
                      f"+ RSI={rsi14:.0f} bounce = short the rally. "
                      f"Capital is exiting despite price recovery.")

        if signal_type is None:
            continue

        rr = abs(tp - current) / abs(current - sl) if abs(current - sl) > 0 else 0
        if rr < 1.2:
            continue

        signals.append({
            "strategy": "tvl_weighted_momentum",
            "symbol": symbol,
            "category": "crypto",
            "signal_type": signal_type,
            "entry_price": _smart_round(current),
            "take_profit": _smart_round(tp),
            "stop_loss": _smart_round(sl),
            "confidence": round(conf, 2),
            "risk_reward": round(rr, 2),
            "reason": reason,
            "timeframe": "1d",
            "rsi_at_entry": round(rsi14, 1),
            "extra": {"tvl_pct": round(tvl_pct, 2), "chain": chain},
            "timestamp": _now_iso(),
        })

    return signals


# =====================================================================
# MUTATION 3: Anti-Consensus Contrarian
# =====================================================================
# Tournament data proved: when all AIs agree (18/18 SHORT in R3),
# the opposite trade wins. This strategy counts how many active scanner
# signals agree on direction for a symbol and FADES the consensus.
#
# If >75% of signals for a symbol are SHORT → go LONG (crowd is wrong)
# If >75% of signals for a symbol are LONG → go SHORT (crowd is wrong)
#
# Only fires when consensus is extreme (>75%) because mild consensus
# (55-65%) usually means the crowd is right.
# =====================================================================

def anti_consensus_contrarian(data: dict, all_signals: list[dict] = None) -> list[dict]:
    """Fade extreme consensus -- if everyone agrees, take the other side (DNA Mutation 3)."""
    if pd is None or all_signals is None:
        return []

    # Count direction consensus per symbol
    symbol_dirs = {}
    for s in all_signals:
        sym = s.get("symbol", "")
        sig = s.get("signal_type", "")
        if sym and sig in ("BUY", "SELL"):
            if sym not in symbol_dirs:
                symbol_dirs[sym] = {"BUY": 0, "SELL": 0}
            symbol_dirs[sym][sig] += 1

    signals = []

    for symbol, counts in symbol_dirs.items():
        total = counts["BUY"] + counts["SELL"]
        if total < 4:
            continue  # Need enough signals to detect consensus

        buy_pct = counts["BUY"] / total
        sell_pct = counts["SELL"] / total

        df = data.get(symbol)
        if df is None or len(df) < 50:
            continue

        close = df["Close"]
        high = df["High"]
        low = df["Low"]
        current = float(close.iloc[-1])
        atr14 = float(_atr(high, low, close, 14).iloc[-1])

        if atr14 <= 0 or np.isnan(atr14):
            continue

        signal_type = None
        reason = ""

        # Extreme SELL consensus (>75%) → contrarian BUY
        if sell_pct > 0.75:
            signal_type = "BUY"
            tp = current + atr14 * 2.0
            sl = current - atr14 * 1.5
            conf = min(0.75, 0.50 + (sell_pct - 0.75) * 1.0)
            reason = (f"DNA Mutation: {counts['SELL']}/{total} signals say SELL "
                      f"({sell_pct:.0%} consensus). When the crowd all shorts, "
                      f"go long. R3 proved this: 18/18 shorts lost, user's longs won.")

        # Extreme BUY consensus (>75%) → contrarian SELL
        elif buy_pct > 0.75:
            signal_type = "SELL"
            tp = current - atr14 * 2.0
            sl = current + atr14 * 1.5
            conf = min(0.75, 0.50 + (buy_pct - 0.75) * 1.0)
            reason = (f"DNA Mutation: {counts['BUY']}/{total} signals say BUY "
                      f"({buy_pct:.0%} consensus). When the crowd all goes long, "
                      f"short it. Extreme agreement = crowded trade.")

        if signal_type is None:
            continue

        rr = abs(tp - current) / abs(current - sl) if abs(current - sl) > 0 else 0
        if rr < 1.0:
            continue

        signals.append({
            "strategy": "anti_consensus_contrarian",
            "symbol": symbol,
            "category": "crypto",
            "signal_type": signal_type,
            "entry_price": _smart_round(current),
            "take_profit": _smart_round(tp),
            "stop_loss": _smart_round(sl),
            "confidence": round(conf, 2),
            "risk_reward": round(rr, 2),
            "reason": reason,
            "timeframe": "1d",
            "extra": {
                "buy_signals": counts["BUY"],
                "sell_signals": counts["SELL"],
                "consensus_pct": round(max(buy_pct, sell_pct) * 100, 1),
            },
            "timestamp": _now_iso(),
        })

    return signals


# =====================================================================
# MUTATION 4: AlphaTrend + WaveTrend Confluence
# =====================================================================
# Parent A: AlphaTrend (KivancOzbilgic) -- 62% WR, PF 2.1. Uses CCI + ATR
#           to build an adaptive trend line that flips between support/resistance.
# Parent B: WaveTrend Oscillator (LazyBear) -- 58% WR on BTC 1H, PF 1.9.
#           Smoothed stochastic oscillator with overbought/oversold crossovers.
#
# Research finding: Trend-following dramatically outperforms mean reversion
# on crypto (QuantifiedStrategies 2024-2025 backtests). This mutation
# combines the two best-performing non-MACD indicators from TradingView
# backtests. Only enters when BOTH confirm direction.
#
# LONG: AlphaTrend line below price (uptrend) AND WaveTrend crossing up
#       from oversold zone (< -60)
# SHORT: AlphaTrend line above price (downtrend) AND WaveTrend crossing
#        down from overbought zone (> 60)
# =====================================================================

def _cci(high, low, close, period=20):
    """Commodity Channel Index."""
    tp = (high + low + close) / 3.0
    sma_tp = tp.rolling(window=period).mean()
    mad = tp.rolling(window=period).apply(lambda x: np.abs(x - x.mean()).mean(), raw=True)
    return (tp - sma_tp) / (0.015 * mad.replace(0, 1e-10))


def _alphatrend(high, low, close, atr_period=14, cci_period=20, multiplier=1.0):
    """AlphaTrend indicator -- adaptive trend line using CCI + ATR."""
    atr_val = _atr(high, low, close, atr_period)
    cci = _cci(high, low, close, cci_period)

    up_line = low - atr_val * multiplier
    dn_line = high + atr_val * multiplier

    alpha = pd.Series(index=close.index, dtype=float)
    alpha.iloc[0] = close.iloc[0]

    for i in range(1, len(close)):
        if cci.iloc[i] >= 0:
            alpha.iloc[i] = max(up_line.iloc[i], alpha.iloc[i - 1]) if not np.isnan(alpha.iloc[i - 1]) else up_line.iloc[i]
        else:
            alpha.iloc[i] = min(dn_line.iloc[i], alpha.iloc[i - 1]) if not np.isnan(alpha.iloc[i - 1]) else dn_line.iloc[i]

    return alpha


def _wavetrend(close, channel_len=9, avg_len=12, oversold=-60, overbought=60):
    """WaveTrend Oscillator -- smoothed stochastic wave cycles."""
    esa = close.ewm(span=channel_len, adjust=False).mean()
    d = (close - esa).abs().ewm(span=channel_len, adjust=False).mean()
    ci = (close - esa) / (0.015 * d.replace(0, 1e-10))
    wt1 = ci.ewm(span=avg_len, adjust=False).mean()
    wt2 = wt1.rolling(window=4).mean()
    return wt1, wt2


def alphatrend_wavetrend_confluence(data: dict) -> list[dict]:
    """Crossover: AlphaTrend trend direction + WaveTrend timing (DNA Mutation 4)."""
    if pd is None:
        return []

    signals = []
    targets = [
        ("BTC-USD", "crypto"), ("ETH-USD", "crypto"), ("SOL-USD", "crypto"),
        ("XRP-USD", "crypto"), ("AVAX-USD", "crypto"), ("LINK-USD", "crypto"),
        ("DOGE-USD", "crypto"), ("DOT-USD", "crypto"), ("ADA-USD", "crypto"),
        ("NEAR-USD", "crypto"), ("INJ-USD", "crypto"), ("TRX-USD", "crypto"),
    ]

    for symbol, cat in targets:
        df = data.get(symbol)
        if df is None or len(df) < 50:
            continue

        close = df["Close"]
        high = df["High"]
        low = df["Low"]
        current = float(close.iloc[-1])

        try:
            alpha_line = _alphatrend(high, low, close)
            wt1, wt2 = _wavetrend(close)
        except Exception:
            continue

        alpha_val = float(alpha_line.iloc[-1])
        wt1_now = float(wt1.iloc[-1])
        wt1_prev = float(wt1.iloc[-2])
        wt2_now = float(wt2.iloc[-1])
        wt2_prev = float(wt2.iloc[-2])
        atr14 = float(_atr(high, low, close, 14).iloc[-1])

        if atr14 <= 0 or np.isnan(atr14):
            continue

        signal_type = None
        reason = ""

        # LONG: price above AlphaTrend (uptrend) + WaveTrend crossing up from oversold
        wt_cross_up = wt1_prev < wt2_prev and wt1_now >= wt2_now
        wt_cross_dn = wt1_prev > wt2_prev and wt1_now <= wt2_now

        if current > alpha_val and wt_cross_up and wt1_prev < -60:
            signal_type = "BUY"
            tp = current + atr14 * 3.0
            sl = current - atr14 * 1.5
            conf = min(0.82, 0.60 + abs(wt1_prev + 60) * 0.003)
            reason = (f"DNA Mutation: AlphaTrend={alpha_val:.2f} confirms uptrend "
                      f"+ WaveTrend crossed up from {wt1_prev:.0f} (oversold). "
                      f"Two best non-MACD indicators agree: buy the pullback in an uptrend.")

        # SHORT: price below AlphaTrend (downtrend) + WaveTrend crossing down from overbought
        elif current < alpha_val and wt_cross_dn and wt1_prev > 60:
            signal_type = "SELL"
            tp = current - atr14 * 3.0
            sl = current + atr14 * 1.5
            conf = min(0.82, 0.60 + abs(wt1_prev - 60) * 0.003)
            reason = (f"DNA Mutation: AlphaTrend={alpha_val:.2f} confirms downtrend "
                      f"+ WaveTrend crossed down from {wt1_prev:.0f} (overbought). "
                      f"Trend + momentum both say short the bounce in a downtrend.")

        if signal_type is None:
            continue

        rr = abs(tp - current) / abs(current - sl) if abs(current - sl) > 0 else 0
        if rr < 1.2:
            continue

        signals.append({
            "strategy": "alphatrend_wavetrend_confluence",
            "symbol": symbol,
            "category": cat,
            "signal_type": signal_type,
            "entry_price": _smart_round(current),
            "take_profit": _smart_round(tp),
            "stop_loss": _smart_round(sl),
            "confidence": round(conf, 2),
            "risk_reward": round(rr, 2),
            "reason": reason,
            "timeframe": "1d",
            "extra": {
                "alphatrend": round(alpha_val, 4),
                "wavetrend1": round(wt1_now, 1),
                "wavetrend2": round(wt2_now, 1),
            },
            "timestamp": _now_iso(),
        })

    return signals


# =====================================================================
# MUTATION 5: CTREND Multi-Horizon Momentum
# =====================================================================
# From: Fieberg et al. 2025, Journal of Financial & Quantitative Analysis
# "A Trend Factor for the Cross-Section of Cryptocurrency Returns"
#
# Academic finding: CTREND aggregates price and volume across MULTIPLE
# time horizons using elastic net. Weekly long-short alpha of 2.62%
# (t-stat = 4.22). Survives transaction costs. Published in a top-tier
# finance journal -- the strongest academic backing of any strategy we have.
#
# Simplified implementation: compute momentum scores across 7, 14, 30,
# and 90 day windows. Combine them with volume-weighted averaging.
# Go LONG on assets with highest composite momentum, SHORT on lowest.
# =====================================================================

def _momentum_score(close, volume, period):
    """Price momentum weighted by volume trend over a period."""
    if len(close) < period + 1:
        return np.nan
    price_mom = (close.iloc[-1] / close.iloc[-period] - 1.0) * 100
    vol_ratio = float(volume.iloc[-5:].mean()) / float(volume.iloc[-period:-5].mean() + 1e-10)
    return price_mom * min(vol_ratio, 3.0)


def ctrend_multi_horizon(data: dict) -> list[dict]:
    """CTREND: multi-horizon momentum from Fieberg et al. 2025 JFQA (DNA Mutation 5)."""
    if pd is None:
        return []

    targets = [
        ("BTC-USD", "crypto"), ("ETH-USD", "crypto"), ("SOL-USD", "crypto"),
        ("XRP-USD", "crypto"), ("AVAX-USD", "crypto"), ("LINK-USD", "crypto"),
        ("DOGE-USD", "crypto"), ("DOT-USD", "crypto"), ("ADA-USD", "crypto"),
        ("NEAR-USD", "crypto"), ("INJ-USD", "crypto"), ("TRX-USD", "crypto"),
    ]

    # Phase 1: compute composite momentum for all assets
    scores = []
    for symbol, cat in targets:
        df = data.get(symbol)
        if df is None or len(df) < 95:
            continue

        close = df["Close"]
        volume = df["Volume"]
        high = df["High"]
        low = df["Low"]

        m7 = _momentum_score(close, volume, 7)
        m14 = _momentum_score(close, volume, 14)
        m30 = _momentum_score(close, volume, 30)
        m90 = _momentum_score(close, volume, 90)

        if any(np.isnan(x) for x in [m7, m14, m30, m90]):
            continue

        # Weighted composite -- short-term windows get more weight for timing
        composite = m7 * 0.35 + m14 * 0.30 + m30 * 0.20 + m90 * 0.15
        scores.append((symbol, cat, composite, float(close.iloc[-1]),
                        float(_atr(high, low, close, 14).iloc[-1])))

    if len(scores) < 4:
        return []

    # Phase 2: rank and pick top/bottom by momentum
    scores.sort(key=lambda x: x[2], reverse=True)
    signals = []

    # Top 3 = LONG candidates (strongest upward momentum)
    for symbol, cat, score, current, atr14 in scores[:3]:
        if score <= 0 or atr14 <= 0:
            continue
        tp = current + atr14 * 2.5
        sl = current - atr14 * 1.5
        conf = min(0.80, 0.55 + abs(score) * 0.005)
        rr = abs(tp - current) / abs(current - sl) if abs(current - sl) > 0 else 0
        if rr < 1.0:
            continue
        signals.append({
            "strategy": "ctrend_multi_horizon",
            "symbol": symbol,
            "category": cat,
            "signal_type": "BUY",
            "entry_price": _smart_round(current),
            "take_profit": _smart_round(tp),
            "stop_loss": _smart_round(sl),
            "confidence": round(conf, 2),
            "risk_reward": round(rr, 2),
            "reason": (f"DNA Mutation: CTREND composite momentum = {score:+.1f} "
                       f"(ranked top 3 of {len(scores)} assets). "
                       f"Multi-horizon momentum (7d/14d/30d/90d) all weighted by volume. "
                       f"Based on Fieberg et al. 2025 JFQA -- 2.62% weekly alpha."),
            "timeframe": "1d",
            "extra": {"ctrend_score": round(score, 2), "rank": scores.index((symbol, cat, score, current, atr14)) + 1},
            "timestamp": _now_iso(),
        })

    # Bottom 3 = SHORT candidates (weakest momentum)
    for symbol, cat, score, current, atr14 in scores[-3:]:
        if score >= 0 or atr14 <= 0:
            continue
        tp = current - atr14 * 2.5
        sl = current + atr14 * 1.5
        conf = min(0.80, 0.55 + abs(score) * 0.005)
        rr = abs(tp - current) / abs(current - sl) if abs(current - sl) > 0 else 0
        if rr < 1.0:
            continue
        signals.append({
            "strategy": "ctrend_multi_horizon",
            "symbol": symbol,
            "category": cat,
            "signal_type": "SELL",
            "entry_price": _smart_round(current),
            "take_profit": _smart_round(tp),
            "stop_loss": _smart_round(sl),
            "confidence": round(conf, 2),
            "risk_reward": round(rr, 2),
            "reason": (f"DNA Mutation: CTREND composite momentum = {score:+.1f} "
                       f"(ranked bottom 3 of {len(scores)} assets). "
                       f"Multi-horizon momentum is negative across all windows. "
                       f"Weakest assets tend to keep falling -- academic cross-sectional momentum."),
            "timeframe": "1d",
            "extra": {"ctrend_score": round(score, 2), "rank": scores.index((symbol, cat, score, current, atr14)) + 1},
            "timestamp": _now_iso(),
        })

    return signals


# =====================================================================
# DNA Mutation 6: INVERSE CTREND -- Buy losers, sell winners (mean reversion)
# Original ctrend_multi_horizon had 0% WR because momentum fails in choppy
# crypto markets. Inverse: buy the dip on weakest, short the top on strongest.
# =====================================================================

def ctrend_inverse_reversion(data: dict) -> list[dict]:
    """Inverse CTREND: mean-reversion on multi-horizon momentum rankings.
    Original went long strongest momentum → 0% WR.
    This inverts: long the weakest (oversold bounce) and short the strongest (overextended)."""
    if pd is None:
        return []

    targets = [
        ("BTC-USD", "crypto"), ("ETH-USD", "crypto"), ("SOL-USD", "crypto"),
        ("XRP-USD", "crypto"), ("AVAX-USD", "crypto"), ("LINK-USD", "crypto"),
        ("DOGE-USD", "crypto"), ("DOT-USD", "crypto"), ("ADA-USD", "crypto"),
        ("NEAR-USD", "crypto"), ("INJ-USD", "crypto"), ("TRX-USD", "crypto"),
    ]

    scores = []
    for symbol, cat in targets:
        df = data.get(symbol)
        if df is None or len(df) < 95:
            continue

        close = df["Close"]
        volume = df["Volume"]
        high = df["High"]
        low = df["Low"]

        m7 = _momentum_score(close, volume, 7)
        m14 = _momentum_score(close, volume, 14)
        m30 = _momentum_score(close, volume, 30)
        m90 = _momentum_score(close, volume, 90)

        if any(np.isnan(x) for x in [m7, m14, m30, m90]):
            continue

        composite = m7 * 0.35 + m14 * 0.30 + m30 * 0.20 + m90 * 0.15

        # Mean-reversion filter: RSI must confirm oversold/overbought
        rsi_val = float(_rsi(close, 14).iloc[-1])

        scores.append((symbol, cat, composite, float(close.iloc[-1]),
                        float(_atr(high, low, close, 14).iloc[-1]), rsi_val))

    if len(scores) < 4:
        return []

    scores.sort(key=lambda x: x[2], reverse=True)
    signals = []

    # INVERSE: Bottom 3 momentum = LONG candidates (oversold bounce)
    for symbol, cat, score, current, atr14, rsi_val in scores[-3:]:
        if atr14 <= 0:
            continue
        # Require RSI < 40 to confirm oversold (not just weak momentum)
        if rsi_val > 40:
            continue
        tp = current + atr14 * 2.0
        sl = current - atr14 * 1.2
        conf = min(0.75, 0.55 + abs(score) * 0.003)
        rr = abs(tp - current) / abs(current - sl) if abs(current - sl) > 0 else 0
        if rr < 1.2:
            continue
        signals.append({
            "strategy": "ctrend_inverse_reversion",
            "symbol": symbol,
            "category": cat,
            "signal_type": "BUY",
            "entry_price": _smart_round(current),
            "take_profit": _smart_round(tp),
            "stop_loss": _smart_round(sl),
            "confidence": round(conf, 2),
            "risk_reward": round(rr, 2),
            "reason": (f"DNA Mutation 6: INVERSE CTREND -- momentum={score:+.1f} (bottom 3), "
                       f"RSI={rsi_val:.0f} confirms oversold. "
                       f"Mean-reversion: weakest momentum assets bounce. "
                       f"Original momentum strategy had 0% WR → inverse logic."),
            "timeframe": "1d",
            "extra": {"ctrend_score": round(score, 2), "rsi": round(rsi_val, 1),
                      "rank": len(scores) - scores[-3:].index((symbol, cat, score, current, atr14, rsi_val))},
            "timestamp": _now_iso(),
        })

    return signals


# =====================================================================
# DNA Mutation 7: CTREND RSI-filtered momentum (tighter entry than original)
# Original fired on any positive momentum → too loose.
# This variant requires RSI alignment + volume surge confirmation.
# =====================================================================

def ctrend_rsi_volume_filter(data: dict) -> list[dict]:
    """CTREND with RSI + volume confirmation. Only fires when momentum
    aligns with RSI trend AND volume is above 20-day average."""
    if pd is None:
        return []

    targets = [
        ("BTC-USD", "crypto"), ("ETH-USD", "crypto"), ("SOL-USD", "crypto"),
        ("XRP-USD", "crypto"), ("AVAX-USD", "crypto"), ("LINK-USD", "crypto"),
        ("DOGE-USD", "crypto"), ("DOT-USD", "crypto"), ("ADA-USD", "crypto"),
        ("NEAR-USD", "crypto"), ("INJ-USD", "crypto"), ("TRX-USD", "crypto"),
    ]

    scores = []
    for symbol, cat in targets:
        df = data.get(symbol)
        if df is None or len(df) < 95:
            continue

        close = df["Close"]
        volume = df["Volume"]
        high = df["High"]
        low = df["Low"]

        m7 = _momentum_score(close, volume, 7)
        m14 = _momentum_score(close, volume, 14)
        m30 = _momentum_score(close, volume, 30)
        m90 = _momentum_score(close, volume, 90)

        if any(np.isnan(x) for x in [m7, m14, m30, m90]):
            continue

        composite = m7 * 0.35 + m14 * 0.30 + m30 * 0.20 + m90 * 0.15
        rsi_val = float(_rsi(close, 14).iloc[-1])

        # Volume filter: current 5-day avg must be > 20-day avg
        vol_5 = float(volume.iloc[-5:].mean())
        vol_20 = float(volume.iloc[-20:].mean())
        vol_surge = vol_5 / (vol_20 + 1e-10)

        scores.append((symbol, cat, composite, float(close.iloc[-1]),
                        float(_atr(high, low, close, 14).iloc[-1]), rsi_val, vol_surge))

    if len(scores) < 4:
        return []

    scores.sort(key=lambda x: x[2], reverse=True)
    signals = []

    # Top 3 = LONG -- but only if RSI 50-70 (trending, not overbought) AND volume surge
    for symbol, cat, score, current, atr14, rsi_val, vol_surge in scores[:3]:
        if score <= 0 or atr14 <= 0:
            continue
        if rsi_val < 50 or rsi_val > 70:
            continue  # RSI must be in trending zone
        if vol_surge < 1.1:
            continue  # Volume must be rising
        tp = current + atr14 * 2.5
        sl = current - atr14 * 1.5
        conf = min(0.80, 0.55 + abs(score) * 0.004 + (vol_surge - 1.0) * 0.1)
        rr = abs(tp - current) / abs(current - sl) if abs(current - sl) > 0 else 0
        if rr < 1.2:
            continue
        signals.append({
            "strategy": "ctrend_rsi_volume_filter",
            "symbol": symbol,
            "category": cat,
            "signal_type": "BUY",
            "entry_price": _smart_round(current),
            "take_profit": _smart_round(tp),
            "stop_loss": _smart_round(sl),
            "confidence": round(conf, 2),
            "risk_reward": round(rr, 2),
            "reason": (f"DNA Mutation 7: CTREND+RSI+Vol -- momentum={score:+.1f} (top 3), "
                       f"RSI={rsi_val:.0f} (trending zone 50-70), "
                       f"Vol surge={vol_surge:.2f}x. "
                       f"Stricter filter than original (0% WR) -- requires RSI+volume confirmation."),
            "timeframe": "1d",
            "extra": {"ctrend_score": round(score, 2), "rsi": round(rsi_val, 1),
                      "vol_surge": round(vol_surge, 2)},
            "timestamp": _now_iso(),
        })

    return signals


# =====================================================================
# DNA Mutation 8: SEASONAL CONTRARIAN -- Inverse of seasonal_factor_rotation
# Original had 0% WR: bought above 252d SMA with positive momentum.
# Inverse: mean-revert when price is extended from seasonal norm.
# =====================================================================

def seasonal_contrarian_reversion(data: dict) -> list[dict]:
    """Inverse seasonal: buy when price is far BELOW 252d SMA (oversold seasonal dip),
    sell when far ABOVE (overextended seasonal rally). Original bought high → 0% WR."""
    if pd is None:
        return []

    targets = [
        ("BTC-USD", "crypto"), ("ETH-USD", "crypto"), ("SOL-USD", "crypto"),
        ("XRP-USD", "crypto"), ("AVAX-USD", "crypto"), ("LINK-USD", "crypto"),
        ("DOGE-USD", "crypto"), ("DOT-USD", "crypto"), ("ADA-USD", "crypto"),
        ("NEAR-USD", "crypto"), ("INJ-USD", "crypto"), ("TRX-USD", "crypto"),
    ]

    signals = []
    for symbol, cat in targets:
        df = data.get(symbol)
        if df is None or len(df) < 252:
            continue

        try:
            close = df["Close"]
            high = df["High"]
            low = df["Low"]
            price = float(close.iloc[-1])

            sma_252 = float(close.rolling(252).mean().iloc[-1])
            if sma_252 <= 0 or not np.isfinite(sma_252):
                continue

            season_factor = price / sma_252
            rsi_val = float(_rsi(close, 14).iloc[-1])
            atr14 = float(_atr(high, low, close, 14).iloc[-1])
            if atr14 <= 0:
                continue

            # INVERSE: Buy when price is well BELOW seasonal average + RSI oversold
            if season_factor < 0.92 and rsi_val < 35:
                tp = _smart_round(price + atr14 * 2.5)
                sl = _smart_round(price - atr14 * 1.5)
                rr = abs(tp - price) / abs(price - sl) if abs(price - sl) > 0 else 0
                if rr < 1.2:
                    continue
                conf = min(0.75, 0.55 + (1.0 - season_factor) * 2)
                signals.append({
                    "strategy": "seasonal_contrarian_reversion",
                    "symbol": symbol,
                    "category": cat,
                    "signal_type": "BUY",
                    "entry_price": _smart_round(price),
                    "take_profit": tp,
                    "stop_loss": sl,
                    "confidence": round(conf, 2),
                    "risk_reward": round(rr, 2),
                    "reason": (f"DNA Mutation 8: SEASONAL CONTRARIAN -- "
                               f"season_factor={season_factor:.3f} (price {(1-season_factor)*100:.1f}% below 252d SMA), "
                               f"RSI={rsi_val:.0f} (oversold). "
                               f"Mean-revert to seasonal norm. Original bought high → 0% WR."),
                    "timeframe": "1d",
                    "extra": {"season_factor": round(season_factor, 4), "rsi": round(rsi_val, 1)},
                    "timestamp": _now_iso(),
                })

            # INVERSE: Sell when price is well ABOVE seasonal average + RSI overbought
            elif season_factor > 1.12 and rsi_val > 70:
                tp = _smart_round(price - atr14 * 2.5)
                sl = _smart_round(price + atr14 * 1.5)
                rr = abs(tp - price) / abs(sl - price) if abs(sl - price) > 0 else 0
                if rr < 1.2:
                    continue
                conf = min(0.75, 0.55 + (season_factor - 1.0) * 2)
                signals.append({
                    "strategy": "seasonal_contrarian_reversion",
                    "symbol": symbol,
                    "category": cat,
                    "signal_type": "SELL",
                    "entry_price": _smart_round(price),
                    "take_profit": tp,
                    "stop_loss": sl,
                    "confidence": round(conf, 2),
                    "risk_reward": round(rr, 2),
                    "reason": (f"DNA Mutation 8: SEASONAL CONTRARIAN -- "
                               f"season_factor={season_factor:.3f} (price {(season_factor-1)*100:.1f}% above 252d SMA), "
                               f"RSI={rsi_val:.0f} (overbought). "
                               f"Mean-revert to seasonal norm."),
                    "timeframe": "1d",
                    "extra": {"season_factor": round(season_factor, 4), "rsi": round(rsi_val, 1)},
                    "timestamp": _now_iso(),
                })
        except Exception:
            continue

    return signals


# =====================================================================
# DNA Mutation 9: SEASONAL MOMENTUM STRICT -- Tighter version of original
# Original had 2% threshold → too loose. This uses 5% + volume + RSI filter.
# =====================================================================

def seasonal_momentum_strict(data: dict) -> list[dict]:
    """Stricter seasonal momentum: requires 5%+ above/below SMA, RSI alignment,
    AND volume confirmation. Original 2% threshold was noise."""
    if pd is None:
        return []

    targets = [
        ("BTC-USD", "crypto"), ("ETH-USD", "crypto"), ("SOL-USD", "crypto"),
        ("XRP-USD", "crypto"), ("AVAX-USD", "crypto"), ("LINK-USD", "crypto"),
        ("DOGE-USD", "crypto"), ("DOT-USD", "crypto"), ("ADA-USD", "crypto"),
        ("NEAR-USD", "crypto"), ("INJ-USD", "crypto"), ("TRX-USD", "crypto"),
    ]

    signals = []
    for symbol, cat in targets:
        df = data.get(symbol)
        if df is None or len(df) < 252:
            continue

        try:
            close = df["Close"]
            volume = df["Volume"]
            high = df["High"]
            low = df["Low"]
            price = float(close.iloc[-1])

            sma_252 = float(close.rolling(252).mean().iloc[-1])
            if sma_252 <= 0 or not np.isfinite(sma_252):
                continue

            season_factor = price / sma_252
            rsi_val = float(_rsi(close, 14).iloc[-1])
            atr14 = float(_atr(high, low, close, 14).iloc[-1])
            if atr14 <= 0:
                continue

            # Volume confirmation
            vol_5 = float(volume.iloc[-5:].mean())
            vol_20 = float(volume.iloc[-20:].mean())
            vol_surge = vol_5 / (vol_20 + 1e-10)

            # 7d and 14d momentum must both be positive/negative
            mom_7d = price / float(close.iloc[-7]) - 1 if len(close) >= 7 else 0
            mom_14d = price / float(close.iloc[-14]) - 1 if len(close) >= 14 else 0

            # LONG: 5%+ above SMA, RSI 55-75 (trending), both momenta positive, volume rising
            if (season_factor > 1.05 and 55 <= rsi_val <= 75
                    and mom_7d > 0 and mom_14d > 0 and vol_surge > 1.05):
                tp = _smart_round(price + atr14 * 2.5)
                sl = _smart_round(price - atr14 * 1.5)
                rr = abs(tp - price) / abs(price - sl) if abs(price - sl) > 0 else 0
                if rr < 1.2:
                    continue
                conf = min(0.75, 0.55 + (season_factor - 1.0) * 2 + (vol_surge - 1.0) * 0.1)
                signals.append({
                    "strategy": "seasonal_momentum_strict",
                    "symbol": symbol,
                    "category": cat,
                    "signal_type": "BUY",
                    "entry_price": _smart_round(price),
                    "take_profit": tp,
                    "stop_loss": sl,
                    "confidence": round(conf, 2),
                    "risk_reward": round(rr, 2),
                    "reason": (f"DNA Mutation 9: SEASONAL STRICT -- "
                               f"factor={season_factor:.3f} (>{'>'}5% above SMA), "
                               f"RSI={rsi_val:.0f}, 7d mom={mom_7d*100:.1f}%, "
                               f"vol_surge={vol_surge:.2f}x. Tighter filter than original (0% WR)."),
                    "timeframe": "1d",
                    "extra": {"season_factor": round(season_factor, 4), "rsi": round(rsi_val, 1),
                              "vol_surge": round(vol_surge, 2), "mom_7d": round(mom_7d, 4)},
                    "timestamp": _now_iso(),
                })
        except Exception:
            continue

    return signals


# -- Strategy registry for scanner import ----------------------------

DNA_MUTATION_STRATEGIES = {
    "connors_williams_hybrid": connors_williams_hybrid,
    "tvl_weighted_momentum": tvl_weighted_momentum,
    "alphatrend_wavetrend_confluence": alphatrend_wavetrend_confluence,
    # Original ctrend_multi_horizon KILLED (0% WR, -37% PnL) -- replaced by mutations:
    "ctrend_inverse_reversion": ctrend_inverse_reversion,
    "ctrend_rsi_volume_filter": ctrend_rsi_volume_filter,
    "seasonal_contrarian_reversion": seasonal_contrarian_reversion,
    "seasonal_momentum_strict": seasonal_momentum_strict,
    # anti_consensus_contrarian needs all_signals param, wired separately in scanner
}


if __name__ == "__main__":
    print("DNA Mutation Strategies")
    print("=" * 50)
    print(f"Registered: {list(DNA_MUTATION_STRATEGIES.keys())}")
    print()
    print("Mutation 1: connors_williams_hybrid")
    print("  Parents: ConnorsRSI (75.7% WR) x Williams %R (81% WR)")
    print("  Logic: BOTH must agree on oversold/overbought + SMA200 trend filter")
    print()
    print("Mutation 2: tvl_weighted_momentum")
    print("  Parents: DefiLlama TVL data x RSI(14) timing")
    print("  Logic: TVL direction decides long/short, RSI times the entry")
    print("  Key insight: TVL inflows predicted R3 bounce that killed all shorts")
    print()
    print("Mutation 3: anti_consensus_contrarian")
    print("  Parents: Tournament data x crowd psychology")
    print("  Logic: When >75% of signals agree, take the opposite trade")
    print("  Key insight: R3 had 18/18 shorts, all lost. User's longs won.")
    print()
    print("Mutation 4: alphatrend_wavetrend_confluence")
    print("  Parents: AlphaTrend (62% WR, PF 2.1) x WaveTrend (58% WR, PF 1.9)")
    print("  Logic: AlphaTrend confirms trend direction, WaveTrend times entry")
    print("  Key insight: Trend-following beats mean reversion on crypto")
    print()
    print("Mutation 5: ctrend_multi_horizon")
    print("  Parents: Fieberg et al. 2025 JFQA (2.62% weekly alpha)")
    print("  Logic: Rank assets by 7/14/30/90-day momentum weighted by volume")
    print("  Key insight: Go long strongest momentum, short weakest -- academic proof")
    print()
    print("Mutation 6: dna_hurst_relaxed")
    print("  Parent: hurst_mean_reversion (100% WR, 3 trades)")
    print("  Relaxed: Hurst<0.48 (was 0.42), BB%B<0.25 (was 0.15), RSI<45 (was 40)")
    print()
    print("Mutation 7: dna_ema_stack_relaxed")
    print("  Parent: multi_timeframe_ema_stack (100% WR, 2 trades)")
    print("  Relaxed: 3-EMA stack (skip SMA 200), proximity entry (0.5% of EMA 9)")
    print()
    print("Mutation 8: dna_fractal_bounce_relaxed")
    print("  Parent: fractal_sr_bounce (71.4% WR, PF 3.68, 14 trades)")
    print("  Relaxed: 2 touches (was 3), 0.75 ATR proximity (was 0.5)")


# =====================================================================
# MUTATION 6: Relaxed Hurst Mean Reversion (DNA variant)
# =====================================================================
# Parent: hurst_mean_reversion -- 100% WR on 3 trades, but filters are
# so tight it almost never fires. Relax thresholds to generate more
# signals while preserving the core mean-reversion logic.
# Original: Hurst<0.42, BB%B<0.15, RSI<40
# Relaxed:  Hurst<0.48, BB%B<0.25, RSI<45
# =====================================================================

def dna_hurst_relaxed(data: dict) -> list[dict]:
    """DNA Mutation 6: Relaxed Hurst mean-reversion (wider thresholds)."""
    if pd is None:
        return []
    signals = []

    targets = [
        ("BTC-USD", "crypto"), ("ETH-USD", "crypto"), ("SOL-USD", "crypto"),
        ("XRP-USD", "crypto"), ("AVAX-USD", "crypto"), ("LINK-USD", "crypto"),
        ("DOGE-USD", "crypto"), ("DOT-USD", "crypto"), ("ADA-USD", "crypto"),
        ("BNB-USD", "crypto"), ("NEAR-USD", "crypto"), ("MATIC-USD", "crypto"),
    ]

    for symbol, cat in targets:
        df = data.get(symbol)
        if df is None or len(df) < 100:
            continue
        try:
            close = df["Close"]
            # Hurst exponent
            lags = range(2, min(21, len(close) // 4))
            tau = []
            for lag in lags:
                tau.append(float(np.std(np.subtract(close.values[lag:], close.values[:-lag]))))
            if not tau or min(tau) <= 0:
                continue
            log_lags = np.log(list(lags))
            log_tau = np.log(tau)
            h = float(np.polyfit(log_lags, log_tau, 1)[0])

            if h >= 0.48:  # RELAXED from 0.42
                continue

            # Bollinger Bands
            bb_mid = close.rolling(20).mean()
            bb_std = close.rolling(20).std()
            bb_upper = bb_mid + 2 * bb_std
            bb_lower = bb_mid - 2 * bb_std
            bb_range = bb_upper - bb_lower
            pct_b = float(((close - bb_lower) / bb_range.replace(0, 1e-10)).iloc[-1])

            if pct_b > 0.25:  # RELAXED from 0.15
                continue

            rsi_val = float(_rsi(close, 14).iloc[-1])
            if rsi_val > 45:  # RELAXED from 40
                continue

            current = float(close.iloc[-1])
            mid = float(bb_mid.iloc[-1])
            lower = float(bb_lower.iloc[-1])
            tp = mid
            sl = lower * 0.97

            rr = (tp - current) / (current - sl) if current > sl else 0
            if rr < 1.2:  # RELAXED from 1.3
                continue

            signals.append({
                "strategy": "dna_hurst_relaxed",
                "symbol": symbol, "category": cat,
                "signal_type": "BUY",
                "entry_price": _smart_round(current),
                "take_profit": _smart_round(tp),
                "stop_loss": _smart_round(sl),
                "confidence": round(min(0.75, 0.50 + (0.48 - h) * 2.5), 2),
                "risk_reward": round(rr, 2),
                "reason": (f"DNA-Hurst relaxed: H={h:.3f}, BB%B={pct_b:.2f}, "
                           f"RSI={rsi_val:.0f}. Parent: 100% WR on 3 trades."),
                "timeframe": "1d",
                "timestamp": _now_iso(),
            })
        except Exception:
            continue
    return signals


# =====================================================================
# MUTATION 7: Relaxed Multi-Timeframe EMA Stack (DNA variant)
# =====================================================================
# Parent: multi_timeframe_ema_stack -- 100% WR on 2 trades.
# Original: Requires perfect 4-EMA alignment (9>21>50>200) + exact crossover.
# Relaxed: 3-EMA stack (skip SMA 200), proximity entry within 0.5% of EMA 9.
# =====================================================================

def dna_ema_stack_relaxed(data: dict) -> list[dict]:
    """DNA Mutation 7: Relaxed EMA stack (3-EMA, proximity entry)."""
    if pd is None:
        return []
    signals = []

    targets = [
        ("BTC-USD", "crypto"), ("ETH-USD", "crypto"), ("SOL-USD", "crypto"),
        ("XRP-USD", "crypto"), ("AVAX-USD", "crypto"), ("LINK-USD", "crypto"),
        ("DOGE-USD", "crypto"), ("DOT-USD", "crypto"), ("ADA-USD", "crypto"),
        ("BNB-USD", "crypto"), ("NEAR-USD", "crypto"), ("MATIC-USD", "crypto"),
    ]

    for symbol, cat in targets:
        df = data.get(symbol)
        if df is None or len(df) < 60:
            continue
        try:
            close = df["Close"]
            high = df["High"]
            low = df["Low"]
            volume = df["Volume"]
            current = float(close.iloc[-1])

            e9 = float(close.ewm(span=9).mean().iloc[-1])
            e21 = float(close.ewm(span=21).mean().iloc[-1])
            e50 = float(close.ewm(span=50).mean().iloc[-1])

            # RELAXED: 3-EMA bullish stack (skip SMA 200)
            if not (e9 > e21 > e50):
                continue

            # RELAXED: proximity entry -- within 0.5% of EMA 9 (not exact crossover)
            distance_to_e9 = abs(current - e9) / e9
            if distance_to_e9 > 0.005:
                continue

            # Must be pulling back (below or near EMA 9)
            if current > e9 * 1.003:
                continue

            rsi_val = float(_rsi(close, 14).iloc[-1])
            if rsi_val > 80:
                continue

            atr_val = float(_atr(high, low, close, 14).iloc[-1])
            if atr_val == 0:
                continue

            tp = _smart_round(current + 3.0 * atr_val)
            sl = _smart_round(e50 * 0.995)

            rr = (tp - current) / (current - sl) if current > sl else 0
            if rr < 1.2:
                continue

            # Stack quality
            spread = (e9 - e50) / e50 * 100
            vol_avg = float(volume.rolling(20).mean().iloc[-1]) or 1
            vol_r = float(volume.iloc[-1]) / vol_avg

            signals.append({
                "strategy": "dna_ema_stack_relaxed",
                "symbol": symbol, "category": cat,
                "signal_type": "BUY",
                "entry_price": _smart_round(current),
                "take_profit": tp,
                "stop_loss": sl,
                "confidence": round(min(0.78, 0.52 + spread * 0.008 + vol_r * 0.015), 2),
                "risk_reward": round(rr, 2),
                "reason": (f"DNA-EMA relaxed: 3-EMA stack ({spread:.1f}% spread), "
                           f"RSI={rsi_val:.0f}, dist={distance_to_e9*100:.2f}%. "
                           f"Parent: 100% WR on 2 trades."),
                "timeframe": "1d",
                "timestamp": _now_iso(),
            })
        except Exception:
            continue
    return signals


# =====================================================================
# MUTATION 8: Relaxed Fractal S/R Bounce (DNA variant)
# =====================================================================
# Parent: fractal_sr_bounce -- 71.4% WR, PF 3.68 on 14 trades.
# Original: 3 touches + 0.5 ATR proximity.
# Relaxed: 2 touches + 0.75 ATR proximity.
# =====================================================================

def dna_fractal_bounce_relaxed(data: dict) -> list[dict]:
    """DNA Mutation 8: Relaxed fractal S/R bounce (2 touches, wider zone)."""
    if pd is None:
        return []
    signals = []

    targets = [
        ("BTC-USD", "crypto"), ("ETH-USD", "crypto"), ("SOL-USD", "crypto"),
        ("XRP-USD", "crypto"), ("AVAX-USD", "crypto"), ("LINK-USD", "crypto"),
        ("DOGE-USD", "crypto"), ("DOT-USD", "crypto"), ("ADA-USD", "crypto"),
        ("BNB-USD", "crypto"), ("NEAR-USD", "crypto"), ("MATIC-USD", "crypto"),
    ]

    for symbol, cat in targets:
        df = data.get(symbol)
        if df is None or len(df) < 60:
            continue
        try:
            close = df["Close"]
            high = df["High"]
            low = df["Low"]
            price = float(close.iloc[-1])

            atr_series = _atr(high, low, close, 14)
            current_atr = float(atr_series.iloc[-1])
            if current_atr == 0 or np.isnan(current_atr):
                continue

            # Find fractal pivots (Williams method, window=5)
            pivots = []
            h_vals = high.values.astype(float)
            l_vals = low.values.astype(float)
            for i in range(5, len(df) - 5):
                if h_vals[i] == max(h_vals[i-5:i+6]):
                    pivots.append({"price": h_vals[i], "type": "high", "idx": i})
                if l_vals[i] == min(l_vals[i-5:i+6]):
                    pivots.append({"price": l_vals[i], "type": "low", "idx": i})

            if len(pivots) < 4:
                continue

            # Cluster pivots into levels (0.5% tolerance)
            levels = []
            used = set()
            pivot_prices = [(p["price"], p["type"], p["idx"]) for p in pivots]
            for i, (p1, t1, idx1) in enumerate(pivot_prices):
                if i in used:
                    continue
                cluster = [{"price": p1, "type": t1, "idx": idx1}]
                used.add(i)
                for j, (p2, t2, idx2) in enumerate(pivot_prices):
                    if j in used:
                        continue
                    if abs(p2 - p1) / max(p1, 1e-10) < 0.005:
                        cluster.append({"price": p2, "type": t2, "idx": idx2})
                        used.add(j)
                if len(cluster) >= 2:  # RELAXED from 3
                    avg_price = np.mean([c["price"] for c in cluster])
                    has_high = any(c["type"] == "high" for c in cluster)
                    has_low = any(c["type"] == "low" for c in cluster)
                    lvl_type = "both" if has_high and has_low else ("resistance" if has_high else "support")
                    levels.append({
                        "level": avg_price,
                        "touches": len(cluster),
                        "type": lvl_type,
                        "indices": [c["idx"] for c in cluster],
                    })

            if not levels:
                continue

            for lvl in levels:
                level_price = lvl["level"]
                touches = lvl["touches"]
                lvl_type = lvl["type"]

                distance = abs(price - level_price)
                if distance > 0.75 * current_atr:  # RELAXED from 0.5
                    continue

                if price <= level_price and lvl_type in ("support", "both"):
                    signal_type = "BUY"
                    tp = price + 2.5 * current_atr
                    sl = level_price - 0.005 * level_price
                elif price >= level_price and lvl_type in ("resistance", "both"):
                    signal_type = "SELL"
                    tp = price - 2.5 * current_atr
                    sl = level_price + 0.005 * level_price
                else:
                    continue

                reward = abs(tp - price)
                risk = abs(price - sl)
                if risk == 0:
                    continue
                rr = reward / risk
                if rr < 1.2:
                    continue

                signals.append({
                    "strategy": "dna_fractal_bounce_relaxed",
                    "symbol": symbol, "category": cat,
                    "signal_type": signal_type,
                    "entry_price": _smart_round(price),
                    "take_profit": _smart_round(tp),
                    "stop_loss": _smart_round(sl),
                    "confidence": round(min(0.78, 0.48 + touches * 0.06), 2),
                    "risk_reward": round(rr, 2),
                    "reason": (f"DNA-Fractal relaxed: {lvl_type} ${level_price:.2f} "
                               f"({touches} touches). Parent: 71.4% WR, PF 3.68."),
                    "timeframe": "1d",
                    "timestamp": _now_iso(),
                })
        except Exception:
            continue
    return signals


# =====================================================================
# Registry of all DNA mutation strategies
# =====================================================================

DNA_MUTATIONS = {
    "connors_williams_hybrid": connors_williams_hybrid,
    "tvl_weighted_momentum": tvl_weighted_momentum,
    "anti_consensus_contrarian": anti_consensus_contrarian,
    "dna_hurst_relaxed": dna_hurst_relaxed,
    "dna_ema_stack_relaxed": dna_ema_stack_relaxed,
    "dna_fractal_bounce_relaxed": dna_fractal_bounce_relaxed,
}
