"""Smoke tests for alpha_engine.hrp_allocator."""
from __future__ import annotations

import math
import random

import pytest

from alpha_engine.hrp_allocator import hrp_allocate


def _series(seed: int, n: int = 60, mean: float = 0.0, sd: float = 0.01):
    rng = random.Random(seed)
    return [rng.gauss(mean, sd) for _ in range(n)]


def test_hrp_thin_sources_excluded():
    out = hrp_allocate(
        {
            "thin": [0.01, -0.005, 0.02],  # below default min_observations=20
            "fat_a": _series(1, n=40),
            "fat_b": _series(2, n=40),
        }
    )
    assert out["thin"] == 0.0
    assert math.isclose(out["fat_a"] + out["fat_b"], 1.0, abs_tol=1e-9)


def test_hrp_single_source_gets_full_weight():
    out = hrp_allocate({"only": _series(3, n=40), "thin": [0.01]})
    assert out["only"] == 1.0
    assert out["thin"] == 0.0


def test_hrp_no_qualifying_sources_returns_zeros():
    out = hrp_allocate({"a": [0.01, 0.02], "b": [0.0, 0.01, -0.01]})
    assert out == {"a": 0.0, "b": 0.0}


def test_hrp_weights_sum_to_one_multi_source():
    src = {f"s{i}": _series(i + 10, n=50) for i in range(5)}
    out = hrp_allocate(src)
    total = sum(out.values())
    assert math.isclose(total, 1.0, abs_tol=1e-9)
    for w in out.values():
        assert 0.0 <= w <= 1.0


def test_hrp_lower_vol_gets_higher_weight():
    # Two sources, otherwise identical, but s_low has 1/4 the variance.
    # HRP (inverse-variance bisection) should weight s_low ~4x higher.
    src = {
        "s_low": _series(7, n=80, sd=0.005),
        "s_high": _series(8, n=80, sd=0.020),
    }
    out = hrp_allocate(src)
    assert out["s_low"] > out["s_high"]
