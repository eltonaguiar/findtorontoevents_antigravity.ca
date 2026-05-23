"""Rolling decay monitoring for source-systems.

Tracks when a source-system's predictive edge is degrading, auto-detects
regime changes, and generates demotion recommendations.  The output is
JSON-serializable so it can be consumed directly by the audit dashboard.

Design principles:
1. Pure functions on numpy/pandas -- no heavy ML dependencies.
2. All outputs are JSON-serializable (floats, ints, strings, dicts).
3. Edge cases (empty input, all zeros, insufficient history) degrade
   gracefully with logged warnings.
4. The decay_ratio < 0.5 threshold is the Two Sigma signal for auto-
   demotion; it can be overridden via config.

This module is OPT-IN.  Nothing in the production pick-generation path
imports it yet.  A follow-up PR will wire ``compute_decay_ratio`` into
the daily ``audit_sync`` cron and ``plot_decay_dashboard`` into the
``/audit`` page JSON feed.

Public API
----------
rolling_sharpe(returns, window=90) -> pd.Series
compute_decay_ratio(picks, short_window=90, long_window=365) -> dict
detect_regime_change(returns, method='hmm', n_regimes=4) -> dict
plot_decay_dashboard(picks_by_source, output_path=None) -> dict
demotion_recommendation(source_system, picks) -> dict
"""

from __future__ import annotations

import json
import logging
import math
import os
from datetime import datetime, timezone
from typing import Any

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

__all__ = [
    "rolling_sharpe",
    "compute_decay_ratio",
    "detect_regime_change",
    "plot_decay_dashboard",
    "demotion_recommendation",
]

# ---------------------------------------------------------------------------
# 1. Rolling Sharpe Ratio
# ---------------------------------------------------------------------------


def rolling_sharpe(
    returns: pd.Series | np.ndarray | list[float],
    window: int = 90,
    ann_factor: float = 252.0,
) -> pd.Series:
    """Compute the annualized rolling Sharpe ratio.

    SR_t = (mean(returns_{t-window+1:t}) / std(returns)) * sqrt(ann_factor)

    Parameters
    ----------
    returns : pd.Series, np.ndarray, or list
        Periodic (e.g. daily) returns.  If a pandas Series, the index is
        preserved in the output.
    window : int, default 90
        Rolling window length in observations.
    ann_factor : float, default 252.0
        Annualization factor.  252 for daily, 52 for weekly, 12 for monthly.

    Returns
    -------
    pd.Series
        Rolling Sharpe ratio indexed like the input.  Leading ``window-1``
        values are NaN.  If the input has fewer than ``window`` finite
        observations, returns a Series of NaN.
    """
    s = pd.Series(returns, dtype=np.float64)
    if s.size < 2:
        logger.warning("rolling_sharpe: need >= 2 observations, got %d", s.size)
        return pd.Series(dtype=np.float64)
    if window < 2:
        logger.warning("rolling_sharpe: window must be >= 2, got %d; using 2", window)
        window = 2

    rolling_mean = s.rolling(window=window, min_periods=window).mean()
    rolling_std = s.rolling(window=window, min_periods=window).std(ddof=1)

    # Avoid division by zero
    rolling_std = rolling_std.replace(0.0, np.nan).clip(lower=1e-12)

    sharpe = (rolling_mean / rolling_std) * math.sqrt(ann_factor)
    return sharpe


# ---------------------------------------------------------------------------
# 2. Decay Ratio (short-window Sharpe / long-window Sharpe)
# ---------------------------------------------------------------------------


def compute_decay_ratio(
    picks: list[dict[str, Any]] | pd.DataFrame,
    short_window: int = 90,
    long_window: int = 365,
    ann_factor: float = 252.0,
) -> dict[str, Any]:
    """Compute the decay ratio of a source-system's edge.

    decay_ratio = sharpe_short / sharpe_long

    Interpretation:
    * ratio >= 1.0   : edge is improving or stable
    * 0.5 <= ratio < 1.0 : mild decay, monitor closely
    * ratio < 0.5    : severe decay (Two Sigma auto-demotion signal)
    * ratio <= 0.0   : edge has inverted (short Sharpe is negative)

    Parameters
    ----------
    picks : list[dict] or pd.DataFrame
        Trade records for the source-system.  Each record must contain
        ``'pnl'`` (float) and ``'date'`` (timestamp or string).  If a
        DataFrame, columns ``'pnl'`` and ``'date'`` are expected.
    short_window : int, default 90
        Short-term rolling window in days.
    long_window : int, default 365
        Long-term rolling window in days.
    ann_factor : float, default 252.0
        Annualization factor for Sharpe computation.

    Returns
    -------
    dict
        JSON-serializable result with keys:
        - ``decay_ratio`` (float)
        - ``sharpe_short`` (float)
        - ``sharpe_long`` (float)
        - ``n_short`` (int) -- observations in short window
        - ``n_long`` (int) -- observations in long window
        - ``timestamp_utc`` (str) -- ISO-8601 timestamp of computation
    """
    df = _normalize_picks(picks)
    if df is None or df.empty:
        return _empty_decay_result()

    # Compute daily returns from PnL
    returns = df["pnl"].dropna().astype(np.float64)
    if returns.size < 2:
        logger.warning("compute_decay_ratio: insufficient PnL data")
        return _empty_decay_result()

    # Short-window Sharpe (most recent *short_window* observations)
    short_returns = returns.iloc[-short_window:]
    sharpe_short = _sharpe_from_series(short_returns, ann_factor)

    # Long-window Sharpe (most recent *long_window* observations)
    long_returns = returns.iloc[-long_window:]
    sharpe_long = _sharpe_from_series(long_returns, ann_factor)

    # Decay ratio
    if abs(sharpe_long) < 1e-12:
        decay_ratio = 0.0 if abs(sharpe_short) < 1e-12 else 999.0
    else:
        decay_ratio = sharpe_short / sharpe_long

    return {
        "decay_ratio": float(decay_ratio),
        "sharpe_short": float(sharpe_short),
        "sharpe_long": float(sharpe_long),
        "n_short": int(short_returns.size),
        "n_long": int(long_returns.size),
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    }


# ---------------------------------------------------------------------------
# 3. Regime Change Detection
# ---------------------------------------------------------------------------


def detect_regime_change(
    returns: pd.Series | np.ndarray | list[float],
    method: str = "hmm",
    n_regimes: int = 4,
    threshold_low: float = -0.005,
    threshold_high: float = 0.005,
) -> dict[str, Any]:
    """Detect the current market regime from return characteristics.

    Two methods are supported:

    * ``'threshold'`` -- Simple volatility + drift thresholding.  Classifies
      the most recent window into one of four regimes:
      - regime_0: low vol, positive drift (ideal)
      - regime_1: low vol, negative drift (boring bear)
      - regime_2: high vol, positive drift (risky rally)
      - regime_3: high vol, negative drift (crisis)

    * ``'hmm'`` -- Hidden Markov Model placeholder.  Currently falls back
      to the threshold method with a logged note.  A future PR will wire
      in ``hmmlearn.hmm.GaussianHMM`` when that dependency is approved.

    Parameters
    ----------
    returns : pd.Series, np.ndarray, or list
        Periodic returns.
    method : str, default "hmm"
        Detection method: ``'threshold'`` or ``'hmm'``.
    n_regimes : int, default 4
        Number of regimes.  Currently only 4 is supported.
    threshold_low : float, default -0.005
        Daily return threshold for negative drift (in decimal).
    threshold_high : float, default 0.005
        Daily return threshold for positive drift (in decimal).

    Returns
    -------
    dict
        JSON-serializable result with keys:
        - ``regime_label`` (str) -- e.g. "regime_0"
        - ``regime_description`` (str) -- human-readable regime name
        - ``mean_return`` (float)
        - ``volatility`` (float)
        - ``method`` (str)
        - ``timestamp_utc`` (str)
    """
    s = pd.Series(returns, dtype=np.float64).dropna()
    if s.size < 10:
        logger.warning("detect_regime_change: need >= 10 observations, got %d", s.size)
        return {
            "regime_label": "unknown",
            "regime_description": "insufficient data",
            "mean_return": 0.0,
            "volatility": 0.0,
            "method": method,
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        }

    if method == "hmm":
        # Placeholder: fall back to threshold method until hmmlearn is wired
        logger.debug("detect_regime_change: HMM not yet wired; using threshold method")
        method = "threshold"

    mean_ret = float(s.mean())
    vol = float(s.std(ddof=1))
    vol_threshold = 0.015  # ~24% annualized daily vol

    if method == "threshold":
        high_vol = vol > vol_threshold
        pos_drift = mean_ret > threshold_high
        neg_drift = mean_ret < threshold_low

        if not high_vol and pos_drift:
            label, desc = "regime_0", "low_vol_positive_drift"
        elif not high_vol and neg_drift:
            label, desc = "regime_1", "low_vol_negative_drift"
        elif high_vol and pos_drift:
            label, desc = "regime_2", "high_vol_positive_drift"
        elif high_vol and neg_drift:
            label, desc = "regime_3", "high_vol_negative_drift"
        else:
            label, desc = "regime_0", "low_vol_positive_drift"  # default neutral
    else:
        logger.warning("detect_regime_change: unknown method '%s', using threshold", method)
        label, desc = "regime_0", "low_vol_positive_drift"

    return {
        "regime_label": label,
        "regime_description": desc,
        "mean_return": round(mean_ret, 6),
        "volatility": round(vol, 6),
        "method": method,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    }


# ---------------------------------------------------------------------------
# 4. Decay Dashboard JSON Generator
# ---------------------------------------------------------------------------


def plot_decay_dashboard(
    picks_by_source: dict[str, list[dict[str, Any]] | pd.DataFrame],
    output_path: str | None = None,
    demotion_threshold: float = 0.5,
) -> dict[str, Any]:
    """Generate decay dashboard data for the audit page.

    Computes decay ratios, regime labels, and demotion recommendations
    for every source-system in one pass.  The returned dict is designed
    to be serialized to JSON and consumed by the frontend ``/audit``
    dashboard.

    Parameters
    ----------
    picks_by_source : dict[str, list[dict] or pd.DataFrame]
        Map from source-system name to its trade records.
    output_path : str or None, default None
        If provided, the dashboard dict is written as indented JSON to
        this path.
    demotion_threshold : float, default 0.5
        Decay ratio below which a source is flagged for demotion.

    Returns
    -------
    dict
        Dashboard payload with keys:
        - ``sources`` : list of per-source detail dicts
        - ``summary`` : aggregate statistics (mean decay, count flagged)
        - ``generated_at`` : ISO-8601 UTC timestamp
    """
    sources: list[dict[str, Any]] = []
    decay_ratios: list[float] = []
    flagged_count = 0

    for source_name, picks in picks_by_source.items():
        decay = compute_decay_ratio(picks)
        regime = detect_regime_change(
            _extract_returns(picks), method="threshold"
        )
        demo = demotion_recommendation(source_name, picks, demotion_threshold)

        entry = {
            "source": source_name,
            "decay_ratio": round(decay["decay_ratio"], 4),
            "sharpe_short": round(decay["sharpe_short"], 4),
            "sharpe_long": round(decay["sharpe_long"], 4),
            "regime": regime["regime_label"],
            "regime_description": regime["regime_description"],
            "should_demote": demo["should_demote"],
            "demotion_reason": demo["reason"],
        }
        sources.append(entry)
        decay_ratios.append(decay["decay_ratio"])
        if demo["should_demote"]:
            flagged_count += 1

    dashboard = {
        "sources": sources,
        "summary": {
            "n_sources": len(sources),
            "mean_decay_ratio": round(float(np.mean(decay_ratios)), 4) if decay_ratios else 0.0,
            "flagged_for_demotion": flagged_count,
            "demotion_threshold": demotion_threshold,
        },
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    if output_path:
        try:
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(dashboard, f, indent=2, default=str)
            logger.info("Decay dashboard written to %s", output_path)
        except OSError as exc:
            logger.error("Failed to write decay dashboard: %s", exc)

    return dashboard


# ---------------------------------------------------------------------------
# 5. Demotion Recommendation
# ---------------------------------------------------------------------------


def demotion_recommendation(
    source_system: str,
    picks: list[dict[str, Any]] | pd.DataFrame,
    demotion_threshold: float = 0.5,
) -> dict[str, Any]:
    """Return a demotion recommendation for a source-system.

    A source should be demoted when:
    1. Its decay_ratio falls below the threshold (default 0.5).
    2. Its short-window Sharpe is negative (edge has inverted).
    3. It has fewer than 30 observations (insufficient data to trust).

    Parameters
    ----------
    source_system : str
        Name of the source-system (e.g. ``'openclaw'``).
    picks : list[dict] or pd.DataFrame
        Trade records for the source.
    demotion_threshold : float, default 0.5
        Decay ratio threshold for auto-demotion.

    Returns
    -------
    dict
        JSON-serializable recommendation with keys:
        - ``should_demote`` (bool)
        - ``reason`` (str)
        - ``decay_ratio`` (float)
        - ``source`` (str)
    """
    decay = compute_decay_ratio(picks)
    ratio = decay["decay_ratio"]
    sharpe_short = decay["sharpe_short"]
    n_short = decay["n_short"]

    should_demote = False
    reasons: list[str] = []

    if ratio < 0.0:
        should_demote = True
        reasons.append("edge_inverted")
    elif ratio < demotion_threshold:
        should_demote = True
        reasons.append(f"decay_ratio_{ratio:.3f}_below_{demotion_threshold}")

    if sharpe_short < -0.5:
        should_demote = True
        reasons.append("sharpe_deeply_negative")

    if n_short < 30:
        should_demote = True
        reasons.append("insufficient_data")

    reason = "; ".join(reasons) if reasons else "healthy"

    return {
        "should_demote": should_demote,
        "reason": reason,
        "decay_ratio": round(ratio, 4),
        "source": source_system,
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _normalize_picks(
    picks: list[dict[str, Any]] | pd.DataFrame,
) -> pd.DataFrame | None:
    """Normalize picks input to a DataFrame with 'pnl' and 'date' columns."""
    if isinstance(picks, pd.DataFrame):
        df = picks.copy()
        if "pnl" not in df.columns:
            logger.warning("_normalize_picks: DataFrame missing 'pnl' column")
            return None
        return df
    elif isinstance(picks, list):
        if not picks:
            return None
        df = pd.DataFrame(picks)
        if "pnl" not in df.columns:
            logger.warning("_normalize_picks: list dicts missing 'pnl' key")
            return None
        return df
    else:
        logger.warning("_normalize_picks: unexpected type %s", type(picks))
        return None


def _sharpe_from_series(returns: pd.Series, ann_factor: float) -> float:
    """Annualized Sharpe from a pandas Series of returns."""
    if returns.size < 2:
        return 0.0
    mu = returns.mean()
    sd = returns.std(ddof=1)
    if sd < 1e-12:
        return 0.0
    return float((mu / sd) * math.sqrt(ann_factor))


def _extract_returns(
    picks: list[dict[str, Any]] | pd.DataFrame,
) -> pd.Series:
    """Extract the PnL series from picks for regime detection."""
    df = _normalize_picks(picks)
    if df is None or "pnl" not in df.columns:
        return pd.Series(dtype=np.float64)
    return df["pnl"].dropna().astype(np.float64)


def _empty_decay_result() -> dict[str, Any]:
    """Return a neutral decay result for degenerate inputs."""
    return {
        "decay_ratio": 1.0,
        "sharpe_short": 0.0,
        "sharpe_long": 0.0,
        "n_short": 0,
        "n_long": 0,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    }
