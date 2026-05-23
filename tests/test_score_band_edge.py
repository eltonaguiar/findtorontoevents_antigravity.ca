"""Unit tests for tools/calibration/score_band_edge.py.

Covers: Wilson math, bucket assignment, direction + asset filtering,
score-field auto-selection, ghost filtering, and the edge-verification
exit-code contract on both healthy and unhealthy synthetic ledgers.
"""
from __future__ import annotations

import json
import math
import os
import sys

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, REPO_ROOT)

from tools.calibration import score_band_edge as sbe  # noqa: E402


def test_wilson_ci_known_values():
    wr, lo, hi = sbe.wilson_ci(50, 100)
    assert abs(wr - 0.5) < 1e-9
    assert 0.39 < lo < 0.41
    assert 0.59 < hi < 0.61


def test_bucket_for_score_boundaries():
    assert sbe.bucket_for_score(0) == "<50"
    assert sbe.bucket_for_score(49.99) == "<50"
    assert sbe.bucket_for_score(50) == "[50,65)"
    assert sbe.bucket_for_score(64.99) == "[50,65)"
    assert sbe.bucket_for_score(65) == "[65,80)"
    assert sbe.bucket_for_score(79.99) == "[65,80)"
    assert sbe.bucket_for_score(80) == "[80,100]"
    assert sbe.bucket_for_score(100) == "[80,100]"


def test_best_score_field_picks_most_populated():
    rows = [
        {"elite_score": 70},
        {"elite_score": 40},
        {"score": 55},
    ]
    assert sbe.best_score_field(rows) == "elite_score"


def test_filters_noncrypto_and_shorts():
    rows = [
        # crypto LONG, score 70, win (should count in [65,80))
        {"symbol": "BTCUSDT", "direction": "LONG", "elite_score": 70, "pnl_pct": 2.0},
        # crypto SHORT, should be skipped
        {"symbol": "BTCUSDT", "direction": "SHORT", "elite_score": 70, "pnl_pct": 5.0},
        # equity LONG, should be skipped (symbol not crypto)
        {"symbol": "AAPL", "direction": "LONG", "elite_score": 70, "pnl_pct": 5.0,
         "asset_class": "EQUITY"},
        # ghost row, skipped
        {"symbol": "MATICUSDT", "direction": "BUY", "elite_score": 70, "pnl_pct": -0.15},
    ]
    res = sbe.build_bands(rows, "elite_score")
    assert res["[65,80)"]["n"] == 1
    assert res["[65,80)"]["wins"] == 1
    assert res["<50"]["n"] == 0


def test_build_bands_pf_and_expectancy():
    rows = []
    # 6 wins of +2% and 4 losses of -1% at score 70 → PF = 12/4 = 3.0, WR 60%
    for _ in range(6):
        rows.append({"symbol": "ETHUSDT", "direction": "LONG",
                     "elite_score": 70, "pnl_pct": 2.0})
    for _ in range(4):
        rows.append({"symbol": "ETHUSDT", "direction": "LONG",
                     "elite_score": 70, "pnl_pct": -1.0})
    res = sbe.build_bands(rows, "elite_score")
    b = res["[65,80)"]
    assert b["n"] == 10
    assert b["wins"] == 6
    assert abs(b["wr"] - 0.6) < 1e-9
    assert abs(b["pf"] - 3.0) < 1e-9
    assert abs(b["expectancy_pct"] - ((6 * 2 + 4 * -1) / 10)) < 1e-9


def test_edge_verified_false_on_low_wr(tmp_path):
    # 40 crypto LONG at score 70 with 10% WR → Wilson CI lower bound ~ 3%
    rows = []
    for _ in range(4):
        rows.append({"symbol": "BTCUSDT", "direction": "LONG",
                     "elite_score": 70, "pnl_pct": 1.0})
    for _ in range(36):
        rows.append({"symbol": "BTCUSDT", "direction": "LONG",
                     "elite_score": 70, "pnl_pct": -1.0})
    p = tmp_path / "closed.json"
    p.write_text(json.dumps(rows))
    rc = sbe.main(["--closed", str(p)])
    assert rc == 2


def test_edge_verified_true_on_strong_wr(tmp_path):
    # 80 crypto LONG at score 70 with 72.5% WR → Wilson CI lo > 50%
    rows = []
    for _ in range(58):
        rows.append({"symbol": "BTCUSDT", "direction": "BUY",
                     "elite_score": 75, "pnl_pct": 2.0})
    for _ in range(22):
        rows.append({"symbol": "BTCUSDT", "direction": "BUY",
                     "elite_score": 75, "pnl_pct": -1.0})
    p = tmp_path / "closed.json"
    p.write_text(json.dumps(rows))
    rc = sbe.main(["--closed", str(p)])
    assert rc == 0


def test_edge_not_verified_when_n_below_30(tmp_path):
    # Only 20 crypto LONG trades in [65+], even if 100% WR — too small
    rows = [{"symbol": "BTCUSDT", "direction": "LONG",
             "elite_score": 70, "pnl_pct": 1.0} for _ in range(20)]
    p = tmp_path / "closed.json"
    p.write_text(json.dumps(rows))
    rc = sbe.main(["--closed", str(p)])
    assert rc == 2


def test_json_output_written(tmp_path, monkeypatch):
    rows = [{"symbol": "BTCUSDT", "direction": "LONG",
             "elite_score": 55, "pnl_pct": 1.0}]
    p = tmp_path / "closed.json"
    p.write_text(json.dumps(rows))
    out_dir = tmp_path / "out"
    monkeypatch.setattr(sbe, "CALIBRATION_OUT_DIR", str(out_dir))
    sbe.run(str(p))
    assert (out_dir / "score_band_edge.json").exists()
    data = json.loads((out_dir / "score_band_edge.json").read_text())
    assert data["[50,65)"]["n"] == 1
    assert data["_meta"]["score_field"] == "elite_score"
