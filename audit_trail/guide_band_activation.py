"""Wilson-LB gated Guide-band activation with hysteresis.

Phase 5 of the /audit roadmap (see
``docs/REMAINING_ENHANCEMENT_PROPOSALS_V3_2026_04_20.md``).

Replaces the unreproducible "Maximum Conviction Combo" Guide band with a
statistically-defensible gate:

* Wilson 95 percent lower bound on win-rate must clear ``activate_at`` (default
  0.52 — DeepSeek power analysis showed 0.45 at n=20 only discriminates WR 0.78
  vs 0.50).
* Minimum sample ``n >= 50`` gives ~70 percent power for a one-sample binomial
  test p=0.50 vs p=0.65 at alpha=0.05 (methodology reviewer recomputed: ~66
  required for 80 percent power). 50 is the statistical-display floor, not
  the confidence floor. Operators can raise ``min_n`` to 66 for stricter
  power discipline.
* Hysteresis: once active, the band stays active until the Wilson LB drops
  below ``deactivate_below`` (default 0.45). Gap ~0.07 ≈ 1 SE of phat at
  n=50 (SE ≈ sqrt(0.25/50) ≈ 0.0707). A narrower gap (e.g. 0.05) would
  thrash on sampling jitter.
* Optional Bonferroni correction via ``k`` for multi-filter families.
"""

from __future__ import annotations

from math import sqrt
from statistics import NormalDist


def wilson_lower_bound(wins: int, n: int, z: float = 1.96) -> float:
    """Standard Wilson score interval lower bound.

    ``z=1.96`` is the 95 percent two-sided critical value. Callers may pass
    ``z=2.576`` for 99 percent confidence, etc.

    Returns 0.0 when ``n == 0`` to avoid division-by-zero. Raises ``ValueError``
    if ``wins < 0``, ``n < 0``, or ``wins > n`` (clipping would silently hide
    upstream bugs).
    """
    if n < 0 or wins < 0:
        raise ValueError(f"wins and n must be non-negative (got wins={wins}, n={n})")
    if wins > n:
        raise ValueError(f"wins ({wins}) cannot exceed n ({n})")
    if n == 0:
        return 0.0
    phat = wins / n
    denom = 1.0 + (z * z) / n
    centre = phat + (z * z) / (2.0 * n)
    margin = z * sqrt((phat * (1.0 - phat) + (z * z) / (4.0 * n)) / n)
    return (centre - margin) / denom


def _z_for_two_sided_confidence(confidence: float) -> float:
    """Return z-score for a two-sided confidence level (e.g. 0.95 -> 1.96)."""
    if not 0.0 < confidence < 1.0:
        raise ValueError(f"confidence must be in (0, 1), got {confidence}")
    # two-sided: alpha/2 in each tail
    return NormalDist().inv_cdf(1.0 - (1.0 - confidence) / 2.0)


def should_activate_guide_band(
    wins: int,
    n: int,
    currently_active: bool,
    min_n: int = 50,
    activate_at: float = 0.52,
    deactivate_below: float = 0.45,
    alpha: float = 0.05,
    k: int = 1,
) -> bool:
    """Decide whether the Guide band should render as active.

    * ``n < min_n`` always returns False regardless of state (statistical floor).
    * When ``k > 1`` (Bonferroni family), the Wilson LB is recomputed at the
      corrected confidence ``1 - alpha/k``. Because higher confidence uses a
      larger z, the resulting LB is tighter — so the bar to activate is
      effectively higher as k grows. ``deactivate_below`` is left on the
      default-confidence scale so hysteresis behaviour is preserved.
    * Hysteresis: if ``currently_active``, the band stays active while the
      Wilson LB ``>= deactivate_below``; otherwise it flips on only when the
      Wilson LB ``>= activate_at``.
    """
    if k < 1:
        raise ValueError(f"k must be >= 1, got {k}")
    if n < min_n:
        return False

    # Default 95 percent LB drives hysteresis and deactivation.
    lb_default = wilson_lower_bound(wins, n)

    if k > 1:
        z_corrected = _z_for_two_sided_confidence(1.0 - alpha / k)
        lb_activate = wilson_lower_bound(wins, n, z=z_corrected)
    else:
        lb_activate = lb_default

    if currently_active:
        return lb_default >= deactivate_below
    return lb_activate >= activate_at
