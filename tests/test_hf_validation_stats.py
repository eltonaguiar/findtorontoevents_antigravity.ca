"""Tests for tools/hf_validation_stats.py (stdlib statistics helpers)."""

import math
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_TOOLS = _ROOT / "tools"
if str(_TOOLS) not in sys.path:
    sys.path.insert(0, str(_TOOLS))

from hf_validation_stats import (
    bootstrap_wr_ci,
    profit_factor,
    sortino_like,
    two_proportion_z_score,
    two_sided_normal_pvalue,
)


def test_two_proportion_symmetric():
    z = two_proportion_z_score(30, 100, 30, 100)
    assert z is not None
    assert abs(z) < 1e-6


def test_two_proportion_different():
    z = two_proportion_z_score(60, 100, 30, 100)
    assert z is not None and z > 0
    p = two_sided_normal_pvalue(z)
    assert p < 0.05


def test_pvalue_extreme():
    p = two_sided_normal_pvalue(6.0)
    assert p < 1e-8


def test_bootstrap_ci_full_wins():
    wins = [True] * 50
    lo, hi = bootstrap_wr_ci(wins, n_bootstrap=500, seed=1)
    assert lo is not None and hi is not None
    assert lo >= 0.99 and hi <= 1.0


def test_profit_factor():
    pf = profit_factor([2.0, -1.0, 3.0, -2.0])
    assert pf is not None
    assert math.isclose(pf, 5.0 / 3.0)


def test_sortino_requires_downside():
    assert sortino_like([1.0, 2.0, 3.0]) is None
    s = sortino_like([1.0, -2.0, 3.0, -1.0])
    assert s is not None
