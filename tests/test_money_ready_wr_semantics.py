"""`wr` must describe the rows in the same object as `n`.

The bug this pins (found 2026-11-19): `money_ready_verdict.json` published
COMMODITY `wr=0.4052` with `sizing_source="intrabar_truth"` — the field named `wr`
was actually the honest-intrabar overlay, computed over a different row set than
the `n` beside it. That is the same failure as the ETF 1.9%-vs-43.1% contradiction
on /audit: two numbers, different denominators, one label.
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from alpha_engine import money_ready_verdict as m  # noqa: E402


def test_wr_reports_the_class_rows_not_the_intrabar_overlay(monkeypatch):
    picks = (
        [{"strategy": "s", "asset_class": "COMMODITY", "status": "WON",
          "pnl_pct": 1.0, "symbol": "CT=F", "source_system": "a"} for _ in range(70)]
        + [{"strategy": "s", "asset_class": "COMMODITY", "status": "LOST",
            "pnl_pct": -1.0, "symbol": "CT=F", "source_system": "a"} for _ in range(30)]
    )
    monkeypatch.setattr(m, "_load_picks", lambda *a, **k: picks)
    monkeypatch.setattr(m, "_load_blocked", lambda *a, **k: set())
    monkeypatch.setattr(m, "_load_dashboard_health", lambda *a, **k: {})
    monkeypatch.setattr(m, "_intrabar_truth_map", lambda: {
        "COMMODITY": {"n": 500, "wr": 0.4052, "pf": 0.9,
                      "source": "at_signal_outcomes.intrabar_*"}})
    monkeypatch.setattr(m, "_INTRABAR_TRUTH_ENABLED", True)
    # ci_mode=True intentionally disables the overlay cache, so the overlay can only
    # be exercised on the production path. Keep that path offline: no DB sleeves.
    monkeypatch.setattr(m, "_top_sleeves_from_outcomes", lambda *a, **k: [])

    r = m.money_ready_verdict(ci_mode=False)["COMMODITY"]

    # 70 wins / 100 resolved rows, net of the COMMODITY round trip.
    assert r["wr"] == 0.7, r
    assert r["wr_pct"] == 70.0
    assert r["n"] == 100
    # The overlay is published, but never under the name `wr`.
    assert r["sizing_wr"] == 0.4052
    assert r["verdict_basis"] == "intrabar_truth"
    assert r["wr"] != r["sizing_wr"]


def test_overlay_can_be_disabled_for_policy_only_runs(monkeypatch):
    monkeypatch.setattr(m, "_INTRABAR_TRUTH_ENABLED", False)
    monkeypatch.setattr(m, "_intrabar_truth_map", lambda: (_ for _ in ()).throw(
        AssertionError("overlay must not be consulted when disabled")))
    assert m._INTRABAR_TRUTH_ENABLED is False
