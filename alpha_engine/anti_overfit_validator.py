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
    times = pd.date_range(start="2000-01-01", periods=T, freq="D")
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
            embargo_td=pd.Timedelta(days=int(os.environ.get("CPCV_EMBARGO_DAYS", "2"))),
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
#: Guard rail for per-period Sharpe. A per-bar Sharpe of 1.0 (mean == one
#: standard deviation per bar) is already an implausible ~15.9 annualized on
#: daily data; anything above it is almost certainly an annualized value that
#: the caller forgot to de-annualize.
#:
#: Why this exists (2026-11-20): passing an annualized Sharpe did not raise --
#: it returned DSR = 1.0000 (a PASS) on a series with provably zero edge,
#: because ``sr_var`` in Lo (2002) scales with ``SR**2`` and the variance term
#: dominates the numerator. See
#: ``reports/VALIDATION_LAYER_AUDIT_2026-11-20.md`` Defect A.
MAX_PER_PERIOD_SHARPE = 1.0

#: Annualization factors that ``strategy_sharpe`` is most likely to have been
#: multiplied by if the caller forgot to de-annualize.
_ANNUALIZATION_PROBES: tuple[tuple[float, str], ...] = (
    (252.0, "daily"),
    (52.0, "weekly"),
    (12.0, "monthly"),
    (4.0, "quarterly"),
)


def _reject_annualized_sharpe(
    strategy_sharpe: float,
    mu: float,
    sd: float,
) -> None:
    """Raise if ``strategy_sharpe`` is manifestly annualized.

    ``returns_array`` is already an argument, so the true per-period Sharpe is
    *implied* by the data: ``mu / sd``. Comparing the supplied value against
    that implied value detects the unit error far more reliably than any
    absolute threshold -- a zero-edge daily series has an annualized Sharpe of
    only ~0.5, which slips under a ``|SR| > 1.0`` guard yet still makes
    ``deflated_sharpe`` return 1.0000.

    The test is deliberately narrow: it fires when the ratio of the supplied
    Sharpe to the implied one lands on a known annualization factor
    (sqrt(4|12|52|252)). A coincidental match is unlikely, so false positives
    stay near zero while the actual bug -- multiplying by sqrt(periods_per_year)
    -- is caught deterministically.
    """
    if sd < 1e-12 or mu == 0.0:
        # Degenerate/zero-edge series: fall back to the absolute backstop.
        if abs(strategy_sharpe) > MAX_PER_PERIOD_SHARPE:
            raise ValueError(
                f"strategy_sharpe={strategy_sharpe:.4f} exceeds "
                f"|SR| <= {MAX_PER_PERIOD_SHARPE} for a per-period Sharpe."
            )
        return

    implied = mu / sd
    ratio = strategy_sharpe / implied

    # If the supplied Sharpe IS the value implied by the data, it is per-period
    # by construction -- no unit error is possible -- so return immediately.
    #
    # This exists because a per-period Sharpe is NOT bounded by 1.0. Lumpy
    # per-trade returns (many exact zeros, a few large losses) can legitimately
    # give |SR| > 1, and an absolute-magnitude reject would misreport those as
    # unit errors and blank out DSR for the systems most in need of a DSR.
    #
    # .. warning::
    #    The original comment here justified the early return with observed
    #    per-period Sharpes of -1.20 / -1.65 / -1.97 / -3.68 on the live
    #    closed-pick ledger. Those values were NOT a property of the strategies:
    #    they came from a loader defect (``tools/run_anti_overfit_audit.py``
    #    filtered ``status in {"WIN","LOST"}`` while the ledger writes ``WON``,
    #    discarding 1,429 of 2,026 resolved rows -- exclusively winners). With
    #    that defect fixed the same three systems show per-period Sharpe of
    #    -0.08 / +0.04 / -0.03. The structural argument for this early return
    #    stands on its own (a per-period Sharpe has no upper bound); it should
    #    not be argued from those numbers again. See
    #    tests/test_closed_pick_loader.py.
    if implied != 0.0 and abs(strategy_sharpe - implied) <= 0.02 * abs(implied):
        return

    for periods_per_year, freq_name in _ANNUALIZATION_PROBES:
        factor = math.sqrt(periods_per_year)
        if abs(ratio - factor) <= 0.15 * factor or abs(ratio + factor) <= 0.15 * factor:
            raise ValueError(
                f"strategy_sharpe={strategy_sharpe:.4f} looks ANNUALIZED, not "
                f"per-period: it is {abs(ratio):.2f}x the per-period Sharpe "
                f"implied by returns_array ({implied:.4f}), and "
                f"sqrt({periods_per_year:.0f}) = {factor:.2f} ({freq_name} "
                f"data). deflated_sharpe needs the per-period value, because "
                f"the Lo (2002) estimator variance scales with SR**2 and an "
                f"annualized input silently returns ~1.0. Pass "
                f"{implied:.4f} directly, or pass annualised=True."
            )

    if abs(strategy_sharpe) > MAX_PER_PERIOD_SHARPE:
        raise ValueError(
            f"strategy_sharpe={strategy_sharpe:.4f} looks annualized: it is "
            f"{strategy_sharpe / implied:.2f}x the per-period Sharpe implied by "
            f"returns_array ({implied:.4f}) and above the |SR| <= "
            f"{MAX_PER_PERIOD_SHARPE} backstop. deflated_sharpe requires a "
            f"PER-PERIOD Sharpe. Either pass {implied:.4f} directly, or pass "
            f"annualised=True."
        )


def deflated_sharpe(
    strategy_sharpe: float,
    n_trials: int,
    returns_array: Sequence[float] | np.ndarray,
    annualised: bool = False,
    periods_per_year: int = 252,
) -> float:
    """Deflated Sharpe -- probability that observed Sharpe is genuine.

    DSR = P(SR > E[max(SR_n)] | n_trials, skew, kurtosis) under the null
    that all candidates have zero true Sharpe. Values >= 0.95 mean the
    headline Sharpe survives the multiple-testing correction.

    .. warning::
       ``strategy_sharpe`` **must be per-period** (same frequency as
       ``returns_array``), not annualized. This is a hard requirement of the
       Lo (2002) estimator variance; an annualized input silently *raises* the
       score. Pass ``annualised=True`` (and set ``periods_per_year``) to have
       an annualized value converted for you.

    Args:
        strategy_sharpe: observed **per-period** Sharpe of the candidate.
        n_trials: number of independent strategy backtests considered. Must
            exceed 1 for the multiple-testing correction to bite; ``n_trials=1``
            sets ``E[max SR] = 0``, which disables the correction entirely.
        returns_array: 1-D series of periodic returns from the candidate
            (used to estimate skew, kurtosis, and the SR estimator variance).
        annualised: set ``True`` if ``strategy_sharpe`` is annualized; it will
            be de-annualized with ``periods_per_year`` before use.
        periods_per_year: only consulted when ``annualised=True``.

    Returns:
        DSR probability in ``[0, 1]``.

    Raises:
        ValueError: if ``returns_array`` has < 4 observations, ``n_trials`` is
            not positive, ``strategy_sharpe`` is manifestly annualized relative
            to the supplied ``returns_array``, or a per-period Sharpe with
            ``|SR| > 1.0`` is supplied (see ``MAX_PER_PERIOD_SHARPE``).
    """
    r = np.asarray(returns_array, dtype=np.float64)
    if r.size < 4:
        raise ValueError(f"Need >= 4 returns for DSR, got {r.size}")
    if n_trials <= 0:
        raise ValueError("n_trials must be positive")

    n = r.size
    mu = r.mean()
    sd = r.std(ddof=1)

    if annualised:
        if periods_per_year <= 0:
            raise ValueError("periods_per_year must be positive")
        strategy_sharpe = float(strategy_sharpe) / math.sqrt(periods_per_year)
    else:
        strategy_sharpe = float(strategy_sharpe)
        _reject_annualized_sharpe(strategy_sharpe, mu, sd)

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
        n_candidates: ignored. Retained only for backward compatibility.

    Returns:
        ``{"dsr": float, "pbo": float, "sharpe": float, "n": int}``

    .. warning::
       ``pbo`` is **always nan** here. PBO is the probability that the
       in-sample-best configuration underperforms out-of-sample *across a real
       candidate set*; it cannot be estimated from a single return history.
       Earlier versions fabricated zero-mean random "peer" columns and ran
       :func:`cpcv_pbo` against them, which measures only "does this beat
       random noise" -- an unrelated quantity that nonetheless returned a
       plausible-looking number and was easy to mistake for PBO. Call
       :func:`cpcv_pbo` directly with a genuine ``(T x N)`` matrix of candidate
       returns when you have one.
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
    # `pbo` intentionally left as nan -- see the warning above. Do NOT
    # reintroduce a synthetic peer matrix to "make the number appear".
    return out


__all__ = [
    "cpcv_pbo",
    "reality_check_pvalue",
    "deflated_sharpe",
    "evaluate_strategy",
]

