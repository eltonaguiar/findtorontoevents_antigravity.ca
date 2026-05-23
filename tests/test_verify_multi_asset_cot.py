"""Tests for tools/verify_multi_asset_cot.py (forensic verifier)."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "tools" / "verify_multi_asset_cot.py"

_spec = importlib.util.spec_from_file_location("verify_multi_asset_cot", SCRIPT)
verify_mod = importlib.util.module_from_spec(_spec)
sys.modules["verify_multi_asset_cot"] = verify_mod
_spec.loader.exec_module(verify_mod)  # type: ignore


def test_runs_without_db(monkeypatch, tmp_path):
    """Script must complete + write report when DB is unavailable."""
    monkeypatch.setattr(verify_mod, "REPORTS_DIR", tmp_path / "reports")
    monkeypatch.setattr(verify_mod, "fetch_trades_db",
                        lambda: (None, "db disabled for test"))
    monkeypatch.setattr(verify_mod, "fetch_trades_json",
                        lambda p: ([], "no json"))
    rc = verify_mod.main([])
    assert rc == 0
    out_files = list((tmp_path / "reports").glob("multi_asset_cot_db_verify_*.md"))
    assert len(out_files) == 1
    txt = out_files[0].read_text(encoding="utf-8")
    assert "Verdict" in txt
    assert "DATA_GAP" in txt


def test_top_n_contribution_math():
    """One outlier of 100 with 3 trades of 1 → top1 = 100/103 ≈ 97%."""
    pnls = [100.0, 1.0, 1.0, 1.0]
    top = verify_mod.top_n_contribution(pnls, 5)
    assert len(top) == 4
    assert top[0][0] == 100.0
    assert abs(top[0][1] - (100.0 / 103.0)) < 1e-6
    # contributions sum to 1.0 when all trades requested
    assert abs(sum(frac for _, frac in top) - 1.0) < 1e-6


def test_bootstrap_pf_ci_plausible():
    """Bootstrap CI on a positive-skew sample should bracket the empirical PF."""
    # 8 wins of +1, 4 losses of -1 → PF = 8/4 = 2.0
    pnls = [1.0] * 8 + [-1.0] * 4
    lo, hi = verify_mod.bootstrap_pf_ci(pnls, n_iter=2000, seed=7)
    assert lo is not None and hi is not None
    assert lo > 0
    assert hi > lo
    # 2.0 should fall within (or very near) the 95% CI
    assert lo <= 2.0 <= hi * 1.5


def test_verdict_outlier_driven():
    """PF>15 with top-1 contribution > 50% → OUTLIER_DRIVEN."""
    # Construct top5 where top-1 = 60% of |abs total|
    top5 = [(100.0, 0.60), (10.0, 0.10), (5.0, 0.05), (2.0, 0.02), (1.0, 0.01)]
    v = verify_mod.decide_verdict(
        headline_pf=19.19, computed_pf=20.0, top_contribs=top5,
        n_trades=120, data_source="test",
    )
    assert v == "OUTLIER_DRIVEN"
    # Sanity: clean profile → REAL
    clean5 = [(1.0, 0.05), (0.9, 0.04), (0.8, 0.04), (0.7, 0.03), (0.6, 0.03)]
    v2 = verify_mod.decide_verdict(
        headline_pf=1.5, computed_pf=1.5, top_contribs=clean5,
        n_trades=120, data_source="test",
    )
    assert v2 == "REAL"
