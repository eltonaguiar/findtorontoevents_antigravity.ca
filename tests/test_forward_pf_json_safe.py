"""A pod with no losing trades must not take the ledger down.

2026-11-20: the first forward rows for POD-FABER-TAA were all winners, so the
profit factor was ``inf``. The ledger build serialises with
``json.dumps(..., allow_nan=False)`` and failed with
"Out of range float values are not JSON compliant: inf" — meaning a *good* record
broke publishing. A perfect PF is capped at a finite ceiling instead.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from alpha_engine.forward_observations import _finite_pf, promotion  # noqa: E402


def _win(i):
    return {"hypothesis_id": "H-X", "symbol": "SYM", "asset_class": "ETF",
            "side": "LONG", "entry_px": 100.0, "exit_px": 101.0, "qty": 1.0,
            "closed_at": f"2026-11-20T0{i}:00:00Z", "intrabar_first_touch": True,
            "benchmark_leg_ret": 0.5, "pod": "POD-A"}


def test_all_winner_pod_serialises_with_a_capped_pf():
    rows = [_win(i) for i in range(3)]
    p = promotion(rows, min_n=1)
    assert p["n_forward"] == 3
    assert p["net_pf"] == 99.0          # infinite PF, capped
    # The whole point: the ledger must still serialise.
    json.dumps(p, allow_nan=False)


def test_finite_pf_helper_edges():
    assert _finite_pf(float("inf")) == 99.0
    assert _finite_pf(float("-inf")) == 0.0
    assert _finite_pf(float("nan")) is None
    assert _finite_pf(None) is None
    assert _finite_pf("nope") is None
    assert _finite_pf(1.5) == 1.5
    assert _finite_pf(float("inf"), ceiling=10.0) == 10.0
