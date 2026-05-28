"""Nelson-Siegel-Svensson (1994) yield-curve fitter for US Treasury par yields.

Fits the Svensson functional form to a set of observed par yields keyed by
tenor and produces a per-tenor fitted yield + observed-vs-fitted residual
(z-scored). This is the BOND-class edge missing from the EAGLE validation
report: BOND has 0 picks today; PR #13 wires 3 strategies but none of them
score a pick by "cheap vs the fitted curve" — that residual is what makes
a BOND pick actionable.

Functional form (Svensson 1994):

    y(tau) = beta0
           + beta1 * g1(tau; lambda1)
           + beta2 * g2(tau; lambda1)
           + beta3 * g3(tau; lambda2)

where:
    g1(tau, lam) = (1 - exp(-tau/lam)) / (tau/lam)
    g2(tau, lam) = g1(tau, lam) - exp(-tau/lam)
    g3(tau, lam) = g1(tau, lam) - exp(-tau/lam)   # uses lambda2

beta0  -> long-run level
beta1  -> short-end slope
beta2  -> medium-term curvature (decay lambda1)
beta3  -> second hump curvature (decay lambda2)

Cheap/rich logic
----------------
A bond whose observed yield is ABOVE the fitted curve (positive residual)
trades at a yield premium vs the fitted curve i.e. price is depressed ->
CHEAP. A negative residual means yield is below the curve -> RICH. We
z-score the residual against the cross-sectional residual stdev so the
threshold is unit-free; +/- 1.5 z is the actionable band.

## Wiring Plan
Consumer file: ``alpha_engine/bond_strategies.py`` (to be wired in PR #13
follow-up — the three BOND strategies need a residual score on each candidate
pick before the smart-pick gate will fire).
Producer cron: ``tools/fetch_fred_treasury_curve.py`` (to be added — pulls
FRED DGS1MO / DGS3MO / DGS6MO / DGS1 / DGS2 / DGS3 / DGS5 / DGS7 / DGS10 /
DGS20 / DGS30 daily and caches to ``alpha_engine/data/fred_treasury_curve.json``).
Until those land this module is opt-in via the env flag
``BOND_NSS_RESIDUAL_ENABLED`` (default off). Per repo CLAUDE.md Wire-Up Rule
this is the "opt-in sidecar" path, not the "wired" path.
"""

from __future__ import annotations

import math
import os
from typing import Any

import numpy as np

try:
    from scipy.optimize import least_squares  # type: ignore

    _HAS_SCIPY = True
except Exception:  # pragma: no cover - fallback path
    _HAS_SCIPY = False


# Tenor string -> years
_TENOR_YEARS: dict[str, float] = {
    "1m": 1.0 / 12.0,
    "2m": 2.0 / 12.0,
    "3m": 3.0 / 12.0,
    "6m": 6.0 / 12.0,
    "1y": 1.0,
    "2y": 2.0,
    "3y": 3.0,
    "5y": 5.0,
    "7y": 7.0,
    "10y": 10.0,
    "20y": 20.0,
    "30y": 30.0,
}


def tenor_to_years(tenor: str) -> float:
    """Convert a tenor string like '3m' or '10y' to years."""
    t = tenor.strip().lower()
    if t in _TENOR_YEARS:
        return _TENOR_YEARS[t]
    # Fall back to permissive parsing.
    if t.endswith("m"):
        return float(t[:-1]) / 12.0
    if t.endswith("y"):
        return float(t[:-1])
    raise ValueError(f"Unrecognized tenor string: {tenor!r}")


def _g1(tau: np.ndarray, lam: float) -> np.ndarray:
    x = tau / lam
    # Limit at x -> 0: (1 - exp(-x)) / x -> 1
    out = np.where(np.abs(x) < 1e-9, 1.0, (1.0 - np.exp(-x)) / np.where(x == 0, 1.0, x))
    return out


def _g2(tau: np.ndarray, lam: float) -> np.ndarray:
    return _g1(tau, lam) - np.exp(-tau / lam)


def _g3(tau: np.ndarray, lam: float) -> np.ndarray:
    # Same shape as g2 but with its own lambda (passed in by caller via lam).
    return _g1(tau, lam) - np.exp(-tau / lam)


def nss_yield(
    tau: np.ndarray | float,
    beta0: float,
    beta1: float,
    beta2: float,
    beta3: float,
    lambda1: float,
    lambda2: float,
) -> np.ndarray:
    """Vectorized Svensson yield for an array of tenors (years)."""
    tau_arr = np.atleast_1d(np.asarray(tau, dtype=float))
    return (
        beta0
        + beta1 * _g1(tau_arr, lambda1)
        + beta2 * _g2(tau_arr, lambda1)
        + beta3 * _g3(tau_arr, lambda2)
    )


def _residuals(params: np.ndarray, tau: np.ndarray, y: np.ndarray) -> np.ndarray:
    beta0, beta1, beta2, beta3, lambda1, lambda2 = params
    return nss_yield(tau, beta0, beta1, beta2, beta3, lambda1, lambda2) - y


def _scan_fit(tau: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, float]:
    """Numpy-only fallback: scan over (lambda1, lambda2), solve linear betas via lstsq."""
    best = None
    best_ss = float("inf")
    lambdas = [0.25, 0.5, 1.0, 1.5, 2.0, 3.0, 4.0, 5.0, 7.0, 10.0, 15.0]
    for l1 in lambdas:
        for l2 in lambdas:
            if l2 == l1:
                continue
            # Linear regression for betas given fixed lambdas.
            X = np.column_stack(
                [
                    np.ones_like(tau),
                    _g1(tau, l1),
                    _g2(tau, l1),
                    _g3(tau, l2),
                ]
            )
            betas, *_ = np.linalg.lstsq(X, y, rcond=None)
            resid = X @ betas - y
            ss = float(np.sum(resid**2))
            if ss < best_ss:
                best_ss = ss
                best = (betas, l1, l2)
    assert best is not None
    betas, l1, l2 = best
    params = np.array([betas[0], betas[1], betas[2], betas[3], l1, l2], dtype=float)
    return params, best_ss


def fit_nss(
    par_yields: dict[str, float],
    beta_init: list[float] | None = None,
) -> dict[str, Any]:
    """Fit a Nelson-Siegel-Svensson curve to observed par yields.

    Parameters
    ----------
    par_yields:
        Mapping of tenor-string ('1m','3m',...,'30y') to yield in percent.
    beta_init:
        Optional warm-start [beta0, beta1, beta2, beta3, lambda1, lambda2].

    Returns
    -------
    dict with keys: beta0, beta1, beta2, beta3, lambda1, lambda2,
    fit_y (per-tenor fitted yield), residuals (per-tenor observed minus
    fitted), r_squared (cross-sectional fit quality).
    """
    if not par_yields:
        raise ValueError("par_yields must be non-empty")

    tenors = list(par_yields.keys())
    tau = np.array([tenor_to_years(t) for t in tenors], dtype=float)
    y = np.array([float(par_yields[t]) for t in tenors], dtype=float)

    # Warm-start: beta0 ~ long-end yield, beta1 ~ short - long, lambdas in
    # the canonical 1y / 5y neighbourhood. The user can override.
    if beta_init is None:
        long_end = float(y[np.argmax(tau)])
        short_end = float(y[np.argmin(tau)])
        beta_init = [long_end, short_end - long_end, 0.0, 0.0, 1.5, 5.0]

    # Always seed with a scan-based warm start: NSS has many local minima
    # (especially when the curve has a hump like a real Treasury curve) and a
    # single starting point reliably under-fits realistic data. The scan gives
    # us a near-global linear-betas fit per (lambda1, lambda2) grid point.
    scan_params, scan_ss = _scan_fit(tau, y)

    if _HAS_SCIPY:
        lb = [-np.inf, -np.inf, -np.inf, -np.inf, 1e-3, 1e-3]
        ub = [np.inf, np.inf, np.inf, np.inf, 30.0, 30.0]
        candidates: list[tuple[float, np.ndarray]] = [(scan_ss, scan_params)]
        starts = [scan_params, np.array(beta_init, dtype=float)]
        for x0 in starts:
            try:
                result = least_squares(
                    _residuals,
                    x0=x0,
                    args=(tau, y),
                    bounds=(lb, ub),
                    method="trf",
                    max_nfev=5000,
                )
                ss = float(np.sum(_residuals(result.x, tau, y) ** 2))
                candidates.append((ss, result.x))
            except Exception:
                continue
        candidates.sort(key=lambda c: c[0])
        params = candidates[0][1]
    else:
        params = scan_params

    beta0, beta1, beta2, beta3, lambda1, lambda2 = (float(p) for p in params)

    fit_arr = nss_yield(tau, beta0, beta1, beta2, beta3, lambda1, lambda2)
    resid_arr = y - fit_arr

    ss_res = float(np.sum(resid_arr**2))
    ss_tot = float(np.sum((y - np.mean(y)) ** 2))
    r_squared = 1.0 - ss_res / ss_tot if ss_tot > 0 else float("nan")

    fit_y = {t: float(fit_arr[i]) for i, t in enumerate(tenors)}
    residuals = {t: float(resid_arr[i]) for i, t in enumerate(tenors)}

    return {
        "beta0": beta0,
        "beta1": beta1,
        "beta2": beta2,
        "beta3": beta3,
        "lambda1": lambda1,
        "lambda2": lambda2,
        "fit_y": fit_y,
        "residuals": residuals,
        "r_squared": float(r_squared),
    }


def _resolve_observed_yield(pick: dict[str, Any], fred_series: dict | None) -> float | None:
    """Best-effort extraction of an observed yield for a bond pick."""
    for key in ("observed_yield", "yield", "ytm", "yield_pct"):
        if key in pick and pick[key] is not None:
            return float(pick[key])
    if fred_series:
        for key in ("fred_series_id", "series_id"):
            sid = pick.get(key)
            if sid and sid in fred_series:
                return float(fred_series[sid])
    return None


def _resolve_tenor(pick: dict[str, Any]) -> str | None:
    for key in ("tenor", "maturity", "bucket"):
        v = pick.get(key)
        if isinstance(v, str) and v:
            return v
    return None


def residual_for_bond_pick(
    pick: dict[str, Any],
    fitted: dict[str, Any],
    fred_series: dict | None = None,
) -> dict[str, Any]:
    """Score a single bond pick against a previously fitted NSS curve.

    Returns a dict with the fitted yield at the pick's tenor, the observed
    yield, raw residual, z-scored residual, and a CHEAP / RICH / FAIR tag.
    """
    if os.getenv("BOND_NSS_RESIDUAL_ENABLED", "").lower() in {"0", "false", "no", ""}:
        # The sidecar is opt-in until the wiring PR lands. We still return a
        # well-formed dict so the caller doesn't need to special-case it; the
        # 'enabled' flag tells downstream code whether to act on the score.
        enabled = False
    else:
        enabled = True

    tenor = _resolve_tenor(pick)
    if tenor is None:
        raise ValueError("pick must contain a tenor/maturity/bucket string")

    fit_y = fitted.get("fit_y", {})
    residuals_map = fitted.get("residuals", {})

    # Fitted yield at the pick's tenor: prefer cached value, otherwise eval
    # the NSS formula directly so picks at arbitrary tenors still work.
    if tenor in fit_y:
        fitted_yield = float(fit_y[tenor])
    else:
        tau = tenor_to_years(tenor)
        fitted_yield = float(
            nss_yield(
                tau,
                fitted["beta0"],
                fitted["beta1"],
                fitted["beta2"],
                fitted["beta3"],
                fitted["lambda1"],
                fitted["lambda2"],
            )[0]
        )

    observed = _resolve_observed_yield(pick, fred_series)
    if observed is None:
        raise ValueError("pick has no observed yield and no resolvable FRED series")

    residual = observed - fitted_yield

    # Cross-sectional residual stdev for z-score.
    resid_vals = np.array(list(residuals_map.values()), dtype=float) if residuals_map else np.array([])
    if resid_vals.size >= 2:
        sd = float(np.std(resid_vals, ddof=1))
    else:
        sd = 0.0
    if sd > 1e-12 and math.isfinite(sd):
        z_resid = residual / sd
    else:
        z_resid = 0.0

    if z_resid > 1.5:
        tag = "CHEAP"
    elif z_resid < -1.5:
        tag = "RICH"
    else:
        tag = "FAIR"

    return {
        "fitted_yield": fitted_yield,
        "observed_yield": float(observed),
        "residual": float(residual),
        "z_residual": float(z_resid),
        "cheap_or_rich": tag,
        "enabled": enabled,
    }


__all__ = [
    "fit_nss",
    "nss_yield",
    "residual_for_bond_pick",
    "tenor_to_years",
]
