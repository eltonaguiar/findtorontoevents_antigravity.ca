"""
Enhanced Metrics Module
========================
Adds the missing risk metrics identified in the audit:
- Max Drawdown Duration (days in drawdown)
- Information Ratio (alpha per unit tracking error)
- Residual Analysis per asset class
- Feature Redundancy (VIF)
- PSI Drift Detection

These supplement the existing BacktestResult metrics in engine.py.

Author: Forensic Audit Implementation (PR #72)
Date: 2026-04-11
"""
import logging
import math
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# Missing Risk Metrics
# ═══════════════════════════════════════════════════════════════════════════════

def max_drawdown_duration(equity_curve: pd.Series) -> int:
    """
    Maximum number of days spent in drawdown.
    
    This was missing from engine.py's _compute_metrics().
    The engine computes max_drawdown_pct but not max_drawdown_duration_days.
    
    Args:
        equity_curve: Time-indexed equity series
        
    Returns:
        Maximum drawdown duration in calendar days
    """
    if equity_curve.empty or len(equity_curve) < 2:
        return 0
    
    peak = equity_curve.cummax()
    in_drawdown = equity_curve < peak
    
    if not in_drawdown.any():
        return 0
    
    # Find consecutive drawdown periods
    dd_start = None
    max_duration = 0
    
    for i, (date, is_dd) in enumerate(in_drawdown.items()):
        if is_dd and dd_start is None:
            dd_start = date
        elif not is_dd and dd_start is not None:
            duration = (date - dd_start).days
            max_duration = max(max_duration, duration)
            dd_start = None
    
    # Handle case where we're still in drawdown at end
    if dd_start is not None:
        duration = (equity_curve.index[-1] - dd_start).days
        max_duration = max(max_duration, duration)
    
    return max_duration


def information_ratio(
    returns: pd.Series,
    benchmark_returns: pd.Series,
    annualization_factor: float = 252,
) -> float:
    """
    Information Ratio = annualized(mean(active_returns)) / annualized(std(active_returns))
    
    This was missing from engine.py — needed for alpha assessment vs benchmark.
    
    Args:
        returns: Strategy daily returns
        benchmark_returns: Benchmark daily returns (aligned dates)
        annualization_factor: 252 for daily, 52 for weekly, 12 for monthly
        
    Returns:
        Annualized Information Ratio
    """
    # Align dates
    aligned = pd.DataFrame({
        "strategy": returns,
        "benchmark": benchmark_returns,
    }).dropna()
    
    if len(aligned) < 20:
        return 0.0
    
    active_returns = aligned["strategy"] - aligned["benchmark"]
    tracking_error = active_returns.std()
    
    if tracking_error < 1e-10:
        return 0.0
    
    return float(active_returns.mean() / tracking_error * np.sqrt(annualization_factor))


def omega_ratio(returns: pd.Series, threshold: float = 0.0) -> float:
    """
    Omega Ratio = P(return > threshold) weighted sum / P(return < threshold) weighted sum
    
    A more complete measure than Sharpe because it captures the entire
    return distribution, not just mean and variance.
    
    Omega > 1.0 = positive expected utility above threshold.
    """
    if len(returns) < 10:
        return 0.0
    
    gains = returns[returns > threshold] - threshold
    losses = threshold - returns[returns <= threshold]
    
    sum_losses = losses.sum()
    if sum_losses < 1e-10:
        return float("inf")
    
    return float(gains.sum() / sum_losses)


def tail_ratio(returns: pd.Series, percentile: float = 95) -> float:
    """
    Tail Ratio = |P95 / P5|
    
    Measures the fatness of the right tail relative to the left tail.
    > 1.0 means bigger gains than losses in the tails.
    """
    if len(returns) < 20:
        return 0.0
    
    upper = np.percentile(returns, percentile)
    lower = np.percentile(returns, 100 - percentile)
    
    if abs(lower) < 1e-10:
        return float("inf") if upper > 0 else 0.0
    
    return float(abs(upper / lower))


# ═══════════════════════════════════════════════════════════════════════════════
# Residual Analysis per Asset Class
# ═══════════════════════════════════════════════════════════════════════════════

def analyze_residuals(
    trades_by_asset_class: Dict[str, List[Dict]],
) -> Dict[str, Dict[str, Any]]:
    """
    Compute residual diagnostics per asset class.
    
    From audit Section 9.1: The system's prediction outputs reveal distinct
    error signatures by asset class (crypto fat-tails, equity near-normal, etc.)
    
    Args:
        trades_by_asset_class: {asset_class: [{"pnl_pct": float, ...}, ...]}
        
    Returns:
        Dict of asset_class -> diagnostic metrics
    """
    results = {}
    
    for asset_class, trades in trades_by_asset_class.items():
        pnls = np.array([t.get("pnl_pct", 0) for t in trades])
        
        if len(pnls) < 10:
            results[asset_class] = {
                "status": "insufficient_data",
                "n_trades": len(pnls),
            }
            continue
        
        # Basic statistics
        mean_pnl = float(np.mean(pnls))
        std_pnl = float(np.std(pnls))
        
        # Higher moments
        skewness = float(_skewness(pnls))
        excess_kurtosis = float(_excess_kurtosis(pnls))
        
        # Jarque-Bera test for normality
        jb_stat, jb_p = _jarque_bera(pnls)
        
        # Percentiles
        p1 = float(np.percentile(pnls, 1))
        p5 = float(np.percentile(pnls, 5))
        p25 = float(np.percentile(pnls, 25))
        p75 = float(np.percentile(pnls, 75))
        p95 = float(np.percentile(pnls, 95))
        p99 = float(np.percentile(pnls, 99))
        
        results[asset_class] = {
            "n_trades": len(pnls),
            "mean_pnl_pct": mean_pnl,
            "std_pnl_pct": std_pnl,
            "skewness": skewness,
            "excess_kurtosis": excess_kurtosis,
            "is_normal": jb_p > 0.05,
            "jarque_bera_stat": jb_stat,
            "jarque_bera_p": jb_p,
            "max_gain_pct": float(np.max(pnls)),
            "max_loss_pct": float(np.min(pnls)),
            "percentiles": {
                "p1": p1, "p5": p5, "p25": p25,
                "p75": p75, "p95": p95, "p99": p99,
            },
            "distribution_shape": _classify_distribution(skewness, excess_kurtosis),
            "risk_recommendation": _risk_recommendation(
                asset_class, skewness, excess_kurtosis, mean_pnl
            ),
        }
    
    return results


def _classify_distribution(skewness: float, excess_kurtosis: float) -> str:
    """Classify the return distribution shape."""
    shape_parts = []
    
    if excess_kurtosis > 3:
        shape_parts.append("heavy-tailed (leptokurtic)")
    elif excess_kurtosis < -0.5:
        shape_parts.append("thin-tailed (platykurtic)")
    else:
        shape_parts.append("near-normal tails")
    
    if skewness < -0.5:
        shape_parts.append("left-skewed (negative)")
    elif skewness > 0.5:
        shape_parts.append("right-skewed (positive)")
    else:
        shape_parts.append("approximately symmetric")
    
    return ", ".join(shape_parts)


def _risk_recommendation(
    asset_class: str, skew: float, kurt: float, mean_pnl: float
) -> str:
    """Generate a risk management recommendation based on residual analysis."""
    recs = []
    
    if kurt > 3:
        recs.append(
            f"Fat tails detected (excess kurtosis={kurt:.1f}). "
            f"Apply kurtosis penalty to Kelly sizing. Use wider stops."
        )
    
    if skew < -0.5:
        recs.append(
            f"Negative skew ({skew:.2f}). Losses are larger than gains. "
            f"Consider tighter hard stops or reduced position sizes."
        )
    
    if mean_pnl < 0:
        recs.append(
            f"Negative mean P&L ({mean_pnl:.2%}). "
            f"Strategy has negative expectancy. Do not deploy."
        )
    
    if not recs:
        recs.append("Distribution within acceptable parameters.")
    
    return " | ".join(recs)


# ═══════════════════════════════════════════════════════════════════════════════
# PSI Drift Detection
# ═══════════════════════════════════════════════════════════════════════════════

def compute_psi(
    expected: np.ndarray,
    actual: np.ndarray,
    buckets: int = 10,
) -> float:
    """
    Population Stability Index for drift detection.
    
    PSI < 0.10: No significant shift
    PSI 0.10-0.25: Moderate shift — investigate
    PSI > 0.25: Significant shift — retrain model
    
    Used in the monitoring dashboard (Section 9.3 of audit).
    
    Args:
        expected: Training/reference distribution
        actual: Current/production distribution
        buckets: Number of histogram bins
        
    Returns:
        PSI value (float, >= 0)
    """
    if len(expected) < buckets or len(actual) < buckets:
        return 0.0
    
    # Create buckets from expected distribution
    breakpoints = np.percentile(expected, np.linspace(0, 100, buckets + 1))
    breakpoints[0] = -np.inf
    breakpoints[-1] = np.inf
    
    expected_counts = np.histogram(expected, bins=breakpoints)[0]
    actual_counts = np.histogram(actual, bins=breakpoints)[0]
    
    # Convert to proportions with smoothing
    expected_pcts = (expected_counts + 1) / (len(expected) + buckets)
    actual_pcts = (actual_counts + 1) / (len(actual) + buckets)
    
    # PSI formula
    psi = np.sum((actual_pcts - expected_pcts) * np.log(actual_pcts / expected_pcts))
    
    return float(psi)


def psi_verdict(psi_value: float) -> Dict[str, str]:
    """Interpret a PSI value."""
    if psi_value < 0.10:
        return {
            "level": "stable",
            "action": "none",
            "message": f"PSI={psi_value:.4f} — No significant distribution shift.",
        }
    elif psi_value < 0.25:
        return {
            "level": "moderate_drift",
            "action": "investigate",
            "message": f"PSI={psi_value:.4f} — Moderate shift detected. "
                       f"Investigate feature distributions and model calibration.",
        }
    else:
        return {
            "level": "significant_drift",
            "action": "retrain",
            "message": f"PSI={psi_value:.4f} — Significant shift. "
                       f"Model is likely stale. Retrain on recent data.",
        }


def monitor_feature_drift(
    training_features: pd.DataFrame,
    production_features: pd.DataFrame,
    threshold: float = 0.25,
) -> Dict[str, Dict]:
    """
    Monitor PSI across all features.
    
    Args:
        training_features: Features from model training period
        production_features: Recent production features
        threshold: PSI threshold for alerting
        
    Returns:
        Dict of feature_name -> {psi, verdict, ...}
    """
    results = {}
    drifted_features = []
    
    for col in training_features.columns:
        if col not in production_features.columns:
            continue
        
        train_vals = training_features[col].dropna().values
        prod_vals = production_features[col].dropna().values
        
        if len(train_vals) < 20 or len(prod_vals) < 20:
            continue
        
        psi = compute_psi(train_vals, prod_vals)
        verdict = psi_verdict(psi)
        
        results[col] = {
            "psi": psi,
            **verdict,
        }
        
        if psi >= threshold:
            drifted_features.append(col)
    
    if drifted_features:
        logger.warning(
            f"DRIFT ALERT: {len(drifted_features)} features have PSI > {threshold}: "
            f"{', '.join(drifted_features[:5])}"
        )
    
    return results


# ═══════════════════════════════════════════════════════════════════════════════
# Feature Redundancy (VIF)
# ═══════════════════════════════════════════════════════════════════════════════

def compute_vif_simple(features: pd.DataFrame) -> pd.DataFrame:
    """
    Compute Variance Inflation Factor for each feature.
    
    VIF > 5: Moderate multicollinearity
    VIF > 10: Severe multicollinearity — consider dropping
    
    This is a simplified version that doesn't require statsmodels.
    For production, use statsmodels.stats.outliers_influence.variance_inflation_factor.
    
    Args:
        features: DataFrame of numeric features (no NaN)
        
    Returns:
        DataFrame with columns: feature, VIF, recommendation
    """
    features = features.dropna(axis=1, how="any").select_dtypes(include=[np.number])
    
    if features.shape[1] < 2:
        return pd.DataFrame(columns=["feature", "VIF", "recommendation"])
    
    # Standardize
    X = features.values
    X = (X - X.mean(axis=0)) / (X.std(axis=0) + 1e-10)
    
    results = []
    for i, col in enumerate(features.columns):
        # R² of regressing feature i on all other features
        others = np.delete(X, i, axis=1)
        
        # OLS: R² = 1 - SS_res / SS_tot
        if others.shape[1] == 0:
            vif = 1.0
        else:
            # Using numpy lstsq for simplicity
            try:
                coeffs, residuals, _, _ = np.linalg.lstsq(others, X[:, i], rcond=None)
                y_pred = others @ coeffs
                ss_res = np.sum((X[:, i] - y_pred) ** 2)
                ss_tot = np.sum((X[:, i] - X[:, i].mean()) ** 2)
                r_squared = 1 - ss_res / ss_tot if ss_tot > 0 else 0
                vif = 1 / (1 - r_squared) if r_squared < 1 else 999
            except np.linalg.LinAlgError:
                vif = 999
        
        if vif > 10:
            rec = "DROP — severe multicollinearity"
        elif vif > 5:
            rec = "INVESTIGATE — moderate multicollinearity"
        else:
            rec = "KEEP"
        
        results.append({"feature": col, "VIF": round(vif, 2), "recommendation": rec})
    
    df = pd.DataFrame(results).sort_values("VIF", ascending=False)
    
    n_drop = len(df[df["VIF"] > 10])
    if n_drop > 0:
        logger.info(f"VIF analysis: {n_drop} features recommended for removal (VIF > 10)")
    
    return df


def prune_features_by_vif(
    features: pd.DataFrame,
    max_vif: float = 10.0,
) -> List[str]:
    """
    Iteratively remove features with highest VIF until all are below threshold.
    
    From audit Section 9.4: Reduce from 70+ to 15-20 features.
    
    Args:
        features: Feature DataFrame
        max_vif: Maximum acceptable VIF
        
    Returns:
        List of feature names to keep
    """
    remaining = list(features.columns)
    dropped = []
    
    while len(remaining) > 2:
        vif_df = compute_vif_simple(features[remaining])
        
        if vif_df.empty:
            break
        
        worst_vif = vif_df.iloc[0]["VIF"]
        if worst_vif <= max_vif:
            break
        
        worst_feature = vif_df.iloc[0]["feature"]
        remaining.remove(worst_feature)
        dropped.append(worst_feature)
        
        logger.debug(f"VIF pruning: dropped {worst_feature} (VIF={worst_vif:.1f})")
    
    logger.info(
        f"VIF pruning: kept {len(remaining)}/{len(remaining) + len(dropped)} features. "
        f"Dropped: {dropped[:10]}{'...' if len(dropped) > 10 else ''}"
    )
    
    return remaining


# ═══════════════════════════════════════════════════════════════════════════════
# Comprehensive Metrics Calculator
# ═══════════════════════════════════════════════════════════════════════════════

def compute_enhanced_metrics(
    equity_curve: pd.Series,
    daily_returns: pd.Series,
    benchmark_returns: Optional[pd.Series] = None,
    trades: Optional[List[Dict]] = None,
) -> Dict[str, Any]:
    """
    Compute ALL metrics from the audit report in one call.
    
    Supplements BacktestResult with missing metrics.
    
    Returns:
        Dict with all computed metrics
    """
    metrics = {}
    
    # ── Standard metrics (already in engine.py, repeated for completeness) ───
    ret = daily_returns.dropna()
    if len(ret) > 10:
        std = ret.std()
        metrics["sharpe"] = float(ret.mean() / std * np.sqrt(252)) if std > 0 else 0
        
        downside = ret[ret < 0]
        ds = downside.std()
        metrics["sortino"] = float(ret.mean() / ds * np.sqrt(252)) if ds > 0 else 0
        
        metrics["var_95_pct"] = float(np.percentile(ret, 5) * 100)
        metrics["cvar_95_pct"] = float(ret[ret <= np.percentile(ret, 5)].mean() * 100)
    
    # ── NEW: Max Drawdown Duration ───────────────────────────────────────────
    metrics["max_drawdown_duration_days"] = max_drawdown_duration(equity_curve)
    
    # ── NEW: Information Ratio ───────────────────────────────────────────────
    if benchmark_returns is not None:
        metrics["information_ratio"] = information_ratio(daily_returns, benchmark_returns)
    
    # ── NEW: Omega Ratio ─────────────────────────────────────────────────────
    if len(ret) > 10:
        metrics["omega_ratio"] = omega_ratio(ret)
    
    # ── NEW: Tail Ratio ──────────────────────────────────────────────────────
    if len(ret) > 20:
        metrics["tail_ratio"] = tail_ratio(ret)
    
    # ── NEW: Calmar with duration ────────────────────────────────────────────
    if not equity_curve.empty and len(equity_curve) > 1:
        total_return = (equity_curve.iloc[-1] / equity_curve.iloc[0]) - 1
        n_years = max((equity_curve.index[-1] - equity_curve.index[0]).days / 365.25, 0.01)
        annual_return = (1 + total_return) ** (1 / n_years) - 1
        
        peak = equity_curve.cummax()
        max_dd = abs((equity_curve - peak) / peak).max()
        
        metrics["calmar_ratio"] = float(annual_return / max_dd) if max_dd > 0 else 0
    
    return metrics


# ═══════════════════════════════════════════════════════════════════════════════
# Statistical Helpers (no scipy dependency)
# ═══════════════════════════════════════════════════════════════════════════════

def _skewness(x: np.ndarray) -> float:
    """Sample skewness (Fisher's definition)."""
    n = len(x)
    if n < 3:
        return 0.0
    m = np.mean(x)
    s = np.std(x, ddof=1)
    if s < 1e-10:
        return 0.0
    return float(n / ((n-1) * (n-2)) * np.sum(((x - m) / s) ** 3))


def _excess_kurtosis(x: np.ndarray) -> float:
    """Sample excess kurtosis (Fisher's definition, 0 for normal)."""
    n = len(x)
    if n < 4:
        return 0.0
    m = np.mean(x)
    s = np.std(x, ddof=1)
    if s < 1e-10:
        return 0.0
    m4 = np.mean((x - m) ** 4)
    return float(m4 / (s ** 4) - 3)


def _jarque_bera(x: np.ndarray) -> Tuple[float, float]:
    """
    Jarque-Bera test for normality.
    Returns (statistic, p-value).
    Uses chi-squared approximation with 2 degrees of freedom.
    """
    n = len(x)
    if n < 8:
        return 0.0, 1.0
    
    s = _skewness(x)
    k = _excess_kurtosis(x)
    
    jb = n / 6 * (s ** 2 + k ** 2 / 4)
    
    # Chi-squared CDF approximation (2 df)
    # P(X > jb) for chi2(2) = exp(-jb/2)
    p_value = math.exp(-jb / 2)
    
    return float(jb), float(min(p_value, 1.0))
