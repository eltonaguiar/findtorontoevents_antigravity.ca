"""Smoke tests for alpha_engine.decay_tracker and reconciliation_report."""
from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone

from alpha_engine.decay_tracker import compute_decay_blocks
from alpha_engine.reconciliation_report import build_reconciliation_report


NOW = datetime(2026, 5, 1, 12, 0, 0, tzinfo=timezone.utc)


def _pick(days_ago: int, pnl: float, source: str = "src_a", asset_class: str = "EQUITY",
          status: str = "WON", emitted_offset_h: int = 24, resolver_version: str = "v2"):
    closed_at = NOW - timedelta(days=days_ago)
    emitted_at = closed_at - timedelta(hours=emitted_offset_h)
    return {
        "source_system": source,
        "pnl_pct": pnl,
        "closed_at": closed_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "resolved_at": closed_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "emitted_at": emitted_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "asset_class": asset_class,
        "status": status,
        "resolver_version": resolver_version,
    }


def test_decay_insufficient_for_thin_source():
    picks = [_pick(d, 0.01) for d in range(1, 5)]
    out = compute_decay_blocks(picks, now=NOW)
    assert out["src_a"]["status"] == "insufficient"


def test_decay_healthy_when_short_matches_long():
    rng = random.Random(0)
    picks = []
    # 60 picks across the last year, evenly distributed, all small positive returns
    for d in range(1, 360, 6):
        picks.append(_pick(d, rng.gauss(0.005, 0.002)))
    out = compute_decay_blocks(picks, now=NOW, min_short_window_trades=5,
                               min_long_window_trades=20)
    assert out["src_a"]["status"] in ("healthy", "decaying")
    assert out["src_a"]["n_long"] >= out["src_a"]["n_short"]


def test_decay_flagged_when_short_window_negative():
    # Long window strongly positive; short window strongly negative -> decaying.
    picks = []
    for d in range(120, 360, 4):  # in long window only
        picks.append(_pick(d, 0.02))
    for d in range(1, 90, 3):  # in short window
        picks.append(_pick(d, -0.02))
    out = compute_decay_blocks(picks, now=NOW, min_short_window_trades=5,
                               min_long_window_trades=20)
    assert out["src_a"]["status"] == "decaying"
    assert out["src_a"]["ratio"] is not None
    assert out["src_a"]["ratio"] < 0.5


def test_reconciliation_basic_shape():
    picks = [
        _pick(1, 0.01, asset_class="EQUITY", status="WON"),
        _pick(2, -0.02, asset_class="EQUITY", status="LOST"),
        _pick(3, 0.005, asset_class="CRYPTO", status="WON"),
    ]
    rep = build_reconciliation_report(picks, now=NOW)
    assert "as_of" in rep
    assert set(rep["by_class"].keys()) == {"EQUITY", "CRYPTO"}
    assert rep["by_class"]["EQUITY"]["n_total"] == 2
    assert rep["by_class"]["EQUITY"]["n_resolved"] == 2
    assert rep["by_class"]["EQUITY"]["pct_resolved"] == 100.0
    assert rep["portfolio"]["n_total"] == 3
    assert rep["portfolio"]["n_v2"] == 3


def test_reconciliation_flags_unresolved():
    picks = [
        _pick(1, 0.01, status="WON"),
        {"source_system": "src_a", "asset_class": "EQUITY", "status": "PENDING",
         "pnl_pct": None, "emitted_at": NOW.strftime("%Y-%m-%dT%H:%M:%SZ")},
    ]
    rep = build_reconciliation_report(picks, now=NOW)
    assert rep["by_class"]["EQUITY"]["n_resolved"] == 1
    assert rep["by_class"]["EQUITY"]["n_unresolved"] == 1
    assert rep["by_class"]["EQUITY"]["pct_resolved"] == 50.0
    # 50% resolved is below the 95% default threshold
    assert rep["by_class"]["EQUITY"]["needs_attention"] is True
