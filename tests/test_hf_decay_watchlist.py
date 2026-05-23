"""Tests for dashboard HF decay watchlist helper."""

from audit_trail.dashboard_generator import _compute_hf_decay_watchlist


def test_watchlist_empty() -> None:
    w = _compute_hf_decay_watchlist([])
    assert w["rows"] == []


def test_watchlist_requires_fwd_n_20() -> None:
    rows = [
        {
            "strategy": "x",
            "system": "t",
            "bt_wr": 70.0,
            "fwd_wr": 50.0,
            "decay": -20.0,
            "fwd_trades": 5,
            "bt_trades": 100,
        }
    ]
    assert _compute_hf_decay_watchlist(rows)["rows"] == []


def test_watchlist_worst_decay_first() -> None:
    rows = [
        {
            "strategy": "ok",
            "system": "t",
            "bt_wr": 70.0,
            "fwd_wr": 56.0,
            "decay": -14.0,
            "fwd_trades": 20,
            "bt_trades": 50,
        },
        {
            "strategy": "bad",
            "system": "t",
            "bt_wr": 80.0,
            "fwd_wr": 40.0,
            "decay": -40.0,
            "fwd_trades": 25,
            "bt_trades": 50,
        },
    ]
    w = _compute_hf_decay_watchlist(rows, limit=5)
    assert len(w["rows"]) == 2
    assert w["rows"][0]["strategy"] == "bad"
    assert w["rows"][0]["hf_threshold_a"] is True
