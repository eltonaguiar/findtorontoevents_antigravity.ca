from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tools.backfill_resolved_pnl import _recompute, _direction_norm


def test_direction_norm():
    assert _direction_norm("SELL") == "SHORT"


def test_recompute_long():
    pnl = _recompute({"entry_price": 100.0, "exit_price": 102.0, "direction": "LONG"})
    assert pnl is not None and abs(pnl - 2.0) < 0.02