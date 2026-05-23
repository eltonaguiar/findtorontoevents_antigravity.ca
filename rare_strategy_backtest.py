#!/usr/bin/env python3
"""
RARE STRATEGY BACKTESTER — Academically-Backed Hourly Crypto Strategies
========================================================================
Implements and backtests the top strategies from deep research:
1. HMM Regime-Switching + Volatility-Scaled Momentum
2. EGARCH Volatility Targeting + Mean-Reversion
3. Hurst Exponent Filtered Pairs Trading (BTC/ETH)
4. Intraday Seasonality Overlay Filter
5. Ornstein-Uhlenbeck Optimal Stopping Pairs

Uses real BTCUSDT 1H data from yfinance (729 days).
"""

import json
import warnings
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import yfinance as yf

warnings.filterwarnings("ignore")

# ─── DATA FETCHING ───────────────────────────────────────────────────────────

def fetch_crypto_1h(symbol: str = "BTC-USD", days: int = 729) -> pd.DataFrame:
    """Fetch hourly OHLCV from yfinance."""
    ticker = yf.Ticker(symbol)
    df = ticker.history(period=f"{days}d", interval="1h")
    if df is None or len(df) < 500:
        raise ValueError(f"Insufficient data for {symbol}: got {len(df) if df is not None else 0} bars")
    df.columns = [c.lower() for c in df.columns]
    df = df[['open', 'high', 'low', 'close', 'volume']].copy()
    df.dropna(inplace=True)
    print(f"  {symbol}: {len(df)} hourly bars from {df.index[0]} to {df.index[-1]}")
    return df


# ─── STRATEGY 1: HMM REGIME + VOL-SCALED MOMENTUM ──────────────────────────

def hmm_regime_momentum(df: pd.DataFrame,
                         n_regimes: int = 3,
                         momentum_window: int = 168,  # 7 days
                         vol_window: int = 72,  # 3 days
                         target_vol: float = 0.15) -> pd.Series:
    """
    HMM Regime-Switching + Volatility-Scaled Momentum

    Based on: "Applications of Hidden Markov Models in Detecting Regime Changes
    in Bitcoin Markets" (2025, AJPAS) + Barroso & Santa-Clara risk management.

    Approach: Simple regime detection via rolling stats (no hmmlearn dependency),
    then momentum with vol scaling.
    """
    close = df['close'].values
    returns = np.diff(np.log(close))
    returns = np.insert(returns, 0, 0)

    n = len(close)
    signals = np.zeros(n)

    # Rolling regime detection (proxy for HMM using rolling mean + vol)
    regime_window = 168  # 7 days

    for i in range(max(momentum_window, regime_window, vol_window) + 1, n):
        # Regime detection via rolling statistics
        recent_returns = returns[i - regime_window:i]
        recent_vol = np.std(recent_returns) * np.sqrt(8760)  # annualized
        recent_mean = np.mean(recent_returns) * 8760  # annualized drift

        # Classify regime
        if recent_vol > 0.8 and recent_mean < -0.1:
            regime = 'bear'  # High vol, negative drift
        elif recent_vol < 0.5 and recent_mean > 0.1:
            regime = 'bull'  # Low vol, positive drift
        else:
            regime = 'neutral'

        # Momentum signal (7-day return)
        mom = (close[i] / close[i - momentum_window] - 1)

        # Volatility scaling (Barroso & Santa-Clara)
        realized_vol = np.std(returns[i - vol_window:i]) * np.sqrt(8760)
        vol_scale = min(target_vol / max(realized_vol, 0.01), 3.0)  # Cap at 3x

        # Per-regime strategy
        if regime == 'bull':
            # Trend-following: buy dips in bull market
            if mom > 0:
                signals[i] = 1.0 * vol_scale
            elif mom < -0.05:
                signals[i] = 0.5 * vol_scale  # Buy the dip
        elif regime == 'bear':
            # Mean-reversion only: fade sharp drops
            short_mom = (close[i] / close[i - 24] - 1)
            if short_mom < -0.03:
                signals[i] = 0.5 * vol_scale  # Bounce play
            elif mom > 0:
                signals[i] = -0.5 * vol_scale  # Fade rallies in bear
        else:
            # Neutral: trade both ways with smaller size
            short_mom = (close[i] / close[i - 24] - 1)
            if short_mom < -0.02:
                signals[i] = 0.3 * vol_scale
            elif short_mom > 0.02:
                signals[i] = -0.3 * vol_scale

    return pd.Series(signals, index=df.index)


# ─── STRATEGY 2: EGARCH VOL TARGETING ───────────────────────────────────────

def egarch_vol_targeting(df: pd.DataFrame,
                         vol_window: int = 72,
                         slow_vol_window: int = 720,
                         target_vol: float = 0.15,
                         rsi_period: int = 14) -> pd.Series:
    """
    EGARCH-inspired Volatility Targeting + Mean-Reversion

    Based on: Du (2025) "Pricing Cryptocurrency Options With Volatility of Volatility"
    + Fidelity Digital Assets vol analysis.

    Uses volatility regime to size positions and RSI for direction.
    Key insight: vol contraction → buy, vol expansion → reduce/hedge.
    """
    close = df['close'].values
    returns = np.diff(np.log(close))
    returns = np.insert(returns, 0, 0)

    n = len(close)
    signals = np.zeros(n)

    for i in range(max(slow_vol_window, rsi_period * 2) + 1, n):
        # Realized vol (short window)
        fast_vol = np.std(returns[i - vol_window:i]) * np.sqrt(8760)
        # Realized vol (long window)
        slow_vol = np.std(returns[i - slow_vol_window:i]) * np.sqrt(8760)

        # Asymmetric vol response (EGARCH-inspired)
        # Negative returns increase vol more than positive returns
        recent_neg = returns[i - 24:i]
        neg_vol = np.std([r for r in recent_neg if r < 0]) if any(r < 0 for r in recent_neg) else 0
        pos_vol = np.std([r for r in recent_neg if r > 0]) if any(r > 0 for r in recent_neg) else 0
        asymmetry = neg_vol / max(pos_vol, 1e-8)

        # Vol regime
        vol_ratio = fast_vol / max(slow_vol, 0.01)

        # RSI for direction
        gains = []
        losses = []
        for j in range(i - rsi_period, i):
            delta = returns[j]
            if delta > 0:
                gains.append(delta)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(abs(delta))
        avg_gain = np.mean(gains)
        avg_loss = np.mean(losses)
        rsi = 100 - (100 / (1 + avg_gain / max(avg_loss, 1e-10)))

        # Vol scaling
        vol_scale = min(target_vol / max(fast_vol, 0.01), 3.0)

        # Strategy logic
        if vol_ratio < 0.7:
            # Vol contraction: expect expansion, prepare for breakout
            if rsi < 35:
                signals[i] = 1.0 * vol_scale  # Oversold in low vol = strong buy
            elif rsi > 65:
                signals[i] = -0.5 * vol_scale  # Overbought in low vol = sell
        elif vol_ratio > 1.5:
            # Vol expansion: mean-revert with reduced size
            if rsi < 25 and asymmetry > 1.5:
                signals[i] = 0.8 * vol_scale  # Panic selling, high asymmetry = bounce
            elif rsi > 75:
                signals[i] = -0.3 * vol_scale  # Don't short aggressively in high vol
        else:
            # Normal vol: standard RSI mean-reversion
            if rsi < 30:
                signals[i] = 0.5 * vol_scale
            elif rsi > 70:
                signals[i] = -0.3 * vol_scale

    return pd.Series(signals, index=df.index)


# ─── STRATEGY 3: HURST EXPONENT FILTERED PAIRS ─────────────────────────────

def hurst_exponent(series: np.ndarray, max_lag: int = 50) -> float:
    """Calculate Hurst exponent using R/S method."""
    n = len(series)
    if n < max_lag * 2:
        return 0.5

    lags = range(10, min(max_lag + 1, n // 4))
    rs_values = []
    lag_values = []

    for lag in lags:
        chunks = n // lag
        if chunks < 2:
            continue
        rs_chunk = []
        for c in range(chunks):
            chunk = series[c * lag:(c + 1) * lag]
            mean_chunk = np.mean(chunk)
            deviations = chunk - mean_chunk
            cumulative = np.cumsum(deviations)
            R = np.max(cumulative) - np.min(cumulative)
            S = np.std(chunk)
            if S > 1e-10:
                rs_chunk.append(R / S)
        if rs_chunk:
            rs_values.append(np.log(np.mean(rs_chunk)))
            lag_values.append(np.log(lag))

    if len(rs_values) < 3:
        return 0.5

    # Linear regression: log(R/S) = H * log(n) + c
    coeffs = np.polyfit(lag_values, rs_values, 1)
    return max(0.01, min(0.99, coeffs[0]))


def hurst_pairs_trading(df_btc: pd.DataFrame, df_eth: pd.DataFrame,
                         hurst_window: int = 168,
                         zscore_entry: float = 2.0,
                         zscore_exit: float = 0.5,
                         hedge_window: int = 72) -> Tuple[pd.Series, pd.Series]:
    """
    Hurst Exponent Adaptive Pairs Trading (BTC/ETH)

    Based on: "Anti-Persistent Values of the Hurst Exponent Anticipate Mean Reversion
    in Pairs Trading" (2024, Mathematics MDPI)

    Only trades when Hurst < 0.5 (spread is mean-reverting).
    """
    # Align dataframes
    common_idx = df_btc.index.intersection(df_eth.index)
    btc = df_btc.loc[common_idx, 'close'].values
    eth = df_eth.loc[common_idx, 'close'].values
    n = len(btc)

    btc_signals = np.zeros(n)
    eth_signals = np.zeros(n)

    for i in range(max(hurst_window, hedge_window) + 1, n):
        # Calculate hedge ratio (rolling OLS)
        btc_window = btc[i - hedge_window:i]
        eth_window = eth[i - hedge_window:i]

        # Simple OLS: btc = beta * eth + alpha
        beta = np.cov(btc_window, eth_window)[0, 1] / max(np.var(eth_window), 1e-10)

        # Spread
        spread_window = btc_window - beta * eth_window
        spread_now = btc[i] - beta * eth[i]

        spread_mean = np.mean(spread_window)
        spread_std = np.std(spread_window)

        if spread_std < 1e-10:
            continue

        zscore = (spread_now - spread_mean) / spread_std

        # Hurst exponent of the spread
        h = hurst_exponent(spread_window, max_lag=min(40, hedge_window // 3))

        # Only trade when Hurst < 0.5 (anti-persistent = mean-reverting)
        if h < 0.45:
            hurst_confidence = (0.45 - h) / 0.45  # Stronger when more anti-persistent

            if zscore > zscore_entry:
                # Spread too wide: short BTC, long ETH
                btc_signals[i] = -1.0 * hurst_confidence
                eth_signals[i] = beta * hurst_confidence
            elif zscore < -zscore_entry:
                # Spread too narrow: long BTC, short ETH
                btc_signals[i] = 1.0 * hurst_confidence
                eth_signals[i] = -beta * hurst_confidence
            elif abs(zscore) < zscore_exit:
                # Close position
                btc_signals[i] = 0
                eth_signals[i] = 0

    return (pd.Series(btc_signals, index=common_idx),
            pd.Series(eth_signals, index=common_idx))


# ─── STRATEGY 4: SEASONALITY OVERLAY ────────────────────────────────────────

def apply_seasonality_overlay(df: pd.DataFrame, signals: pd.Series) -> pd.Series:
    """
    Intraday Seasonality Overlay Filter

    Based on: "The crypto world trades at tea time" (2024, RQFA)
    - Best returns: 21:00-23:00 UTC
    - Worst returns: 03:00-04:00 UTC
    - Kill signals during bad hours, boost during good hours
    """
    filtered = signals.copy()
    for i, idx in enumerate(df.index):
        hour = idx.hour if hasattr(idx, 'hour') else 12

        # Kill long signals during worst hours
        if 3 <= hour <= 4:
            if filtered.iloc[i] > 0:
                filtered.iloc[i] = 0  # No longs during dead zone

        # Boost signals during best hours
        elif 21 <= hour <= 23:
            filtered.iloc[i] *= 1.3  # 30% boost during optimal window

        # Reduce during early morning (lower liquidity)
        elif 5 <= hour <= 8:
            filtered.iloc[i] *= 0.7

    return filtered


# ─── STRATEGY 5: OU OPTIMAL STOPPING PAIRS ──────────────────────────────────

def ou_optimal_stopping_pairs(df_btc: pd.DataFrame, df_eth: pd.DataFrame,
                               calibration_window: int = 500,
                               min_half_life: int = 6,
                               max_half_life: int = 72) -> Tuple[pd.Series, pd.Series]:
    """
    Ornstein-Uhlenbeck Optimal Stopping for Crypto Pairs

    Based on: Cantarutti (2025) "Considerations on the mean-reversion time"
    + Hudson & Thames arbitragelab.

    Analytically derives optimal entry/exit from OU parameters.
    """
    common_idx = df_btc.index.intersection(df_eth.index)
    btc = df_btc.loc[common_idx, 'close'].values
    eth = df_eth.loc[common_idx, 'close'].values
    n = len(btc)

    btc_signals = np.zeros(n)
    eth_signals = np.zeros(n)

    for i in range(calibration_window + 1, n):
        # Hedge ratio
        btc_w = btc[i - calibration_window:i]
        eth_w = eth[i - calibration_window:i]
        beta = np.cov(btc_w, eth_w)[0, 1] / max(np.var(eth_w), 1e-10)

        # Spread
        spread = btc_w - beta * eth_w
        spread_now = btc[i] - beta * eth[i]

        # Calibrate OU process: dS = theta*(mu - S)*dt + sigma*dW
        # Using AR(1): S_t = a + b*S_{t-1} + e
        S = spread
        S_lag = S[:-1]
        S_now = S[1:]

        if np.std(S_lag) < 1e-10:
            continue

        b = np.cov(S_now, S_lag)[0, 1] / np.var(S_lag)
        a = np.mean(S_now) - b * np.mean(S_lag)

        # OU parameters
        theta = -np.log(max(abs(b), 1e-10))  # Mean-reversion speed
        mu = a / (1 - b) if abs(1 - b) > 1e-10 else np.mean(S)  # Long-run mean
        sigma_eq = np.std(S_now - a - b * S_lag)  # Equilibrium vol

        # Half-life
        half_life = np.log(2) / max(theta, 1e-10)

        # Only trade if half-life is in acceptable range
        if half_life < min_half_life or half_life > max_half_life:
            continue

        # Optimal entry: ~2.0-2.5 sigma from mean (depends on theta)
        # Higher theta (faster reversion) → tighter entry
        optimal_entry = 1.5 + 0.5 * min(theta, 1.0)

        # Z-score
        spread_std = max(sigma_eq / np.sqrt(2 * theta), 1e-10) if theta > 0 else np.std(S)
        zscore = (spread_now - mu) / spread_std

        # Position sizing based on half-life confidence
        hl_confidence = 1.0 - (half_life - min_half_life) / (max_half_life - min_half_life)

        if abs(zscore) > optimal_entry:
            if zscore > 0:
                btc_signals[i] = -hl_confidence
                eth_signals[i] = beta * hl_confidence
            else:
                btc_signals[i] = hl_confidence
                eth_signals[i] = -beta * hl_confidence
        elif abs(zscore) < 0.5:
            btc_signals[i] = 0
            eth_signals[i] = 0

    return (pd.Series(btc_signals, index=common_idx),
            pd.Series(eth_signals, index=common_idx))


# ─── BACKTESTER ENGINE ──────────────────────────────────────────────────────

def backtest_signals(df: pd.DataFrame, signals: pd.Series,
                      tp_pct: float = 2.0, sl_pct: float = 1.5,
                      max_hold: int = 48, commission_pct: float = 0.1,
                      strategy_name: str = "Unknown") -> Dict:
    """
    Backtest with triple-barrier method (TP, SL, max hold time).
    Returns detailed performance metrics.
    """
    close = df['close'].values
    high = df['high'].values
    low = df['low'].values
    n = len(close)

    trades = []
    i = 0

    while i < n - 1:
        sig = signals.iloc[i] if i < len(signals) else 0

        if abs(sig) < 0.1:
            i += 1
            continue

        direction = 1 if sig > 0 else -1
        size = min(abs(sig), 2.0)
        entry_price = close[i]
        entry_idx = i

        tp_price = entry_price * (1 + direction * tp_pct / 100)
        sl_price = entry_price * (1 - direction * sl_pct / 100)

        # Walk forward to find exit
        exit_reason = "max_hold"
        exit_price = close[min(i + max_hold, n - 1)]
        exit_idx = min(i + max_hold, n - 1)

        for j in range(i + 1, min(i + max_hold + 1, n)):
            if direction == 1:
                if high[j] >= tp_price:
                    exit_price = tp_price
                    exit_reason = "TP"
                    exit_idx = j
                    break
                elif low[j] <= sl_price:
                    exit_price = sl_price
                    exit_reason = "SL"
                    exit_idx = j
                    break
            else:
                if low[j] <= tp_price:
                    exit_price = tp_price
                    exit_reason = "TP"
                    exit_idx = j
                    break
                elif high[j] >= sl_price:
                    exit_price = sl_price
                    exit_reason = "SL"
                    exit_idx = j
                    break

        pnl_pct = direction * (exit_price / entry_price - 1) * 100 * size
        pnl_pct -= commission_pct * 2 * size  # Entry + exit commission

        trades.append({
            'entry_time': str(df.index[entry_idx]),
            'exit_time': str(df.index[exit_idx]),
            'direction': 'LONG' if direction == 1 else 'SHORT',
            'entry_price': round(entry_price, 2),
            'exit_price': round(exit_price, 2),
            'pnl_pct': round(pnl_pct, 4),
            'exit_reason': exit_reason,
            'bars_held': exit_idx - entry_idx,
            'size': round(size, 2),
        })

        # Skip ahead past exit
        i = exit_idx + 1

    # Calculate metrics
    if not trades:
        return {
            'strategy': strategy_name,
            'total_trades': 0,
            'win_rate': 0,
            'avg_pnl': 0,
            'total_pnl': 0,
            'sharpe': 0,
            'max_drawdown': 0,
            'profit_factor': 0,
            'trades': [],
        }

    pnls = [t['pnl_pct'] for t in trades]
    wins = sum(1 for p in pnls if p > 0)
    losses = sum(1 for p in pnls if p <= 0)

    win_rate = wins / len(pnls) * 100
    avg_pnl = np.mean(pnls)
    total_pnl = sum(pnls)

    # Sharpe (annualized, assuming avg ~1 trade per day)
    if np.std(pnls) > 0:
        sharpe = (np.mean(pnls) / np.std(pnls)) * np.sqrt(365)
    else:
        sharpe = 0

    # Max drawdown
    equity = np.cumsum(pnls)
    running_max = np.maximum.accumulate(equity)
    drawdowns = equity - running_max
    max_dd = abs(min(drawdowns)) if len(drawdowns) > 0 else 0

    # Profit factor
    gross_profit = sum(p for p in pnls if p > 0)
    gross_loss = abs(sum(p for p in pnls if p <= 0))
    profit_factor = gross_profit / max(gross_loss, 1e-10)

    # Win/loss ratio
    avg_win = np.mean([p for p in pnls if p > 0]) if wins > 0 else 0
    avg_loss_val = abs(np.mean([p for p in pnls if p <= 0])) if losses > 0 else 0

    return {
        'strategy': strategy_name,
        'total_trades': len(trades),
        'win_rate': round(win_rate, 1),
        'avg_pnl': round(avg_pnl, 4),
        'total_pnl': round(total_pnl, 2),
        'sharpe': round(sharpe, 2),
        'max_drawdown': round(max_dd, 2),
        'profit_factor': round(profit_factor, 2),
        'avg_win': round(avg_win, 4),
        'avg_loss': round(avg_loss_val, 4),
        'avg_bars_held': round(np.mean([t['bars_held'] for t in trades]), 1),
        'trades': trades,
    }


def backtest_pairs(df_btc: pd.DataFrame, df_eth: pd.DataFrame,
                    btc_signals: pd.Series, eth_signals: pd.Series,
                    max_hold: int = 48, commission_pct: float = 0.1,
                    strategy_name: str = "Pairs") -> Dict:
    """Backtest pairs strategy (market-neutral)."""
    common_idx = df_btc.index.intersection(df_eth.index)
    btc = df_btc.loc[common_idx]
    eth = df_eth.loc[common_idx]

    n = len(common_idx)
    trades = []
    i = 0

    while i < n - 1:
        btc_sig = btc_signals.get(common_idx[i], 0) if common_idx[i] in btc_signals.index else 0

        if abs(btc_sig) < 0.1:
            i += 1
            continue

        eth_sig = eth_signals.get(common_idx[i], 0) if common_idx[i] in eth_signals.index else 0

        btc_entry = btc['close'].iloc[i]
        eth_entry = eth['close'].iloc[i]
        entry_idx = i

        # Hold until max_hold or signal reverses
        exit_idx = min(i + max_hold, n - 1)
        for j in range(i + 1, min(i + max_hold + 1, n)):
            future_sig = btc_signals.get(common_idx[j], 0) if j < n and common_idx[j] in btc_signals.index else 0
            if abs(future_sig) < 0.05:  # Signal closed
                exit_idx = j
                break

        btc_exit = btc['close'].iloc[exit_idx]
        eth_exit = eth['close'].iloc[exit_idx]

        # PnL from both legs
        btc_pnl = btc_sig * (btc_exit / btc_entry - 1) * 100
        eth_pnl = eth_sig * (eth_exit / eth_entry - 1) * 100
        total_pnl = btc_pnl + eth_pnl - commission_pct * 4  # 4 trades (open+close both legs)

        trades.append({
            'entry_time': str(common_idx[entry_idx]),
            'exit_time': str(common_idx[exit_idx]),
            'direction': 'LONG_SPREAD' if btc_sig > 0 else 'SHORT_SPREAD',
            'btc_entry': round(btc_entry, 2),
            'eth_entry': round(eth_entry, 2),
            'pnl_pct': round(total_pnl, 4),
            'bars_held': exit_idx - entry_idx,
        })

        i = exit_idx + 1

    if not trades:
        return {'strategy': strategy_name, 'total_trades': 0, 'win_rate': 0,
                'sharpe': 0, 'total_pnl': 0, 'trades': []}

    pnls = [t['pnl_pct'] for t in trades]
    wins = sum(1 for p in pnls if p > 0)

    return {
        'strategy': strategy_name,
        'total_trades': len(trades),
        'win_rate': round(wins / len(trades) * 100, 1),
        'avg_pnl': round(np.mean(pnls), 4),
        'total_pnl': round(sum(pnls), 2),
        'sharpe': round((np.mean(pnls) / max(np.std(pnls), 1e-10)) * np.sqrt(365), 2),
        'max_drawdown': round(abs(min(np.minimum.accumulate(np.cumsum(pnls)) - np.maximum.accumulate(np.cumsum(pnls)))), 2) if pnls else 0,
        'profit_factor': round(sum(p for p in pnls if p > 0) / max(abs(sum(p for p in pnls if p <= 0)), 1e-10), 2),
        'avg_bars_held': round(np.mean([t['bars_held'] for t in trades]), 1),
        'trades': trades,
    }


# ─── MAIN ────────────────────────────────────────────────────────────────────

def main():
    print("=" * 80)
    print("RARE STRATEGY BACKTESTER — Academically-Backed Hourly Crypto")
    print("=" * 80)

    # Fetch data
    print("\n[*] Fetching data...")
    df_btc = fetch_crypto_1h("BTC-USD", days=729)
    df_eth = fetch_crypto_1h("ETH-USD", days=729)

    results = []

    # ─── Strategy 1: HMM Regime + Vol-Scaled Momentum ───
    print("\n[*] Strategy 1: HMM Regime + Vol-Scaled Momentum...")
    signals_1 = hmm_regime_momentum(df_btc)
    result_1 = backtest_signals(df_btc, signals_1, tp_pct=3.0, sl_pct=2.0,
                                 max_hold=48, strategy_name="HMM Regime + Momentum")
    results.append(result_1)

    # With seasonality overlay
    signals_1s = apply_seasonality_overlay(df_btc, signals_1)
    result_1s = backtest_signals(df_btc, signals_1s, tp_pct=3.0, sl_pct=2.0,
                                  max_hold=48, strategy_name="HMM Regime + Momentum + Seasonality")
    results.append(result_1s)

    # ─── Strategy 2: EGARCH Vol Targeting ───
    print("[*] Strategy 2: EGARCH Vol Targeting...")
    signals_2 = egarch_vol_targeting(df_btc)
    result_2 = backtest_signals(df_btc, signals_2, tp_pct=2.5, sl_pct=1.5,
                                 max_hold=36, strategy_name="EGARCH Vol Targeting")
    results.append(result_2)

    signals_2s = apply_seasonality_overlay(df_btc, signals_2)
    result_2s = backtest_signals(df_btc, signals_2s, tp_pct=2.5, sl_pct=1.5,
                                  max_hold=36, strategy_name="EGARCH Vol Targeting + Seasonality")
    results.append(result_2s)

    # ─── Strategy 3: Hurst Exponent Pairs ───
    print("[*] Strategy 3: Hurst Exponent Pairs Trading (BTC/ETH)...")
    btc_sig3, eth_sig3 = hurst_pairs_trading(df_btc, df_eth)
    result_3 = backtest_pairs(df_btc, df_eth, btc_sig3, eth_sig3,
                               max_hold=72, strategy_name="Hurst Pairs BTC/ETH")
    results.append(result_3)

    # ─── Strategy 4: OU Optimal Stopping Pairs ───
    print("[*] Strategy 4: OU Optimal Stopping Pairs (BTC/ETH)...")
    btc_sig4, eth_sig4 = ou_optimal_stopping_pairs(df_btc, df_eth)
    result_4 = backtest_pairs(df_btc, df_eth, btc_sig4, eth_sig4,
                               max_hold=48, strategy_name="OU Optimal Stopping BTC/ETH")
    results.append(result_4)

    # ─── Strategy 5: Combined Best (HMM + EGARCH + Seasonality) ───
    print("[*] Strategy 5: Combined Ensemble (HMM + EGARCH + Seasonality)...")
    # Only enter when both HMM and EGARCH agree
    combined = pd.Series(0.0, index=df_btc.index)
    for i in range(len(df_btc)):
        s1 = signals_1s.iloc[i] if i < len(signals_1s) else 0
        s2 = signals_2s.iloc[i] if i < len(signals_2s) else 0
        if s1 * s2 > 0:  # Same direction
            combined.iloc[i] = (s1 + s2) / 2  # Average signal
        # If they disagree, no position (market-neutral caution)

    result_5 = backtest_signals(df_btc, combined, tp_pct=2.5, sl_pct=1.5,
                                 max_hold=36, strategy_name="Ensemble (HMM+EGARCH+Season)")
    results.append(result_5)

    # ─── RESULTS ───
    print("\n" + "=" * 100)
    print("BACKTEST RESULTS SUMMARY")
    print("=" * 100)
    print(f"{'Strategy':<45} {'Trades':>6} {'WR%':>6} {'AvgPnL':>8} {'TotalPnL':>10} {'Sharpe':>7} {'MaxDD':>7} {'PF':>6}")
    print("-" * 100)

    for r in sorted(results, key=lambda x: x.get('sharpe', 0), reverse=True):
        print(f"{r['strategy']:<45} {r['total_trades']:>6} {r['win_rate']:>5.1f}% "
              f"{r.get('avg_pnl', 0):>+7.3f}% {r['total_pnl']:>+9.2f}% "
              f"{r['sharpe']:>6.2f} {r.get('max_drawdown', 0):>6.2f}% "
              f"{r.get('profit_factor', 0):>5.2f}")

    # Save results
    output_path = Path("rare_strategy_results.json")
    save_data = []
    for r in results:
        save_r = {k: v for k, v in r.items() if k != 'trades'}
        save_r['trade_count'] = len(r.get('trades', []))
        save_r['first_5_trades'] = r.get('trades', [])[:5]
        save_r['last_5_trades'] = r.get('trades', [])[-5:]
        save_data.append(save_r)

    output_path.write_text(json.dumps(save_data, indent=2))
    print(f"\nResults saved to {output_path}")

    # Save full trades for best strategy
    best = max(results, key=lambda x: x.get('sharpe', 0))
    best_path = Path("rare_strategy_best_trades.json")
    best_path.write_text(json.dumps(best, indent=2))
    print(f"Best strategy ({best['strategy']}) full trades saved to {best_path}")

    return results


if __name__ == "__main__":
    main()
