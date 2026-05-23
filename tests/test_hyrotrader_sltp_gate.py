"""Tests for the SL/TP population gate in tools.hyrotrader_log_trade._sync_pick_open.

PR #5 of 6 from the 2026-05-05 quant-performance-auditor agent run on
/audit/hyrotrader. Pins behaviour:

- A trade with entry/SL/TP all populated → pick transitions to status='open'.
- A trade with any of entry/SL/TP set to None → write is REFUSED, pick keeps
  its existing status, function returns False.
- Legit zero-valued SL (market-making) still passes — gate uses `is None`,
  not `> 0`.
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))


def _import():
    from tools.hyrotrader_log_trade import _sync_pick_open
    return _sync_pick_open


def _fresh_picks_doc(initial_status: str = "pending_entry") -> dict:
    return {
        "picks": [
            {"id": "hyro-test-1", "status": initial_status,
             "entry_price": None, "stop_loss": None, "take_profit": None,
             "sl_confirmed": False},
        ]
    }


def _full_trade(**overrides) -> dict:
    base = {
        "pick_id": "hyro-test-1",
        "symbol": "BTCUSDT",
        "entry_price": 100000.0,
        "stop_loss": 98000.0,
        "take_profit": 105000.0,
        "entry_time": "2026-05-05T17:00:00Z",
    }
    base.update(overrides)
    return base


def test_full_fields_writes_open():
    fn = _import()
    doc = _fresh_picks_doc()
    changed = fn(doc, _full_trade())
    assert changed is True
    p = doc["picks"][0]
    assert p["status"] == "open"
    assert p["entry_price"] == 100000.0
    assert p["stop_loss"] == 98000.0
    assert p["take_profit"] == 105000.0
    assert p["sl_confirmed"] is True


def test_missing_entry_refused(capsys):
    fn = _import()
    doc = _fresh_picks_doc(initial_status="pending_entry")
    changed = fn(doc, _full_trade(entry_price=None))
    assert changed is False
    assert doc["picks"][0]["status"] == "pending_entry"
    assert "refusing 'open' write" in capsys.readouterr().err


def test_missing_stop_loss_refused(capsys):
    fn = _import()
    doc = _fresh_picks_doc()
    changed = fn(doc, _full_trade(stop_loss=None))
    assert changed is False
    assert doc["picks"][0]["status"] == "pending_entry"
    assert "refusing 'open' write" in capsys.readouterr().err


def test_missing_take_profit_refused(capsys):
    fn = _import()
    doc = _fresh_picks_doc()
    changed = fn(doc, _full_trade(take_profit=None))
    assert changed is False
    assert doc["picks"][0]["status"] == "pending_entry"
    assert "refusing 'open' write" in capsys.readouterr().err


def test_zero_stop_loss_passes():
    """Cerebras swarm-review concern: legit zero stops (market-making) must NOT
    be blocked by the gate. The gate uses `is None`, not `> 0`."""
    fn = _import()
    doc = _fresh_picks_doc()
    changed = fn(doc, _full_trade(stop_loss=0.0))
    assert changed is True
    p = doc["picks"][0]
    assert p["status"] == "open"
    assert p["stop_loss"] == 0.0


def test_pick_id_mismatch_no_change():
    """Trade with a pick_id not present in the doc → no change, no error."""
    fn = _import()
    doc = _fresh_picks_doc()
    changed = fn(doc, _full_trade(pick_id="hyro-nonexistent"))
    assert changed is False
    assert doc["picks"][0]["status"] == "pending_entry"
