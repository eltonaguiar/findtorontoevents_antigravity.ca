"""audit3 must price execution the way the dashboard measured it.

The review's §1.5 point: audit3's flat constants sat ABOVE measured cost for
CRYPTO/EQUITY/ETF/FOREX (conservative) and BELOW it for FUTURES/COMMODITY
(optimistic) — so a commodities cell could clear a gate at a cost it never paid.
audit3 now adopts `slippage_validation` from the payload it is already reading.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from alpha_engine import audit3_tribunal as t  # noqa: E402


def _payload(tmp_path, slippage):
    rows = [{
        "id": f"p{i}", "symbol": "BTCUSDT", "asset_class": "CRYPTO",
        "strategy": "luxalgo_confluence", "direction": "SHORT",
        "pnl_pct": 1.0, "status": "WON", "closed_at": "2026-11-01T00:00:00Z",
    } for i in range(120)]
    p = tmp_path / "dashboard_data.json"
    p.write_text(json.dumps({
        "generated_at": "2026-11-19T00:00:00Z",
        "slippage_validation": slippage,
        "picks": {"recent_closed": rows},
    }), encoding="utf-8")
    return p


def _slippage():
    return {
        "asset_class_stats": {
            "CRYPTO": {"n": 11341, "avg_slippage_pct": 0.0997},
            "FUTURES": {"n": 19, "avg_slippage_pct": 0.15},
            "BOND": {"n": 5, "avg_slippage_pct": 0.05},   # thin -> must be ignored
        },
        "flagged_strategies": {
            "luxalgo_confluence": {"n": 476, "avg_slippage_pct": 0.10},
        },
    }


def test_measured_class_cost_replaces_the_flat_constant(tmp_path):
    t.load_rows(str(_payload(tmp_path, _slippage())))
    assert t.SLIPPAGE_PCT["CRYPTO"] == 0.0997
    assert t.COST_BASIS["model"] == "measured"


def test_thin_class_sample_keeps_the_flat_fallback(tmp_path):
    t.load_rows(str(_payload(tmp_path, _slippage())))
    # BOND had only 5 measured closes in the fixture; the flat 0.08 stands.
    assert t.SLIPPAGE_PCT["BOND"] == 0.08


def test_measured_strategy_cost_wins_over_the_class(tmp_path):
    t.load_rows(str(_payload(tmp_path, _slippage())))
    row = {"asset_class": "CRYPTO", "strategy": "luxalgo_confluence", "pnl_pct": 1.0}
    assert t._cost_pct(row) == 0.10
    other = {"asset_class": "CRYPTO", "strategy": "something_else", "pnl_pct": 1.0}
    assert t._cost_pct(other) == 0.0997
    assert t._net(row) == 0.9


def test_missing_slippage_block_falls_back_and_says_so(tmp_path):
    t.load_rows(str(_payload(tmp_path, {})))
    assert t.COST_BASIS["model"] == "flat_fallback"
    assert "no measured slippage" in t.COST_BASIS["note"]
