"""ENHANCEMENT #111 — return-attribution gate (alpha vs beta/style) tests."""
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "verified_strategies"))
import return_attribution as ra  # noqa: E402


def test_pure_beta_sleeve_has_no_alpha():
    # sleeve is EXACTLY 1.5 * market, zero intercept -> no stock-selection alpha
    # -> gate FAIL (deterministic; no RNG Type-I fluke).
    rng = random.Random(1)
    market = [rng.gauss(0, 1) for _ in range(120)]
    sleeve = [1.5 * m for m in market]
    g = ra.attribution_gate(sleeve, market)
    assert g["ok"] is False
    assert abs(g["market_beta"] - 1.5) < 1e-6


def test_real_alpha_sleeve_passes():
    # sleeve = 0.5*market + 0.20 constant alpha each period -> positive sig alpha
    rng = random.Random(2)
    market = [rng.gauss(0, 1) for _ in range(120)]
    sleeve = [0.20 + 0.5 * m + rng.gauss(0, 0.1) for m in market]
    g = ra.attribution_gate(sleeve, market)
    assert g["ok"] is True
    assert g["alpha"] > 0
    assert g["alpha_t"] >= ra.ALPHA_T_MIN
    assert g["alpha_ir"] >= ra.ALPHA_IR_MIN


def test_negative_alpha_fails():
    rng = random.Random(3)
    market = [rng.gauss(0, 1) for _ in range(120)]
    sleeve = [-0.15 + 1.0 * m + rng.gauss(0, 0.05) for m in market]
    g = ra.attribution_gate(sleeve, market)
    assert g["ok"] is False
    assert g["alpha"] < 0


def test_insufficient_data_fail_open():
    g = ra.attribution_gate([0.1] * 5, [0.1] * 5)
    assert g["ok"] is None


def test_style_factor_included():
    rng = random.Random(4)
    market = [rng.gauss(0, 1) for _ in range(150)]
    style = [rng.gauss(0, 1) for _ in range(150)]
    sleeve = [0.10 + 0.4 * market[i] + 0.3 * style[i] + rng.gauss(0, 0.05)
              for i in range(150)]
    a = ra.attribute_returns(sleeve, market, style)
    assert a["style_beta"] is not None
    assert abs(a["style_beta"] - 0.3) < 0.1
