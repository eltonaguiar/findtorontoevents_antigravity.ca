"""PyPortfolioOpt sidecar — Ledoit-Wolf shrinkage HRP + mean-variance.

OPT-IN SIDECAR — does not modify production pick-generation, scoring, or
active-gate paths. This extends (does not replace) the existing
hand-rolled allocators in ``tools/risk_parity_allocator.py`` and
``tools/hrp_allocator.py``.

Why
---
The hand-rolled HRP allocator uses raw Pearson correlation, which is
unstable at the small-n typical of per-asset-class history (we have
n=17 BOND, n=83 ETF). PyPortfolioOpt provides:

  - ``risk_models.CovarianceShrinkage(...).ledoit_wolf()`` — covariance
    estimator that's well-conditioned at small n.
  - ``HRPOpt`` — Lopez de Prado HRP with SciPy-grade single-linkage
    clustering (the hand-rolled version reimplements clustering in pure
    Python, which is correct but slower and harder to extend).
  - ``EfficientFrontier`` — mean-variance optimizer with constraints.

All three are exposed here as thin wrappers that take a returns
DataFrame and return a ``{asset_or_strategy: weight}`` dict — same shape
as the hand-rolled allocators, so callers can A/B them.

PyPortfolioOpt is an **optional dependency**. If it (or its cvxpy
backend) isn't installed, the sidecar reports ``available=False`` and
all wrapper functions raise ``RuntimeError`` with a pointer to the
install command. Importing this module is always safe.

Wiring (per CLAUDE.md Wire-Up Rule)
-----------------------------------
This is an **opt-in sidecar**. No production pick-generation or scoring
path imports it. Production wiring is deferred — see the PR description's
``## Wiring Plan`` section. Existing hand-rolled allocators
(``tools/risk_parity_allocator.py``, ``tools/hrp_allocator.py``) remain
the default.

License notice
--------------
PyPortfolioOpt is MIT-licensed (compatible with this project).
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# Probe whether pypfopt is importable. We don't import its submodules at
# module load time because cvxpy can fail noisily on import on some
# environments; we want this file to be import-safe regardless.
try:
    import pypfopt  # type: ignore  # noqa: F401
    _PYPFOPT_AVAILABLE = True
except Exception as _e:  # pragma: no cover - install detection
    logger.debug("pypfopt not available: %s", _e)
    _PYPFOPT_AVAILABLE = False


def is_available() -> bool:
    """Return True iff pypfopt is importable in this environment."""
    return _PYPFOPT_AVAILABLE


_INSTALL_HINT = (
    "PyPortfolioOpt is not installed. Install with "
    "`pip install -r requirements-hedge-fund.txt` "
    "or `pip install PyPortfolioOpt`. (Note: cvxpy is a transitive "
    "dependency and may need a C compiler on first install.)"
)


def _require():
    if not _PYPFOPT_AVAILABLE:
        raise RuntimeError(_INSTALL_HINT)


def ledoit_wolf_covariance(returns_df):
    """Ledoit-Wolf shrinkage covariance estimator.

    Parameters
    ----------
    returns_df : pandas.DataFrame
        Rows = time periods, columns = asset / strategy / asset-class
        labels. Values = period returns (decimal).

    Returns
    -------
    pandas.DataFrame
        Shrinkage-estimated covariance matrix, same column order.
    """
    _require()
    from pypfopt import risk_models  # type: ignore

    return risk_models.CovarianceShrinkage(returns_df, returns_data=True).ledoit_wolf()


def hrp_weights(returns_df) -> dict[str, float]:
    """Hierarchical Risk Parity weights (Lopez de Prado 2016).

    Drop-in companion to ``tools/hrp_allocator.py:hrp_weights`` that
    uses PyPortfolioOpt's SciPy-backed clustering and Ledoit-Wolf cov.

    Returns
    -------
    dict[str, float]
        ``{label: weight}`` summing to 1.0.
    """
    _require()
    from pypfopt import HRPOpt  # type: ignore

    cov = ledoit_wolf_covariance(returns_df)
    hrp = HRPOpt(returns=returns_df, cov_matrix=cov)
    hrp.optimize()
    weights = hrp.clean_weights()
    # ``clean_weights`` returns an OrderedDict[str, float] with values rounded
    # to 5 decimals and tiny weights snapped to 0. Convert to plain dict.
    return {str(k): float(v) for k, v in weights.items()}


def mean_variance_weights(
    returns_df,
    *,
    target_return: float | None = None,
    target_volatility: float | None = None,
    weight_bounds: tuple[float, float] = (0.0, 1.0),
) -> dict[str, float]:
    """Mean-variance optimal weights.

    Defaults to the maximum Sharpe portfolio. Pass ``target_return`` to
    minimize variance subject to a return constraint, or
    ``target_volatility`` to maximize return subject to a vol cap.

    Returns
    -------
    dict[str, float]
        ``{label: weight}`` summing to 1.0 (long-only by default).
    """
    _require()
    from pypfopt import EfficientFrontier, expected_returns, risk_models  # type: ignore

    mu = expected_returns.mean_historical_return(returns_df, returns_data=True)
    cov = risk_models.CovarianceShrinkage(returns_df, returns_data=True).ledoit_wolf()
    ef = EfficientFrontier(mu, cov, weight_bounds=weight_bounds)
    if target_return is not None and target_volatility is not None:
        raise ValueError("provide at most one of target_return / target_volatility")
    if target_return is not None:
        ef.efficient_return(target_return=target_return)
    elif target_volatility is not None:
        ef.efficient_risk(target_volatility=target_volatility)
    else:
        ef.max_sharpe()
    weights = ef.clean_weights()
    return {str(k): float(v) for k, v in weights.items()}


def diagnostic_report() -> dict[str, Any]:
    """One-line health probe for ops dashboards."""
    info: dict[str, Any] = {"available": _PYPFOPT_AVAILABLE}
    if _PYPFOPT_AVAILABLE:
        try:
            import pypfopt  # type: ignore

            info["version"] = getattr(pypfopt, "__version__", "unknown")
        except Exception as exc:  # pragma: no cover
            info["version_error"] = str(exc)
    else:
        info["install_hint"] = _INSTALL_HINT
    return info


if __name__ == "__main__":  # pragma: no cover
    import json
    import sys

    print(json.dumps(diagnostic_report(), indent=2))
    sys.exit(0 if _PYPFOPT_AVAILABLE else 1)
