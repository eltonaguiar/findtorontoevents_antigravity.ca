"""Tests for the walk-forward OOS gate in money_ready_verdict.

2026-11-16 audit: `wf_oos_ok` used to pass on ratio >= 0.85 alone, so a class
with BOTH in-sample and out-of-sample PF below 1 could still show a green
walk-forward flag. It must also require the OOS leg to be profitable.
"""
from datetime import datetime, timedelta, timezone

from alpha_engine.money_ready_verdict import _simple_wf_oos_ratio

_BASE = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _interleaved(wins, losses, start=0):
    """Alternate W/L so both halves of a chronological split have both."""
    out = []
    w, l = 0, 0
    i = 0
    while w < wins or l < losses:
        if w < wins:
            out.append(("WON", 0.03)); w += 1; i += 1
        if l < losses:
            out.append(("LOST", -0.02)); l += 1; i += 1
    return [
        {
            "status": s, "pnl_pct": p, "asset_class": "CRYPTO",
            "closed_at": (_BASE + timedelta(days=start + idx)).isoformat(),
        }
        for idx, (s, p) in enumerate(out)
    ]


def test_n_below_30_is_none():
    r = _simple_wf_oos_ratio(_interleaved(10, 10))
    assert r["ok"] is None


def test_both_unprofitable_is_not_ok():
    # IS PF 0.5, OOS PF 0.5 -> ratio 1.0 but OOS unprofitable
    r = _simple_wf_oos_ratio(_interleaved(12, 24) + _interleaved(8, 16, start=100))
    assert r["ratio"] is not None
    assert r["ratio"] >= 0.85
    assert r["ok"] is False


def test_profitable_oos_with_good_ratio_is_ok():
    # IS PF 1.0, OOS PF 1.0 -> ratio 1.0 and OOS profitable
    r = _simple_wf_oos_ratio(_interleaved(18, 18) + _interleaved(12, 12, start=100))
    assert r["ratio"] >= 0.85
    assert r["oos_pf"] >= 1.0
    assert r["ok"] is True


def test_poor_ratio_is_not_ok():
    # IS PF 1.0, OOS PF 0.25 -> ratio 0.25
    r = _simple_wf_oos_ratio(_interleaved(18, 18) + _interleaved(4, 12, start=100))
    assert r["ok"] is False
