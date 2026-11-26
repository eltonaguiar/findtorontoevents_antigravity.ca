"""Tests locking the PBO contract and the fail-closed north-star gate.

Two defects are locked here (both found 2026-11-20):

1. ``tools.pbo.probability_of_backtest_overfitting`` used to fabricate PBO
   from a single return series by pairing it with 1e-6-scale noise. A single
   series cannot yield PBO, and the fabricated number flowed into a kill
   switch. It now returns nan unless a real ``peer_matrix`` is supplied.

2. ``tools.h037_forward_verification`` gates were written as
   ``if v is not None and v < threshold``. ``nan < threshold`` is False, so an
   unmeasurable statistic silently PASSED. They now fail closed.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.pbo import probability_of_backtest_overfitting as pbo_single  # noqa: E402


# --------------------------------------------------------------------------
# PBO contract
# --------------------------------------------------------------------------

def test_pbo_returns_nan_for_single_series():
    """A single return series cannot produce PBO -> nan, never a fake number."""
    r = np.random.default_rng(0).normal(0.0, 0.01, 200)
    with pytest.warns(DeprecationWarning):
        val = pbo_single(r)
    assert isinstance(val, float)
    assert math.isnan(val), f"expected nan, got {val}"


def test_pbo_rejects_single_column_peer_matrix():
    """A 1-column 'peer matrix' is not a candidate set."""
    with pytest.raises(ValueError, match="N >= 2"):
        pbo_single(peer_matrix=np.zeros((50, 1)))


def test_pbo_rejects_1d_peer_matrix():
    with pytest.raises(ValueError, match=r"\(T, N\)"):
        pbo_single(peer_matrix=np.zeros(50))


def test_pbo_computes_with_real_peer_matrix():
    """With genuine competing candidates the result is a real probability."""
    m = np.random.default_rng(1).normal(0.0, 0.01, (200, 5))
    val = pbo_single(peer_matrix=m, n_splits=4)
    assert 0.0 <= val <= 1.0, f"PBO out of range: {val}"


def test_pbo_insufficient_data_assumes_overfit():
    """Too few rows -> 1.0 (assume overfit), which is the safe direction."""
    m = np.random.default_rng(2).normal(0.0, 0.01, (3, 4))
    assert pbo_single(peer_matrix=m, n_splits=4) == 1.0


# --------------------------------------------------------------------------
# Fail-closed gate
# --------------------------------------------------------------------------

def _gate_verdict(metrics: dict) -> tuple[bool, list[str]]:
    """Replicate the north-star gate loop from h037_forward_verification."""
    ns_pass = True
    ns_reasons: list[str] = []

    def _unmeasurable(value) -> bool:
        return value is None or (isinstance(value, float) and value != value)

    for name, thr, cmp_ in (("DSR", 0.95, "lt"), ("PBO", 0.05, "ge"),
                            ("WFE", 0.60, "lt"), ("FDR q", 0.10, "gt")):
        key = {"DSR": "dsr", "PBO": "pbo", "WFE": "wfe",
               "FDR q": "fdr_q"}[name]
        val = metrics.get(key)
        if _unmeasurable(val):
            ns_pass = False
            ns_reasons.append(f"{name} NOT EVALUABLE (nan/None)")
            continue
        fails = (val < thr if cmp_ == "lt"
                 else val >= thr if cmp_ == "ge" else val > thr)
        if fails:
            ns_pass = False
            ns_reasons.append(f"{name} fails gate")
    return ns_pass, ns_reasons


GOOD = {"dsr": 0.97, "pbo": 0.01, "wfe": 0.75, "fdr_q": 0.02}


def test_gate_passes_on_clean_metrics():
    ok, reasons = _gate_verdict(GOOD)
    assert ok, reasons


def test_gate_fails_closed_on_nan_pbo():
    """The regression: nan PBO must BLOCK, not silently pass.

    Under the old `if v is not None and v >= 0.05` form, nan >= 0.05 is False,
    so a PBO that could not be computed passed the gate.
    """
    ok, reasons = _gate_verdict({**GOOD, "pbo": float("nan")})
    assert not ok, "nan PBO must fail the gate, not pass it"
    assert any("NOT EVALUABLE" in r for r in reasons), reasons


def test_gate_fails_closed_on_none_metrics():
    for key in ("dsr", "pbo", "wfe", "fdr_q"):
        ok, reasons = _gate_verdict({**GOOD, key: None})
        assert not ok, f"{key}=None must fail the gate"
        assert any("NOT EVALUABLE" in r for r in reasons), reasons


def test_gate_fails_on_breach():
    for key, bad in (("dsr", 0.50), ("pbo", 0.40), ("wfe", 0.20),
                     ("fdr_q", 0.50)):
        ok, _ = _gate_verdict({**GOOD, key: bad})
        assert not ok, f"{key}={bad} must fail the gate"
