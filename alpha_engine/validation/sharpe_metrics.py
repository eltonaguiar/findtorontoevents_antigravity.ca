"""
sharpe_metrics.py — Deflated Sharpe, Probabilistic Sharpe, and standard Sharpe.

References:
  - Bailey & Lopez de Prado (2014): Deflated Sharpe Ratio
  - Lo (2015): Probabilistic Sharpe Ratio

Usage:
  from alpha_engine.validation.sharpe_metrics import (
      compute_sharpe, deflated_sharpe_ratio, probabilistic_sharpe_ratio,
  )
  sr  = compute_sharpe(returns, risk_free_rate=0.02, freq="daily")
  dsr = deflated_sharpe_ratio(returns, risk_free_rate=0.02, freq="daily")
  psr = probabilistic_sharpe_ratio(returns, risk_free_rate=0.02, target_sharpe=0.0, freq="daily")
"""

import numpy as np
import pandas as pd
from scipy.stats import skew, kurtosis, norm


def annualise_factor(freq: str) -> int:
    """Return number of periods per year for common frequencies."""
    freq = freq.lower()
    if freq in {"daily", "d"}:
        return 252
    if freq in {"weekly", "w"}:
        return 52
    if freq in {"monthly", "m"}:
        return 12
    if freq in {"hourly", "h"}:
        return 252 * 6
    raise ValueError(f"Unsupported frequency: {freq}")


def compute_sharpe(
    returns: pd.Series,
    risk_free_rate: float = 0.0,
    freq: str = "daily",
) -> float:
    """Annualised Sharpe ratio (excess returns / std dev)."""
    n_per_year = annualise_factor(freq)
    rf_per_period = (1 + risk_free_rate) ** (1 / n_per_year) - 1
    excess = returns - rf_per_period
    mean_excess = excess.mean()
    std_excess = excess.std(ddof=1)
    if std_excess == 0:
        return np.nan
    return (mean_excess / std_excess) * np.sqrt(n_per_year)


def _sharpe_std_error(
    returns: pd.Series,
    sharpe: float,
    freq: str = "daily",
) -> float:
    """
    Analytical standard error of the Sharpe ratio incorporating
    skewness and excess kurtosis (Bailey & Lopez de Prado 2014).
    """
    n = len(returns)
    if n <= 1:
        return np.nan

    sk = skew(returns, bias=False)
    kurt_val = kurtosis(returns, fisher=True, bias=False)

    term1 = (1 + 0.5 * sharpe ** 2) / (n - 1)
    term2 = (sk * sharpe) / (6 * np.sqrt(n))
    term3 = (kurt_val * sharpe ** 2) / (24 * n)

    return np.sqrt(max(term1 + term2 + term3, 0))


def deflated_sharpe_ratio(
    returns: pd.Series,
    risk_free_rate: float = 0.0,
    freq: str = "daily",
) -> float:
    """
    Deflated Sharpe Ratio (DSR) = Sharpe / SE(Sharpe).
    DSR > 1.64 implies ~95% confidence that true Sharpe > 0.
    """
    n_per_year = annualise_factor(freq)
    rf_per_period = (1 + risk_free_rate) ** (1 / n_per_year) - 1
    excess = returns - rf_per_period

    sr = compute_sharpe(returns, risk_free_rate, freq)
    se = _sharpe_std_error(excess, sr, freq)

    if se == 0 or np.isnan(se):
        return np.nan
    return sr / se


def probabilistic_sharpe_ratio(
    returns: pd.Series,
    risk_free_rate: float = 0.0,
    target_sharpe: float = 0.0,
    freq: str = "daily",
) -> float:
    """
    Probabilistic Sharpe Ratio (PSR) = Phi((SR - target) / SE).
    Returns probability (0-1) that true Sharpe exceeds target_sharpe.
    """
    n_per_year = annualise_factor(freq)
    rf_per_period = (1 + risk_free_rate) ** (1 / n_per_year) - 1
    excess = returns - rf_per_period

    sr = compute_sharpe(returns, risk_free_rate, freq)
    se = _sharpe_std_error(excess, sr, freq)

    if se == 0 or np.isnan(se):
        return np.nan
    z = (sr - target_sharpe) / se
    return norm.cdf(z)


def compute_tail_risk_metrics(returns: pd.Series, freq: str = "daily") -> dict:
    """
    Compute tail-risk metrics mandated by Testing Protocol Layer 4.
    Returns dict with: sortino, calmar, omega, cvar_95, expected_shortfall,
    skewness, kurtosis_excess, evt_tail_index.
    """
    n_per_year = annualise_factor(freq)
    r = returns.dropna()

    # Sortino (downside deviation)
    downside = r[r < 0]
    downside_std = downside.std(ddof=1) if len(downside) > 1 else np.nan
    sortino = (r.mean() / downside_std * np.sqrt(n_per_year)) if downside_std and downside_std > 0 else np.nan

    # Calmar (annualised return / max drawdown)
    cum = (1 + r).cumprod()
    peak = cum.cummax()
    dd = (cum - peak) / peak
    max_dd = abs(dd.min()) if len(dd) > 0 else np.nan
    ann_return = (1 + r.mean()) ** n_per_year - 1
    calmar = (ann_return / max_dd) if max_dd > 0 else np.nan

    # Omega (ratio of gains to losses above/below threshold 0)
    gains = r[r > 0].sum()
    losses = abs(r[r < 0].sum())
    omega = (gains / losses) if losses > 0 else np.nan

    # CVaR 95% (Conditional Value at Risk)
    var_95 = np.percentile(r, 5)
    cvar_95 = r[r <= var_95].mean() if len(r[r <= var_95]) > 0 else var_95

    # Expected Shortfall (same as CVaR for continuous distributions)
    expected_shortfall = cvar_95

    # Skewness & Kurtosis
    sk = skew(r, bias=False)
    kurt_val = kurtosis(r, fisher=True, bias=False)

    # EVT tail index (simple Hill estimator on left tail)
    sorted_losses = np.sort(-r[r < 0])
    if len(sorted_losses) > 10:
        k = max(int(len(sorted_losses) * 0.1), 5)
        top_k = sorted_losses[:k]
        threshold = sorted_losses[k]
        if threshold > 0:
            evt_tail_index = 1.0 / np.mean(np.log(top_k / threshold))
        else:
            evt_tail_index = np.nan
    else:
        evt_tail_index = np.nan

    return {
        "sortino": round(sortino, 4) if not np.isnan(sortino) else None,
        "calmar": round(calmar, 4) if not np.isnan(calmar) else None,
        "omega": round(omega, 4) if not np.isnan(omega) else None,
        "cvar_95": round(cvar_95, 6) if not np.isnan(cvar_95) else None,
        "expected_shortfall": round(expected_shortfall, 6) if not np.isnan(expected_shortfall) else None,
        "skewness": round(sk, 4),
        "kurtosis_excess": round(kurt_val, 4),
        "evt_tail_index": round(evt_tail_index, 4) if evt_tail_index and not np.isnan(evt_tail_index) else None,
    }


if __name__ == "__main__":
    np.random.seed(42)
    daily_ret = pd.Series(np.random.normal(0.0005, 0.015, size=252 * 2))

    sr = compute_sharpe(daily_ret, risk_free_rate=0.02, freq="daily")
    dsr = deflated_sharpe_ratio(daily_ret, risk_free_rate=0.02, freq="daily")
    psr = probabilistic_sharpe_ratio(daily_ret, risk_free_rate=0.02, target_sharpe=0.0, freq="daily")
    tail = compute_tail_risk_metrics(daily_ret, freq="daily")

    print(f"Annualised Sharpe       : {sr: .4f}")
    print(f"Deflated Sharpe Ratio   : {dsr: .4f}")
    print(f"Probabilistic Sharpe    : {psr:.2%}")
    print(f"Tail-risk metrics       : {tail}")
