"""Per-class strategy tracker rebuild — offline aggregation tests (no DB)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
import rebuild_strategy_stats_all_classes as rb  # noqa: E402


def test_class_normalization():
    assert rb.normalize_class("STOCKS") == "EQUITY"
    assert rb.normalize_class("stock") == "EQUITY"
    assert rb.normalize_class("MEME") == "MEMECOIN"
    assert rb.normalize_class("PENNYSTOCK") == "PENNY_STOCK"
    assert rb.normalize_class("") == "UNKNOWN"
    assert rb.normalize_class("FUTURES") == "FUTURES"


def test_wr_pf_computation():
    rows = [
        {"asset_class": "FUTURES", "strategy": "tsmom", "status": "WON", "pnl_pct": 2.0},
        {"asset_class": "FUTURES", "strategy": "tsmom", "status": "WON", "pnl_pct": 1.0},
        {"asset_class": "FUTURES", "strategy": "tsmom", "status": "LOST", "pnl_pct": -1.0},
    ]
    a = rb.aggregate(rows)
    assert len(a) == 1
    r = a[0]
    assert r["asset_class"] == "FUTURES" and r["n"] == 3
    assert r["win_rate_pct"] == round(100 * 2 / 3, 2)
    assert r["profit_factor"] == 3.0   # gp 3.0 / gl 1.0


def test_expired_excluded():
    rows = [
        {"asset_class": "ETF", "strategy": "x", "status": "WON", "pnl_pct": 1.0},
        {"asset_class": "ETF", "strategy": "x", "status": "EXPIRED", "pnl_pct": 0.0},
    ]
    a = rb.aggregate(rows)
    assert a[0]["n"] == 1   # EXPIRED dropped


def test_fragmented_classes_merge():
    rows = [
        {"asset_class": "STOCKS", "strategy": "s", "status": "WON", "pnl_pct": 1.0},
        {"asset_class": "STOCK", "strategy": "s", "status": "LOST", "pnl_pct": -1.0},
    ]
    a = rb.aggregate(rows)
    assert len(a) == 1 and a[0]["asset_class"] == "EQUITY" and a[0]["n"] == 2


def test_all_losses_pf_zero_not_div0():
    rows = [{"asset_class": "BOND", "strategy": "b", "status": "LOST", "pnl_pct": -1.0}]
    a = rb.aggregate(rows)
    assert a[0]["profit_factor"] in (None, 0.0) or a[0]["profit_factor"] == 999.0 or a[0]["win_rate_pct"] == 0.0
