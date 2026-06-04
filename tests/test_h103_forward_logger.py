"""H-103 forward-paper logger — offline tests (idempotency + record shape)."""
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "verified_strategies", "paper_pilot"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "verified_strategies"))
import h103_forward_logger as fl  # noqa: E402
from etf_dual_momentum_backtest import monthly_closes  # noqa: E402


def _ramp(start, drift, n=500, seed=0):
    rng = np.random.RandomState(seed)
    idx = pd.date_range("2024-01-01", periods=n, freq="D")
    return pd.DataFrame({"close": start * np.cumprod(1 + drift + rng.normal(0, 0.002, n))}, index=idx)


def _closes():
    return {
        "SPY": monthly_closes(_ramp(100, 0.0010, seed=1)),
        "QQQ": monthly_closes(_ramp(100, 0.0008, seed=2)),
        "EFA": monthly_closes(_ramp(100, 0.0003, seed=3)),
        "AGG": monthly_closes(_ramp(100, 0.0001, seed=4)),
        "GLD": monthly_closes(_ramp(100, 0.0004, seed=5)),
        "BIL": monthly_closes(_ramp(100, 0.00004, seed=6)),
    }


def test_record_shape_and_pick():
    closes = _closes()
    asof = sorted(closes["SPY"].index)[-1]
    rec = fl.build_record(closes, asof, asof.isoformat())
    assert rec["hypothesis_id"] == "H-103"
    assert isinstance(rec["pick"], list) and len(rec["pick"]) >= 1
    assert rec["month"] == asof.isoformat()[:7]


def test_idempotent_per_month(tmp_path):
    closes = _closes()
    asof = sorted(closes["SPY"].index)[-1]
    log = str(tmp_path / "h103.jsonl")
    r1 = fl.log_current(closes, asof, asof.isoformat(), log_path=log)
    r2 = fl.log_current(closes, asof, asof.isoformat(), log_path=log)   # same month
    assert r1 is not None and r2 is None
    assert len(open(log).read().strip().splitlines()) == 1
