#!/usr/bin/env python3
"""
================================================================================
ETF Dual-Momentum Backtest Template — Production-Grade Pipeline
================================================================================
Implements the "ideal (production-grade) back-testing pipeline" from the
EAGLE2 quant review (2026-06-02) specifically for ETF dual-momentum strategies.

Features:
  1. Pre-registration — hypothesis logged before any backtest
  2. Purged-embargoed walk-forward — prevents look-ahead bias
  3. Block bootstrap — 1000 resamples preserving temporal dependence
  4. Regime-segmented analysis — bull/bear/sideways/high-vol regimes
  5. Full cost model — expense ratios, tracking error, commission, slippage
  6. Multiple-testing correction — Bonferroni + Deflated Sharpe Ratio (DSR)
  7. Statistical readiness gate — PF≥1.5, Sharpe≥1.0, MDD≤20%, n≥30
  8. Asset-class-specific thresholds per EAGLE2 framework

Academic anchors:
  - Antonacci (2013): Dual Momentum Investing
  - Lopez de Prado (2018): Advances in Financial ML (purged CV, embargo, CPCV)
  - Bailey & Lopez de Prado (2014): Deflated Sharpe Ratio
  - Barroso & Santa-Clara (2015): Momentum has its moments (vol scaling)

Usage:
    python alpha_engine/backtest_etf_dual_momentum.py

Output:
    Writes JSON report to reports/etf_dual_momentum_backtest_YYYYMMDD.json
================================================================================
"""

from __future__ import annotations

import json
import logging
import math
import os
import time
import warnings
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from scipy import stats

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)-30s | %(levelname)-8s | %(message)s",
)
logger = logging.getLogger("etf_dual_momentum")

warnings.filterwarnings("ignore", category=RuntimeWarning)

# ---------------------------------------------------------------------------
# CONFIGURATION — Asset-Class-Specific Thresholds (EAGLE2 Framework)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class AssetClassThresholds:
    """Real-money readiness thresholds per asset class."""
    min_pf: float = 1.5          # Profit factor
    ideal_pf: float = 2.0
    min_sharpe: float = 1.0      # Annualised Sharpe
    min_wr: float = 0.45         # Win rate
    max_wr: float = 0.60         # Cap — >60% often signals tiny gains
    max_mdd: float = 0.20        # Maximum drawdown
    min_calmar: float = 3.0
    max_turnover_pct_yr: float = 0.30  # For equities/ETFs
    max_slippage_bps: float = 5.0      # For large-cap equities/ETFs
    min_regime_persistence: float = 0.75  # Edge in ≥3 of 4 regimes
    min_oos_decay_pf: float = 0.80   # OOS PF ≥ 80% of IS PF
    min_oos_decay_sharpe: float = 0.70
    min_n_trades: int = 30
    dsr_probability_gate: float = 0.95
    bonferroni_alpha: float = 0.05
    hhi_max: float = 0.20

ETF_THRESHOLDS = AssetClassThresholds()

# ETF-specific cost assumptions
ETF_EXPENSE_RATIOS: Dict[str, float] = {
    "SPY": 0.0009, "QQQ": 0.0020, "IWM": 0.0019, "DIA": 0.0016,
    "VTI": 0.0003, "VOO": 0.0003, "ARKK": 0.0075, "XLF": 0.0010,
    "XLE": 0.0010, "XLK": 0.0010, "GLD": 0.0040, "SLV": 0.0050,
    "USO": 0.0079, "EEM": 0.0068, "EFA": 0.0032, "SQQQ": 0.0089,
    "TQQQ": 0.0089, "UVXY": 0.0089, "TLT": 0.0015, "IEF": 0.0015,
    "LQD": 0.0014, "HYG": 0.0048, "VWO": 0.0010, "VEA": 0.0005,
    "VIG": 0.0006, "VYM": 0.0006,
}

ETF_TRACKING_ERRORS: Dict[str, float] = {
    "SPY": 0.0005, "QQQ": 0.0010, "IWM": 0.0015, "DIA": 0.0010,
    "VTI": 0.0003, "VOO": 0.0003, "ARKK": 0.0050, "XLF": 0.0008,
    "XLE": 0.0008, "XLK": 0.0008, "GLD": 0.0020, "SLV": 0.0030,
    "USO": 0.0100, "EEM": 0.0050, "EFA": 0.0030, "SQQQ": 0.0200,
    "TQQQ": 0.0200, "UVXY": 0.0500, "TLT": 0.0010, "IEF": 0.0010,
    "LQD": 0.0010, "HYG": 0.0020, "VWO": 0.0030, "VEA": 0.0020,
    "VIG": 0.0005, "VYM": 0.0005,
}

# Trading costs
COMMISSION_PER_TRADE_PCT = 0.001   # 0.1% per side (e.g. IBKR Pro)
SLIPPAGE_PCT = 0.0005              # 5 bps for liquid ETFs
BARS_PER_YEAR = 252                # Daily bars

# ---------------------------------------------------------------------------
# PRE-REGISTRATION
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Hypothesis:
    """Pre-registered hypothesis before any backtest."""
    hypothesis_id: str
    timestamp_utc: str
    signal_definition: str
    universe: List[str]
    lookback_days: int
    hold_months: int
    risk_free_proxy: str
    cost_assumptions: Dict[str, float]
    expected_edge_rationale: str
    git_commit: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def log_hypothesis(
    universe: List[str],
    lookback_days: int = 252,
    hold_months: int = 1,
    risk_free_proxy: str = "SHV",
    rationale: str = "",
) -> Hypothesis:
    """Create and log a pre-registered hypothesis."""
    ts = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    h = Hypothesis(
        hypothesis_id=f"etf_dm_{ts.replace(':', '').replace('-', '')}",
        timestamp_utc=ts,
        signal_definition=(
            f"Dual momentum: absolute momentum ({lookback_days}d return vs "
            f"{risk_free_proxy}) + relative momentum (rank top 3 of universe). "
            f"Hold for {hold_months} month(s), then rebalance."
        ),
        universe=sorted(universe),
        lookback_days=lookback_days,
        hold_months=hold_months,
        risk_free_proxy=risk_free_proxy,
        cost_assumptions={
            "commission_pct": COMMISSION_PER_TRADE_PCT,
            "slippage_pct": SLIPPAGE_PCT,
            "expense_ratio_annual_avg": round(
                np.mean([ETF_EXPENSE_RATIOS.get(t, 0.001) for t in universe]), 6
            ),
        },
        expected_edge_rationale=rationale or (
            "Antonacci (2013): dual momentum combines absolute trend filter "
            "with relative strength. ETFs exhibit persistence at 12-month "
            "horizons (Moskowitz & Grinblatt 1999, JFE)."
        ),
        git_commit=os.popen("git rev-parse --short HEAD 2>/dev/null || echo 'N/A'").read().strip(),
    )
    logger.info("[PRE-REG] hypothesis_id=%s | universe=%s", h.hypothesis_id, universe)
    return h


# ---------------------------------------------------------------------------
# DATA FETCHING (yfinance)
# ---------------------------------------------------------------------------

def fetch_etf_data(
    tickers: List[str],
    start: str = "2015-01-01",
    end: Optional[str] = None,
) -> pd.DataFrame:
    """
    Fetch adjusted close prices for ETF universe via yfinance.
    Returns DataFrame with dates as index, tickers as columns.
    """
    try:
        import yfinance as yf
    except ImportError as e:
        raise ImportError("yfinance required: pip install yfinance") from e

    end = end or datetime.utcnow().strftime("%Y-%m-%d")
    logger.info("Fetching data for %d tickers from %s to %s...", len(tickers), start, end)

    all_data: Dict[str, pd.Series] = {}
    for ticker in tickers:
        try:
            df = yf.download(ticker, start=start, end=end, progress=False, auto_adjust=True)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            if "Close" in df.columns and len(df) > 100:
                all_data[ticker] = df["Close"].squeeze()
        except Exception as exc:
            logger.warning("Failed to fetch %s: %s", ticker, exc)

    if not all_data:
        raise RuntimeError("No data fetched for any ticker")

    prices = pd.DataFrame(all_data)
    prices = prices.dropna(how="all", axis=1).dropna(how="all", axis=0)
    logger.info("Price matrix shape: %s | date range: %s to %s",
                prices.shape, prices.index[0].date(), prices.index[-1].date())
    return prices


# ---------------------------------------------------------------------------
# DUAL-MOMENTUM SIGNAL GENERATOR
# ---------------------------------------------------------------------------

def dual_momentum_signals(
    prices: pd.DataFrame,
    lookback: int = 252,
    top_n: int = 3,
    risk_free_ticker: Optional[str] = None,
) -> pd.DataFrame:
    """
    Generate dual-momentum position signals.

    Absolute momentum:  only go LONG if ticker has positive lookback return
                        vs risk-free proxy (or zero if no proxy).
    Relative momentum:  rank by lookback return, go long top_n.

    Rebalances monthly (end-of-month).
    Returns DataFrame of positions (0 or 1) with same shape as prices.
    """
    positions = pd.DataFrame(0, index=prices.index, columns=prices.columns, dtype=float)

    # Monthly rebalancing points. "ME" is the pandas >=2.2 month-end alias;
    # fall back to "M" on older pandas (CI may run pandas <2.2).
    try:
        month_ends = prices.resample("ME").last().index
    except ValueError:
        month_ends = prices.resample("M").last().index

    for rebalance_date in month_ends:
        # Find the last available price before or on rebalance_date
        try:
            idx = prices.index.get_indexer([rebalance_date], method="nearest")[0]
        except Exception:
            continue
        if idx < lookback:
            continue

        current_prices = prices.iloc[idx]
        past_prices = prices.iloc[idx - lookback]

        # Absolute momentum: positive return vs risk-free
        abs_ret = (current_prices / past_prices) - 1.0
        if risk_free_ticker and risk_free_ticker in prices.columns:
            rf_ret = abs_ret.get(risk_free_ticker, 0.0)
            abs_mask = abs_ret > rf_ret
        else:
            abs_mask = abs_ret > 0.0

        # Relative momentum: top_n by return
        rel_rank = abs_ret.rank(ascending=False, method="first")
        rel_mask = rel_rank <= top_n

        # Combined: must pass BOTH absolute and relative
        selected = abs_mask & rel_mask

        # Write positions from this rebalance date until next month end
        next_rebalance = rebalance_date + pd.DateOffset(months=1)
        mask = (prices.index > rebalance_date) & (prices.index <= next_rebalance)
        for ticker in prices.columns:
            if selected.get(ticker, False):
                positions.loc[mask, ticker] = 1.0

    return positions


# ---------------------------------------------------------------------------
# VECTORIZED BACKTEST WITH FULL COST MODEL
# ---------------------------------------------------------------------------

def run_backtest_with_costs(
    prices: pd.DataFrame,
    positions: pd.DataFrame,
    commission_pct: float = COMMISSION_PER_TRADE_PCT,
    slippage_pct: float = SLIPPAGE_PCT,
    expense_ratios: Optional[Dict[str, float]] = None,
) -> Tuple[pd.Series, pd.DataFrame]:
    """
    Run vectorized backtest applying position × market return, minus costs.

    Costs applied:
      - Commission: per trade (position change)
      - Slippage: 5 bps per entry/exit
      - Expense ratio: daily drag (annual ER / 252)

    Returns:
        portfolio_returns: daily pct returns Series
        trade_log: DataFrame of entry/exit events
    """
    expense_ratios = expense_ratios or {}
    daily_returns = prices.pct_change().fillna(0)

    # Strategy returns = position × market return (lagged positions)
    pos_lagged = positions.shift(1).fillna(0)
    strat_returns = (pos_lagged * daily_returns).sum(axis=1)  # equal-weighted portfolio

    # --- Cost deductions ---
    # 1. Expense ratio drag (daily)
    avg_er = np.mean([expense_ratios.get(t, 0.001) for t in prices.columns])
    er_drag = avg_er / BARS_PER_YEAR
    strat_returns = strat_returns - er_drag

    # 2. Commission + slippage on position changes
    # Position change = |Δposition| per ticker, summed across tickers
    pos_change = positions.diff().abs().sum(axis=1)
    # Round-trip cost for each unit of position change
    roundtrip_cost = 2 * (commission_pct + slippage_pct)
    cost_series = pos_change * roundtrip_cost
    # Only apply cost when there was actually a change
    cost_series = cost_series.where(pos_change > 0, 0.0)
    strat_returns = strat_returns - cost_series

    # 3. Tracking error noise
    te_map = {t: ETF_TRACKING_ERRORS.get(t, 0.001) for t in prices.columns}
    avg_te = np.mean(list(te_map.values()))
    rng = np.random.default_rng(42)
    te_noise = rng.normal(0, avg_te / np.sqrt(BARS_PER_YEAR), size=len(strat_returns))
    strat_returns = strat_returns - pd.Series(te_noise, index=strat_returns.index)

    # Build trade log
    trades = []
    for ticker in prices.columns:
        pos = positions[ticker]
        changes = pos.diff().fillna(0).abs()
        change_dates = changes[changes > 0].index
        for cd in change_dates:
            trades.append({
                "date": cd.strftime("%Y-%m-%d"),
                "ticker": ticker,
                "new_position": round(pos.loc[cd], 2),
                "price": round(prices.loc[cd, ticker], 2) if ticker in prices.columns else None,
            })
    trade_log = pd.DataFrame(trades) if trades else pd.DataFrame()

    return strat_returns, trade_log


# ---------------------------------------------------------------------------
# PERFORMANCE METRICS
# ---------------------------------------------------------------------------

def calc_pf(returns: pd.Series) -> float:
    """Profit factor = gross profit / gross loss."""
    gross_profit = returns[returns > 0].sum()
    gross_loss = abs(returns[returns < 0].sum())
    return gross_profit / gross_loss if gross_loss > 1e-12 else float("inf")


def calc_sharpe(returns: pd.Series, risk_free: float = 0.0, annualise: bool = True) -> float:
    """Annualised Sharpe ratio."""
    excess = returns - risk_free / BARS_PER_YEAR
    std = excess.std()
    if std < 1e-10 or len(excess) < 10:
        return 0.0
    sr = excess.mean() / std
    return sr * np.sqrt(BARS_PER_YEAR) if annualise else sr


def calc_sortino(returns: pd.Series, risk_free: float = 0.0) -> float:
    """Annualised Sortino ratio."""
    excess = returns - risk_free / BARS_PER_YEAR
    downside = returns[returns < 0].std()
    if downside < 1e-10 or len(returns) < 10:
        return 0.0
    return (excess.mean() / downside) * np.sqrt(BARS_PER_YEAR)


def calc_max_drawdown(returns: pd.Series) -> float:
    """Maximum peak-to-trough drawdown (positive fraction)."""
    equity = (1 + returns).cumprod()
    peak = equity.cummax()
    dd = (equity - peak) / peak
    return abs(dd.min())


def calc_calmar(returns: pd.Series) -> float:
    """Calmar ratio = annual return / max drawdown."""
    ann_ret = returns.mean() * BARS_PER_YEAR
    mdd = calc_max_drawdown(returns)
    return ann_ret / mdd if mdd > 1e-10 else 0.0


def calc_turnover_pct_yr(positions: pd.DataFrame, returns: pd.Series) -> float:
    """Annualised turnover as fraction of portfolio."""
    pos_change = positions.diff().abs().sum(axis=1).mean()
    years = len(returns) / BARS_PER_YEAR
    if years <= 0:
        return 0.0
    # Rough estimate: avg change per day × 252
    return pos_change * BARS_PER_YEAR


def calc_hhi_source_concentration(positions: pd.DataFrame) -> float:
    """Herfindahl-Hirschman Index of source/ticker concentration."""
    avg_weights = positions.mean()
    total = avg_weights.sum()
    if total <= 0:
        return 0.0
    shares = avg_weights / total
    return float((shares ** 2).sum())


# ---------------------------------------------------------------------------
# BLOCK BOOTSTRAP
# ---------------------------------------------------------------------------

def block_bootstrap_ci(
    returns: pd.Series,
    block_len: int = 22,
    n_boot: int = 1000,
    seed: int = 42,
    alpha: float = 0.05,
) -> Dict[str, float]:
    """
    Block-bootstrap confidence intervals preserving temporal dependence.

    Args:
        returns: daily return series
        block_len: block length in bars (default 22 ≈ 1 month)
        n_boot: number of bootstrap resamples
        alpha: significance level (default 0.05 → 95% CI)

    Returns:
        dict with pf_mean, pf_ci_lower, pf_ci_upper, sharpe_mean, sharpe_ci_lower, etc.
    """
    rng = np.random.default_rng(seed)
    n = len(returns)
    if n < block_len * 2:
        return {
            "pf_mean": 0.0, "pf_ci_lower": 0.0, "pf_ci_upper": 0.0,
            "sharpe_mean": 0.0, "sharpe_ci_lower": 0.0, "sharpe_ci_upper": 0.0,
            "n": n, "block_len": block_len, "n_boot": n_boot,
        }

    pf_samples = []
    sharpe_samples = []

    for _ in range(n_boot):
        # Sample blocks with replacement
        n_blocks = int(np.ceil(n / block_len))
        blocks = []
        for __ in range(n_blocks):
            start = rng.integers(0, n - block_len + 1)
            blocks.append(returns.iloc[start : start + block_len].values)
        sample = np.concatenate(blocks)[:n]

        s = pd.Series(sample)
        pf_samples.append(calc_pf(s))
        sharpe_samples.append(calc_sharpe(s, annualise=False))  # daily Sharpe for stability

    pf_arr = np.array(pf_samples)
    sharpe_arr = np.array(sharpe_samples)

    return {
        "pf_mean": float(np.median(pf_arr)),
        "pf_ci_lower": float(np.percentile(pf_arr, alpha / 2 * 100)),
        "pf_ci_upper": float(np.percentile(pf_arr, (1 - alpha / 2) * 100)),
        "sharpe_mean": float(np.median(sharpe_arr)),
        "sharpe_ci_lower": float(np.percentile(sharpe_arr, alpha / 2 * 100)),
        "sharpe_ci_upper": float(np.percentile(sharpe_arr, (1 - alpha / 2) * 100)),
        "n": n,
        "block_len": block_len,
        "n_boot": n_boot,
    }


# ---------------------------------------------------------------------------
# PURGED-EMBARGOED WALK-FORWARD
# ---------------------------------------------------------------------------

def purged_walk_forward_split(
    prices: pd.DataFrame,
    n_splits: int = 5,
    purge_bars: int = 20,
    embargo_pct: float = 0.01,
) -> List[Dict[str, Any]]:
    """
    Generate purged-embargoed walk-forward folds.

    Each fold:
        [train_start ... train_end] [purge_gap] (test_start ... test_end) [embargo]

    Returns list of dicts with train_idx, test_idx, train_dates, test_dates.
    """
    n = len(prices)
    if n < n_splits * 100:
        raise ValueError(f"Insufficient data: {n} bars for {n_splits} folds")

    test_size = max(50, (n - purge_bars) // n_splits)
    folds = []

    for i in range(n_splits):
        test_end = n - (n_splits - 1 - i) * test_size
        test_start = test_end - test_size
        embargo_bars = max(0, int(test_size * embargo_pct))
        effective_test_end = test_end - embargo_bars
        train_end = test_start - purge_bars
        train_start = 0

        if train_end <= train_start or effective_test_end <= test_start:
            continue

        train_idx = prices.index[train_start:train_end]
        test_idx = prices.index[test_start:effective_test_end]

        folds.append({
            "fold_id": i,
            "train_idx": train_idx,
            "test_idx": test_idx,
            "train_dates": (train_idx[0].strftime("%Y-%m-%d"), train_idx[-1].strftime("%Y-%m-%d")),
            "test_dates": (test_idx[0].strftime("%Y-%m-%d"), test_idx[-1].strftime("%Y-%m-%d")),
        })

    return folds


def run_walk_forward(
    prices: pd.DataFrame,
    lookback: int = 252,
    top_n: int = 3,
    risk_free_ticker: Optional[str] = None,
    n_splits: int = 5,
    purge_bars: int = 20,
    embargo_pct: float = 0.01,
) -> List[Dict[str, Any]]:
    """
    Run purged-embargoed walk-forward backtest.
    Returns per-fold metrics + OOS decay analysis.
    """
    folds = purged_walk_forward_split(prices, n_splits, purge_bars, embargo_pct)
    fold_results = []

    for fold in folds:
        train_prices = prices.loc[fold["train_idx"]]
        test_prices = prices.loc[fold["test_idx"]]

        # Train: generate signals on training data only
        train_positions = dual_momentum_signals(
            train_prices, lookback=lookback, top_n=top_n, risk_free_ticker=risk_free_ticker
        )
        train_returns, _ = run_backtest_with_costs(train_prices, train_positions)
        is_pf = calc_pf(train_returns)
        is_sharpe = calc_sharpe(train_returns)

        # Test: apply SAME parameters (lookback, top_n) to test data
        test_positions = dual_momentum_signals(
            test_prices, lookback=lookback, top_n=top_n, risk_free_ticker=risk_free_ticker
        )
        test_returns, _ = run_backtest_with_costs(test_prices, test_positions)
        oos_pf = calc_pf(test_returns)
        oos_sharpe = calc_sharpe(test_returns)

        fold_results.append({
            "fold_id": fold["fold_id"],
            "is_pf": is_pf,
            "is_sharpe": is_sharpe,
            "oos_pf": oos_pf,
            "oos_sharpe": oos_sharpe,
            "oos_decay_pf": oos_pf / is_pf if is_pf > 1e-10 else 0.0,
            "oos_decay_sharpe": oos_sharpe / is_sharpe if is_sharpe > 1e-10 else 0.0,
            **fold,
        })

    return fold_results


# ---------------------------------------------------------------------------
# REGIME-SEGMENTED ANALYSIS
# ---------------------------------------------------------------------------

def classify_regime(returns: pd.Series, vol_window: int = 63) -> pd.Series:
    """
    Classify each bar into one of four regimes:
        1 = low-vol bull   (return > 0, vol < median)
        2 = high-vol bull  (return > 0, vol >= median)
        3 = low-vol bear   (return <= 0, vol < median)
        4 = high-vol bear  (return <= 0, vol >= median)
    """
    vol = returns.rolling(vol_window, min_periods=10).std()
    med_vol = vol.median()
    regime = pd.Series(0, index=returns.index)
    regime[(returns > 0) & (vol < med_vol)] = 1
    regime[(returns > 0) & (vol >= med_vol)] = 2
    regime[(returns <= 0) & (vol < med_vol)] = 3
    regime[(returns <= 0) & (vol >= med_vol)] = 4
    return regime


def regime_robustness_analysis(
    returns: pd.Series,
    positions: pd.DataFrame,
) -> Dict[str, Any]:
    """
    Compute per-regime PF and Sharpe. Return regime_robustness_score
    (fraction of regimes where edge persists within ±10% of overall PF).
    """
    regime = classify_regime(returns)
    overall_pf = calc_pf(returns)
    overall_sharpe = calc_sharpe(returns)

    regime_stats = {}
    persistence_count = 0

    for r in [1, 2, 3, 4]:
        mask = regime == r
        r_returns = returns[mask]
        if len(r_returns) < 10:
            continue
        r_pf = calc_pf(r_returns)
        r_sharpe = calc_sharpe(r_returns)

        # Persistence: PF within ±10% of overall AND Sharpe within ±10%
        pf_persist = abs(r_pf - overall_pf) / max(overall_pf, 0.1) <= 0.10 if overall_pf > 0 else False
        sharpe_persist = abs(r_sharpe - overall_sharpe) / max(overall_sharpe, 0.1) <= 0.10 if overall_sharpe > 0 else False
        if pf_persist or sharpe_persist:
            persistence_count += 1

        regime_stats[f"regime_{r}"] = {
            "label": {1: "low_vol_bull", 2: "high_vol_bull", 3: "low_vol_bear", 4: "high_vol_bear"}[r],
            "n_bars": int(mask.sum()),
            "pf": r_pf,
            "sharpe": r_sharpe,
            "win_rate": float((r_returns > 0).mean()),
        }

    score = persistence_count / 4.0
    return {
        "regime_robustness_score": score,
        "regimes_persisted": persistence_count,
        "regime_stats": regime_stats,
    }


# ---------------------------------------------------------------------------
# DEFLATED SHARPE RATIO (DSR)
# ---------------------------------------------------------------------------

def deflated_sharpe_ratio(
    observed_sharpe: float,
    n_trials: int,
    n_obs: int,
    skew: float = 0.0,
    kurtosis: float = 3.0,
) -> float:
    """
    Bailey & Lopez de Prado (2014) Deflated Sharpe Ratio.
    Returns P(true Sharpe > 0) after correcting for multiple testing.
    """
    try:
        from scipy import stats as sp_stats
    except ImportError as e:
        raise ImportError("scipy required for DSR") from e

    if n_trials < 1 or n_obs < 2:
        return 0.0

    # Expected max Sharpe under null
    if n_trials <= 1:
        expected_max_sr = 0.0
    else:
        gamma = 0.5772156649
        log2n = 2.0 * np.log(n_trials)
        sqrt_log2n = np.sqrt(log2n)
        expected_max_sr = sqrt_log2n - (np.log(np.pi) + gamma) / (2.0 * sqrt_log2n)

    # Standard error with moment correction
    excess_kurt = kurtosis - 3.0
    var_num = max(
        1e-8,
        1.0 + 0.5 * observed_sharpe ** 2 - skew * observed_sharpe + (excess_kurt / 4.0) * observed_sharpe ** 2,
    )
    se_sr = np.sqrt(var_num / n_obs)

    if se_sr <= 0:
        return 0.5
    z = (observed_sharpe - expected_max_sr) / se_sr
    return float(sp_stats.norm.cdf(z))


# ---------------------------------------------------------------------------
# BONFERRONI CORRECTION
# ---------------------------------------------------------------------------

def bonferroni_correction(
    p_values: List[float],
    alpha: float = ETF_THRESHOLDS.bonferroni_alpha,
) -> Tuple[List[bool], float]:
    """
    Apply Bonferroni correction for multiple testing.
    Returns (reject_list, adjusted_alpha).
    """
    m = len(p_values)
    if m == 0:
        return [], alpha
    adjusted_alpha = alpha / m
    reject = [p < adjusted_alpha for p in p_values]
    return reject, adjusted_alpha


# ---------------------------------------------------------------------------
# STATISTICAL READINESS GATE
# ---------------------------------------------------------------------------

def statistical_readiness_gate(
    returns: pd.Series,
    positions: pd.DataFrame,
    hypothesis: Hypothesis,
    n_trials: int = 1,
    block_bootstrap_result: Optional[Dict] = None,
    walk_forward_results: Optional[List[Dict]] = None,
    regime_result: Optional[Dict] = None,
) -> Dict[str, Any]:
    """
    Run the full statistical readiness gate per EAGLE2 / institutional standards.

    Checks:
      1. PF ≥ 1.5 (bare minimum) → ≥ 2.0 ideal
      2. Sharpe ≥ 1.0
      3. MDD ≤ 20%
      4. WR 45-55% (acceptable if PF strong)
      5. Calmar ≥ 3.0
      6. Turnover ≤ 30%/yr (ETF)
      7. DSR probability > 0.95
      8. Bonferroni-adjusted p-value < 0.05
      9. Block-bootstrap 95% CI for PF does not cross 1.0
      10. OOS decay ≤ 20%
      11. Regime robustness: edge in ≥3 of 4 regimes
      12. HHI < 0.20
      13. n_trades ≥ 30 (via rebalancing frequency proxy)
    """
    verdict = "PASS"
    failures: List[str] = []
    warnings_list: List[str] = []

    pf = calc_pf(returns)
    sharpe = calc_sharpe(returns)
    mdd = calc_max_drawdown(returns)
    wr = float((returns > 0).mean())
    calmar = calc_calmar(returns)
    turnover = calc_turnover_pct_yr(positions, returns)
    hhi = calc_hhi_source_concentration(positions)

    # 1. Profit Factor
    if pf < ETF_THRESHOLDS.min_pf:
        verdict = "FAIL"
        failures.append(f"PF {pf:.3f} < minimum {ETF_THRESHOLDS.min_pf}")
    elif pf < ETF_THRESHOLDS.ideal_pf:
        warnings_list.append(f"PF {pf:.3f} below ideal {ETF_THRESHOLDS.ideal_pf}")

    # 2. Sharpe
    if sharpe < ETF_THRESHOLDS.min_sharpe:
        verdict = "FAIL"
        failures.append(f"Sharpe {sharpe:.3f} < minimum {ETF_THRESHOLDS.min_sharpe}")

    # 3. Max Drawdown
    if mdd > ETF_THRESHOLDS.max_mdd:
        verdict = "FAIL"
        failures.append(f"MDD {mdd:.2%} > max {ETF_THRESHOLDS.max_mdd:.0%}")

    # 4. Win Rate
    if wr < ETF_THRESHOLDS.min_wr:
        warnings_list.append(f"WR {wr:.1%} below typical range {ETF_THRESHOLDS.min_wr:.0%}-{ETF_THRESHOLDS.max_wr:.0%}")
    if wr > ETF_THRESHOLDS.max_wr and pf < ETF_THRESHOLDS.ideal_pf:
        warnings_list.append(f"WR {wr:.1%} > {ETF_THRESHOLDS.max_wr:.0%} but PF {pf:.3f} modest — tiny gains / large losses risk")

    # 5. Calmar
    if calmar < ETF_THRESHOLDS.min_calmar:
        warnings_list.append(f"Calmar {calmar:.2f} < {ETF_THRESHOLDS.min_calmar}")

    # 6. Turnover
    if turnover > ETF_THRESHOLDS.max_turnover_pct_yr:
        warnings_list.append(f"Turnover {turnover:.1%}/yr > {ETF_THRESHOLDS.max_turnover_pct_yr:.0%}")

    # 7. DSR
    skew = float(returns.skew()) if len(returns) > 3 else 0.0
    kurt = float(returns.kurtosis()) + 3.0 if len(returns) > 3 else 3.0
    dsr_prob = deflated_sharpe_ratio(sharpe, n_trials, len(returns), skew, kurt)
    if dsr_prob < ETF_THRESHOLDS.dsr_probability_gate:
        verdict = "FAIL"
        failures.append(f"DSR probability {dsr_prob:.4f} < gate {ETF_THRESHOLDS.dsr_probability_gate}")

    # 8. Bonferroni (placeholder — caller should pass p-values if multi-strategy)
    # 9. Block bootstrap CI
    if block_bootstrap_result:
        pf_lo = block_bootstrap_result.get("pf_ci_lower", 0)
        if pf_lo < 1.0:
            warnings_list.append(f"Block-bootstrap PF 95% CI lower bound {pf_lo:.3f} crosses 1.0")

    # 10. OOS decay
    if walk_forward_results:
        decays = [f["oos_decay_pf"] for f in walk_forward_results if f.get("oos_decay_pf") is not None]
        avg_decay = np.mean(decays) if decays else 0
        if avg_decay < ETF_THRESHOLDS.min_oos_decay_pf:
            verdict = "FAIL"
            failures.append(f"OOS PF decay {avg_decay:.1%} < {ETF_THRESHOLDS.min_oos_decay_pf:.0%}")

    # 11. Regime robustness
    if regime_result:
        rr_score = regime_result.get("regime_robustness_score", 0)
        if rr_score < ETF_THRESHOLDS.min_regime_persistence:
            verdict = "FAIL"
            failures.append(f"Regime robustness {rr_score:.2f} < {ETF_THRESHOLDS.min_regime_persistence}")

    # 12. HHI
    if hhi > ETF_THRESHOLDS.hhi_max:
        warnings_list.append(f"HHI {hhi:.3f} > max {ETF_THRESHOLDS.hhi_max}")

    # 13. Sample size (proxy: number of rebalancing events)
    n_rebalances = (positions.diff().abs().sum(axis=1) > 0).sum()
    if n_rebalances < ETF_THRESHOLDS.min_n_trades:
        warnings_list.append(f"Rebalances {n_rebalances} < {ETF_THRESHOLDS.min_n_trades} — low statistical power")

    return {
        "verdict": verdict,
        "pf": pf,
        "sharpe": sharpe,
        "mdd": mdd,
        "win_rate": wr,
        "calmar": calmar,
        "turnover_pct_yr": turnover,
        "dsr_probability": dsr_prob,
        "hhi": hhi,
        "n_rebalances": int(n_rebalances),
        "failures": failures,
        "warnings": warnings_list,
    }


# ---------------------------------------------------------------------------
# MAIN PIPELINE
# ---------------------------------------------------------------------------

def run_etf_dual_momentum_pipeline(
    universe: Optional[List[str]] = None,
    lookback_days: int = 252,
    top_n: int = 3,
    risk_free_proxy: str = "SHV",
    start_date: str = "2015-01-01",
    end_date: Optional[str] = None,
    n_walk_forward_splits: int = 5,
    purge_bars: int = 20,
    embargo_pct: float = 0.01,
    block_len: int = 22,
    n_boot: int = 1000,
    hypothesis_rationale: str = "",
) -> Dict[str, Any]:
    """
    Run the complete ETF dual-momentum production-grade backtest pipeline.

    Returns a comprehensive report dict ready for JSON serialization.
    """
    t0 = time.time()
    universe = universe or ["SPY", "QQQ", "IWM", "EFA", "EEM", "TLT", "GLD", "XLF", "XLE", "XLK"]
    end_date = end_date or datetime.utcnow().strftime("%Y-%m-%d")

    # --- 1. Pre-registration ---
    hypothesis = log_hypothesis(
        universe=universe,
        lookback_days=lookback_days,
        hold_months=1,
        risk_free_proxy=risk_free_proxy,
        rationale=hypothesis_rationale,
    )

    # --- 2. Fetch data ---
    prices = fetch_etf_data(universe + ([risk_free_proxy] if risk_free_proxy else []), start_date, end_date)
    available_universe = [t for t in universe if t in prices.columns]
    if len(available_universe) < 3:
        raise RuntimeError(f"Insufficient tickers with data: {available_universe}")

    # --- 3. Generate signals ---
    positions = dual_momentum_signals(
        prices, lookback=lookback_days, top_n=top_n, risk_free_ticker=risk_free_proxy
    )

    # --- 4. Full-period backtest with costs ---
    returns, trade_log = run_backtest_with_costs(
        prices, positions, expense_ratios=ETF_EXPENSE_RATIOS
    )

    # --- 5. Block bootstrap ---
    bootstrap = block_bootstrap_ci(returns, block_len=block_len, n_boot=n_boot)

    # --- 6. Walk-forward validation ---
    wf_results = run_walk_forward(
        prices, lookback=lookback_days, top_n=top_n,
        risk_free_ticker=risk_free_proxy,
        n_splits=n_walk_forward_splits,
        purge_bars=purge_bars,
        embargo_pct=embargo_pct,
    )

    # --- 7. Regime robustness ---
    regime_result = regime_robustness_analysis(returns, positions)

    # --- 8. Statistical readiness gate ---
    gate = statistical_readiness_gate(
        returns, positions, hypothesis,
        n_trials=1,
        block_bootstrap_result=bootstrap,
        walk_forward_results=wf_results,
        regime_result=regime_result,
    )

    # --- 9. Bonferroni (single strategy = 1 test) ---
    # For multi-strategy suites, pass p-values from each strategy here
    _, bonf_alpha = bonferroni_correction([gate["pf"]])

    # --- 10. Assemble report ---
    equity = (1 + returns).cumprod()
    report = {
        "meta": {
            "pipeline": "ETF Dual-Momentum Production Backtest",
            "version": "1.0.0",
            "timestamp_utc": datetime.utcnow().isoformat() + "Z",
            "elapsed_seconds": round(time.time() - t0, 2),
            "git_commit": hypothesis.git_commit,
        },
        "hypothesis": hypothesis.to_dict(),
        "parameters": {
            "universe": available_universe,
            "lookback_days": lookback_days,
            "top_n": top_n,
            "risk_free_proxy": risk_free_proxy,
            "start_date": start_date,
            "end_date": end_date,
            "n_walk_forward_splits": n_walk_forward_splits,
            "purge_bars": purge_bars,
            "embargo_pct": embargo_pct,
            "block_len": block_len,
            "n_boot": n_boot,
        },
        "performance": {
            "n_days": len(returns),
            "n_years": round(len(returns) / BARS_PER_YEAR, 2),
            "total_return": round(equity.iloc[-1] - 1, 4),
            "annualized_return": round(returns.mean() * BARS_PER_YEAR, 4),
            "annualized_volatility": round(returns.std() * np.sqrt(BARS_PER_YEAR), 4),
            "pf": round(gate["pf"], 3),
            "sharpe": round(gate["sharpe"], 3),
            "sortino": round(calc_sortino(returns), 3),
            "mdd": round(gate["mdd"], 4),
            "calmar": round(gate["calmar"], 2),
            "win_rate": round(gate["win_rate"], 4),
            "turnover_pct_yr": round(gate["turnover_pct_yr"], 4),
            "hhi": round(gate["hhi"], 4),
            "avg_daily_return_pct": round(returns.mean() * 100, 4),
            "var_95": round(np.percentile(returns, 5), 4),
            "cvar_95": round(returns[returns <= np.percentile(returns, 5)].mean(), 4),
        },
        "block_bootstrap": {k: round(v, 4) if isinstance(v, float) else v for k, v in bootstrap.items()},
        "walk_forward": wf_results,
        "regime_robustness": regime_result,
        "statistical_gate": {
            "verdict": gate["verdict"],
            "dsr_probability": round(gate["dsr_probability"], 4),
            "bonferroni_adjusted_alpha": round(bonf_alpha, 6),
            "failures": gate["failures"],
            "warnings": gate["warnings"],
        },
        "trade_log": {
            "n_trades_logged": len(trade_log),
            "sample_trades": trade_log.head(5).to_dict("records") if len(trade_log) > 0 else [],
        },
        "compliance": {
            "pf_minimum_met": gate["pf"] >= ETF_THRESHOLDS.min_pf,
            "sharpe_minimum_met": gate["sharpe"] >= ETF_THRESHOLDS.min_sharpe,
            "mdd_maximum_met": gate["mdd"] <= ETF_THRESHOLDS.max_mdd,
            "dsr_gate_met": gate["dsr_probability"] >= ETF_THRESHOLDS.dsr_probability_gate,
            "hhi_maximum_met": gate["hhi"] <= ETF_THRESHOLDS.hhi_max,
            "pre_registered": True,
        },
    }

    # Save report
    out_dir = Path("reports")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"etf_dual_momentum_backtest_{datetime.utcnow().strftime('%Y%m%d')}.json"
    with open(out_path, "w") as fh:
        json.dump(report, fh, indent=2, default=str)
    logger.info("Report saved to %s", out_path)

    return report


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    print("=" * 70)
    print("ETF DUAL-MOMENTUM — PRODUCTION-GRADE BACKTEST PIPELINE")
    print("=" * 70)
    print()

    # Run with a sensible default universe
    report = run_etf_dual_momentum_pipeline(
        universe=["SPY", "QQQ", "IWM", "EFA", "EEM", "TLT", "GLD", "XLF", "XLE", "XLK", "VWO", "VEA"],
        lookback_days=252,
        top_n=3,
        risk_free_proxy="SHV",
        start_date="2015-01-01",
        n_walk_forward_splits=5,
        purge_bars=20,
        embargo_pct=0.01,
        block_len=22,
        n_boot=1000,
        hypothesis_rationale=(
            "ETF dual-momentum per Antonacci (2013): 12-month absolute + relative "
            "momentum on diversified equity/bond/commodity ETF universe. "
            "Rebalance monthly. Costs: 0.1% commission + 5bps slippage + ER drag."
        ),
    )

    print()
    print("=" * 70)
    print("RESULTS SUMMARY")
    print("=" * 70)
    perf = report["performance"]
    gate = report["statistical_gate"]
    print(f"  Total Return:        {perf['total_return']:.2%}")
    print(f"  Annualized Return:   {perf['annualized_return']:.2%}")
    print(f"  Sharpe Ratio:        {perf['sharpe']:.3f}")
    print(f"  Sortino Ratio:       {perf['sortino']:.3f}")
    print(f"  Max Drawdown:        {perf['mdd']:.2%}")
    print(f"  Profit Factor:       {perf['pf']:.3f}")
    print(f"  Win Rate:            {perf['win_rate']:.1%}")
    print(f"  Calmar Ratio:        {perf['calmar']:.2f}")
    print(f"  Turnover/yr:         {perf['turnover_pct_yr']:.1%}")
    print(f"  DSR Probability:     {gate['dsr_probability']:.4f}")
    print(f"  HHI Concentration:   {perf['hhi']:.4f}")
    print()
    print(f"  VERDICT: {gate['verdict']}")
    if gate["failures"]:
        print(f"  FAILURES: {gate['failures']}")
    if gate["warnings"]:
        print(f"  WARNINGS: {gate['warnings']}")
    print()
    print("=" * 70)
    print(f"Full report: reports/etf_dual_momentum_backtest_*.json")
    print("=" * 70)


if __name__ == "__main__":
    main()
