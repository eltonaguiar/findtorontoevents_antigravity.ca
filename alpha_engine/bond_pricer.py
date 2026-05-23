"""Treasury bond pricing + key-rate-duration sidecar.

Wraps QuantLib for fixed-rate Treasury pricing (price/YTM/duration/DV01) +
a numerically-bumped key-rate-duration profile. If ``QuantLib`` is not
importable (the 80MB binary is finicky on some Python/OS combos), all three
public functions fall back to a self-contained numpy-only flat-curve pricer.

Public API
~~~~~~~~~~
- :func:`price_treasury` — clean price, YTM, modified duration, DV01
- :func:`krd_profile`    — key-rate-duration buckets (default 2/5/10/30Y)
- :func:`credit_spread_zscore` — rolling z-score of an LQD-HYG spread

Opt-in sidecar (CLAUDE.md Wire-Up Rule). No production scoring imports it.
"""
from __future__ import annotations

import logging
import math
from typing import Iterable, Optional

logger = logging.getLogger(__name__)

try:  # pragma: no cover — QuantLib path covered when the lib is present
    import QuantLib as ql  # type: ignore
    _QL_AVAILABLE = True
except Exception as _e:  # noqa: BLE001
    ql = None  # type: ignore
    _QL_AVAILABLE = False
    logger.info("QuantLib unavailable (%s); using numpy fallback pricer", _e)


# Maps the 11 FRED Treasury tenors to a canonical short-label curve list,
# used by krd_profile() to bump specific points on the curve.
DEFAULT_TENORS_Y: dict[str, float] = {
    "1M": 1 / 12, "3M": 0.25, "6M": 0.5,
    "1Y": 1.0, "2Y": 2.0, "3Y": 3.0, "5Y": 5.0,
    "7Y": 7.0, "10Y": 10.0, "20Y": 20.0, "30Y": 30.0,
}

# FRED column-name -> tenor in years (for parsing get_treasury_curve output).
_FRED_COL_TO_YEAR: dict[str, float] = {
    "DGS1MO": 1 / 12, "DGS3MO": 0.25, "DGS6MO": 0.5,
    "DGS1": 1.0, "DGS2": 2.0, "DGS3": 3.0, "DGS5": 5.0,
    "DGS7": 7.0, "DGS10": 10.0, "DGS20": 20.0, "DGS30": 30.0,
}


def _finite(x) -> bool:
    try:
        return math.isfinite(float(x))
    except (TypeError, ValueError):
        return False


def _curve_to_tenor_yield_pairs(curve_df) -> list[tuple[float, float]]:
    """Latest non-NaN row of ``curve_df`` -> sorted (tenor_y, yield_decimal)."""
    if curve_df is None or (hasattr(curve_df, "empty") and curve_df.empty):
        raise ValueError("curve_df is empty/None")
    row = None
    for _, candidate in curve_df.iloc[::-1].iterrows():
        if any(_finite(v) for v in candidate.values):
            row = candidate
            break
    if row is None:
        raise ValueError("curve_df has no finite values")
    pairs: list[tuple[float, float]] = []
    for col, val in row.items():
        if not _finite(val):
            continue
        tenor = _FRED_COL_TO_YEAR.get(str(col)) or DEFAULT_TENORS_Y.get(str(col))
        if tenor is None:
            continue
        pairs.append((float(tenor), float(val) / 100.0))
    pairs.sort(key=lambda x: x[0])
    if not pairs:
        raise ValueError("curve_df has no recognizable tenor columns")
    return pairs


def _interp_yield(tenor_y: float, pairs: list[tuple[float, float]]) -> float:
    """Linear interpolation; flat extrapolation off the ends."""
    if tenor_y <= pairs[0][0]:
        return pairs[0][1]
    if tenor_y >= pairs[-1][0]:
        return pairs[-1][1]
    for i in range(len(pairs) - 1):
        x0, y0 = pairs[i]
        x1, y1 = pairs[i + 1]
        if x0 <= tenor_y <= x1:
            return y0 + (tenor_y - x0) / (x1 - x0) * (y1 - y0)
    return pairs[-1][1]  # pragma: no cover


def _years_to_maturity(maturity) -> float:
    from datetime import date, datetime
    if isinstance(maturity, (int, float)):
        return float(maturity)
    if isinstance(maturity, str):
        maturity = datetime.fromisoformat(maturity).date()
    if isinstance(maturity, datetime):
        maturity = maturity.date()
    if isinstance(maturity, date):
        return (maturity - datetime.utcnow().date()).days / 365.25
    raise TypeError(f"unsupported maturity type: {type(maturity)}")


def _np_price_bond(coupon, years, ytm, freq=2, face=100.0):
    """Closed-form clean price for a fixed-coupon bond."""
    n = max(1, int(round(years * freq)))
    c = coupon * face / freq
    r = ytm / freq
    if abs(r) < 1e-12:
        return c * n + face
    return c * (1.0 - (1.0 + r) ** (-n)) / r + face * (1.0 + r) ** (-n)


def _np_solve_ytm(price, coupon, years, freq=2, face=100.0):
    lo, hi = -0.5, 1.0
    for _ in range(100):
        mid = 0.5 * (lo + hi)
        if _np_price_bond(coupon, years, mid, freq, face) > price:
            lo = mid
        else:
            hi = mid
        if hi - lo < 1e-9:
            break
    return 0.5 * (lo + hi)


def _np_modified_duration(coupon, years, ytm, freq=2, face=100.0):
    bp = 1e-4
    p_up = _np_price_bond(coupon, years, ytm + bp, freq, face)
    p_dn = _np_price_bond(coupon, years, ytm - bp, freq, face)
    p_0 = _np_price_bond(coupon, years, ytm, freq, face)
    return 0.0 if p_0 == 0 else -(p_up - p_dn) / (2.0 * bp * p_0)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def price_treasury(
    coupon: float,
    maturity,
    curve_df,
    *,
    face: float = 100.0,
    freq: int = 2,
) -> dict:
    """Price a fixed-rate Treasury bond off ``curve_df``.

    Args:
        coupon: annual coupon rate (e.g. 0.04 for 4%).
        maturity: years (float) or date / ISO-string.
        curve_df: DataFrame from
            :func:`alpha_engine.fred_data_fetcher.get_treasury_curve` (yields in %).
        face: notional, default 100.
        freq: coupon frequency per year (Treasuries: 2).

    Returns:
        ``{"price", "ytm", "dur", "dv01"}``. ``ytm``/``dur`` in decimal/years,
        ``dv01`` in dollars per ``face`` per 1bp.
    """
    pairs = _curve_to_tenor_yield_pairs(curve_df)
    years = _years_to_maturity(maturity)
    par_yield = _interp_yield(years, pairs)

    if _QL_AVAILABLE:
        try:
            return _ql_price_treasury(coupon, years, par_yield, face, freq)
        except Exception as e:  # noqa: BLE001
            logger.warning("QuantLib pricing failed (%s); using numpy", e)

    price = _np_price_bond(coupon, years, par_yield, freq, face)
    ytm = _np_solve_ytm(price, coupon, years, freq, face)
    dur = _np_modified_duration(coupon, years, ytm, freq, face)
    return {"price": price, "ytm": ytm, "dur": dur, "dv01": dur * price * 1e-4}


def krd_profile(
    bond_spec: dict,
    curve_df,
    key_tenors: Optional[Iterable[str]] = None,
    *,
    bump_bp: float = 1.0,
) -> dict:
    """Key-rate-duration buckets (numerically-bumped).

    Bumps each key tenor on the curve by ``bump_bp`` and re-prices. Sum of
    bucket KRDs approximates the total modified duration.

    Args:
        bond_spec: ``{"coupon", "maturity", "face"?, "freq"?}``.
        curve_df: same as :func:`price_treasury`.
        key_tenors: labels from :data:`DEFAULT_TENORS_Y`,
            default ``("2Y", "5Y", "10Y", "30Y")``.
        bump_bp: curve bump in basis points.
    """
    pairs = _curve_to_tenor_yield_pairs(curve_df)
    coupon = float(bond_spec["coupon"])
    years = _years_to_maturity(bond_spec["maturity"])
    face = float(bond_spec.get("face", 100.0))
    freq = int(bond_spec.get("freq", 2))
    tenors = list(key_tenors) if key_tenors else ["2Y", "5Y", "10Y", "30Y"]

    base_yield = _interp_yield(years, pairs)
    base_price = _np_price_bond(coupon, years, base_yield, freq, face)
    bump = bump_bp * 1e-4

    out: dict = {}
    for label in tenors:
        if label not in DEFAULT_TENORS_Y:
            logger.warning("krd_profile: skipping unknown tenor %r", label)
            continue
        target = DEFAULT_TENORS_Y[label]
        nearest_idx = min(range(len(pairs)),
                          key=lambda i: abs(pairs[i][0] - target))
        bumped = [(t, y + bump if i == nearest_idx else y)
                  for i, (t, y) in enumerate(pairs)]
        p_up = _np_price_bond(coupon, years, _interp_yield(years, bumped),
                              freq, face)
        out[label] = (-(p_up - base_price) / (base_price * bump)
                      if base_price else 0.0)

    out["_total_dur"] = _np_modified_duration(coupon, years, base_yield, freq, face)
    out["_base_price"] = base_price
    return out


def credit_spread_zscore(lqd_hyg_spread_series, lookback: int = 60) -> float:
    """Rolling z-score: latest spread vs prior ``lookback`` window.

    LQD-HYG strategy thresholds: ``z >= +2`` -> long IG (spread rich);
    ``z <= -2`` -> long HY (spread cheap); else neutral. Returns NaN if
    fewer than ``lookback + 1`` finite observations.
    """
    try:
        import numpy as np
    except ImportError as e:  # pragma: no cover
        raise RuntimeError("numpy required for credit_spread_zscore") from e
    vals = list(getattr(lqd_hyg_spread_series, "values", lqd_hyg_spread_series))
    vals = [float(v) for v in vals if _finite(v)]
    if len(vals) < lookback + 1:
        return float("nan")
    window = np.array(vals[-(lookback + 1):-1], dtype=float)
    sd = float(window.std(ddof=1))
    if sd <= 0 or not math.isfinite(sd):
        return float("nan")
    return (vals[-1] - float(window.mean())) / sd


# ---------------------------------------------------------------------------
# QuantLib path
# ---------------------------------------------------------------------------
def _ql_price_treasury(coupon, years, par_yield, face, freq):  # pragma: no cover
    today = ql.Date.todaysDate()
    ql.Settings.instance().evaluationDate = today
    calendar = ql.UnitedStates(ql.UnitedStates.GovernmentBond)
    day_count = ql.ActualActual(ql.ActualActual.Bond)
    coupon_freq = (ql.Period(ql.Semiannual) if freq == 2
                   else ql.Period(int(12 / max(freq, 1)), ql.Months))
    days = max(1, int(round(years * 365.25)))
    schedule = ql.Schedule(
        today, today + ql.Period(days, ql.Days), coupon_freq, calendar,
        ql.Unadjusted, ql.Unadjusted, ql.DateGeneration.Backward, False,
    )
    bond = ql.FixedRateBond(1, face, schedule, [coupon], day_count)
    flat = ql.FlatForward(today, par_yield, day_count, ql.Compounded, ql.Semiannual)
    bond.setPricingEngine(ql.DiscountingBondEngine(ql.YieldTermStructureHandle(flat)))
    price = bond.cleanPrice()
    ytm = bond.bondYield(price, day_count, ql.Compounded, ql.Semiannual)
    rate = ql.InterestRate(ytm, day_count, ql.Compounded, ql.Semiannual)
    dur = ql.BondFunctions.duration(bond, rate, ql.Duration.Modified)
    return {"price": float(price), "ytm": float(ytm),
            "dur": float(dur), "dv01": float(dur) * float(price) * 1e-4}
