#!/usr/bin/env python3
"""Tests for tools/r4b_power.py — arithmetic only, no network, no rule run."""
from __future__ import annotations

import importlib.util
import math
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("r4b_power", ROOT / "tools" / "r4b_power.py")
power = importlib.util.module_from_spec(_spec)
sys.modules["r4b_power"] = power
_spec.loader.exec_module(power)


def test_book_sigma_bounds():
    sig = 0.045
    assert power.book_sigma(sig, 1.0, k=5) == pytest.approx(sig)
    assert power.book_sigma(sig, 0.0, k=5) == pytest.approx(sig / math.sqrt(5))


def test_book_sigma_is_monotone_in_rho():
    vals = [power.book_sigma(0.045, r, k=5) for r in (0.0, 0.3, 0.5, 0.7, 1.0)]
    assert vals == sorted(vals)


def test_mde_scales_as_inverse_sqrt_n():
    sb = 0.035
    # more observations => smaller detectable effect; quadrupling n halves the MDE
    assert power.mde(sb, 4) == pytest.approx(power.mde(sb, 1) / 2)


def test_months_needed_round_trips_to_the_edge():
    sb, edge = 0.035, 0.010
    n = power.months_needed(sb, edge)
    assert power.mde(sb, max(1, round(n))) == pytest.approx(edge, rel=0.02)


def test_confirm_threshold_is_exactly_hurdle_plus_1_645_se():
    sb, n = 0.035, 60
    # clock.HURDLE is ANNUAL; the threshold is MONTHLY. Mixing them inflates it 12x.
    assert power.confirm_threshold(sb, n) == pytest.approx(
        power.clock.HURDLE / 12 + 1.645 * power.standard_error(sb, n), rel=1e-4)


def test_units_are_monthly_not_annual():
    sb = 0.035
    assert power.monthly_hurdle() == pytest.approx(power.clock.HURDLE / 12)
    assert power.confirm_threshold(sb, 60) < power.clock.HURDLE  # 0.0110 < 0.0432, not 0.0506


def test_thresholds_tighten_as_records_accumulate():
    sb = 0.035
    c = [power.confirm_threshold(sb, n) for n in (12, 36, 60, 120)]
    r = [power.refute_threshold(sb, n) for n in (12, 36, 60, 120)]
    assert c == sorted(c, reverse=True)
    assert r == sorted(r)


def test_power_is_one_half_at_the_threshold():
    sb = 0.035
    thr = power.confirm_threshold(sb, 60)
    assert power.power_confirm(sb, 60, thr) == pytest.approx(0.5, abs=1e-6)
    rthr = power.refute_threshold(sb, 60)
    assert power.power_refute(sb, 60, rthr) == pytest.approx(0.5, abs=1e-6)


def test_power_increases_with_the_effect():
    sb = 0.035
    ps = [power.power_confirm(sb, 60, mu) for mu in (0.0036, 0.005, 0.010, 0.015)]
    assert ps == sorted(ps)
    assert ps[-1] > 0.75


def test_analyse_reports_the_frozen_universe_only():
    d = power.analyse()
    assert d["universe"] == 20
    assert d["top_k"] == power.clock.TOP_K
    # a 20-ETF book cannot plausibly have monthly sigma outside this band
    assert 0.015 < d["sigma_book_monthly"] < 0.08
    assert d["monthly_obs_per_series"] >= 36
    # the central finding must be reproduced by the tool, not just by the report
    assert d["confirm_threshold_monthly"] > 4 * d["hurdle_monthly"]
    assert d["power_confirm_n60"]["36"] < 0.20
