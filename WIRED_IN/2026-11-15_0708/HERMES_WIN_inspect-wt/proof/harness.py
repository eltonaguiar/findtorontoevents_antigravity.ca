"""Proof harness — reusable tests for the 10-step standard.

Implements the pieces the repo audit found missing:
  - block-bootstrap Monte Carlo (arch)          (proof step 4)
  - shuffle / permutation control               (proof step 8)
  - deflated Sharpe ratio + trial count         (proof step 3)
  - regime split                                (proof step 7)
  - t-stat / bootstrap CI on excess return       (proof step 6)

All functions are deterministic given a seed. No network access here.
"""
from __future__ import annotations

import math
import numpy as np
import pandas as pd
from scipy import stats

TRADING_DAYS = 252


# ---------------------------------------------------------------- metrics
def perf_stats(returns: pd.Series, rf: float = 0.0) -> dict:
    """Annualised performance stats from a daily return series."""
    r = returns.dropna()
    if len(r) < 2:
        return {}
    ann_ret = (1 + r).prod() ** (TRADING_DAYS / len(r)) - 1
    ann_vol = r.std(ddof=1) * math.sqrt(TRADING_DAYS)
    excess = r - rf / TRADING_DAYS
    sharpe = (excess.mean() / r.std(ddof=1) * math.sqrt(TRADING_DAYS)) if r.std(ddof=1) > 0 else 0.0
    downside = r[r < 0].std(ddof=1) * math.sqrt(TRADING_DAYS)
    sortino = (ann_ret - rf) / downside if downside and downside > 0 else 0.0
    eq = (1 + r).cumprod()
    dd = eq / eq.cummax() - 1
    max_dd = float(dd.min())
    calmar = (ann_ret - rf) / abs(max_dd) if max_dd < 0 else 0.0
    return {
        "n_days": int(len(r)),
        "cagr": float(ann_ret),
        "ann_vol": float(ann_vol),
        "sharpe": float(sharpe),
        "sortino": float(sortino),
        "max_drawdown": max_dd,
        "calmar": float(calmar),
        "skew": float(stats.skew(r)),
        "kurtosis": float(stats.kurtosis(r, fisher=False)),
        "total_return": float(eq.iloc[-1] - 1),
    }


def trade_stats(pnl: pd.Series) -> dict:
    """Per-trade stats. pnl = per-trade fractional returns."""
    p = pnl.dropna()
    if len(p) == 0:
        return {}
    wins, losses = p[p > 0], p[p < 0]
    gp, gl = wins.sum(), abs(losses.sum())
    return {
        "n_trades": int(len(p)),
        "hit_rate": float(len(wins) / len(p)),
        "profit_factor": float(gp / gl) if gl > 0 else float("inf"),
        "expectancy": float(p.mean()),
        "avg_win": float(wins.mean()) if len(wins) else 0.0,
        "avg_loss": float(losses.mean()) if len(losses) else 0.0,
        "payoff_ratio": float(wins.mean() / abs(losses.mean())) if len(wins) and len(losses) else 0.0,
        "longest_loss_streak": int(_max_streak(p < 0)),
    }


def _max_streak(mask: pd.Series) -> int:
    best = cur = 0
    for v in mask:
        cur = cur + 1 if v else 0
        best = max(best, cur)
    return best


# ------------------------------------------------------- uncertainty
def bootstrap_ci(returns: pd.Series, n_boot: int = 2000, block: int = 20, seed: int = 42,
                 alpha: float = 0.05) -> dict:
    """Stationary block bootstrap CI for the annualised mean return."""
    r = returns.dropna().values
    if len(r) < block * 2:
        return {"error": "series too short for block bootstrap"}
    rng = np.random.default_rng(seed)
    n = len(r)
    n_blocks = int(np.ceil(n / block))
    means = np.empty(n_boot)
    for i in range(n_boot):
        starts = rng.integers(0, n - block, size=n_blocks)
        sample = np.concatenate([r[s:s + block] for s in starts])[:n]
        means[i] = sample.mean() * TRADING_DAYS
    lo, hi = np.percentile(means, [100 * alpha / 2, 100 * (1 - alpha / 2)])
    return {
        "ann_mean": float(r.mean() * TRADING_DAYS),
        "ci_lo": float(lo),
        "ci_hi": float(hi),
        "excludes_zero": bool(lo > 0 or hi < 0),
        "pct_positive": float((means > 0).mean()),
        "p5": float(np.percentile(means, 5)),
        "n_boot": n_boot,
        "block": block,
    }


def ttest_excess(excess: pd.Series) -> dict:
    """One-sided t-test that mean excess return > 0."""
    x = excess.dropna().values
    if len(x) < 3:
        return {"error": "too few observations"}
    t, p_two = stats.ttest_1samp(x, 0.0)
    return {
        "n": int(len(x)),
        "mean_ann": float(x.mean() * TRADING_DAYS),
        "t_stat": float(t),
        "p_two_sided": float(p_two),
        "p_one_sided": float(p_two / 2 if t > 0 else 1 - p_two / 2),
    }


# -------------------------------------------------- multiple testing
def deflated_sharpe(sr: float, n_trials: int, n_obs: int, skew: float, kurt: float,
                    sr_variance: float | None = None) -> dict:
    """Bailey & Lopez de Prado (2014) deflated Sharpe ratio.

    sr          : observed (non-annualised, per-period) Sharpe
    n_trials    : total independent configurations tried project-wide
    n_obs       : number of return observations
    skew, kurt  : skewness and (non-excess) kurtosis of returns
    """
    if n_obs < 3 or n_trials < 1:
        return {"error": "insufficient inputs"}
    gamma = 0.5772156649  # Euler-Mascheroni
    if sr_variance is None:
        sr_variance = 1.0 / n_obs  # conservative default
    z1 = stats.norm.ppf(1 - 1.0 / max(n_trials, 2))
    z2 = stats.norm.ppf(1 - 1.0 / max(n_trials, 2) * math.exp(-1))
    sr0 = math.sqrt(sr_variance) * ((1 - gamma) * z1 + gamma * z2)
    denom = math.sqrt(max(1e-9, 1 - skew * sr + (kurt - 1) / 4.0 * sr ** 2))
    z = (sr - sr0) * math.sqrt(max(n_obs - 1, 1)) / denom
    return {
        "sr_per_period": float(sr),
        "sr0_expected_max_under_null": float(sr0),
        "n_trials": int(n_trials),
        "n_obs": int(n_obs),
        "deflated_sharpe": float(stats.norm.cdf(z)),
        "passes_95": bool(stats.norm.cdf(z) > 0.95),
    }


# ------------------------------------------------------ shuffle control
def shuffle_control(price_levels: pd.DataFrame, strat_fn, n_shuffles: int = 100, seed: int = 7) -> dict:
    """Run the strategy on permuted return series.

    Permutes each asset's daily returns independently (destroys any real
    cross-sectional / serial structure) and re-runs the strategy. If the
    shuffled distribution matches the real result, the pipeline leaks.
    """
    rng = np.random.default_rng(seed)
    rets = price_levels.pct_change()
    real = strat_fn(price_levels)
    real_sharpe = real["sharpe"]
    sims = []
    for _ in range(n_shuffles):
        shuffled = pd.DataFrame(
            {c: rng.permutation(rets[c].dropna().values) for c in rets.columns},
            index=rets.index[: len(rets[c].dropna())] if False else None,
        )
        # build price paths from shuffled returns, aligned to original index
        idx = price_levels.index[1:1 + len(shuffled)]
        shuffled.index = idx
        prices = (1 + shuffled).cumprod() * price_levels.iloc[0][shuffled.columns].values
        prices = pd.concat([price_levels.iloc[[0]][shuffled.columns], prices])
        try:
            sims.append(strat_fn(prices)["sharpe"])
        except Exception:
            continue
    sims = np.array(sims)
    pct = float((sims >= real_sharpe).mean()) if len(sims) else 1.0
    # PASS only if the real strategy beats ~all shuffled variants.
    # If permuted data frequently matches or beats it, there is no exploitable
    # structure (or the pipeline leaks).
    ok = pct <= 0.05
    return {
        "real_sharpe": float(real_sharpe),
        "shuffled_mean_sharpe": float(sims.mean()) if len(sims) else None,
        "shuffled_p95_sharpe": float(np.percentile(sims, 95)) if len(sims) else None,
        "pct_shuffled_beating_real": pct,
        "n_shuffles": int(len(sims)),
        "verdict": "PASS (real beats 95% of shuffles)" if ok else "FAIL (shuffled data matches or beats real)",
    }


# ------------------------------------------------------- regime split
def regime_split(returns: pd.Series, bench_prices: pd.Series) -> dict:
    """Split returns by benchmark TREND (price vs 200d SMA) and volatility tercile."""
    df = pd.DataFrame({"r": returns, "px": bench_prices}).dropna()
    if len(df) < 300:
        return {"error": "insufficient history for regime split"}
    sma = df["px"].rolling(200).mean()
    vol = df["r"].rolling(20).std()
    out = {}
    for label, mask in {
        "bench_uptrend": df["px"] > sma,
        "bench_downtrend": df["px"] <= sma,
    }.items():
        seg = df.loc[mask, "r"]
        out[label] = {"ann_mean": float(seg.mean() * TRADING_DAYS), "n_days": int(len(seg))}
    try:
        terciles = pd.qcut(vol.dropna(), 3, labels=["low_vol", "mid_vol", "high_vol"])
        for label in ["low_vol", "mid_vol", "high_vol"]:
            seg = df.loc[terciles[terciles == label].index, "r"]
            out[label] = {"ann_mean": float(seg.mean() * TRADING_DAYS), "n_days": int(len(seg))}
    except Exception:
        pass
    vals = [v["ann_mean"] for v in out.values()]
    out["regimes_positive"] = f"{sum(1 for v in vals if v > 0)}/{len(vals)}"
    return out


# ------------------------------------------------------ walk-forward
def walk_forward_oos(returns: pd.Series, train_years: int = 4, test_years: int = 1) -> dict:
    """Rolling out-of-sample consistency: fraction of test windows with positive return.

    Used here as a stability check (no parameters to optimise). Efficiency is
    defined as mean(test ann return) / mean(train ann return).
    """
    r = returns.dropna()
    if len(r) < 252 * (train_years + test_years):
        return {"error": "insufficient history for walk-forward"}
    windows = []
    start = 0
    train_n, test_n = 252 * train_years, 252 * test_years
    while start + train_n + test_n <= len(r):
        tr = r.iloc[start:start + train_n]
        te = r.iloc[start + train_n:start + train_n + test_n]
        windows.append({
            "train_ann": float(tr.mean() * TRADING_DAYS),
            "test_ann": float(te.mean() * TRADING_DAYS),
        })
        start += test_n
    if not windows:
        return {"error": "no complete windows"}
    train_mean = np.mean([w["train_ann"] for w in windows])
    test_mean = np.mean([w["test_ann"] for w in windows])
    eff = test_mean / train_mean if train_mean != 0 else 0.0
    pos = sum(1 for w in windows if w["test_ann"] > 0)
    return {
        "n_windows": len(windows),
        "windows": windows,
        "train_mean_ann": float(train_mean),
        "test_mean_ann": float(test_mean),
        "walk_forward_efficiency": float(eff),
        "pct_windows_positive": float(pos / len(windows)),
    }
