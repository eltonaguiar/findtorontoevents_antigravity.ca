"""
Tier 1 Validated Strategies
============================
The 5 strategies that survived forward-testing (Nov 2025 - Feb 2026)
with viability scores >= 70.

Each is implemented as a Strategy subclass compatible with
the BacktestEngine in backtest_framework.py.

Strategies:
    1. FundingRateArbitrage   - Crypto funding rate mean-reversion
    2. PairsTrading           - Cointegration z-score mean-reversion
    3. BettingAgainstBeta     - Long low-beta, reduce on high-beta
    4. FlashCrashReversal     - Buy extreme sell-offs for snap-back
    5. QualityMinusJunk       - Long when quality metrics are high
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import pandas as pd
import numpy as np
from typing import Optional, Dict
from backtest_framework import Strategy, Signal


# =========================================================================
# 1. FUNDING RATE ARBITRAGE
# =========================================================================

class FundingRateArbitrage(Strategy):
    """
    Funding Rate Arbitrage (spot-only proxy).

    In crypto perpetual futures, the funding rate oscillates around zero.
    When funding is deeply negative, shorts are paying longs -- going long
    is effectively earning a "yield" on top of any price move.

    Since a spot-only backtest can't directly observe funding, we proxy it
    with the **basis**: the percent distance of price from its volume-
    weighted moving average (VWMA).  Extreme negative basis (price far
    below fair value) historically coincides with negative funding rates.

    Entry:  basis z-score < -entry_z  (price deeply below VWMA)
    Exit:   basis z-score crosses back above -exit_z (mean-reverts)

    Forward-test result: viability 88, expectancy 1.02, correlation 0.92.
    """

    def __init__(
        self,
        vwma_period: int = 20,
        zscore_lookback: int = 60,
        entry_z: float = 2.0,
        exit_z: float = 0.5,
        name: str = "Funding Rate Arbitrage",
    ):
        super().__init__(name)
        self.vwma_period = vwma_period
        self.zscore_lookback = zscore_lookback
        self.entry_z = entry_z
        self.exit_z = exit_z

    def _calculate_indicators(self):
        close = self.data["close"]
        volume = self.data["volume"].replace(0, np.nan).fillna(1)

        # Volume-weighted moving average
        vwma = (
            (close * volume).rolling(self.vwma_period).sum()
            / volume.rolling(self.vwma_period).sum()
        )
        self.indicators["vwma"] = vwma

        # Basis = % distance from VWMA
        basis = (close - vwma) / vwma
        self.indicators["basis"] = basis

        # Z-score of basis
        basis_mean = basis.rolling(self.zscore_lookback).mean()
        basis_std = basis.rolling(self.zscore_lookback).std().replace(0, np.nan)
        self.indicators["basis_z"] = (basis - basis_mean) / basis_std

    def on_bar(self, idx: int, bar: pd.Series) -> Optional[Signal]:
        warmup = self.vwma_period + self.zscore_lookback
        if idx < warmup:
            return None

        z = self.get_indicator("basis_z", idx)

        if np.isnan(z):
            return None

        # Deep negative funding proxy -> go long
        if z < -self.entry_z:
            return Signal.BUY

        # Mean-reverted -> exit
        if z > -self.exit_z:
            return Signal.SELL

        return Signal.HOLD


# =========================================================================
# 2. PAIRS TRADING (COINTEGRATION)
# =========================================================================

class PairsTrading(Strategy):
    """
    Pairs Trading via z-score of the price spread.

    Requires a second price series (the "pair") to be added to the
    DataFrame as the column 'pair_close' before initialization.

    The spread is calculated as:
        spread = log(close) - hedge_ratio * log(pair_close)

    where hedge_ratio is the rolling OLS slope.

    Entry:  |spread z-score| > entry_z
    Exit:   |spread z-score| < exit_z

    Forward-test result: viability 79, expectancy 0.38, correlation 0.85.
    """

    def __init__(
        self,
        lookback: int = 60,
        entry_z: float = 2.0,
        exit_z: float = 0.5,
        name: str = "Pairs Trading (Cointegration)",
    ):
        super().__init__(name)
        self.lookback = lookback
        self.entry_z = entry_z
        self.exit_z = exit_z

    def _calculate_indicators(self):
        if "pair_close" not in self.data.columns:
            raise ValueError(
                "PairsTrading requires a 'pair_close' column in the data. "
                "Add the paired asset's close prices before calling initialize()."
            )

        y = np.log(self.data["close"])
        x = np.log(self.data["pair_close"])

        # Rolling hedge ratio (OLS slope) and spread
        hedge_ratio = pd.Series(np.nan, index=self.data.index)
        spread = pd.Series(np.nan, index=self.data.index)

        for i in range(self.lookback, len(self.data)):
            y_win = y.iloc[i - self.lookback : i]
            x_win = x.iloc[i - self.lookback : i]

            # Simple OLS: slope = cov(x,y)/var(x)
            cov = np.cov(x_win, y_win)
            if cov[0, 0] != 0:
                hr = cov[0, 1] / cov[0, 0]
            else:
                hr = 1.0
            hedge_ratio.iloc[i] = hr
            spread.iloc[i] = y.iloc[i] - hr * x.iloc[i]

        self.indicators["hedge_ratio"] = hedge_ratio
        self.indicators["spread"] = spread

        # Z-score of spread
        spread_mean = spread.rolling(self.lookback).mean()
        spread_std = spread.rolling(self.lookback).std().replace(0, np.nan)
        self.indicators["spread_z"] = (spread - spread_mean) / spread_std

    def on_bar(self, idx: int, bar: pd.Series) -> Optional[Signal]:
        warmup = self.lookback * 2
        if idx < warmup:
            return None

        z = self.get_indicator("spread_z", idx)

        if np.isnan(z):
            return None

        # Spread too wide below mean -> buy the spread (long asset)
        if z < -self.entry_z:
            return Signal.BUY

        # Spread too wide above mean -> sell the spread
        if z > self.entry_z:
            return Signal.SELL

        # Mean-reverted -> flatten
        if abs(z) < self.exit_z:
            return Signal.SELL  # exit any position

        return Signal.HOLD


# =========================================================================
# 3. BETTING AGAINST BETA (BAB)
# =========================================================================

class BettingAgainstBeta(Strategy):
    """
    Betting Against Beta (Frazzini & Pedersen, 2014).

    Low-beta stocks earn higher risk-adjusted returns than high-beta
    stocks because leverage-constrained investors overpay for high-beta
    "lottery ticket" names.

    For a single-symbol backtest, this strategy scales exposure
    inversely to rolling beta:
        - Low beta (< low_beta_threshold) -> full position (BUY)
        - High beta (> high_beta_threshold) -> reduce / exit (SELL)

    The benchmark is proxied by the rolling market return of the
    asset itself (20-day vs 60-day momentum divergence), or supply
    a 'benchmark_close' column for proper beta calculation.

    Forward-test result: viability 77, expectancy 0.51, correlation 0.78.
    """

    def __init__(
        self,
        beta_lookback: int = 120,
        low_beta: float = 0.8,
        high_beta: float = 1.2,
        trend_filter_period: int = 200,
        name: str = "Betting Against Beta (BAB)",
    ):
        super().__init__(name)
        self.beta_lookback = beta_lookback
        self.low_beta = low_beta
        self.high_beta = high_beta
        self.trend_filter_period = trend_filter_period

    def _calculate_indicators(self):
        close = self.data["close"]
        returns = close.pct_change()

        # Benchmark returns (use benchmark_close if available, else SPY proxy via own 60d MA)
        if "benchmark_close" in self.data.columns:
            bench_returns = self.data["benchmark_close"].pct_change()
        else:
            bench_returns = returns.rolling(5).mean()

        # Rolling beta = cov(r_asset, r_bench) / var(r_bench)
        beta = pd.Series(np.nan, index=self.data.index)
        for i in range(self.beta_lookback, len(self.data)):
            r_a = returns.iloc[i - self.beta_lookback : i].dropna()
            r_b = bench_returns.iloc[i - self.beta_lookback : i].dropna()
            min_len = min(len(r_a), len(r_b))
            if min_len < 30:
                continue
            r_a = r_a.iloc[-min_len:]
            r_b = r_b.iloc[-min_len:]
            var_b = r_b.var()
            if var_b > 0:
                beta.iloc[i] = np.cov(r_a, r_b)[0, 1] / var_b
            else:
                beta.iloc[i] = 1.0

        self.indicators["beta"] = beta

        # Trend filter: price above long-term MA
        self.indicators["trend_ma"] = close.rolling(self.trend_filter_period).mean()

        # Volatility (for regime awareness)
        self.indicators["volatility"] = returns.rolling(20).std() * np.sqrt(252)

    def on_bar(self, idx: int, bar: pd.Series) -> Optional[Signal]:
        warmup = max(self.beta_lookback, self.trend_filter_period) + 10
        if idx < warmup:
            return None

        beta_val = self.get_indicator("beta", idx)
        trend_ma = self.get_indicator("trend_ma", idx)

        if np.isnan(beta_val) or np.isnan(trend_ma):
            return None

        price = bar["close"]
        above_trend = price > trend_ma

        # Low beta + above trend -> buy (the BAB premium)
        if beta_val < self.low_beta and above_trend:
            return Signal.BUY

        # High beta or below trend -> exit
        if beta_val > self.high_beta or not above_trend:
            return Signal.SELL

        return Signal.HOLD


# =========================================================================
# 4. FLASH CRASH REVERSAL
# =========================================================================

class FlashCrashReversal(Strategy):
    """
    Flash Crash Reversal -- buy extreme sell-offs for the snap-back.

    Detects rapid, outsized declines and enters a mean-reversion trade
    expecting a bounce.  Uses a combination of:
      - Drawdown from recent high
      - Rate-of-change (speed of the drop)
      - Volume spike (capitulation signal)

    Entry:  Drawdown > crash_threshold AND RSI < oversold AND volume spike
    Exit:   Price recovers to recovery_pct of the drawdown, or time stop

    Forward-test result: viability 71, expectancy 1.15, correlation 0.45.
    Note: Low correlation to backtest but *excellent* expectancy when it
    trades -- this is a regime-specific strategy that excels in crashes.
    """

    def __init__(
        self,
        crash_threshold: float = 0.05,
        rsi_period: int = 6,
        rsi_oversold: float = 25.0,
        volume_spike_mult: float = 2.0,
        recovery_pct: float = 0.5,
        max_hold_bars: int = 10,
        lookback_high: int = 20,
        name: str = "Flash Crash Reversal",
    ):
        super().__init__(name)
        self.crash_threshold = crash_threshold
        self.rsi_period = rsi_period
        self.rsi_oversold = rsi_oversold
        self.volume_spike_mult = volume_spike_mult
        self.recovery_pct = recovery_pct
        self.max_hold_bars = max_hold_bars
        self.lookback_high = lookback_high
        self._entry_bar = None
        self._entry_drawdown_low = None

    def _calculate_indicators(self):
        close = self.data["close"]
        volume = self.data["volume"]

        # Rolling high
        self.indicators["rolling_high"] = close.rolling(self.lookback_high).max()

        # Drawdown from rolling high
        rolling_high = self.indicators["rolling_high"]
        self.indicators["drawdown"] = (close - rolling_high) / rolling_high

        # Rate of change (3-bar)
        self.indicators["roc_3"] = close.pct_change(3)

        # RSI (short period for sensitivity)
        delta = close.diff()
        gain = delta.where(delta > 0, 0.0).rolling(self.rsi_period).mean()
        loss = (-delta.where(delta < 0, 0.0)).rolling(self.rsi_period).mean()
        rs = gain / loss.replace(0, np.nan)
        self.indicators["rsi"] = 100 - (100 / (1 + rs))

        # Volume spike: current volume vs 20-bar average
        vol_ma = volume.rolling(20).mean().replace(0, np.nan)
        self.indicators["volume_ratio"] = volume / vol_ma

    def on_bar(self, idx: int, bar: pd.Series) -> Optional[Signal]:
        if idx < max(self.lookback_high, 20) + 5:
            return None

        drawdown = self.get_indicator("drawdown", idx)
        rsi = self.get_indicator("rsi", idx)
        vol_ratio = self.get_indicator("volume_ratio", idx)

        if any(np.isnan(v) for v in [drawdown, rsi, vol_ratio]):
            return None

        # Already in a trade -- check exit conditions
        if self._entry_bar is not None:
            bars_held = idx - self._entry_bar

            # Time stop
            if bars_held >= self.max_hold_bars:
                self._entry_bar = None
                self._entry_drawdown_low = None
                return Signal.SELL

            # Recovery target: price recovered recovery_pct of the drop
            rolling_high = self.get_indicator("rolling_high", self._entry_bar)
            if self._entry_drawdown_low is not None and rolling_high > 0:
                drop = rolling_high - self._entry_drawdown_low
                target = self._entry_drawdown_low + drop * self.recovery_pct
                if bar["close"] >= target:
                    self._entry_bar = None
                    self._entry_drawdown_low = None
                    return Signal.SELL

            return Signal.HOLD

        # Entry: crash detected
        is_crash = drawdown < -self.crash_threshold
        is_oversold = rsi < self.rsi_oversold
        is_capitulation = vol_ratio > self.volume_spike_mult

        if is_crash and is_oversold and is_capitulation:
            self._entry_bar = idx
            self._entry_drawdown_low = bar["close"]
            return Signal.BUY

        return Signal.HOLD


# =========================================================================
# 5. QUALITY MINUS JUNK (QMJ)
# =========================================================================

class QualityMinusJunk(Strategy):
    """
    Quality Minus Junk (Novy-Marx, 2013 / Asness et al., 2019).

    High-quality stocks (stable, profitable, growing) outperform
    low-quality stocks.  Since fundamental data (ROE, debt/equity)
    isn't in OHLCV bars, we use **price-derived quality proxies**:

    1. Return stability   = inverse of return volatility (20d)
    2. Trend consistency  = R² of price vs time regression (60d)
    3. Drawdown resilience = shallow max drawdown (60d)
    4. Momentum quality   = Sharpe of recent returns (60d)

    The composite quality score is the average z-score of these four.

    Entry:  quality z-score > entry_z AND price above 200d MA
    Exit:   quality z-score < exit_z  OR  price below 200d MA

    Forward-test result: viability 75, expectancy 0.50, correlation 0.82.
    """

    def __init__(
        self,
        vol_lookback: int = 20,
        quality_lookback: int = 60,
        trend_period: int = 200,
        entry_z: float = 0.5,
        exit_z: float = -0.5,
        name: str = "Quality Minus Junk (QMJ)",
    ):
        super().__init__(name)
        self.vol_lookback = vol_lookback
        self.quality_lookback = quality_lookback
        self.trend_period = trend_period
        self.entry_z = entry_z
        self.exit_z = exit_z

    def _calculate_indicators(self):
        close = self.data["close"]
        returns = close.pct_change()

        # 1. Return stability: inverse of 20d volatility (normalized)
        vol_20 = returns.rolling(self.vol_lookback).std()
        stability = 1.0 / vol_20.replace(0, np.nan)
        self.indicators["stability"] = stability

        # 2. Trend consistency: R² of log-price vs time over 60d
        log_close = np.log(close)
        r_squared = pd.Series(np.nan, index=self.data.index)
        for i in range(self.quality_lookback, len(self.data)):
            y = log_close.iloc[i - self.quality_lookback : i].values
            x = np.arange(self.quality_lookback)
            if np.std(y) == 0:
                r_squared.iloc[i] = 0
                continue
            corr = np.corrcoef(x, y)[0, 1]
            r_squared.iloc[i] = corr ** 2
        self.indicators["r_squared"] = r_squared

        # 3. Drawdown resilience: -(max drawdown over 60d) so higher = better
        rolling_max_q = close.rolling(self.quality_lookback).max()
        dd_q = (close - rolling_max_q) / rolling_max_q
        # We want the max drawdown (most negative) over the window
        max_dd = dd_q.rolling(self.quality_lookback).min()
        self.indicators["dd_resilience"] = -max_dd  # negate so higher = shallower DD

        # 4. Momentum quality: rolling Sharpe (60d)
        ret_mean = returns.rolling(self.quality_lookback).mean()
        ret_std = returns.rolling(self.quality_lookback).std().replace(0, np.nan)
        self.indicators["mom_sharpe"] = ret_mean / ret_std

        # Composite quality score (z-score average of the 4 metrics)
        quality_metrics = pd.DataFrame(
            {
                "stability": stability,
                "r_squared": r_squared,
                "dd_resilience": -max_dd,
                "mom_sharpe": ret_mean / ret_std,
            }
        )
        # Z-score each column using expanding stats for out-of-sample correctness
        quality_z = quality_metrics.apply(
            lambda col: (col - col.expanding().mean()) / col.expanding().std()
        )
        self.indicators["quality_score"] = quality_z.mean(axis=1)

        # Trend filter
        self.indicators["trend_ma"] = close.rolling(self.trend_period).mean()

    def on_bar(self, idx: int, bar: pd.Series) -> Optional[Signal]:
        warmup = max(self.quality_lookback, self.trend_period) + 20
        if idx < warmup:
            return None

        quality = self.get_indicator("quality_score", idx)
        trend_ma = self.get_indicator("trend_ma", idx)

        if np.isnan(quality) or np.isnan(trend_ma):
            return None

        price = bar["close"]
        above_trend = price > trend_ma

        # High quality + above trend -> buy
        if quality > self.entry_z and above_trend:
            return Signal.BUY

        # Low quality or below trend -> exit
        if quality < self.exit_z or not above_trend:
            return Signal.SELL

        return Signal.HOLD


# =========================================================================
# STRATEGY REGISTRY
# =========================================================================

TIER1_STRATEGIES = {
    "funding_rate_arb": FundingRateArbitrage,
    "pairs_trading": PairsTrading,
    "bab": BettingAgainstBeta,
    "flash_crash": FlashCrashReversal,
    "qmj": QualityMinusJunk,
}


def get_all_strategies() -> dict:
    """Return default instances of all Tier 1 strategies."""
    return {
        "funding_rate_arb": FundingRateArbitrage(),
        "pairs_trading": PairsTrading(),
        "bab": BettingAgainstBeta(),
        "flash_crash": FlashCrashReversal(),
        "qmj": QualityMinusJunk(),
    }
