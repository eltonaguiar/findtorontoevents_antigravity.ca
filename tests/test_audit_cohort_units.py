"""AUD-01 -- return-unit contract for the at_pick_outcomes adapter.

`at_pick_outcomes.pnl_pct` is stored in PERCENT. Traced evidence (2026-10-19):

  * CADJPY=X WON row = 427.9526, matching the documented "+428%" price-feed
    artifact (a fraction 427.95 would be +42,795% -- impossible).
  * CRYPTO floor is exactly -100.0 (a long position cannot lose more than
    -100%; a fraction -100 would be -10,000%).
  * The SQL sanity cap in `_load_outcomes_rows` is commented "Caps in PERCENT".

The OLD loader used magnitude inference::

    r["pnl_pct"] = pnl_f / 100.0 if abs(pnl_f) > 1.0 else pnl_f

That mixes units inside one cohort: a 2.0 percent value is scaled to 0.02 but a
0.5 percent value is left at 0.5 (read downstream as a 50% fraction, 100x too
big). Downstream (`SPOT_FLICKER_THRESHOLD=0.0002`, `DOLLAR_SCALE=1.0`,
`_net_pnl` fraction-unit slippage, `_rolling_mdd` compounding `1.0 + r`) all
expect fractions, so every percent value <= 1 silently inflates PF/WR.

These tests are pure/offline: no DB, no generator, no network.
"""

import pytest

from tools.build_pf_registry import _pnl_percent_to_fraction


def test_plan_fixture_percent_to_fraction():
    """AUD-01 acceptance: percent 0.25 / 1.0 / 2.0 -> 0.0025 / 0.01 / 0.02."""
    assert _pnl_percent_to_fraction(0.25) == pytest.approx(0.0025)
    assert _pnl_percent_to_fraction(1.0) == pytest.approx(0.01)
    assert _pnl_percent_to_fraction(2.0) == pytest.approx(0.02)


def test_negative_and_artifact_values():
    assert _pnl_percent_to_fraction(-0.5) == pytest.approx(-0.005)
    assert _pnl_percent_to_fraction(-1.0) == pytest.approx(-0.01)
    assert _pnl_percent_to_fraction(-100.0) == pytest.approx(-1.0)
    # the traced +428% CADJPY artifact -> 4.2795 fraction (>1.0 so the
    # dollar-scale filter still drops it after conversion)
    assert _pnl_percent_to_fraction(427.9526) == pytest.approx(4.279526)


def test_no_magnitude_inference():
    """The regression: values <= 1 must ALSO be scaled by 1/100.

    The old `abs(v) > 1` heuristic left these untouched. The scale factor must
    be identical for every magnitude.
    """
    for pct in (0.05, 0.25, 0.5, 1.0, 1.5, 2.0, 7.5, 99.67):
        got = _pnl_percent_to_fraction(pct)
        assert got == pytest.approx(pct / 100.0), f"{pct} not scaled to fraction"
        # uniform scale factor == 0.01 regardless of magnitude
        assert got / pct == pytest.approx(0.01)


def test_identity_not_applied_to_already_scaled():
    """Guard: this adapter is percent->fraction ONLY. It must never return the
    input unchanged (that was the old bug for |v| <= 1)."""
    for pct in (0.1, 0.9, 1.0):
        assert _pnl_percent_to_fraction(pct) != pct


def test_float_and_int_inputs():
    assert _pnl_percent_to_fraction(1) == pytest.approx(0.01)
    assert _pnl_percent_to_fraction(0) == 0.0
