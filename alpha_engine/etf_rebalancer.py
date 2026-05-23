"""ETF sector-rotation sleeve constructor — HRP weights + 12-1 momentum.

Opt-in sidecar per CLAUDE.md Wire-Up Rule. Default OFF.

Wires the long-orphan portfolio-optimizer pinned in
`scripts/worldclass/requirements.txt:20` (`riskfolio-lib>=4.0.0`) into a
production-shaped caller. See `reports/library_research_stocks_etfs_bonds_2026_04_28.md`
§7 row 2.

Reality: Riskfolio-Lib v7.2.1 fails to install in this env (Py 3.14 + scipy
mesonpy build error). Fallback = PyPortfolioOpt's HRPOpt (already at
`pypfopt 1.6.0`, shipped via PR #466). Same recursive-bisection HRP, same
single-linkage cluster on correlation distance. We lose HERC + CDaR + factor
BL; we keep the HRP weight vector, which is what the MVP needs.

Public API:
    hrp_weights(returns_df, codependence="pearson") -> dict[str, float]
    sector_rotation_signal(prices_df, lookback=60, top_n=3) -> dict
Both soft-fail to equal-weight when the optimizer lib is unavailable.
"""
from __future__ import annotations

import logging
import math
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)

# SPDR sector ETF universe (S1 ETF-team recommendation: SPDR sector momentum)
SPDR_SECTOR_ETFS: tuple[str, ...] = (
    "XLK",   # Technology
    "XLV",   # Health Care
    "XLF",   # Financials
    "XLE",   # Energy
    "XLP",   # Consumer Staples
    "XLY",   # Consumer Discretionary
    "XLRE",  # Real Estate
    "XLB",   # Materials
    "XLI",   # Industrials
    "XLU",   # Utilities
    "XLC",   # Communication Services
)


def _equal_weights(tickers: list[str]) -> dict[str, float]:
    """Fallback equal-weight allocation. Used when optimizer lib unavailable."""
    if not tickers:
        return {}
    w = 1.0 / len(tickers)
    return {t: w for t in tickers}


def hrp_weights(
    returns_df: pd.DataFrame,
    codependence: str = "pearson",
) -> dict[str, float]:
    """Hierarchical Risk Parity sleeve weights for an ETF universe.

    Args:
        returns_df: DataFrame of daily returns, columns = tickers, index = dates.
            Must have at least 2 columns and >=20 rows of clean data.
        codependence: Correlation measure ("pearson" only via the pypfopt
            fallback; Riskfolio's "spearman"/"abs_pearson" are unavailable
            until the install is fixed).

    Returns:
        Dict of {ticker: weight}, summing to ~1.0, all weights >=0.

    Soft-fails to equal-weight if:
        - returns_df has <2 columns or <20 rows (insufficient data)
        - PyPortfolioOpt not importable (install missing)
        - HRPOpt raises (singular cov matrix, all-NaN row, etc.)
    """
    if returns_df is None or returns_df.empty:
        return {}

    tickers = list(returns_df.columns)
    if len(tickers) < 2:
        return _equal_weights(tickers)

    # Drop all-NaN rows + forward-fill remaining NaN; require minimum sample.
    cleaned = returns_df.dropna(how="all").ffill().dropna()
    if len(cleaned) < 20:
        logger.warning(
            "hrp_weights: only %d clean rows for %d tickers — "
            "falling back to equal-weight.",
            len(cleaned), len(tickers),
        )
        return _equal_weights(tickers)

    # Lazy import — keeps cvxpy/scipy/scikit-learn off the import path of any
    # production scanner that pulls this module transitively. Per CLAUDE.md
    # Wire-Up Rule, sidecars must not regress startup time of live paths.
    try:
        from pypfopt import HRPOpt  # type: ignore
    except ImportError:
        logger.warning(
            "hrp_weights: PyPortfolioOpt not installed — equal-weight fallback. "
            "(Riskfolio-Lib also unavailable; see module docstring.)"
        )
        return _equal_weights(tickers)

    if codependence != "pearson":
        # pypfopt HRP is pearson-only. Document the loss vs Riskfolio's API.
        logger.info(
            "hrp_weights: codependence=%r requested but pypfopt fallback "
            "supports only 'pearson'. Using pearson.",
            codependence,
        )

    try:
        hrp = HRPOpt(returns=cleaned)
        raw = hrp.optimize()
        # raw is OrderedDict[str, float]; normalise to plain dict + tiny-float clean-up
        weights: dict[str, float] = {}
        total = 0.0
        for t, w in raw.items():
            wf = float(w)
            if not math.isfinite(wf) or wf < 0:
                wf = 0.0
            weights[t] = wf
            total += wf
        if total <= 0:
            logger.warning("hrp_weights: optimizer returned zero-sum weights — equal-weight fallback.")
            return _equal_weights(tickers)
        # Renormalise to exactly 1.0
        return {t: w / total for t, w in weights.items()}
    except Exception as exc:  # pragma: no cover - depends on pypfopt internals
        logger.warning("hrp_weights: HRPOpt raised %s — equal-weight fallback.", exc)
        return _equal_weights(tickers)


def _twelve_one_momentum(prices_df: pd.DataFrame, lookback: int) -> pd.Series:
    """Jegadeesh-Titman 12-1 momentum (skip last month).

    For ETF MVP we use ``lookback`` trading days as proxy for 12 months,
    skipping the most recent ~21 (1 month) to dampen short-term reversal.
    With lookback=60 (3mo proxy) we skip 5 days. With lookback=252 (12mo)
    we skip 21. The ratio is preserved.
    """
    if prices_df.empty or len(prices_df) < lookback + 5:
        return pd.Series(dtype=float)

    skip = max(1, lookback // 12)  # ~1mo skip per ~12mo lookback
    end = prices_df.iloc[-skip - 1]
    start = prices_df.iloc[-lookback - skip]
    momentum = (end / start) - 1.0
    return momentum.sort_values(ascending=False)


def sector_rotation_signal(
    prices_df: pd.DataFrame,
    lookback: int = 60,
    top_n: int = 3,
) -> dict[str, Any]:
    """Rank SPDR sectors by 12-1 momentum, return top-N + HRP weights.

    Args:
        prices_df: DataFrame of close prices, columns=tickers, index=dates.
        lookback: Days to compute momentum over (60 = ~3mo proxy).
        top_n: Number of top-ranked sectors to size.

    Returns:
        {
          "top_n":        [ticker, ...] in momentum-rank order,
          "momentum":     {ticker: 12-1 return},
          "weights":      {ticker: HRP weight} for top_n only, sums to ~1.0,
          "method":       "hrp" | "equal_weight_fallback",
          "lookback":     int,
          "n_sectors":    int (size of input universe),
        }
    """
    if prices_df is None or prices_df.empty:
        return {"top_n": [], "momentum": {}, "weights": {},
                "method": "empty_input", "lookback": lookback, "n_sectors": 0}

    momentum = _twelve_one_momentum(prices_df, lookback)
    if momentum.empty:
        logger.warning("sector_rotation_signal: insufficient price history for lookback=%d.", lookback)
        return {"top_n": [], "momentum": {}, "weights": {},
                "method": "insufficient_history", "lookback": lookback,
                "n_sectors": prices_df.shape[1]}

    top_tickers = list(momentum.head(top_n).index)
    top_returns = prices_df[top_tickers].pct_change().dropna()

    weights = hrp_weights(top_returns)
    method = "hrp" if any(abs(w - 1.0 / len(top_tickers)) > 1e-9 for w in weights.values()) else "equal_weight_fallback"
    # Equal-weight detection above is a hint, not a strict signal — HRP can
    # legitimately produce equal weights when assets are perfectly homogeneous.

    return {
        "top_n": top_tickers,
        "momentum": {t: float(momentum[t]) for t in momentum.index},
        "weights": weights,
        "method": method,
        "lookback": lookback,
        "n_sectors": prices_df.shape[1],
    }
