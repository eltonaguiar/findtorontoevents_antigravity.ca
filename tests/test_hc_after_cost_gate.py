"""Tests for B17 — HC after-cost shadow gate + after-cost field stamping.

Covers:
- stamp_after_cost_fields: null strategy, matching strategy (compound + fallback keys),
  stale artifact passthrough, field values
- passes_hc_after_cost: flag OFF (always pass), flag ON + survivor, flag ON + non-survivor,
  flag ON + None fields (unknown strategy), malformed fields
- _load_ac_strategy_index: empty glob, stale artifact detection
"""
from __future__ import annotations

import json
import os
import tempfile
import datetime
from pathlib import Path
from unittest import mock


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_row(strategy: str, asset_class: str, after_cost: float, wilson_lb: float, both: bool) -> dict:
    return {
        "strategy": strategy,
        "asset_class": asset_class,
        "after_cost_mean_pnl_pct": after_cost,
        "wilson_lb_wr_pct": wilson_lb,
        "both_survive": both,
    }


def _make_artifact(strategies: list[dict], generated_at: str | None = None) -> dict:
    if generated_at is None:
        generated_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
    return {
        "generated_at": generated_at,
        "date": "2026-05-02",
        "version": "1",
        "strategies": strategies,
        "survivors": [],
        "summary": {},
    }


# ---------------------------------------------------------------------------
# stamp_after_cost_fields
# ---------------------------------------------------------------------------

def test_stamp_null_strategy_sets_null_fields():
    """Pick with empty strategy → all three fields None."""
    from audit_trail.dashboard_generator import stamp_after_cost_fields
    pick = {"symbol": "AAPL", "strategy": None, "asset_class": "EQUITY"}
    stamp_after_cost_fields(pick, {})
    assert pick["after_cost_net_per_trade"] is None
    assert pick["wilson_lb_wr"] is None
    assert pick["is_ac_survivor"] is None


def test_stamp_compound_key_match():
    """Exact (strategy, asset_class) hit returns correct values."""
    from audit_trail.dashboard_generator import stamp_after_cost_fields
    index = {
        ("rs-breakout-scout", "EQUITY"): _make_row("rs-breakout-scout", "EQUITY", 2.48, 54.8, True),
    }
    pick = {"symbol": "AAPL", "strategy": "rs-breakout-scout", "asset_class": "EQUITY"}
    stamp_after_cost_fields(pick, index)
    assert pick["after_cost_net_per_trade"] == 2.48
    assert pick["wilson_lb_wr"] == 54.8
    assert pick["is_ac_survivor"] is True


def test_stamp_fallback_key_when_no_asset_class():
    """Fallback to strategy-only key when asset_class is absent."""
    from audit_trail.dashboard_generator import stamp_after_cost_fields
    row = _make_row("rs-breakout-scout", "EQUITY", 2.48, 54.8, True)
    index = {
        ("rs-breakout-scout", "EQUITY"): row,
        "rs-breakout-scout": row,
    }
    pick = {"symbol": "AAPL", "strategy": "rs-breakout-scout", "asset_class": ""}
    stamp_after_cost_fields(pick, index)
    assert pick["after_cost_net_per_trade"] == 2.48


def test_stamp_unknown_strategy_sets_null():
    """Strategy not in index → None fields."""
    from audit_trail.dashboard_generator import stamp_after_cost_fields
    index = {
        ("rs-breakout-scout", "EQUITY"): _make_row("rs-breakout-scout", "EQUITY", 2.48, 54.8, True),
    }
    pick = {"strategy": "some_new_strategy", "asset_class": "EQUITY"}
    stamp_after_cost_fields(pick, index)
    assert pick["after_cost_net_per_trade"] is None
    assert pick["wilson_lb_wr"] is None
    assert pick["is_ac_survivor"] is None


def test_stamp_non_survivor_flags_correctly():
    """Strategy that doesn't survive after-cost gates → is_ac_survivor False."""
    from audit_trail.dashboard_generator import stamp_after_cost_fields
    row = _make_row("bad_strategy", "CRYPTO", -0.5, 42.0, False)
    index = {("bad_strategy", "CRYPTO"): row, "bad_strategy": row}
    pick = {"strategy": "bad_strategy", "asset_class": "CRYPTO"}
    stamp_after_cost_fields(pick, index)
    assert pick["is_ac_survivor"] is False
    assert pick["after_cost_net_per_trade"] == -0.5


def test_stamp_case_insensitive_strategy():
    """Strategy lookup is case-insensitive (lowercased in index)."""
    from audit_trail.dashboard_generator import stamp_after_cost_fields
    row = _make_row("rs-breakout-scout", "EQUITY", 2.48, 54.8, True)
    index = {("rs-breakout-scout", "EQUITY"): row, "rs-breakout-scout": row}
    pick = {"strategy": "RS-Breakout-Scout", "asset_class": "equity"}
    stamp_after_cost_fields(pick, index)
    assert pick["after_cost_net_per_trade"] == 2.48


# ---------------------------------------------------------------------------
# passes_hc_after_cost — flag OFF
# ---------------------------------------------------------------------------

def test_passes_hc_after_cost_flag_off_always_true():
    """With HC_AFTER_COST_GATE_ENABLED unset, all picks pass."""
    from tools.hc_gates_python import passes_hc_after_cost
    with mock.patch.dict(os.environ, {}, clear=False):
        os.environ.pop("HC_AFTER_COST_GATE_ENABLED", None)
        assert passes_hc_after_cost({"after_cost_net_per_trade": -5.0, "wilson_lb_wr": 10.0}) is True
        assert passes_hc_after_cost({}) is True


def test_passes_hc_after_cost_flag_explicitly_zero():
    """HC_AFTER_COST_GATE_ENABLED=0 → all picks pass."""
    from tools.hc_gates_python import passes_hc_after_cost
    with mock.patch.dict(os.environ, {"HC_AFTER_COST_GATE_ENABLED": "0"}):
        assert passes_hc_after_cost({"after_cost_net_per_trade": -1.0, "wilson_lb_wr": 40.0}) is True


# ---------------------------------------------------------------------------
# passes_hc_after_cost — flag ON
# ---------------------------------------------------------------------------

def test_passes_hc_after_cost_survivor_passes():
    """Strategy that passes both criteria passes the gate."""
    from tools.hc_gates_python import passes_hc_after_cost
    with mock.patch.dict(os.environ, {"HC_AFTER_COST_GATE_ENABLED": "1"}):
        pick = {"after_cost_net_per_trade": 2.48, "wilson_lb_wr": 54.8}
        assert passes_hc_after_cost(pick) is True


def test_passes_hc_after_cost_negative_net_fails():
    """Negative after-cost return fails even if wilson_lb is high."""
    from tools.hc_gates_python import passes_hc_after_cost
    with mock.patch.dict(os.environ, {"HC_AFTER_COST_GATE_ENABLED": "1"}):
        pick = {"after_cost_net_per_trade": -0.5, "wilson_lb_wr": 75.0}
        assert passes_hc_after_cost(pick) is False


def test_passes_hc_after_cost_low_wilson_lb_fails():
    """Wilson lb below 50% fails even if after-cost is positive."""
    from tools.hc_gates_python import passes_hc_after_cost
    with mock.patch.dict(os.environ, {"HC_AFTER_COST_GATE_ENABLED": "1"}):
        pick = {"after_cost_net_per_trade": 1.5, "wilson_lb_wr": 49.9}
        assert passes_hc_after_cost(pick) is False


def test_passes_hc_after_cost_exactly_50_lb_passes():
    """Wilson lb == 50.0 is the boundary — should pass."""
    from tools.hc_gates_python import passes_hc_after_cost
    with mock.patch.dict(os.environ, {"HC_AFTER_COST_GATE_ENABLED": "1"}):
        pick = {"after_cost_net_per_trade": 0.01, "wilson_lb_wr": 50.0}
        assert passes_hc_after_cost(pick) is True


def test_passes_hc_after_cost_none_fields_pass():
    """None fields (unknown strategy) always pass."""
    from tools.hc_gates_python import passes_hc_after_cost
    with mock.patch.dict(os.environ, {"HC_AFTER_COST_GATE_ENABLED": "1"}):
        assert passes_hc_after_cost({"after_cost_net_per_trade": None, "wilson_lb_wr": None}) is True
        assert passes_hc_after_cost({}) is True


def test_passes_hc_after_cost_malformed_fields_pass():
    """Malformed non-numeric fields pass safely (no crash)."""
    from tools.hc_gates_python import passes_hc_after_cost
    with mock.patch.dict(os.environ, {"HC_AFTER_COST_GATE_ENABLED": "1"}):
        assert passes_hc_after_cost({"after_cost_net_per_trade": "bad", "wilson_lb_wr": "data"}) is True


# ---------------------------------------------------------------------------
# _load_ac_strategy_index
# ---------------------------------------------------------------------------

def test_load_ac_strategy_index_no_artifacts(tmp_path):
    """Empty glob → returns empty dict."""
    import audit_trail.dashboard_generator as dg
    # Reset cache
    dg._AC_STRATEGY_INDEX_CACHE = None
    dg._AC_STRATEGY_INDEX_LOADED_AT = 0.0
    with mock.patch("glob.glob", return_value=[]):
        result = dg._load_ac_strategy_index()
    assert result == {}


def test_load_ac_strategy_index_stale_artifact(tmp_path):
    """Artifact with generated_at > 25h ago → empty dict."""
    import audit_trail.dashboard_generator as dg
    dg._AC_STRATEGY_INDEX_CACHE = None
    dg._AC_STRATEGY_INDEX_LOADED_AT = 0.0

    stale_ts = (
        datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=30)
    ).isoformat()
    data = _make_artifact(
        [_make_row("rs-breakout-scout", "EQUITY", 2.48, 54.8, True)],
        generated_at=stale_ts,
    )
    artifact = tmp_path / "forward_edge_audit_2026-04-30.json"
    artifact.write_text(json.dumps(data))

    with mock.patch("glob.glob", return_value=[str(artifact)]):
        result = dg._load_ac_strategy_index()
    assert result == {}


def test_load_ac_strategy_index_fresh_artifact(tmp_path):
    """Fresh artifact → index has compound and fallback keys."""
    import audit_trail.dashboard_generator as dg
    dg._AC_STRATEGY_INDEX_CACHE = None
    dg._AC_STRATEGY_INDEX_LOADED_AT = 0.0

    fresh_ts = datetime.datetime.now(datetime.timezone.utc).isoformat()
    data = _make_artifact(
        [_make_row("rs-breakout-scout", "EQUITY", 2.48, 54.8, True)],
        generated_at=fresh_ts,
    )
    artifact = tmp_path / "forward_edge_audit_2026-05-02.json"
    artifact.write_text(json.dumps(data))

    with mock.patch("glob.glob", return_value=[str(artifact)]):
        result = dg._load_ac_strategy_index()

    assert ("rs-breakout-scout", "EQUITY") in result
    assert "rs-breakout-scout" in result


def test_load_ac_strategy_index_cached(tmp_path):
    """Second call within TTL returns cached dict without re-reading file."""
    import audit_trail.dashboard_generator as dg
    import time
    dg._AC_STRATEGY_INDEX_CACHE = {"cached": True}
    dg._AC_STRATEGY_INDEX_LOADED_AT = time.time()

    with mock.patch("glob.glob") as mock_glob:
        result = dg._load_ac_strategy_index()
        mock_glob.assert_not_called()
    assert result == {"cached": True}


# ---------------------------------------------------------------------------
# Integration: stamp fields called from _normalize_pick
# ---------------------------------------------------------------------------

def test_normalize_pick_stamps_after_cost_fields(tmp_path):
    """_normalize_pick stamps after_cost_net_per_trade etc. from the live index."""
    import audit_trail.dashboard_generator as dg

    # Inject a known index
    dg._AC_STRATEGY_INDEX_CACHE = {
        ("rs-breakout-scout", "EQUITY"): _make_row("rs-breakout-scout", "EQUITY", 2.48, 54.8, True),
        "rs-breakout-scout": _make_row("rs-breakout-scout", "EQUITY", 2.48, 54.8, True),
    }
    import time
    dg._AC_STRATEGY_INDEX_LOADED_AT = time.time()

    raw = {
        "symbol": "AAPL",
        "strategy": "rs-breakout-scout",
        "asset_class": "EQUITY",
        "direction": "LONG",
        "entry_price": 100.0,
        "take_profit": 105.0,
        "stop_loss": 97.0,
        "confidence": 0.8,
    }
    pick = dg._normalize_pick(raw, "equity_scanner")
    assert pick.get("after_cost_net_per_trade") == 2.48
    assert pick.get("wilson_lb_wr") == 54.8
    assert pick.get("is_ac_survivor") is True
