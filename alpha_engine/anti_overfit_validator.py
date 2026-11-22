"""Anti-overfitting validation sidecar (CPCV/PBO + Reality Check + DSR).

Free-license replacement for the mlfinlab (AGPL) workflow. Wraps:

  * ``timeseriescv.CombPurgedKFoldCV`` (MIT)  --  Combinatorial Purged
    Cross-Validation backbone for the Probability of Backtest Overfitting.
  * ``arch.bootstrap`` (NCSA)                 --  Stationary Bootstrap
    used by White's Reality Check / Hansen SPA test.
  * Numpy-only Deflated Sharpe Ratio          --  Lopez de Prado AFML eq. 14.5,
    independent of ``alpha_engine.deflated_sharpe`` so this module stays
    importable even when scipy / the validation package is missing.

This module is OPT-IN. Nothing in the production pick-generation or scoring
path imports it yet (per CLAUDE.md Wire-Up Rule). The follow-up PR wires the
output into ``audit_trail.quality_gates.calculate_smart_score``; that work is
explicitly out of scope here.

Public API (all three functions degrade gracefully if optional deps are
missing -- they raise ``ImportError`` only when the caller actually invokes a
function that needs that dependency, never at import time):

    cpcv_pbo(strategy_returns_matrix, n_folds=10, n_test_groups=2) -> float
    reality_check_pvalue(returns_array, benchmark=0.0, B=1000, block_size=10) -> float
    deflated_sharpe(strategy_sharpe, n_trials, returns_array) -> float
"""
from __future__ import annotations

import math
import os
from datetime import datetime, timedelta, timezone
from typing import Sequence

import numpy as np

# ---------------------------------------------------------------------------
# Optional dependencies -- soft-fail at import, hard-fail at call site.
# ---------------------------------------------------------------------------
try:
    from arch.bootstrap import SPA, StationaryBootstrap  # type: ignore
    _ARCH_AVAILABLE = True
except Exception:  # pragma: no cover - exercised only on missing dep
    SPA = None  # type: ignore[assignment]
    StationaryBootstrap = None  # type: ignore[assignment]
    _ARCH_AVAILABLE = False

try:
    from timeseriescv.cross_validation import CombPurgedKFoldCV  # type: ignore
    _TSCV_AVAILABLE = True
except Exception:  # pragma: no cover
    CombPurgedKFoldCV = None  # type: ignore[assignment]
    _TSCV_AVAILABLE = False


# ---------------------------------------------------------------------------
# 1. CPCV-based Probability of Backtest Overfitting (PBO)
# ---------------------------------------------------------------------------
def cpcv_pbo(
    strategy_returns_matrix: np.ndarray,
    n_folds: int = 10,
    n_test_groups: int = 2,
    period_index: Sequence | None = None,
) -> float:
    """Probability of Backtest Overfitting via Combinatorial Purged CV.

    Implements the Bailey-Borwein-Lopez de Prado-Zhu (2017) PBO estimator on
    top of timeseriescv's ``CombPurgedKFoldCV``. PBO is the probability that
    the in-sample best strategy underperforms the median strategy out of
    sample -- so values >= 0.5 indicate the selection process is not
    statistically distinguishable from picking by chance.

    Args:
        strategy_returns_matrix: 2-D array shape ``(T, S)`` of per-period
            returns for ``S`` candidate strategies over ``T`` observations.
        n_folds: total CPCV folds N (default 10, AFML 12.4 recommendation).
        n_test_groups: folds held out per combinatorial split k (default 2).
        period_index: optional real timestamps, one per row, in the same order
            as the matrix rows. When supplied these are used as the fold
            ``pred_times``/``eval_times`` and the purge embargo is derived from
            the median spacing between rows, so purging drops a genuinely
            adjacent period instead of assuming a daily grid (2026-11-20).
            Supply it whenever the rows were built from real event times --
            otherwise the internal synthetic daily index claims a calendar the
            data never had.

    Returns:
        PBO estimate in ``[0, 1]``. Values < 0.5 = selection edge survives
        out of sample; >= 0.5 = backtest is statistically overfit.
    """
    M = np.asarray(strategy_returns_matrix, dtype=np.float64)
    if M.ndim != 2:
        raise ValueError(f"Expected 2-D returns matrix, got shape {M.shape}")
    T, S = M.shape
    if S < 2:
        raise ValueError(f"PBO requires >= 2 candidate strategies, got {S}")
    if T < n_folds * 2:
        raise ValueError(
            f"Need >= {n_folds * 2} observations for {n_folds} folds, got {T}"
        )

    # CPCV needs predict_times / eval_times for purging. With per-period
    # returns we treat each row as instantaneously labeled. timeseriescv
    # internally adds an embargo_td (Timedelta) to eval_times, so they must
    # be datetime-typed to support the addition.
    import pandas as pd  # local import keeps module import-cost low

    idx = pd.RangeIndex(T)
    if period_index is None:
        times = pd.date_range(start="2000-01-01", periods=T, freq="D")
        embargo_days = int(os.environ.get("CPCV_EMBARGO_DAYS", "2"))
    else:
        if len(period_index) != T:
            raise ValueError(
                f"period_index has {len(period_index)} periods but the matrix "
                f"has {T} rows"
            )
        times = pd.DatetimeIndex(pd.to_datetime(list(period_index)))
        if times.is_monotonic_increasing is not True:
            raise ValueError("period_index must be sorted ascending")
        gaps = np.diff(times.asi8).astype("float64") / 86_400_000_000_000.0
        embargo_days = max(1, int(round(float(np.median(gaps))))) if gaps.size else 1
    pred_times = pd.Series(times, index=idx)
    eval_times = pd.Series(times, index=idx)

    if not _TSCV_AVAILABLE:
        # Graceful degradation: equal-block splitter without purging. Good
        # enough for the PBO logit -- folds are still disjoint.
        fold_bounds = np.linspace(0, T, n_folds + 1, dtype=int)
        all_folds = [np.arange(fold_bounds[i], fold_bounds[i + 1])
                     for i in range(n_folds)]
        from itertools import combinations
        splits = []
        for test_idx in combinations(range(n_folds), n_test_groups):
            test = np.concatenate([all_folds[i] for i in test_idx])
            train = np.concatenate(
                [all_folds[i] for i in range(n_folds) if i not in test_idx]
            )
            splits.append((train, test))
    else:
        cv = CombPurgedKFoldCV(
            n_splits=n_folds,
            n_test_splits=n_test_groups,
            embargo_td=pd.Timedelta(days=embargo_days),
        )
        # CombPurgedKFoldCV.split requires a pandas DataFrame as X.
        X_df = pd.DataFrame(M, index=idx)
        splits = list(
            cv.split(X_df, pred_times=pred_times, eval_times=eval_times)
        )

    # For each combinatorial split: rank strategies by IS Sharpe, then look
    # up the *relative OOS rank* of the IS-winner. Following BBLZ 2017 eq.
    # 4, omega in (0, 1) is high when IS-best ranks high OOS (= no
    # overfitting); the logit is positive in that case.
    #   PBO = P(logit <= 0) = probability IS-winner falls below OOS median.
    logits: list[float] = []
    for train_idx, test_idx in splits:
        if len(train_idx) < 2 or len(test_idx) < 2:
            continue
        is_block = M[train_idx]
        oos_block = M[test_idx]
        is_sharpe = _sharpe_per_col(is_block)
        oos_sharpe = _sharpe_per_col(oos_block)
        best_is = int(np.argmax(is_sharpe))
        # 1 + (# strategies the IS-winner beats OOS) -> [1, S]
        oos_rank = 1 + int(np.sum(oos_sharpe < oos_sharpe[best_is]))
        omega = oos_rank / (S + 1)  # in (0, 1), higher = better OOS
        omega = min(max(omega, 1.0 / (S + 1)), 1.0 - 1.0 / (S + 1))
        logits.append(math.log(omega / (1.0 - omega)))

    if not logits:
        return float("nan")
    # PBO = fraction of splits where IS-best ranked at-or-below OOS median
    return float(np.mean([1.0 if l <= 0 else 0.0 for l in logits]))


def _parse_exit_ts(value: object) -> "datetime | None":
    """Best-effort parse of a closed-pick timestamp into naive UTC.

    Accepts ISO-8601 (with or without ``Z``), ``YYYY-MM-DD[ HH:MM:SS]``,
    ``YYYY/MM/DD``, epoch seconds, and ``datetime``. Returns ``None`` rather
    than guessing when the string is unparseable -- an invented timestamp is
    worse than a dropped row, because it silently joins the wrong period.
    """
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, (int, float)) and not isinstance(value, bool):
        try:
            return datetime.fromtimestamp(float(value), tz=timezone.utc).replace(tzinfo=None)
        except (OverflowError, OSError, ValueError):
            return None
    else:
        s = str(value).strip().replace("Z", "+00:00")
        try:
            dt = datetime.fromisoformat(s)
        except ValueError:
            dt = None
            for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%Y/%m/%d", "%m/%d/%Y"):
                try:
                    dt = datetime.strptime(s, fmt)
                    break
                except ValueError:
                    continue
            if dt is None:
                return None
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def _period_floor(dt: datetime, period: str) -> datetime:
    if period == "D":
        return dt.replace(hour=0, minute=0, second=0, microsecond=0)
    if period == "W":
        d = dt.replace(hour=0, minute=0, second=0, microsecond=0)
        return d - timedelta(days=d.weekday())
    if period == "M":
        return dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    raise ValueError(f"Unknown period {period!r}; expected 'D', 'W' or 'M'")


def align_returns_by_period(
    series_by_strategy: dict[str, Sequence[tuple[object, float]]],
    min_obs: int = 30,
    period: str = "auto",
    min_rows: int = 16,
) -> tuple[np.ndarray | None, list[datetime], dict]:
    """Build a ``(T x S)`` matrix whose rows are the SAME calendar periods.

    PBO compares strategies *against each other, period by period*. Slicing each
    strategy's own pick sequence (``v[:T]`` or ``v[-T:]``) does not do that: two
    strategies that traded in different months end up stacked as if row 0 of one
    happened at the same time as row 0 of the other, so the in-sample/out-of-
    sample blocks mix eras and the PBO logit measures the calendar, not the
    selection process.

    This aggregates each strategy's pick returns onto a shared period grid
    (day -> week -> month, escalating until there are enough rows for CPCV). A
    strategy with no pick in a period gets ``0.0`` -- no position, no P&L -- which
    is the truthful value and keeps every column on the same clock.

    Returns ``(matrix, periods, info)``. ``matrix`` is ``None`` when fewer than 2
    strategies clear ``min_obs`` timestamped picks.
    """
    info: dict = {
        "requested_period": period,
        "period": None,
        "n_rows": 0,
        "n_cols": 0,
        "n_strategies_input": len(series_by_strategy or {}),
        "dropped_below_min_obs": [],
        "dropped_untimestamped_picks": 0,
        "coverage_pct": 0.0,
        "escalated_from": [],
        "min_rows_required": int(min_rows),
    }

    eligible = {
        str(k): v for k, v in (series_by_strategy or {}).items()
        if v is not None and len(v) >= min_obs
    }
    info["dropped_below_min_obs"] = sorted(
        str(k) for k, v in (series_by_strategy or {}).items()
        if v is None or len(v) < min_obs
    )
    if len(eligible) < 2:
        info["note"] = (
            f"only {len(eligible)} strategy(ies) with >= {min_obs} observations; "
            "PBO needs >= 2"
        )
        return None, [], info

    parsed: dict[str, list[tuple[datetime, float]]] = {}
    dropped = 0
    for name, rows in eligible.items():
        kept: list[tuple[datetime, float]] = []
        for row in rows:
            try:
                ts, ret = row
            except (TypeError, ValueError):
                continue
            dt = _parse_exit_ts(ts)
            if dt is None:
                dropped += 1
                continue
            try:
                kept.append((dt, float(ret)))
            except (TypeError, ValueError):
                continue
        if len(kept) < min_obs:
            info["dropped_below_min_obs"].append(name)
            continue
        parsed[name] = kept
    info["dropped_untimestamped_picks"] = dropped
    if len(parsed) < 2:
        info["note"] = (
            f"only {len(parsed)} strategy(ies) left after timestamp parsing; "
            f"{dropped} picks had no usable exit timestamp"
        )
        return None, [], info

    names = sorted(parsed)
    ladder = ["D", "W", "M"] if period == "auto" else [period]
    periods: list[datetime] = []
    buckets: dict[str, dict[datetime, list[float]]] = {}
    chosen = ladder[-1]
    for step in ladder:
        chosen = step
        buckets = {name: {} for name in names}
        for name in names:
            for dt, ret in parsed[name]:
                buckets[name].setdefault(_period_floor(dt, step), []).append(ret)
        periods = sorted({d for b in buckets.values() for d in b})
        if len(periods) >= info["min_rows_required"]:
            break
        if step != ladder[-1]:
            info["escalated_from"].append(step)

    if len(periods) < 2:
        info["note"] = f"{len(periods)} distinct {chosen} periods; need >= 2"
        return None, [], info

    matrix = np.zeros((len(periods), len(names)), dtype=np.float64)
    row_of = {d: i for i, d in enumerate(periods)}
    for j, name in enumerate(names):
        for d, vals in buckets[name].items():
            matrix[row_of[d], j] = float(np.mean(vals))

    filled = int(np.count_nonzero(matrix))
    info.update({
        "period": chosen,
        "n_rows": int(matrix.shape[0]),
        "n_cols": int(matrix.shape[1]),
        "coverage_pct": round(100.0 * filled / matrix.size, 2) if matrix.size else 0.0,
        "strategies": names,
        # Zero cells are real information (strategy flat that period) -- this is
        # what lets every column share one clock.
        "empty_cell_policy": "0.0 (no position that period)",
    })
    return matrix, periods, info


def _sharpe_per_col(block: np.ndarray) -> np.ndarray:
    """Annualization-free Sharpe per column; safe on zero-variance columns."""
    mu = block.mean(axis=0)
    sd = block.std(axis=0, ddof=1)
    sd = np.where(sd < 1e-12, 1e-12, sd)
    return mu / sd


# ---------------------------------------------------------------------------
# 2. Reality Check / Hansen SPA p-value via Stationary Bootstrap
# ---------------------------------------------------------------------------
def reality_check_pvalue(
    returns_array: Sequence[float] | np.ndarray,
    benchmark: float | Sequence[float] = 0.0,
    B: int = 1000,
    block_size: int = 10,
) -> float:
    """Hansen SPA-test p-value (consistent w/ White's Reality Check).

    Uses ``arch.bootstrap.SPA`` with a stationary bootstrap. The null is "no
    candidate model has lower loss than the benchmark"; small p-values reject
    the null and constitute evidence of genuine outperformance.

    arch's SPA expects *losses*; we negate returns so higher returns map to
    lower losses, which is the convention required for the test to interpret
    "strategy beats benchmark" as the alternative hypothesis.

    Args:
        returns_array: 1-D returns for a single strategy, OR 2-D shape
            ``(T, S)`` for joint testing across S candidate strategies (the
            multiple-testing case for which Reality Check was designed).
        benchmark: scalar (e.g. 0.0 for "edge vs zero") or per-period array.
        B: bootstrap replications (1000 typical; arch default).
        block_size: expected stationary-bootstrap block length.

    Returns:
        SPA-test consistent p-value in ``[0, 1]``.
    """
    if not _ARCH_AVAILABLE:
        raise ImportError(
            "reality_check_pvalue requires the 'arch' package "
            "(see requirements-validation.txt)"
        )

    r = np.asarray(returns_array, dtype=np.float64)
    if r.ndim == 1:
        r = r.reshape(-1, 1)
    T = r.shape[0]
    if T < 10:
        raise ValueError(f"Need >= 10 observations for Reality Check, got {T}")

    if np.isscalar(benchmark):
        bench = np.full(T, float(benchmark))
    else:
        bench = np.asarray(benchmark, dtype=np.float64)
        if bench.shape[0] != T:
            raise ValueError(
                f"benchmark length {bench.shape[0]} != returns length {T}"
            )

    # SPA's convention is losses; flip sign so higher returns -> lower losses.
    spa = SPA(
        -bench, -r,
        block_size=block_size, reps=B, bootstrap="stationary",
    )
    spa.compute()
    # SPA returns three p-values (lower / consistent / upper). The
    # "consistent" version is the one Hansen recommends as the headline test.
    return float(spa.pvalues["consistent"])


# ---------------------------------------------------------------------------
# 3. Deflated Sharpe Ratio (Bailey & Lopez de Prado 2014, AFML eq. 14.5)
# ---------------------------------------------------------------------------
def deflated_sharpe(
    strategy_sharpe: float,
    n_trials: int,
    returns_array: Sequence[float] | np.ndarray,
) -> float:
    """Deflated Sharpe -- probability that observed Sharpe is genuine.

    DSR = P(SR > E[max(SR_n)] | n_trials, skew, kurtosis) under the null
    that all candidates have zero true Sharpe. Values >= 0.95 mean the
    headline Sharpe survives the multiple-testing correction.

    Args:
        strategy_sharpe: observed (un-annualized OR annualized -- consistent
            with the returns_array sampling rate) Sharpe of the candidate.
        n_trials: number of independent strategy backtests considered.
        returns_array: 1-D series of periodic returns from the candidate
            (used to estimate skew, kurtosis, and the SR estimator variance).

    Returns:
        DSR probability in ``[0, 1]``.
    """
    r = np.asarray(returns_array, dtype=np.float64)
    if r.size < 4:
        raise ValueError(f"Need >= 4 returns for DSR, got {r.size}")
    if n_trials <= 0:
        raise ValueError("n_trials must be positive")

    n = r.size
    mu = r.mean()
    sd = r.std(ddof=1)
    if sd < 1e-12:
        return 1.0 if strategy_sharpe > 0 else 0.0

    # Sample skew & excess kurtosis (Fisher-corrected, matches existing module)
    z = (r - mu) / sd
    skew = float(((n * n) / ((n - 1) * (n - 2))) * np.mean(z ** 3))
    kurt_raw = float(np.mean(z ** 4))
    kurt = ((n + 1) * kurt_raw - 3 * (n - 1)) * (n - 1) / ((n - 2) * (n - 3))

    # Variance of the Sharpe estimator (Lo 2002, non-normality adjusted)
    sr_var = (1.0 / n) * (
        1.0 - skew * strategy_sharpe + (kurt / 4.0) * strategy_sharpe ** 2
    )
    # NaN-safe: negative sr_var (numerical instability, n<<) propagates NaN through DSR
    # instead of flooring to 1e-16 (Kimi BUG-1 / cavecrew confirmed 2026-05-20)
    sr_std = math.sqrt(sr_var) if sr_var > 0 else float("nan")

    # Expected max SR under null (mean=0, variance=sr_var) -- AFML eq. 14.5
    if n_trials == 1:
        e_max = 0.0
    else:
        gamma = 0.5772156649  # Euler-Mascheroni
        e_max = sr_std * (
            (1.0 - gamma) * _norm_ppf(1.0 - 1.0 / n_trials)
            + gamma * _norm_ppf(1.0 - 1.0 / (n_trials * math.e))
        )

    return float(_norm_cdf((strategy_sharpe - e_max) / sr_std))


# ---------------------------------------------------------------------------
# Stdlib normal CDF / PPF (avoid hard scipy dep -- module must import cleanly
# even on a stripped CI image).
# ---------------------------------------------------------------------------
def _norm_cdf(x: float) -> float:
    return 0.5 * math.erfc(-x / math.sqrt(2.0))


def _norm_ppf(p: float) -> float:
    """Standard normal inverse CDF -- Acklam (2003) approximation."""
    if p <= 0.0:
        return -math.inf
    if p >= 1.0:
        return math.inf
    a = [-3.969683028665376e+01, 2.209460984245205e+02,
         -2.759285104469687e+02, 1.383577518672690e+02,
         -3.066479806614716e+01, 2.506628277459239e+00]
    b = [-5.447609879822406e+01, 1.615858368580409e+02,
         -1.556989798598866e+02, 6.680131188771972e+01,
         -1.328068155288572e+01]
    c = [-7.784894002430293e-03, -3.223964580411365e-01,
         -2.400758277161838e+00, -2.549732539343734e+00,
         4.374664141464968e+00, 2.938163982698783e+00]
    d = [7.784695709041462e-03, 3.224671290700398e-01,
         2.445134137142996e+00, 3.754408661907416e+00]
    p_low, p_high = 0.02425, 1.0 - 0.02425
    if p < p_low:
        q = math.sqrt(-2.0 * math.log(p))
        return (((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / \
               ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1.0)
    if p <= p_high:
        q = p - 0.5
        r = q * q
        return (((((a[0]*r+a[1])*r+a[2])*r+a[3])*r+a[4])*r+a[5]) * q / \
               (((((b[0]*r+b[1])*r+b[2])*r+b[3])*r+b[4])*r+1.0)
    q = math.sqrt(-2.0 * math.log(1.0 - p))
    return -(((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / \
            ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1.0)


def evaluate_strategy(
    history: Sequence[float],
    n_trials: int = 1,
    n_candidates: int = 2,
) -> dict:
    """Convenience wrapper returning DSR + PBO for a single strategy's
    per-period return history.

    Designed for the ``audit_trail.quality_gates`` opt-in wire-in. Never
    raises on degenerate input -- returns ``nan`` so the caller can treat
    "no evidence" as a fall-through.

    Args:
        history: 1-D iterable of per-period returns for the candidate.
        n_trials: number of strategies considered during selection (for DSR
            multiple-testing correction). Defaults to 1 (no correction).
        n_candidates: number of synthetic peer columns used for the PBO
            estimate. Defaults to 2 (CPCV minimum); callers with a real peer
            matrix should call ``cpcv_pbo`` directly.

    Returns:
        ``{"dsr": float, "pbo": float, "sharpe": float, "n": int}``
    """
    r = np.asarray(list(history), dtype=np.float64)
    out: dict = {"dsr": float("nan"), "pbo": float("nan"),
                 "sharpe": float("nan"), "n": int(r.size)}
    if r.size < 4:
        return out
    mu = r.mean()
    sd = r.std(ddof=1)
    if sd < 1e-12:
        return out
    sharpe = float(mu / sd)
    out["sharpe"] = sharpe
    try:
        out["dsr"] = float(deflated_sharpe(sharpe, max(int(n_trials), 1), r))
    except Exception:
        out["dsr"] = float("nan")
    # PBO needs >= 2 candidate columns. Previously this synthesized a zero-mean
    # peer so the estimator had something to compare against ("degraded mode"),
    # but that produced PLAUSIBLE WRONG NUMBERS (pbo in {0.578, 0.467, ...}
    # on pure noise where the honest answer is ~0.333). A plausible wrong number
    # is worse than nan. P0.0j: return nan in degraded mode. Callers with a real
    # peer matrix should call cpcv_pbo() directly.
    out["pbo"] = float("nan")
    out["pbo_degraded"] = True
    out["pbo_note"] = ("PBO not computed: synthetic zero-mean peers produce "
                       "plausible but invalid numbers. Pass a real candidate "
                       "matrix to cpcv_pbo() directly.")
    return out


__all__ = [
    "cpcv_pbo",
    "reality_check_pvalue",
    "deflated_sharpe",
    "evaluate_strategy",
]

