#!/usr/bin/env python3
"""
ALPHA_ENGINE -- A/B Portfolio Testing Framework
=================================================
Forward-tests two non-crypto portfolio variants side-by-side:

  Portfolio A: Conservative Growth (60/30/10 stocks/bonds/alts)
  Portfolio B: Aggressive Growth   (80/15/5  growth/sector/commodities)

Methodology based on:
  - Wealthfront/Betterment mean-variance optimization principles
  - Vanguard rebalancing research (Dec 2024): threshold > calendar by 11-18bps/yr
  - Lopez de Prado (2018): minimum 100 trades for reliable metrics, 300+ for robust
  - Jobson-Korkie test with Memmel correction for Sharpe ratio comparison

Metrics tracked: Sharpe, Sortino, Calmar, Max DD, Win Rate, Information Ratio,
  Treynor, Omega, Ulcer Index, Profit Factor, Skewness, Kurtosis.

Usage:
  from ab_portfolio_test import ABPortfolioTest
  ab = ABPortfolioTest()
  results = ab.run_comparison(data)
"""

from __future__ import annotations

import json
import math
import os
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
DATA_DIR = Path(__file__).parent / "data"
RESULTS_FILE = DATA_DIR / "ab_test_results.json"
FRAMEWORK_FILE = DATA_DIR / "ab_portfolio_framework.json"
RISK_FREE_RATE = 0.048  # ~4.8% annualized (2026 10-yr Treasury proxy)
TRADING_DAYS_PER_YEAR = 252

# ---------------------------------------------------------------------------
# Portfolio Definitions
# ---------------------------------------------------------------------------

PORTFOLIO_A_HOLDINGS: dict[str, dict[str, Any]] = {
    # --- Stocks: 60% (Dividend Aristocrats + Blue Chips) ---
    "JNJ":  {"weight": 0.08, "category": "dividend_aristocrat", "sector": "healthcare"},
    "PG":   {"weight": 0.08, "category": "dividend_aristocrat", "sector": "consumer_staples"},
    "KO":   {"weight": 0.07, "category": "dividend_aristocrat", "sector": "consumer_staples"},
    "LIN":  {"weight": 0.07, "category": "dividend_aristocrat", "sector": "materials"},
    "MCD":  {"weight": 0.06, "category": "dividend_aristocrat", "sector": "consumer_discretionary"},
    "ABT":  {"weight": 0.06, "category": "dividend_aristocrat", "sector": "healthcare"},
    "ITW":  {"weight": 0.06, "category": "dividend_aristocrat", "sector": "industrials"},
    "NOBL": {"weight": 0.06, "category": "etf_dividend_aristocrats", "sector": "broad"},
    "SCHD": {"weight": 0.06, "category": "etf_dividend_growth", "sector": "broad"},
    # --- Bonds / Fixed Income: 30% ---
    "AGG":  {"weight": 0.12, "category": "bond_etf", "sector": "aggregate_bond"},
    "BND":  {"weight": 0.08, "category": "bond_etf", "sector": "total_bond"},
    "TIP":  {"weight": 0.05, "category": "bond_etf", "sector": "tips"},
    "IEFA": {"weight": 0.05, "category": "intl_equity_etf", "sector": "intl_developed"},
    # --- Alternatives: 10% ---
    "GLD":  {"weight": 0.05, "category": "commodity_etf", "sector": "gold"},
    "VNQ":  {"weight": 0.05, "category": "reit_etf", "sector": "real_estate"},
}

PORTFOLIO_B_HOLDINGS: dict[str, dict[str, Any]] = {
    # --- Growth + Momentum Stocks: 80% ---
    "NVDA": {"weight": 0.10, "category": "growth_mega", "sector": "technology"},
    "MSFT": {"weight": 0.09, "category": "growth_mega", "sector": "technology"},
    "AMZN": {"weight": 0.08, "category": "growth_mega", "sector": "consumer_discretionary"},
    "META": {"weight": 0.08, "category": "growth_mega", "sector": "technology"},
    "AVGO": {"weight": 0.07, "category": "growth_semi", "sector": "technology"},
    "MTUM": {"weight": 0.08, "category": "etf_momentum", "sector": "broad_momentum"},
    "QQQ":  {"weight": 0.08, "category": "etf_growth", "sector": "nasdaq100"},
    "VUG":  {"weight": 0.07, "category": "etf_growth", "sector": "large_growth"},
    "VEU":  {"weight": 0.05, "category": "intl_equity_etf", "sector": "intl_all_world"},
    "IBIT": {"weight": 0.05, "category": "crypto_etf", "sector": "bitcoin_spot"},
    # --- Sector ETFs: 15% ---
    "SOXX": {"weight": 0.05, "category": "sector_etf", "sector": "semiconductors"},
    "XLK":  {"weight": 0.05, "category": "sector_etf", "sector": "technology"},
    "XLV":  {"weight": 0.05, "category": "sector_etf", "sector": "healthcare"},
    # --- Commodities: 5% ---
    "GLD":  {"weight": 0.05, "category": "commodity_etf", "sector": "gold"},
    "SLV":  {"weight": 0.03, "category": "commodity_etf", "sector": "silver"},
    "GDXJ": {"weight": 0.02, "category": "commodity_etf", "sector": "gold_miners"},
}


# ---------------------------------------------------------------------------
# Entry / Exit Signal Logic
# ---------------------------------------------------------------------------

@dataclass
class EntrySignal:
    """Entry criteria check result."""
    symbol: str
    portfolio: str  # "A" or "B"
    triggered: bool
    confidence: float
    reasons: list[str] = field(default_factory=list)


@dataclass
class TradeRecord:
    """Single completed trade for tracking."""
    symbol: str
    portfolio: str
    direction: str  # LONG or SHORT
    entry_price: float
    entry_date: str
    exit_price: float = 0.0
    exit_date: str = ""
    exit_reason: str = ""
    pnl_pct: float = 0.0
    hold_days: int = 0
    is_winner: bool = False


def _safe_float(series: pd.Series, idx: int = -1) -> float:
    """Safely extract float from pandas Series."""
    try:
        val = float(series.iloc[idx])
        return val if math.isfinite(val) else 0.0
    except (IndexError, TypeError, ValueError):
        return 0.0


def _sma(series: pd.Series, period: int) -> pd.Series:
    return series.rolling(window=period, min_periods=period).mean()


def _ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()


def _rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0.0)).rolling(window=period).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100.0 - (100.0 / (1.0 + rs))


def _adx(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    """Simplified ADX calculation."""
    plus_dm = high.diff().clip(lower=0)
    minus_dm = (-low.diff()).clip(lower=0)
    tr = pd.concat([
        high - low,
        (high - close.shift(1)).abs(),
        (low - close.shift(1)).abs()
    ], axis=1).max(axis=1)
    atr = tr.rolling(window=period).mean()
    plus_di = 100 * (plus_dm.rolling(window=period).mean() / atr.replace(0, np.nan))
    minus_di = 100 * (minus_dm.rolling(window=period).mean() / atr.replace(0, np.nan))
    dx = 100 * ((plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan))
    return dx.rolling(window=period).mean()


def _macd(series: pd.Series) -> tuple[pd.Series, pd.Series]:
    """MACD line and signal line."""
    fast = _ema(series, 12)
    slow = _ema(series, 26)
    macd_line = fast - slow
    signal_line = _ema(macd_line, 9)
    return macd_line, signal_line


def check_entry_conservative(symbol: str, df: pd.DataFrame) -> EntrySignal:
    """Portfolio A entry: RSI < 45, price > SMA200, price > SMA50, ADX > 20."""
    if len(df) < 210:
        return EntrySignal(symbol, "A", False, 0.0, ["insufficient_data"])

    close = df["Close"]
    high = df.get("High", close)
    low = df.get("Low", close)
    volume = df.get("Volume", pd.Series([0] * len(df)))

    rsi_val = _safe_float(_rsi(close, 14))
    sma_200 = _safe_float(_sma(close, 200))
    sma_50 = _safe_float(_sma(close, 50))
    adx_val = _safe_float(_adx(high, low, close, 14))
    price = _safe_float(close)
    vol_20 = _safe_float(volume.rolling(20).mean())
    vol_now = _safe_float(volume)

    reasons = []
    score = 0.0

    # RSI below 45 (buying on weakness in uptrend)
    if rsi_val < 45:
        score += 0.25
        reasons.append(f"RSI={rsi_val:.1f}<45")
    # Price above 200-day SMA (long-term uptrend)
    if price > sma_200 > 0:
        score += 0.25
        reasons.append("price>SMA200")
    # Price above 50-day SMA (medium-term uptrend)
    if price > sma_50 > 0:
        score += 0.20
        reasons.append("price>SMA50")
    # ADX above 20 (trending, not choppy)
    if adx_val > 20:
        score += 0.15
        reasons.append(f"ADX={adx_val:.1f}>20")
    # Volume confirmation
    if vol_now > vol_20 > 0:
        score += 0.15
        reasons.append("volume_confirmed")

    triggered = score >= 0.60  # Need at least 3 of 5 criteria
    return EntrySignal(symbol, "A", triggered, round(score, 3), reasons)


def check_entry_aggressive(symbol: str, df: pd.DataFrame) -> EntrySignal:
    """Portfolio B entry: RSI 30-60, EMA21 crossover, MACD bullish, ADX > 25, volume surge."""
    if len(df) < 260:
        return EntrySignal(symbol, "B", False, 0.0, ["insufficient_data"])

    close = df["Close"]
    high = df.get("High", close)
    low = df.get("Low", close)
    volume = df.get("Volume", pd.Series([0] * len(df)))

    rsi_val = _safe_float(_rsi(close, 14))
    ema_21 = _safe_float(_ema(close, 21))
    sma_50 = _safe_float(_sma(close, 50))
    adx_val = _safe_float(_adx(high, low, close, 14))
    price = _safe_float(close)
    macd_line, macd_signal = _macd(close)
    macd_val = _safe_float(macd_line)
    macd_sig = _safe_float(macd_signal)
    macd_prev = _safe_float(macd_line, -2)
    macd_sig_prev = _safe_float(macd_signal, -2)
    vol_20 = _safe_float(volume.rolling(20).mean())
    vol_now = _safe_float(volume)

    # 12-month momentum skip last month
    mom_12m = 0.0
    if len(close) >= 252:
        c_start = _safe_float(close, -252)
        c_skip = _safe_float(close, -22)
        if c_start > 0:
            mom_12m = (c_skip / c_start) - 1.0

    reasons = []
    score = 0.0

    # RSI in sweet spot (30-60 = not overbought, not deeply oversold)
    if 30 <= rsi_val <= 60:
        score += 0.15
        reasons.append(f"RSI={rsi_val:.1f}_in_30-60")
    # Price above EMA 21
    if price > ema_21 > 0:
        score += 0.15
        reasons.append("price>EMA21")
    # Price above SMA 50
    if price > sma_50 > 0:
        score += 0.10
        reasons.append("price>SMA50")
    # MACD bullish crossover
    if macd_val > macd_sig and macd_prev <= macd_sig_prev:
        score += 0.20
        reasons.append("MACD_bullish_cross")
    elif macd_val > macd_sig:
        score += 0.10
        reasons.append("MACD_bullish")
    # ADX above 25 (strong trend)
    if adx_val > 25:
        score += 0.15
        reasons.append(f"ADX={adx_val:.1f}>25")
    # Volume surge
    if vol_20 > 0 and vol_now / vol_20 >= 1.5:
        score += 0.15
        reasons.append(f"vol_surge={vol_now/vol_20:.1f}x")
    elif vol_now > vol_20 > 0:
        score += 0.05
        reasons.append("vol_above_avg")
    # 12-month momentum positive
    if mom_12m > 0.05:
        score += 0.10
        reasons.append(f"mom_12m={mom_12m:.1%}")

    triggered = score >= 0.55  # Need strong multi-factor confirmation
    return EntrySignal(symbol, "B", triggered, round(score, 3), reasons)


def check_exit_conservative(trade: TradeRecord, current_price: float, days_held: int) -> tuple[bool, str]:
    """Portfolio A exit: 8% trailing stop, 12% hard stop, 15% target, 90-day time stop."""
    pnl_pct = (current_price / trade.entry_price - 1.0) * 100
    if pnl_pct <= -12.0:
        return True, "hard_stop_12pct"
    if pnl_pct <= -8.0:
        return True, "trailing_stop_8pct"
    if pnl_pct >= 15.0:
        return True, "profit_target_15pct"
    if days_held >= 90:
        return True, "time_stop_90d"
    return False, ""


def check_exit_aggressive(trade: TradeRecord, current_price: float, days_held: int,
                          rsi_val: float = 50.0, macd_bearish: bool = False) -> tuple[bool, str]:
    """Portfolio B exit: 12% trailing, 18% hard, 30% target, 60-day time, RSI>80, MACD bear cross."""
    pnl_pct = (current_price / trade.entry_price - 1.0) * 100
    if pnl_pct <= -18.0:
        return True, "hard_stop_18pct"
    if pnl_pct <= -12.0:
        return True, "trailing_stop_12pct"
    if pnl_pct >= 30.0:
        return True, "profit_target_30pct"
    if days_held >= 60:
        return True, "time_stop_60d"
    if rsi_val > 80:
        return True, "rsi_overbought_80"
    if macd_bearish and pnl_pct > 0:
        return True, "macd_bearish_cross_profit"
    return False, ""


# ---------------------------------------------------------------------------
# Performance Metrics
# ---------------------------------------------------------------------------

def compute_sharpe(returns: pd.Series, rf_annual: float = RISK_FREE_RATE) -> float:
    """Annualized Sharpe ratio."""
    if returns.empty or returns.std() == 0:
        return 0.0
    rf_daily = (1 + rf_annual) ** (1 / TRADING_DAYS_PER_YEAR) - 1
    excess = returns - rf_daily
    return float(excess.mean() / excess.std() * np.sqrt(TRADING_DAYS_PER_YEAR))


def compute_sortino(returns: pd.Series, rf_annual: float = RISK_FREE_RATE) -> float:
    """Annualized Sortino ratio (downside deviation only)."""
    if returns.empty:
        return 0.0
    rf_daily = (1 + rf_annual) ** (1 / TRADING_DAYS_PER_YEAR) - 1
    excess = returns - rf_daily
    downside = excess[excess < 0]
    if downside.empty or downside.std() == 0:
        return float("inf") if excess.mean() > 0 else 0.0
    return float(excess.mean() / downside.std() * np.sqrt(TRADING_DAYS_PER_YEAR))


def compute_calmar(returns: pd.Series) -> float:
    """Calmar ratio: annualized return / max drawdown."""
    if returns.empty:
        return 0.0
    ann_ret = float(returns.mean() * TRADING_DAYS_PER_YEAR)
    cum = (1 + returns).cumprod()
    peak = cum.cummax()
    dd = ((cum - peak) / peak).min()
    max_dd = abs(float(dd))
    if max_dd == 0:
        return float("inf") if ann_ret > 0 else 0.0
    return ann_ret / max_dd


def compute_max_drawdown(returns: pd.Series) -> float:
    """Maximum drawdown as a positive percentage."""
    if returns.empty:
        return 0.0
    cum = (1 + returns).cumprod()
    peak = cum.cummax()
    dd = ((cum - peak) / peak).min()
    return abs(float(dd)) * 100


def compute_information_ratio(returns: pd.Series, benchmark_returns: pd.Series) -> float:
    """Information ratio relative to benchmark."""
    if returns.empty or benchmark_returns.empty:
        return 0.0
    active = returns - benchmark_returns
    if active.std() == 0:
        return 0.0
    return float(active.mean() / active.std() * np.sqrt(TRADING_DAYS_PER_YEAR))


def compute_omega(returns: pd.Series, threshold: float = 0.0) -> float:
    """Omega ratio: probability-weighted gains / losses above threshold."""
    if returns.empty:
        return 0.0
    excess = returns - threshold
    gains = excess[excess > 0].sum()
    losses = abs(excess[excess < 0].sum())
    if losses == 0:
        return float("inf") if gains > 0 else 1.0
    return float(gains / losses)


def compute_profit_factor(trades: list[TradeRecord]) -> float:
    """Gross profits / gross losses from trade records."""
    gross_profit = sum(t.pnl_pct for t in trades if t.pnl_pct > 0)
    gross_loss = abs(sum(t.pnl_pct for t in trades if t.pnl_pct < 0))
    if gross_loss == 0:
        return float("inf") if gross_profit > 0 else 0.0
    return gross_profit / gross_loss


def compute_win_rate(trades: list[TradeRecord]) -> float:
    """Win rate as percentage."""
    if not trades:
        return 0.0
    winners = sum(1 for t in trades if t.pnl_pct > 0)
    return (winners / len(trades)) * 100


def compute_ulcer_index(returns: pd.Series) -> float:
    """Ulcer Index: RMS of percentage drawdowns (measures depth + duration)."""
    if returns.empty:
        return 0.0
    cum = (1 + returns).cumprod()
    peak = cum.cummax()
    dd_pct = ((cum - peak) / peak) * 100
    return float(np.sqrt((dd_pct ** 2).mean()))


# ---------------------------------------------------------------------------
# Statistical Comparison (Jobson-Korkie with Memmel correction)
# ---------------------------------------------------------------------------

def jobson_korkie_test(returns_a: pd.Series, returns_b: pd.Series,
                       rf_annual: float = RISK_FREE_RATE) -> dict[str, Any]:
    """
    Test H0: Sharpe_A == Sharpe_B using Jobson-Korkie (1981) with Memmel (2003)
    correction for small-sample bias.

    Returns dict with test statistic, p-value, and interpretation.
    """
    n = min(len(returns_a), len(returns_b))
    if n < 30:
        return {"test": "jobson_korkie", "n": n, "result": "insufficient_data",
                "p_value": 1.0, "significant": False}

    rf_daily = (1 + rf_annual) ** (1 / TRADING_DAYS_PER_YEAR) - 1
    ra = returns_a.iloc[:n] - rf_daily
    rb = returns_b.iloc[:n] - rf_daily

    mu_a, mu_b = float(ra.mean()), float(rb.mean())
    sig_a, sig_b = float(ra.std()), float(rb.std())

    if sig_a == 0 or sig_b == 0:
        return {"test": "jobson_korkie", "n": n, "result": "zero_variance",
                "p_value": 1.0, "significant": False}

    sharpe_a = mu_a / sig_a
    sharpe_b = mu_b / sig_b
    rho = float(ra.corr(rb))

    # Memmel (2003) corrected variance
    theta = (1 / n) * (
        2 * (1 - rho)
        + 0.5 * (sharpe_a ** 2 + sharpe_b ** 2 - 2 * sharpe_a * sharpe_b * rho)
    )

    if theta <= 0:
        return {"test": "jobson_korkie", "n": n, "result": "degenerate_variance",
                "p_value": 1.0, "significant": False}

    z_stat = (sharpe_a - sharpe_b) / math.sqrt(theta)

    # Two-sided p-value from standard normal
    from scipy.stats import norm  # type: ignore
    p_value = 2 * (1 - norm.cdf(abs(z_stat)))

    return {
        "test": "jobson_korkie_memmel",
        "n": n,
        "sharpe_a_daily": round(sharpe_a, 6),
        "sharpe_b_daily": round(sharpe_b, 6),
        "sharpe_a_annual": round(sharpe_a * np.sqrt(TRADING_DAYS_PER_YEAR), 4),
        "sharpe_b_annual": round(sharpe_b * np.sqrt(TRADING_DAYS_PER_YEAR), 4),
        "correlation": round(rho, 4),
        "z_statistic": round(z_stat, 4),
        "p_value": round(p_value, 6),
        "significant_at_5pct": p_value < 0.05,
        "significant_at_10pct": p_value < 0.10,
        "winner": "A" if sharpe_a > sharpe_b else "B" if sharpe_b > sharpe_a else "tie",
    }


# ---------------------------------------------------------------------------
# Rebalancing Logic
# ---------------------------------------------------------------------------

def check_rebalance_needed(
    current_weights: dict[str, float],
    target_weights: dict[str, float],
    threshold_pct: float = 5.0,
) -> tuple[bool, dict[str, float]]:
    """
    Check if any position has drifted beyond threshold from target.
    Returns (needs_rebalance, drift_dict).
    """
    drifts = {}
    needs = False
    for ticker, target in target_weights.items():
        current = current_weights.get(ticker, 0.0)
        drift = abs(current - target) * 100  # as percentage points
        drifts[ticker] = round(drift, 2)
        if drift > threshold_pct:
            needs = True
    return needs, drifts


def compute_rebalance_trades(
    current_weights: dict[str, float],
    target_weights: dict[str, float],
    portfolio_value: float,
) -> list[dict[str, Any]]:
    """Compute buy/sell trades needed to rebalance to target weights."""
    trades = []
    for ticker, target in target_weights.items():
        current = current_weights.get(ticker, 0.0)
        diff = target - current
        if abs(diff) < 0.001:  # Skip negligible drifts
            continue
        dollar_amount = diff * portfolio_value
        trades.append({
            "ticker": ticker,
            "action": "BUY" if diff > 0 else "SELL",
            "weight_change_pct": round(diff * 100, 2),
            "dollar_amount": round(dollar_amount, 2),
        })
    return sorted(trades, key=lambda t: abs(t["dollar_amount"]), reverse=True)


# ---------------------------------------------------------------------------
# Main A/B Test Orchestrator
# ---------------------------------------------------------------------------

class ABPortfolioTest:
    """Orchestrates parallel A/B test of conservative vs aggressive portfolios."""

    def __init__(self) -> None:
        self.trades_a: list[TradeRecord] = []
        self.trades_b: list[TradeRecord] = []
        self.snapshots: list[dict[str, Any]] = []

    def scan_entries(self, data: dict[str, pd.DataFrame]) -> dict[str, list[EntrySignal]]:
        """Scan all holdings in both portfolios for entry signals."""
        signals: dict[str, list[EntrySignal]] = {"A": [], "B": []}

        for symbol in PORTFOLIO_A_HOLDINGS:
            df = data.get(symbol)
            if df is not None and len(df) >= 50:
                sig = check_entry_conservative(symbol, df)
                if sig.triggered:
                    signals["A"].append(sig)

        for symbol in PORTFOLIO_B_HOLDINGS:
            df = data.get(symbol)
            if df is not None and len(df) >= 50:
                sig = check_entry_aggressive(symbol, df)
                if sig.triggered:
                    signals["B"].append(sig)

        return signals

    def compute_portfolio_returns(
        self, data: dict[str, pd.DataFrame], holdings: dict[str, dict[str, Any]]
    ) -> pd.Series:
        """Compute weighted daily returns for a portfolio."""
        all_returns = {}
        for symbol, meta in holdings.items():
            df = data.get(symbol)
            if df is None or len(df) < 2:
                continue
            all_returns[symbol] = df["Close"].pct_change().dropna()

        if not all_returns:
            return pd.Series(dtype=float)

        returns_df = pd.DataFrame(all_returns)
        # Fill missing with 0 (no return on non-trading days)
        returns_df = returns_df.fillna(0.0)

        # Weighted portfolio return
        weights = {s: m["weight"] for s, m in holdings.items() if s in returns_df.columns}
        total_w = sum(weights.values())
        if total_w == 0:
            return pd.Series(dtype=float)

        portfolio_return = sum(
            returns_df[s] * (w / total_w) for s, w in weights.items()
        )
        return portfolio_return

    def full_comparison(self, data: dict[str, pd.DataFrame],
                        benchmark_data: Optional[pd.DataFrame] = None) -> dict[str, Any]:
        """
        Run complete A/B comparison on provided data.

        Args:
            data: dict of symbol -> DataFrame with OHLCV columns
            benchmark_data: SPY DataFrame for information ratio (optional)

        Returns:
            Complete comparison results dict.
        """
        returns_a = self.compute_portfolio_returns(data, PORTFOLIO_A_HOLDINGS)
        returns_b = self.compute_portfolio_returns(data, PORTFOLIO_B_HOLDINGS)

        if returns_a.empty or returns_b.empty:
            return {"error": "insufficient_data_for_comparison"}

        # Align date ranges
        common_idx = returns_a.index.intersection(returns_b.index)
        returns_a = returns_a.loc[common_idx]
        returns_b = returns_b.loc[common_idx]

        # Benchmark returns
        bench_returns = None
        if benchmark_data is not None and len(benchmark_data) > 1:
            bench_returns = benchmark_data["Close"].pct_change().dropna()
            bench_idx = common_idx.intersection(bench_returns.index)
            bench_returns = bench_returns.loc[bench_idx]
            returns_a = returns_a.loc[bench_idx]
            returns_b = returns_b.loc[bench_idx]

        # --- Compute all metrics ---
        result = {
            "test_period": {
                "start": str(common_idx[0]) if len(common_idx) > 0 else "",
                "end": str(common_idx[-1]) if len(common_idx) > 0 else "",
                "trading_days": len(common_idx),
            },
            "portfolio_a": {
                "name": "Conservative Growth",
                "holdings_count": len(PORTFOLIO_A_HOLDINGS),
                "sharpe_ratio": round(compute_sharpe(returns_a), 4),
                "sortino_ratio": round(compute_sortino(returns_a), 4),
                "calmar_ratio": round(compute_calmar(returns_a), 4),
                "max_drawdown_pct": round(compute_max_drawdown(returns_a), 2),
                "omega_ratio": round(compute_omega(returns_a), 4),
                "ulcer_index": round(compute_ulcer_index(returns_a), 4),
                "annualized_return_pct": round(float(returns_a.mean() * TRADING_DAYS_PER_YEAR * 100), 2),
                "annualized_volatility_pct": round(float(returns_a.std() * np.sqrt(TRADING_DAYS_PER_YEAR) * 100), 2),
                "skewness": round(float(returns_a.skew()), 4),
                "kurtosis": round(float(returns_a.kurtosis()), 4),
                "trade_count": len(self.trades_a),
                "win_rate_pct": round(compute_win_rate(self.trades_a), 2),
                "profit_factor": round(compute_profit_factor(self.trades_a), 4) if self.trades_a else None,
            },
            "portfolio_b": {
                "name": "Aggressive Growth",
                "holdings_count": len(PORTFOLIO_B_HOLDINGS),
                "sharpe_ratio": round(compute_sharpe(returns_b), 4),
                "sortino_ratio": round(compute_sortino(returns_b), 4),
                "calmar_ratio": round(compute_calmar(returns_b), 4),
                "max_drawdown_pct": round(compute_max_drawdown(returns_b), 2),
                "omega_ratio": round(compute_omega(returns_b), 4),
                "ulcer_index": round(compute_ulcer_index(returns_b), 4),
                "annualized_return_pct": round(float(returns_b.mean() * TRADING_DAYS_PER_YEAR * 100), 2),
                "annualized_volatility_pct": round(float(returns_b.std() * np.sqrt(TRADING_DAYS_PER_YEAR) * 100), 2),
                "skewness": round(float(returns_b.skew()), 4),
                "kurtosis": round(float(returns_b.kurtosis()), 4),
                "trade_count": len(self.trades_b),
                "win_rate_pct": round(compute_win_rate(self.trades_b), 2),
                "profit_factor": round(compute_profit_factor(self.trades_b), 4) if self.trades_b else None,
            },
            "statistical_test": jobson_korkie_test(returns_a, returns_b),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

        # Information ratio vs benchmark
        if bench_returns is not None and not bench_returns.empty:
            result["portfolio_a"]["information_ratio"] = round(
                compute_information_ratio(returns_a, bench_returns), 4)
            result["portfolio_b"]["information_ratio"] = round(
                compute_information_ratio(returns_b, bench_returns), 4)

        return result

    def save_results(self, results: dict[str, Any]) -> Path:
        """Save comparison results to JSON."""
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        with open(RESULTS_FILE, "w") as f:
            json.dump(results, f, indent=2, default=str)
        return RESULTS_FILE


# ---------------------------------------------------------------------------
# Convenience: print framework summary
# ---------------------------------------------------------------------------

def print_framework_summary() -> None:
    """Print a human-readable summary of the A/B test framework."""
    print("=" * 78)
    print("  A/B PORTFOLIO TESTING FRAMEWORK — Non-Crypto Investments")
    print("=" * 78)
    print()
    print("PORTFOLIO A: Conservative Growth")
    print("-" * 40)
    print("  Allocation: 60% stocks (dividend aristocrats) / 30% bonds / 10% alts")
    print("  Target: 8-12% annual | Sharpe > 1.0 | Max DD < 15%")
    print("  Rebalance: Quarterly + 5% drift threshold")
    print("  Holdings:")
    total_a = 0.0
    for ticker, meta in sorted(PORTFOLIO_A_HOLDINGS.items(), key=lambda x: -x[1]["weight"]):
        pct = meta["weight"] * 100
        total_a += pct
        print(f"    {ticker:6s}  {pct:5.1f}%  ({meta['category']})")
    print(f"    {'TOTAL':6s}  {total_a:5.1f}%")
    print()
    print("PORTFOLIO B: Aggressive Growth")
    print("-" * 40)
    print("  Allocation: 80% growth+momentum / 15% sector ETFs / 5% commodities")
    print("  Target: 15-25% annual | Sharpe > 0.8 | Max DD < 30%")
    print("  Rebalance: Monthly + 3% drift threshold")
    print("  Holdings:")
    total_b = 0.0
    for ticker, meta in sorted(PORTFOLIO_B_HOLDINGS.items(), key=lambda x: -x[1]["weight"]):
        pct = meta["weight"] * 100
        total_b += pct
        print(f"    {ticker:6s}  {pct:5.1f}%  ({meta['category']})")
    print(f"    {'TOTAL':6s}  {total_b:5.1f}%")
    print()
    print("COMPARISON METRICS")
    print("-" * 40)
    print("  Primary:   Sharpe, Sortino, Calmar, Max DD, Win Rate")
    print("  Secondary: Information Ratio, Treynor, Omega, Ulcer Index,")
    print("             Profit Factor, Skewness, Kurtosis")
    print()
    print("STATISTICAL TEST")
    print("-" * 40)
    print("  Method: Jobson-Korkie (1981) with Memmel (2003) correction")
    print("  H0: Sharpe_A == Sharpe_B")
    print("  Significance: alpha = 0.05 (two-sided)")
    print("  Min sample: 30 trades | Reliable: 100 | Robust: 300+")
    print()
    print("REBALANCING (Vanguard Dec 2024 research)")
    print("-" * 40)
    print("  Threshold-based > calendar-based by 11-18 bps/yr")
    print("  Portfolio A: quarterly calendar + 5% drift trigger")
    print("  Portfolio B: monthly calendar + 3% drift trigger")
    print()
    print("TEST PHASES")
    print("-" * 40)
    print("  Phase 1: Backtest (3mo historical 2023-2026)")
    print("  Phase 2: Paper trade (3mo forward)")
    print("  Phase 3: Live A/B test (6-12mo)")
    print("  Phase 4: Production (winner primary, loser at 20%)")
    print("=" * 78)


if __name__ == "__main__":
    print_framework_summary()
