"""Tier-2 forward gate tests (audit_trail/promotion_gate.py)."""
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from audit_trail.promotion_gate import evaluate_forward_tier2, TIER2_MIN_N


def _pnls(n: int, win_rate: float, win_pnl: float = 2.0, loss_pnl: float = -1.0) -> list[float]:
    wins = int(round(n * win_rate))
    return [win_pnl] * wins + [loss_pnl] * (n - wins)


def test_tier2_passes_strong_window():
    pnls = _pnls(TIER2_MIN_N, 0.60, win_pnl=3.0, loss_pnl=-1.0)
    r = evaluate_forward_tier2(pnls, oos_pf=1.5, is_pf=1.6, dsr=0.9)
    assert r["passed"], r


def test_tier2_fails_low_n():
    r = evaluate_forward_tier2(_pnls(30, 0.70))
    assert not r["passed"]
    assert any("n<" in b for b in r["blockers"])