#!/usr/bin/env python3
"""
Kimi Claw Elite v4 — Academic Strategy Backtester
===================================================
Implements the 5 academic strategies from the Kimi Claw Elite v4
Pine Script indicator as a rigorous Python backtester.

Strategies:
  1. Jegadeesh-Titman Cross-Sectional Momentum (JF 1993)
  2. Moskowitz-Grinblatt Time-Series Momentum / TSMOM (JFE 2012)
  3. Blitz Residual Momentum (FAJ 2011)
  4. Multi-TF Mean Reversion (composite Z-score)
  5. Volatility Breakout / VRB (compression → expansion)

Ensemble: Regime-adaptive weighted voting with:
  - VaR / CVaR risk management (95% and 99%)
  - Kelly Criterion sizing (quarter-Kelly cap at 25%)
  - Bayesian confidence scoring with regime-based priors

Usage:
  py backtest_elite_v4.py
  py backtest_elite_v4.py --symbols BTC-USD,ETH-USD --period 2y
  py backtest_elite_v4.py --no-ensemble

Requires: pandas, numpy, yfinance (ccxt as fallback)
Python 3.10+
"""

from __future__ import annotations

import argparse
import sys
import warnings
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore", category=FutureWarning)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent
ANNUALIZATION_FACTOR = 365  # crypto trades every day
TRADING_DAYS_PER_YEAR = 365
RISK_FREE_RATE = 0.045  # ~4.5% (current US T-bill rate)

DEFAULT_SYMBOLS = ["BTC-USD", "ETH-USD", "SOL-USD"]
DEFAULT_PERIOD = "2y"

# Regime-adaptive ensemble weights: [JT, TSMOM, Blitz, MeanRev, VRB]
REGIME_WEIGHTS = {
    "Trending":      [0.30, 0.30, 0.20, 0.10, 0.10],
    "MeanReverting": [0.10, 0.10, 0.15, 0.45, 0.20],
    "HighVol":       [0.20, 0.25, 0.20, 0.15, 0.20],
    "Quiet":         [0.25, 0.25, 0.25, 0.15, 0.10],
}

# Regime performance priors (used in Bayesian confidence)
REGIME_PRIORS = {
    "Trending":      [0.75, 0.70, 0.60, 0.45, 0.55],
    "MeanReverting": [0.45, 0.50, 0.50, 0.70, 0.60],
    "HighVol":       [0.55, 0.60, 0.55, 0.50, 0.65],
    "Quiet":         [0.60, 0.65, 0.60, 0.55, 0.50],
}

STRATEGY_NAMES = [
    "JT_Momentum",
    "TSMOM",
    "Blitz_Residual",
    "MeanReversion",
    "VolBreakout",
]

# Transaction costs (round-trip)
TX_COST = 0.002  # 0.2% round-trip for crypto


# ---------------------------------------------------------------------------
# Data Fetching
# ---------------------------------------------------------------------------
def fetch_data(symbol: str, period: str = "2y", interval: str = "1d") -> Optional[pd.DataFrame]:
    """Fetch OHLCV data. Try yfinance first, fall back to ccxt."""
    df = _fetch_yfinance(symbol, period, interval)
    if df is not None and len(df) >= 200:
        return df
    df = _fetch_ccxt(symbol, period)
    if df is not None and len(df) >= 200:
        return df
    return None


def _fetch_yfinance(symbol: str, period: str, interval: str) -> Optional[pd.DataFrame]:
    try:
        import yfinance as yf
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period, interval=interval, auto_adjust=True)
        if df is None or df.empty:
            return None
        df.columns = [c.lower() for c in df.columns]
        # Ensure required columns
        for col in ["open", "high", "low", "close", "volume"]:
            if col not in df.columns:
                return None
        df = df[["open", "high", "low", "close", "volume"]].copy()
        df.dropna(inplace=True)
        return df
    except Exception as e:
        print(f"  [yfinance] {symbol}: {e}")
        return None


def _fetch_ccxt(symbol: str, period: str) -> Optional[pd.DataFrame]:
    """Fallback: fetch from Binance via ccxt."""
    try:
        import ccxt
    except ImportError:
        return None

    try:
        exchange = ccxt.binance({"enableRateLimit": True})
        # Convert symbol: BTC-USD -> BTC/USDT
        base = symbol.replace("-USD", "").replace("USD", "")
        ccxt_symbol = f"{base}/USDT"

        # Parse period to determine since timestamp
        period_days = _period_to_days(period)
        since_ms = int((datetime.utcnow() - timedelta(days=period_days)).timestamp() * 1000)

        all_candles = []
        while True:
            candles = exchange.fetch_ohlcv(ccxt_symbol, "1d", since=since_ms, limit=1000)
            if not candles:
                break
            all_candles.extend(candles)
            since_ms = candles[-1][0] + 1
            if len(candles) < 1000:
                break

        if not all_candles:
            return None

        df = pd.DataFrame(all_candles, columns=["timestamp", "open", "high", "low", "close", "volume"])
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        df.set_index("timestamp", inplace=True)
        df.dropna(inplace=True)
        return df
    except Exception as e:
        print(f"  [ccxt] {symbol}: {e}")
        return None


def _period_to_days(period: str) -> int:
    period = period.lower().strip()
    if period.endswith("y"):
        return int(period[:-1]) * 365
    if period.endswith("mo"):
        return int(period[:-2]) * 30
    if period.endswith("d"):
        return int(period[:-1])
    return 730  # default 2 years


# ---------------------------------------------------------------------------
# Regime Detection
# ---------------------------------------------------------------------------
def detect_regime(df: pd.DataFrame) -> pd.Series:
    """
    Classify each bar into one of 4 regimes using ADX-like trend strength
    and volatility percentile.

    Returns a Series of regime labels aligned with df.index.
    """
    close = df["close"]
    high = df["high"]
    low = df["low"]

    # Trend detection: directional movement via EMA slope
    ema50 = close.ewm(span=50, adjust=False).mean()
    ema200 = close.ewm(span=200, adjust=False).mean()
    trend_strength = ((ema50 - ema200) / ema200).abs()
    trend_threshold = trend_strength.rolling(100, min_periods=50).quantile(0.6)

    # Volatility detection: ATR percentile
    tr = pd.concat([
        high - low,
        (high - close.shift(1)).abs(),
        (low - close.shift(1)).abs()
    ], axis=1).max(axis=1)
    atr14 = tr.rolling(14).mean()
    vol_pct = atr14.rolling(100, min_periods=50).rank(pct=True)

    # Classify
    regime = pd.Series("Quiet", index=df.index)
    regime[trend_strength > trend_threshold] = "Trending"
    regime[(trend_strength <= trend_threshold) & (vol_pct > 0.7)] = "HighVol"
    regime[(trend_strength <= trend_threshold) & (vol_pct <= 0.4)] = "MeanReverting"

    return regime


# ---------------------------------------------------------------------------
# Strategy 1: Jegadeesh-Titman Cross-Sectional Momentum
# ---------------------------------------------------------------------------
def strategy_jt_momentum(df: pd.DataFrame) -> pd.DataFrame:
    """
    Jegadeesh & Titman (1993) cross-sectional momentum.
    12-month return, skip most recent month (avoid short-term reversal).
    Long if trimmedMom > 5% AND price > SMA200.
    Short if trimmedMom < -5% AND price < SMA200.
    """
    close = df["close"].copy()
    n = len(close)

    # 12-month lookback (~252 trading days for daily), skip last ~21 days
    lookback = min(252, n - 1)
    skip = 21

    # Trimmed momentum: return from t-lookback to t-skip
    trimmed_mom = pd.Series(np.nan, index=close.index)
    for i in range(lookback, n):
        past_price = close.iloc[i - lookback]
        recent_price = close.iloc[i - skip] if i - skip >= 0 else close.iloc[0]
        if past_price > 0:
            trimmed_mom.iloc[i] = (recent_price - past_price) / past_price

    sma200 = close.rolling(200, min_periods=200).mean()

    signal = pd.Series(0.0, index=close.index)
    long_cond = (trimmed_mom > 0.05) & (close > sma200)
    short_cond = (trimmed_mom < -0.05) & (close < sma200)
    signal[long_cond] = 1.0
    signal[short_cond] = -1.0

    # Strength: clamp |trimmed_mom| to [0, 1]
    strength = trimmed_mom.abs().clip(0, 1).fillna(0)

    out = pd.DataFrame(index=df.index)
    out["signal"] = signal
    out["strength"] = strength
    return out


# ---------------------------------------------------------------------------
# Strategy 2: Moskowitz-Grinblatt TSMOM (JFE 2012)
# ---------------------------------------------------------------------------
def strategy_tsmom(df: pd.DataFrame) -> pd.DataFrame:
    """
    Time-Series Momentum (Moskowitz, Ooi, Pedersen, JFE 2012).
    Risk-adjusted momentum: returns12 / volatility12.
    Long if tsmomScore > 0.5, short if < -0.5.
    Volatility targeting: targetVol = 10% annualized.
    """
    close = df["close"].copy()
    log_ret = np.log(close / close.shift(1))

    # 12-month cumulative return
    lookback = 252
    returns12 = log_ret.rolling(lookback, min_periods=lookback).sum()

    # 12-month realized volatility (annualized)
    vol12 = log_ret.rolling(lookback, min_periods=lookback).std() * np.sqrt(ANNUALIZATION_FACTOR)

    # TSMOM score: risk-adjusted momentum
    tsmom_score = returns12 / vol12.replace(0, np.nan)

    # Volatility targeting
    target_vol = 0.10  # 10% annualized
    realized_vol = log_ret.rolling(60, min_periods=30).std() * np.sqrt(ANNUALIZATION_FACTOR)
    pos_size = (target_vol / realized_vol.replace(0, np.nan)).clip(0.1, 3.0).fillna(1.0)

    signal = pd.Series(0.0, index=close.index)
    signal[tsmom_score > 0.5] = 1.0
    signal[tsmom_score < -0.5] = -1.0

    # Strength is |tsmom_score| scaled by position size, clamped
    strength = (tsmom_score.abs() * pos_size / 3.0).clip(0, 1).fillna(0)

    out = pd.DataFrame(index=df.index)
    out["signal"] = signal
    out["strength"] = strength
    out["pos_size"] = pos_size  # kept for Kelly integration
    return out


# ---------------------------------------------------------------------------
# Strategy 3: Blitz Residual Momentum (FAJ 2011)
# ---------------------------------------------------------------------------
def strategy_blitz_residual(df: pd.DataFrame, market_df: Optional[pd.DataFrame] = None) -> pd.DataFrame:
    """
    Blitz, Huij, Martens (2011) Residual Momentum.
    Rolling 60-period beta to market (BTC).
    Residual = actual_return - beta * market_return.
    Residual momentum = SMA(residual, 12 periods).
    Long if residualMom > 0 and rising; short if < 0 and falling.
    """
    close = df["close"].copy()
    log_ret = np.log(close / close.shift(1)).fillna(0)

    # Market returns (BTC as proxy, or self if no market_df)
    if market_df is not None and len(market_df) >= len(df):
        market_close = market_df["close"].reindex(df.index, method="ffill")
        market_ret = np.log(market_close / market_close.shift(1)).fillna(0)
    else:
        # Self-reference: use equal-weight as proxy (residual = 0 mostly)
        market_ret = log_ret.copy()

    # Rolling beta (60 periods)
    window = 60
    cov_rm = log_ret.rolling(window, min_periods=window).cov(market_ret)
    var_m = market_ret.rolling(window, min_periods=window).var()
    beta = (cov_rm / var_m.replace(0, np.nan)).fillna(0).clip(-3, 3)

    # Residual return
    residual = log_ret - beta * market_ret

    # Residual momentum: SMA of residual over 12 periods
    residual_mom = residual.rolling(12, min_periods=12).mean()
    residual_mom_prev = residual_mom.shift(1)

    signal = pd.Series(0.0, index=close.index)
    rising = residual_mom > residual_mom_prev
    falling = residual_mom < residual_mom_prev
    signal[(residual_mom > 0) & rising] = 1.0
    signal[(residual_mom < 0) & falling] = -1.0

    strength = residual_mom.abs().clip(0, 0.05) / 0.05  # normalize
    strength = strength.fillna(0)

    out = pd.DataFrame(index=df.index)
    out["signal"] = signal
    out["strength"] = strength
    return out


# ---------------------------------------------------------------------------
# Strategy 4: Multi-TF Mean Reversion
# ---------------------------------------------------------------------------
def strategy_mean_reversion(df: pd.DataFrame) -> pd.DataFrame:
    """
    Multi-timeframe Z-score mean reversion.
    Z = (price - SMA20) / stdev20 on 4 simulated timeframes.
    Composite Z = weighted sum (10%-25%-35%-30% for 15m-1H-4H-D).
    Long if compositeZ < -2.0 AND price > SMA200.
    Short if compositeZ > 2.0 AND price < SMA200.

    Since we're on daily data, we simulate lower-resolution timeframes
    by using different lookback windows:
      "15m" -> 5-bar window (representing intraday noise)
      "1H"  -> 10-bar window
      "4H"  -> 20-bar window (standard)
      "D"   -> 40-bar window (weekly-scale smoothing)
    """
    close = df["close"].copy()

    # Simulated multi-TF Z-scores using different lookback windows
    tf_params = [
        (5,  0.10),   # "15m" analog
        (10, 0.25),   # "1H"  analog
        (20, 0.35),   # "4H"  analog (standard daily)
        (40, 0.30),   # "D"   analog (smoothed)
    ]

    composite_z = pd.Series(0.0, index=close.index)
    for window, weight in tf_params:
        sma = close.rolling(window, min_periods=window).mean()
        std = close.rolling(window, min_periods=window).std()
        z = ((close - sma) / std.replace(0, np.nan)).fillna(0)
        composite_z += weight * z

    sma200 = close.rolling(200, min_periods=200).mean()

    signal = pd.Series(0.0, index=close.index)
    # Mean reversion: buy when extremely oversold, sell when extremely overbought
    # Require trend filter: only long above SMA200, only short below SMA200
    long_cond = (composite_z < -2.0) & (close > sma200)
    short_cond = (composite_z > 2.0) & (close < sma200)
    signal[long_cond] = 1.0
    signal[short_cond] = -1.0

    strength = (composite_z.abs() / 4.0).clip(0, 1).fillna(0)

    out = pd.DataFrame(index=df.index)
    out["signal"] = signal
    out["strength"] = strength
    out["composite_z"] = composite_z
    return out


# ---------------------------------------------------------------------------
# Strategy 5: Volatility Breakout (VRB)
# ---------------------------------------------------------------------------
def strategy_vol_breakout(df: pd.DataFrame) -> pd.DataFrame:
    """
    Volatility Regime Breakout.
    VCI = stdev20 / stdev50 (Volatility Compression Index).
    Compression = VCI < 0.8 for 3+ consecutive bars.
    Breakout = compression ends AND normalizedRange > 1.5.
    Long if close > open; short if close < open.
    """
    close = df["close"].copy()
    high = df["high"].copy()
    low = df["low"].copy()
    opn = df["open"].copy()

    std20 = close.rolling(20, min_periods=20).std()
    std50 = close.rolling(50, min_periods=50).std()
    vci = (std20 / std50.replace(0, np.nan)).fillna(1.0)

    # Compression: VCI < 0.8
    compressed = (vci < 0.8).astype(int)
    # Count consecutive compression bars
    # Reset counter when compression breaks
    consec = pd.Series(0, index=close.index)
    for i in range(1, len(consec)):
        if compressed.iloc[i] == 1:
            consec.iloc[i] = consec.iloc[i - 1] + 1
        else:
            consec.iloc[i] = 0

    # Was compressed for 3+ bars in prior period
    was_compressed = consec.shift(1) >= 3

    # Normalized range: current bar range vs ATR14
    bar_range = high - low
    atr14 = bar_range.rolling(14, min_periods=14).mean()
    norm_range = (bar_range / atr14.replace(0, np.nan)).fillna(0)

    # Breakout: was compressed, now expanding, big range bar
    breakout = was_compressed & (vci >= 0.8) & (norm_range > 1.5)

    signal = pd.Series(0.0, index=close.index)
    signal[breakout & (close > opn)] = 1.0   # bullish breakout
    signal[breakout & (close < opn)] = -1.0  # bearish breakout

    strength = (norm_range / 3.0).clip(0, 1).fillna(0)

    out = pd.DataFrame(index=df.index)
    out["signal"] = signal
    out["strength"] = strength
    out["vci"] = vci
    return out


# ---------------------------------------------------------------------------
# Risk Management: VaR, CVaR, Kelly Criterion
# ---------------------------------------------------------------------------
def calculate_var_cvar(returns: pd.Series, confidence: float = 0.95) -> dict:
    """Calculate Value-at-Risk and Conditional VaR (Expected Shortfall)."""
    if len(returns) < 30:
        return {"VaR": 0.0, "CVaR": 0.0}
    clean = returns.dropna()
    if len(clean) < 30:
        return {"VaR": 0.0, "CVaR": 0.0}
    alpha = 1 - confidence
    var = np.percentile(clean, alpha * 100)
    cvar = clean[clean <= var].mean() if (clean <= var).any() else var
    return {"VaR": float(var), "CVaR": float(cvar)}


def kelly_criterion(win_rate: float, avg_win: float, avg_loss: float,
                    quarter_kelly: bool = True) -> float:
    """
    Kelly Criterion for position sizing.
    f* = (p * b - q) / b  where b = avg_win / |avg_loss|
    Quarter-Kelly caps at 25% of full Kelly.
    """
    if avg_loss == 0 or avg_win == 0 or win_rate <= 0:
        return 0.0
    p = win_rate
    q = 1 - p
    b = abs(avg_win / avg_loss)
    kelly = (p * b - q) / b
    kelly = max(0, kelly)
    if quarter_kelly:
        kelly = min(kelly * 0.25, 0.25)  # quarter-Kelly, max 25%
    return kelly


def bayesian_confidence(strategy_idx: int, regime: str, recent_wr: float,
                        n_trades: int) -> float:
    """
    Bayesian confidence scoring.
    Prior: regime-based expected win rate.
    Likelihood: recent observed win rate weighted by sample size.
    Posterior: weighted combination.
    """
    prior = REGIME_PRIORS.get(regime, [0.5] * 5)[strategy_idx]
    # Weight prior vs observed: more data -> trust observed more
    prior_weight = max(5, 30 - n_trades)  # pseudo-count for prior
    posterior = (prior * prior_weight + recent_wr * n_trades) / (prior_weight + n_trades)
    return float(np.clip(posterior, 0, 1))


# ---------------------------------------------------------------------------
# Ensemble Engine
# ---------------------------------------------------------------------------
def run_ensemble(strategy_signals: list[pd.DataFrame], regime: pd.Series) -> pd.DataFrame:
    """
    Combine 5 strategy signals using regime-adaptive weights.
    Uses a two-pass approach:
      1. Weighted vote: sum of weight_i * signal_i (direction only)
      2. Confidence: average strength of agreeing strategies
    Returns ensemble signal (-1 to +1) and confidence.
    """
    n = len(strategy_signals[0])
    ensemble_signal = pd.Series(0.0, index=strategy_signals[0].index)
    ensemble_confidence = pd.Series(0.0, index=strategy_signals[0].index)

    for i in range(n):
        r = regime.iloc[i]
        weights = REGIME_WEIGHTS.get(r, REGIME_WEIGHTS["Quiet"])

        # Weighted directional vote (signal is -1, 0, or +1)
        vote = 0.0
        active_weight = 0.0
        avg_strength = 0.0
        n_active = 0
        for j, sig_df in enumerate(strategy_signals):
            s = sig_df["signal"].iloc[i]
            st = sig_df["strength"].iloc[i]
            if s != 0:
                vote += weights[j] * s
                active_weight += weights[j]
                avg_strength += st
                n_active += 1

        if active_weight > 0:
            # Normalize vote by active weight so partial participation scales properly
            normalized_vote = vote / active_weight
            ensemble_signal.iloc[i] = np.clip(normalized_vote, -1, 1)
            ensemble_confidence.iloc[i] = avg_strength / n_active if n_active > 0 else 0.0
        else:
            ensemble_signal.iloc[i] = 0.0
            ensemble_confidence.iloc[i] = 0.0

    out = pd.DataFrame(index=strategy_signals[0].index)
    out["signal"] = ensemble_signal
    out["confidence"] = ensemble_confidence
    out["regime"] = regime
    return out


# ---------------------------------------------------------------------------
# Backtesting Engine
# ---------------------------------------------------------------------------
class BacktestResult:
    """Container for backtest metrics."""

    def __init__(self, name: str):
        self.name = name
        self.trades: list[dict] = []
        self.equity_curve: list[float] = []
        self.returns: list[float] = []

    @property
    def n_trades(self) -> int:
        return len(self.trades)

    @property
    def n_wins(self) -> int:
        return sum(1 for t in self.trades if t["pnl"] > 0)

    @property
    def n_losses(self) -> int:
        return sum(1 for t in self.trades if t["pnl"] <= 0)

    @property
    def win_rate(self) -> float:
        return self.n_wins / max(1, self.n_trades) * 100

    @property
    def avg_win(self) -> float:
        wins = [t["pnl"] for t in self.trades if t["pnl"] > 0]
        return np.mean(wins) if wins else 0.0

    @property
    def avg_loss(self) -> float:
        losses = [t["pnl"] for t in self.trades if t["pnl"] <= 0]
        return np.mean(losses) if losses else 0.0

    @property
    def total_return(self) -> float:
        if not self.equity_curve or self.equity_curve[0] == 0:
            return 0.0
        return (self.equity_curve[-1] / self.equity_curve[0] - 1) * 100

    @property
    def sharpe_ratio(self) -> float:
        if not self.returns:
            return 0.0
        rets = np.array(self.returns)
        if rets.std() == 0:
            return 0.0
        excess = rets.mean() - RISK_FREE_RATE / ANNUALIZATION_FACTOR
        return float(excess / rets.std() * np.sqrt(ANNUALIZATION_FACTOR))

    @property
    def max_drawdown(self) -> float:
        if not self.equity_curve:
            return 0.0
        peak = self.equity_curve[0]
        max_dd = 0.0
        for v in self.equity_curve:
            if v > peak:
                peak = v
            dd = (peak - v) / peak if peak > 0 else 0
            max_dd = max(max_dd, dd)
        return max_dd * 100

    @property
    def profit_factor(self) -> float:
        gross_wins = sum(t["pnl"] for t in self.trades if t["pnl"] > 0)
        gross_losses = abs(sum(t["pnl"] for t in self.trades if t["pnl"] <= 0))
        if gross_losses == 0:
            return float("inf") if gross_wins > 0 else 0.0
        return gross_wins / gross_losses

    @property
    def calmar_ratio(self) -> float:
        if self.max_drawdown == 0:
            return 0.0
        # Annualized return / max drawdown
        n_days = len(self.equity_curve)
        if n_days <= 1 or self.equity_curve[0] == 0:
            return 0.0
        total = self.equity_curve[-1] / self.equity_curve[0] - 1
        ann = total * (ANNUALIZATION_FACTOR / n_days)
        return ann * 100 / self.max_drawdown

    def var_cvar(self, confidence: float = 0.95) -> dict:
        return calculate_var_cvar(pd.Series(self.returns), confidence)

    def kelly_size(self) -> float:
        return kelly_criterion(self.win_rate / 100, self.avg_win, self.avg_loss)


def backtest_signal(df: pd.DataFrame, signals: pd.DataFrame, name: str,
                    initial_capital: float = 10000.0,
                    stop_loss: float = -0.08,
                    take_profit: float = 0.15,
                    max_hold: int = 30) -> BacktestResult:
    """
    Event-driven backtester with stop-loss, take-profit, and max hold period.
    """
    result = BacktestResult(name)
    close = df["close"].values
    high = df["high"].values
    low = df["low"].values
    sig = signals["signal"].values
    n = len(close)

    capital = initial_capital
    position = 0  # 1=long, -1=short, 0=flat
    entry_price = 0.0
    entry_idx = 0
    bars_held = 0

    result.equity_curve.append(capital)

    for i in range(1, n):
        daily_ret = 0.0

        if position != 0:
            bars_held += 1
            # Calculate unrealized P&L
            if position == 1:
                pnl_pct = (close[i] - entry_price) / entry_price
                # Check intrabar stop/TP
                intrabar_low_pnl = (low[i] - entry_price) / entry_price
                intrabar_high_pnl = (high[i] - entry_price) / entry_price
            else:  # short
                pnl_pct = (entry_price - close[i]) / entry_price
                intrabar_low_pnl = (entry_price - high[i]) / entry_price
                intrabar_high_pnl = (entry_price - low[i]) / entry_price

            # Check stop-loss (intrabar)
            if intrabar_low_pnl <= stop_loss:
                daily_ret = stop_loss - TX_COST
                result.trades.append({
                    "entry_idx": entry_idx, "exit_idx": i,
                    "direction": "LONG" if position == 1 else "SHORT",
                    "entry_price": entry_price, "exit_price": close[i],
                    "pnl": daily_ret, "bars_held": bars_held, "exit_reason": "STOP"
                })
                capital *= (1 + daily_ret)
                position = 0

            # Check take-profit (intrabar)
            elif intrabar_high_pnl >= take_profit:
                daily_ret = take_profit - TX_COST
                result.trades.append({
                    "entry_idx": entry_idx, "exit_idx": i,
                    "direction": "LONG" if position == 1 else "SHORT",
                    "entry_price": entry_price, "exit_price": close[i],
                    "pnl": daily_ret, "bars_held": bars_held, "exit_reason": "TP"
                })
                capital *= (1 + daily_ret)
                position = 0

            # Check max hold
            elif bars_held >= max_hold:
                daily_ret = pnl_pct - TX_COST
                result.trades.append({
                    "entry_idx": entry_idx, "exit_idx": i,
                    "direction": "LONG" if position == 1 else "SHORT",
                    "entry_price": entry_price, "exit_price": close[i],
                    "pnl": daily_ret, "bars_held": bars_held, "exit_reason": "MAX_HOLD"
                })
                capital *= (1 + daily_ret)
                position = 0

            # Check signal reversal
            elif sig[i] != 0 and sig[i] != position:
                daily_ret = pnl_pct - TX_COST
                result.trades.append({
                    "entry_idx": entry_idx, "exit_idx": i,
                    "direction": "LONG" if position == 1 else "SHORT",
                    "entry_price": entry_price, "exit_price": close[i],
                    "pnl": daily_ret, "bars_held": bars_held, "exit_reason": "REVERSAL"
                })
                capital *= (1 + daily_ret)
                position = 0
            else:
                # Still in position, mark-to-market
                if position == 1:
                    daily_ret = (close[i] - close[i - 1]) / close[i - 1]
                else:
                    daily_ret = (close[i - 1] - close[i]) / close[i - 1]

        # Enter new position if flat and signal present
        if position == 0 and sig[i] != 0:
            position = int(sig[i])
            entry_price = close[i]
            entry_idx = i
            bars_held = 0
            capital *= (1 - TX_COST / 2)  # entry cost

        result.returns.append(daily_ret)
        result.equity_curve.append(capital)

    # Close any remaining position
    if position != 0:
        if position == 1:
            pnl_pct = (close[-1] - entry_price) / entry_price
        else:
            pnl_pct = (entry_price - close[-1]) / entry_price
        daily_ret = pnl_pct - TX_COST
        result.trades.append({
            "entry_idx": entry_idx, "exit_idx": n - 1,
            "direction": "LONG" if position == 1 else "SHORT",
            "entry_price": entry_price, "exit_price": close[-1],
            "pnl": daily_ret, "bars_held": bars_held, "exit_reason": "END"
        })
        capital *= (1 + daily_ret)
        result.equity_curve[-1] = capital

    return result


# ---------------------------------------------------------------------------
# Display & Reporting
# ---------------------------------------------------------------------------
def print_header(text: str):
    w = 80
    print("\n" + "=" * w)
    print(f"  {text}")
    print("=" * w)


def print_strategy_results(results: dict[str, BacktestResult], symbol: str):
    """Print formatted results table for all strategies on a symbol."""
    print(f"\n{'Strategy':<20} {'Trades':>7} {'WinRate':>8} {'Sharpe':>7} "
          f"{'MaxDD':>7} {'Return':>8} {'PF':>6} {'Kelly':>6} {'VaR95':>8} {'CVaR95':>8}")
    print("-" * 105)

    for name, res in results.items():
        var_cvar = res.var_cvar(0.95)
        kelly = res.kelly_size()
        pf_str = f"{res.profit_factor:.2f}" if res.profit_factor != float("inf") else "Inf"
        print(f"{name:<20} {res.n_trades:>7d} {res.win_rate:>7.1f}% {res.sharpe_ratio:>7.2f} "
              f"{res.max_drawdown:>6.1f}% {res.total_return:>7.1f}% {pf_str:>6} "
              f"{kelly:>5.1f}% {var_cvar['VaR']:>7.4f} {var_cvar['CVaR']:>7.4f}")


def print_regime_distribution(regime: pd.Series):
    """Print regime distribution summary."""
    counts = regime.value_counts()
    total = len(regime)
    print(f"\n  Regime Distribution:")
    for r in ["Trending", "MeanReverting", "HighVol", "Quiet"]:
        n = counts.get(r, 0)
        pct = n / total * 100
        bar = "#" * int(pct / 2)
        print(f"    {r:<15} {n:>5} bars ({pct:>5.1f}%) {bar}")


def print_risk_report(result: BacktestResult):
    """Print detailed risk metrics."""
    var95 = result.var_cvar(0.95)
    var99 = result.var_cvar(0.99)
    kelly = result.kelly_size()

    print(f"\n  Risk Report for {result.name}:")
    print(f"    VaR  95%: {var95['VaR']:.4f}  |  CVaR 95%: {var95['CVaR']:.4f}")
    print(f"    VaR  99%: {var99['VaR']:.4f}  |  CVaR 99%: {var99['CVaR']:.4f}")
    print(f"    Kelly Criterion (quarter): {kelly:.1f}%")
    print(f"    Calmar Ratio: {result.calmar_ratio:.2f}")


def print_grand_summary(all_results: dict[str, dict[str, BacktestResult]]):
    """Print cross-symbol aggregated summary."""
    print_header("GRAND SUMMARY — Cross-Symbol Aggregation")

    # Aggregate by strategy
    strat_metrics = {}
    for strat_name in STRATEGY_NAMES + ["Ensemble"]:
        all_trades = []
        all_sharpes = []
        all_returns = []
        all_drawdowns = []
        for symbol, results in all_results.items():
            if strat_name in results:
                res = results[strat_name]
                all_trades.extend(res.trades)
                all_sharpes.append(res.sharpe_ratio)
                all_returns.append(res.total_return)
                all_drawdowns.append(res.max_drawdown)
        if not all_trades:
            continue
        n_wins = sum(1 for t in all_trades if t["pnl"] > 0)
        wr = n_wins / max(1, len(all_trades)) * 100
        strat_metrics[strat_name] = {
            "trades": len(all_trades),
            "win_rate": wr,
            "avg_sharpe": np.mean(all_sharpes),
            "avg_return": np.mean(all_returns),
            "avg_maxdd": np.mean(all_drawdowns),
        }

    print(f"\n{'Strategy':<20} {'TotalTrades':>12} {'AvgWR':>8} {'AvgSharpe':>10} "
          f"{'AvgReturn':>10} {'AvgMaxDD':>10}")
    print("-" * 80)
    for name, m in strat_metrics.items():
        marker = " <<<" if name == "Ensemble" else ""
        print(f"{name:<20} {m['trades']:>12d} {m['win_rate']:>7.1f}% "
              f"{m['avg_sharpe']:>10.2f} {m['avg_return']:>9.1f}% "
              f"{m['avg_maxdd']:>9.1f}%{marker}")

    # Best strategy
    if strat_metrics:
        best = max(strat_metrics.items(), key=lambda x: x[1]["avg_sharpe"])
        print(f"\n  Best strategy by Sharpe: {best[0]} (avg Sharpe {best[1]['avg_sharpe']:.2f})")


def print_bayesian_report(strategy_signals: list[pd.DataFrame], regime: pd.Series,
                          results: dict[str, BacktestResult]):
    """Print Bayesian confidence scores per strategy per regime."""
    print(f"\n  Bayesian Confidence Scores (posterior win-rate estimates):")
    print(f"  {'Strategy':<20} {'Trending':>10} {'MeanRev':>10} {'HighVol':>10} {'Quiet':>10}")
    print(f"  {'-'*60}")
    for j, name in enumerate(STRATEGY_NAMES):
        if name not in results:
            continue
        res = results[name]
        confs = []
        for r in ["Trending", "MeanReverting", "HighVol", "Quiet"]:
            conf = bayesian_confidence(j, r, res.win_rate / 100, res.n_trades)
            confs.append(f"{conf*100:.1f}%")
        print(f"  {name:<20} {confs[0]:>10} {confs[1]:>10} {confs[2]:>10} {confs[3]:>10}")


# ---------------------------------------------------------------------------
# Main Orchestrator
# ---------------------------------------------------------------------------
def run_backtest(symbols: list[str], period: str = "2y",
                 run_ensemble_flag: bool = True) -> dict[str, dict[str, BacktestResult]]:
    """Run full backtest pipeline across all symbols."""
    all_results: dict[str, dict[str, BacktestResult]] = {}

    # Fetch BTC as market proxy for Blitz residual
    print("\n  Fetching BTC-USD as market proxy for residual momentum...")
    btc_df = fetch_data("BTC-USD", period)
    if btc_df is None:
        print("  WARNING: Could not fetch BTC data. Blitz residual will use self-reference.")

    for symbol in symbols:
        print_header(f"BACKTESTING: {symbol}")

        # Fetch data
        print(f"  Fetching {symbol} ({period} daily)...")
        df = fetch_data(symbol, period)
        if df is None:
            print(f"  SKIP: Could not fetch data for {symbol}")
            continue
        print(f"  Loaded {len(df)} bars: {df.index[0].strftime('%Y-%m-%d')} to {df.index[-1].strftime('%Y-%m-%d')}")

        # Detect regime
        regime = detect_regime(df)
        print_regime_distribution(regime)

        # Run all 5 strategies
        print(f"\n  Running strategies...")
        strat_funcs = [
            ("JT_Momentum",     lambda d: strategy_jt_momentum(d)),
            ("TSMOM",           lambda d: strategy_tsmom(d)),
            ("Blitz_Residual",  lambda d: strategy_blitz_residual(d, btc_df)),
            ("MeanReversion",   lambda d: strategy_mean_reversion(d)),
            ("VolBreakout",     lambda d: strategy_vol_breakout(d)),
        ]

        strategy_signals = []
        symbol_results = {}

        for sname, sfunc in strat_funcs:
            sig_df = sfunc(df)
            strategy_signals.append(sig_df)

            # Backtest individual strategy
            res = backtest_signal(df, sig_df, sname)
            symbol_results[sname] = res
            n_long = sum(1 for t in res.trades if t["direction"] == "LONG")
            n_short = sum(1 for t in res.trades if t["direction"] == "SHORT")
            print(f"    {sname:<20} -> {res.n_trades:>3} trades "
                  f"(L:{n_long} S:{n_short}), WR: {res.win_rate:.1f}%, "
                  f"Sharpe: {res.sharpe_ratio:.2f}")

        # Ensemble
        if run_ensemble_flag:
            ens_df = run_ensemble(strategy_signals, regime)
            ens_sig = pd.DataFrame(index=df.index)
            # Threshold ensemble signal for discrete position
            # Use moderate threshold: majority of active strategies must agree
            ens_sig["signal"] = 0.0
            ens_sig.loc[ens_df["signal"] > 0.3, "signal"] = 1.0
            ens_sig.loc[ens_df["signal"] < -0.3, "signal"] = -1.0
            ens_sig["strength"] = ens_df["confidence"]

            ens_result = backtest_signal(df, ens_sig, "Ensemble")
            symbol_results["Ensemble"] = ens_result
            n_long = sum(1 for t in ens_result.trades if t["direction"] == "LONG")
            n_short = sum(1 for t in ens_result.trades if t["direction"] == "SHORT")
            print(f"    {'Ensemble':<20} -> {ens_result.n_trades:>3} trades "
                  f"(L:{n_long} S:{n_short}), WR: {ens_result.win_rate:.1f}%, "
                  f"Sharpe: {ens_result.sharpe_ratio:.2f}")

        # Print results table
        print_strategy_results(symbol_results, symbol)

        # Print risk reports for ensemble
        if "Ensemble" in symbol_results:
            print_risk_report(symbol_results["Ensemble"])

        # Bayesian confidence
        print_bayesian_report(strategy_signals, regime, symbol_results)

        all_results[symbol] = symbol_results

    return all_results


# ---------------------------------------------------------------------------
# Entry Point
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description="Kimi Claw Elite v4 — Academic Strategy Backtester"
    )
    parser.add_argument(
        "--symbols", type=str, default=",".join(DEFAULT_SYMBOLS),
        help="Comma-separated symbols (default: BTC-USD,ETH-USD,SOL-USD)"
    )
    parser.add_argument(
        "--period", type=str, default=DEFAULT_PERIOD,
        help="Data period (default: 2y)"
    )
    parser.add_argument(
        "--no-ensemble", action="store_true",
        help="Skip ensemble voting (run individual strategies only)"
    )
    args = parser.parse_args()

    symbols = [s.strip() for s in args.symbols.split(",")]

    print_header("Kimi Claw Elite v4 — Academic Strategy Backtester")
    print(f"""
  Strategies:
    1. Jegadeesh-Titman Cross-Sectional Momentum  (JF 1993)
    2. Moskowitz-Grinblatt Time-Series Momentum    (JFE 2012)
    3. Blitz Residual Momentum                     (FAJ 2011)
    4. Multi-TF Mean Reversion (composite Z-score)
    5. Volatility Regime Breakout (VRB)

  Symbols:  {', '.join(symbols)}
  Period:   {args.period}
  Ensemble: {'ON (regime-adaptive weights)' if not args.no_ensemble else 'OFF'}
  Risk:     VaR/CVaR (95%/99%) + Kelly Criterion (quarter-Kelly)
  Costs:    {TX_COST*100:.1f}% round-trip
""")

    all_results = run_backtest(symbols, args.period, not args.no_ensemble)

    if all_results:
        print_grand_summary(all_results)

    print("\n  Done.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
