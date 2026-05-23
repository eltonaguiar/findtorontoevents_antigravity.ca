"""Unit tests for tools/data_integrity/ledger_reconciliation.py."""
from __future__ import annotations

import json
import os
import sys

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, REPO_ROOT)

from tools.data_integrity import ledger_reconciliation as lr  # noqa: E402


def _make_closed():
    return [
        {"symbol": "BTCUSDT", "direction": "LONG", "strategy": "s1",
         "created_at": "2026-03-01 10:00:00", "asset_class": None, "pnl_pct": 2.0},
        {"symbol": "ETHUSDT", "direction": "SHORT", "strategy": "s2",
         "created_at": "2026-03-02 11:00:00", "asset_class": "CRYPTO", "pnl_pct": -1.0},
        {"symbol": "AAPL", "direction": "LONG", "strategy": "s3",
         "created_at": "2026-03-03 12:00:00", "asset_class": None, "pnl_pct": 0.5},
    ]


def _make_universal():
    return [
        {"symbol": "BTCUSDT", "direction": "LONG", "strategy": "s1",
         "timestamp": "2026-03-01T10:00:00Z", "pnl_pct": 2.0},
        {"symbol": "SOLUSDT", "direction": "LONG", "strategy": "s9",
         "timestamp": "2026-03-04T09:00:00Z", "pnl_pct": 1.0},
    ]


def test_reconcile_overlap_counts():
    s = lr.reconcile(_make_closed(), _make_universal())
    assert s["closed_rows"] == 3
    assert s["universal_rows"] == 2
    # BTC row matches across ledgers.
    assert s["overlap_keys"] == 1
    assert s["only_in_closed"] == 2
    assert s["only_in_universal"] == 1


def test_main_writes_json(tmp_path):
    cp = tmp_path / "closed.json"
    up = tmp_path / "uni.json"
    out = tmp_path / "out.json"
    cp.write_text(json.dumps(_make_closed()))
    up.write_text(json.dumps(_make_universal()))
    # overlap_pct = 1/3 = 33.3% — pass with --min-overlap 10
    rc = lr.main([
        "--closed", str(cp), "--universal", str(up),
        "--out", str(out), "--min-overlap", "10",
    ])
    assert rc == 0
    data = json.loads(out.read_text())
    assert data["overlap_keys"] == 1


def test_main_fails_below_threshold(tmp_path):
    cp = tmp_path / "closed.json"
    up = tmp_path / "uni.json"
    out = tmp_path / "out.json"
    cp.write_text(json.dumps(_make_closed()))
    up.write_text(json.dumps(_make_universal()))
    rc = lr.main([
        "--closed", str(cp), "--universal", str(up),
        "--out", str(out), "--min-overlap", "95",
    ])
    assert rc == 2


def test_asset_breakdown_flags_missing():
    s = lr.reconcile(_make_closed(), _make_universal())
    # All closed asset_class raw values are None/CRYPTO, inferred always fills.
    inferred = s["closed_asset_breakdown"]["inferred"]
    assert inferred.get("CRYPTO", 0) >= 2
