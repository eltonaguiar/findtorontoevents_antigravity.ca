"""Backtest engine with costs, train/OOS metrics, bootstrap, DSR and PBO."""
from __future__ import annotations

import itertools
import math
from dataclasses import dataclass, asdict
from typing import Dict, Iterable

import numpy as np
import pandas as pd
from scipy import stats


@dataclass
class PeriodMetrics:
    start: str
    end: str
    n_days: int
    cagr: float
    vol: float
    sharpe: float
    sortino: float
    max_dd: float
    calmar: float
    hit_rate: float
    profit_factor: float
    total_return: float
    turnover_ann: float
    avg_exposure: float
    n_changes: int
    n_entries: int


def _as_frame(weights) -> pd.DataFrame:
    if isinstance(weights, pd.Series):
        return weights.to_frame("asset")
    return weights.copy()


def portfolio_returns(weights: pd.DataFrame, rets: pd.DataFrame, bps: float) -> tuple[pd.Series, pd.Series]:
    """Weights are targets at close t; execution at t+1. Costs charged on |Δw|."""
    w = weights.reindex(index=rets.index, columns=rets.columns).fillna(0.0)
    risk_cols = [c for c in w.columns if c != "CASH"]
    turn = w[risk_cols].diff().abs().sum(axis=1)
    if len(turn):
        turn.iloc[0] = w[risk_cols].iloc[0].abs().sum()
    cost = turn.shift(1).fillna(0.0) * (bps / 10_000.0)
    port = (w.shift(1) * rets).sum(axis=1) - cost
    return port.dropna(), turn


def metrics(ret: pd.Series, ann: int, weights: pd.DataFrame | None = None, turn: pd.Series | None = None) -> PeriodMetrics:
    r = ret.dropna()
    if len(r) < 5:
        return PeriodMetrics(str(r.index.min().date()) if len(r) else "",
                             str(r.index.max().date()) if len(r) else "",
                             len(r), *([float("nan")] * 13))
    eq = (1 + r).cumprod()
    dd = eq / eq.cummax() - 1
    mu, sd = r.mean(), r.std(ddof=1)
    sharpe = float(mu / sd * math.sqrt(ann)) if sd > 0 else float("nan")
    downside = r[r < 0].std(ddof=1)
    sortino = float(mu / downside * math.sqrt(ann)) if downside and downside > 0 else float("nan")
    cagr = float(eq.iloc[-1] ** (ann / len(r)) - 1)
    max_dd = float(dd.min())
    total = float(eq.iloc[-1] - 1)
    wins = r[r > 0].sum()
    losses = -r[r < 0].sum()
    pf = float(wins / losses) if losses > 0 else float("inf")
    hit = float((r > 0).mean())
    calmar = float(cagr / abs(max_dd)) if max_dd < 0 else float("nan")
    if weights is not None:
        w = weights.reindex(index=r.index, columns=weights.columns).fillna(0)
        rw = w.drop(columns=["CASH"], errors="ignore")
        expo = float(rw.abs().sum(axis=1).mean())
        ch = rw.diff().abs().sum(axis=1)
        n_changes = int((ch > 1e-9).sum())
        n_entries = int(((rw > 0) & (rw.shift(1).fillna(0) <= 0)).sum().sum())
        turn_ann = float((turn.reindex(r.index).fillna(0).sum()) / max(len(r) / ann, 1e-9)) if turn is not None else float("nan")
    else:
        expo = n_changes = n_entries = 0
        turn_ann = float("nan")
    return PeriodMetrics(
        start=str(r.index.min().date()), end=str(r.index.max().date()), n_days=len(r),
        cagr=cagr, vol=float(sd * math.sqrt(ann)), sharpe=sharpe, sortino=sortino,
        max_dd=max_dd, calmar=calmar, hit_rate=hit, profit_factor=pf, total_return=total,
        turnover_ann=turn_ann, avg_exposure=expo, n_changes=n_changes, n_entries=n_entries,
    )


def split_metrics(port: pd.Series, train_end: str, oos_start: str, ann: int,
                  weights: pd.DataFrame | None = None, turn: pd.Series | None = None,
                  train_start: str = "2018-01-01") -> Dict[str, PeriodMetrics]:
    tr = port.loc[train_start:train_end]
    oo = port.loc[oos_start:]
    wtr = weights.loc[train_start:train_end] if weights is not None else None
    woo = weights.loc[oos_start:] if weights is not None else None
    ttr = turn.loc[train_start:train_end] if turn is not None else None
    too = turn.loc[oos_start:] if turn is not None else None
    return {"train": metrics(tr, ann, wtr, ttr), "oos": metrics(oo, ann, woo, too)}


def block_bootstrap_sharpe(ret: pd.Series, ann: int, n: int = 2000, block: int = 20, seed: int = 7) -> dict:
    r = ret.dropna().values
    if len(r) < block * 2:
        return {"mean": float("nan"), "p05": float("nan"), "p95": float("nan")}
    rng = np.random.default_rng(seed)
    nb = int(math.ceil(len(r) / block))
    out = np.empty(n)
    for i in range(n):
        starts = rng.integers(0, len(r) - block, size=nb)
        sample = np.concatenate([r[s:s + block] for s in starts])[:len(r)]
        sd = sample.std(ddof=1)
        out[i] = sample.mean() / sd * math.sqrt(ann) if sd > 0 else np.nan
    return {"mean": float(np.nanmean(out)), "p05": float(np.nanpercentile(out, 5)),
            "p95": float(np.nanpercentile(out, 95))}


def deflated_sharpe(ret: pd.Series, n_trials: int) -> float:
    """Bailey & López de Prado DSR (probability the true SR exceeds the null max)."""
    r = ret.dropna().values
    if len(r) < 30 or n_trials < 2:
        return float("nan")
    sr = r.mean() / r.std(ddof=1)
    skew = float(stats.skew(r))
    kurt = float(stats.kurtosis(r, fisher=False))
    var_sr = (1 - skew * sr + (kurt - 1) / 4 * sr ** 2) / (len(r) - 1)
    if var_sr <= 0:
        return float("nan")
    gamma = 0.5772156649
    sr0 = math.sqrt(var_sr) * ((1 - gamma) * stats.norm.ppf(1 - 1 / n_trials)
                               + gamma * stats.norm.ppf(1 - 1 / (n_trials * math.e)))
    return float(stats.norm.cdf((sr - sr0) / math.sqrt(var_sr)))


def pbo_cscv(returns_matrix: pd.DataFrame, n_blocks: int = 16) -> float:
    """Probability of Backtest Overfitting via CSCV. Returns nan if not computable."""
    R = returns_matrix.dropna(how="any")
    S = R.shape[1]
    T = R.shape[0]
    if S < 4 or T < n_blocks * 4:
        return float("nan")
    blocks = np.array_split(np.arange(T), n_blocks)
    half = n_blocks // 2
    omegas = []
    for combo in itertools.combinations(range(n_blocks), half):
        is_idx = np.concatenate([blocks[i] for i in combo])
        oos_idx = np.concatenate([blocks[i] for i in range(n_blocks) if i not in combo])
        is_r = R.iloc[is_idx]
        oos_r = R.iloc[oos_idx]
        is_sr = is_r.mean() / is_r.std(ddof=1)
        oos_sr = oos_r.mean() / oos_r.std(ddof=1)
        best = is_sr.idxmax() if is_sr.notna().any() else None
        if best is None:
            continue
        rank = int(oos_sr.rank(method="average").loc[best])
        omegas.append(rank / (S + 1))
    if not omegas:
        return float("nan")
    return float(np.mean(np.array(omegas) <= 0.5))


def sharpe_pvalue(ret: pd.Series, ann: int) -> float:
    r = ret.dropna()
    if len(r) < 10:
        return float("nan")
    sr = r.mean() / r.std(ddof=1) * math.sqrt(ann)
    t = sr * math.sqrt(len(r) / ann)
    return float(2 * (1 - stats.norm.cdf(abs(t))))


def multiple_testing(pvals: Dict[str, float]) -> dict:
    clean = {k: v for k, v in pvals.items() if v == v}
    n = len(clean)
    if n == 0:
        return {"n": 0, "bonferroni_alpha": float("nan"), "bh_reject": []}
    alpha = 0.05
    ordered = sorted(clean.items(), key=lambda kv: kv[1])
    bh = []
    for i, (k, p) in enumerate(ordered, 1):
        if p <= alpha * i / n:
            bh.append(k)
    return {"n": n, "bonferroni_alpha": alpha / n,
            "bonferroni_reject": [k for k, p in clean.items() if p <= alpha / n],
            "bh_reject": bh, "pvalues": clean}


def evaluate(name: str, weights: pd.DataFrame, rets: pd.DataFrame, bps: float, ann: int,
             benchmark: pd.DataFrame, train_end: str = "2023-12-31",
             oos_start: str = "2024-01-01", train_start: str = "2018-01-01") -> dict:
    weights = _as_frame(weights)
    port, turn = portfolio_returns(weights, rets, bps)
    bench, _ = portfolio_returns(benchmark, rets, 0.0)
    sm = split_metrics(port, train_end, oos_start, ann, weights, turn, train_start)
    bm = split_metrics(bench, train_end, oos_start, ann, train_start=train_start)
    oos = port.loc[oos_start:]
    return {
        "name": name,
        "cost_bps": bps,
        "ann": ann,
        "train": asdict(sm["train"]),
        "oos": asdict(sm["oos"]),
        "benchmark_train": asdict(bm["train"]),
        "benchmark_oos": asdict(bm["oos"]),
        "bootstrap_oos": block_bootstrap_sharpe(oos, ann),
        "pvalue_oos": sharpe_pvalue(oos, ann),
        "oos_returns": oos,
        "oos_weights": weights.loc[oos_start:],
    }
