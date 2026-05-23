"""Unit tests for tools/data_integrity/win_rate_wilson_ci.py."""
from __future__ import annotations

import json
import os
import sys

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, REPO_ROOT)

from tools.data_integrity import win_rate_wilson_ci as wc  # noqa: E402


def test_wilson_ci_known_values():
    wr, lo, hi = wc.wilson_ci(50, 100)
    assert abs(wr - 0.5) < 1e-9
    # For 50/100 the 95% Wilson CI is roughly (0.402, 0.598).
    assert 0.39 < lo < 0.41
    assert 0.59 < hi < 0.61


def test_wilson_ci_all_wins():
    wr, lo, hi = wc.wilson_ci(10, 10)
    assert wr == 1.0
    assert hi <= 1.0
    assert lo < 1.0


def test_ghost_row_filtered():
    rows = [
        {"symbol": "MATICUSDT", "pnl_pct": -0.15, "strategy": "ghost"},
    ] * 5
    rows += [
        {"symbol": "BTCUSDT", "pnl_pct": 1.0, "strategy": "s1", "asset_class": "CRYPTO"},
        {"symbol": "BTCUSDT", "pnl_pct": -1.0, "strategy": "s1", "asset_class": "CRYPTO"},
    ]
    stats = wc.build_stats(rows)
    # Ghosts must be dropped; only CRYPTO group with n=2 present.
    assert any(s["group"] == "asset:CRYPTO" and s["n"] == 2 for s in stats)
    assert not any("ghost" in s["group"] for s in stats)


def test_main_flags_kill_candidates(tmp_path):
    rows = [{"symbol": "ETHUSDT", "pnl_pct": -1.0, "strategy": "losing",
             "asset_class": "CRYPTO"} for _ in range(30)]
    rows += [{"symbol": "ETHUSDT", "pnl_pct": 1.0, "strategy": "losing",
              "asset_class": "CRYPTO"} for _ in range(2)]
    p = tmp_path / "closed.json"
    p.write_text(json.dumps(rows))
    rc = wc.main(["--closed", str(p), "--min-n", "10", "--kill-threshold", "0.5"])
    assert rc == 2  # CRYPTO has 2/32 WR, CI_hi ~22%, below 50%


def test_main_passes_when_healthy(tmp_path):
    rows = []
    for _ in range(20):
        rows.append({"symbol": "BTCUSDT", "pnl_pct": 1.0,
                     "strategy": "winning", "asset_class": "CRYPTO"})
    for _ in range(2):
        rows.append({"symbol": "BTCUSDT", "pnl_pct": -1.0,
                     "strategy": "winning", "asset_class": "CRYPTO"})
    p = tmp_path / "closed.json"
    p.write_text(json.dumps(rows))
    rc = wc.main(["--closed", str(p), "--min-n", "10", "--kill-threshold", "0.5"])
    assert rc == 0
