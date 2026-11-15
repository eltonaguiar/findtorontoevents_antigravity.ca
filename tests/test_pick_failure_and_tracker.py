"""Root-cause labels, open-pick QA, ledger tracker, Admiral min gate."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))


def test_open_pick_is_not_a_blank_exit_failure():
    from alpha_engine.risk_qa_validator import validate_pick

    pick = {
        "id": "wired_in_childlike::XLV::2026-11-13",
        "symbol": "XLV",
        "asset_class": "ETF",
        "direction": "LONG",
        "status": "OPEN",
        "strategy": "wired_in_trend_momo_4d",
        "entry_price": 188.85,
        "entry_time": "2026-11-15T01:50:00+00:00",
        "take_profit": 195.03,
        "stop_loss": 185.15,
        "pnl_pct": 0.0,
        "max_hold_hours": 504,
    }
    result = validate_pick(pick, {"XLV": {"close_price": 190.0, "current_price": 190.0, "asof": "2026-11-14"}})
    checks = {i.get("check") for i in result["issues"]}
    assert "blank_field" not in checks
    assert result["critical_count"] == 0


def test_same_bar_and_horizon_are_named():
    from alpha_engine.pick_failure_root_cause import diagnose, explicit_hold_hours

    row = diagnose({
        "id": "x",
        "symbol": "XLV",
        "asset_class": "ETF",
        "status": "OPEN",
        "pnl_pct": 0.0,
        "entry_basis": "same_bar_close",
        "leakage": "SAME_BAR_ENTRY",
        "signal_asof": "2026-11-13T21:00:00+00:00",
        "timestamp": "2026-11-15T01:50:00+00:00",
    })
    assert "SAME_BAR_ENTRY" in row["reasons"]
    assert "HORIZON_MISMATCH" in row["reasons"]
    assert explicit_hold_hours({"max_hold_hours": 504}) == 504
    assert explicit_hold_hours({"max_hold_hours": 1}) is None


def test_ledger_k4_and_no_restart(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    spec = importlib.util.spec_from_file_location(
        "ft_ledger",
        REPO / "alpha_engine/data/forward_testing/forward_tracker.py",
    )
    ft = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ft)
    ft.DATA_DIR = tmp_path
    ft.log_trade("K4", "EQUITY", "SPY", 100, 80, 1, 0, "2026-11-01T00:00:00+00:00", "2026-11-02T00:00:00+00:00")
    eliminated = list(tmp_path.glob("forward_test_eliminated.csv"))
    text = eliminated[0].read_text()
    assert "K4" in text
    assert "-20.0" in text
    ft.log_trade("K4", "EQUITY", "SPY", 100, 101, 1, 0, "2026-11-03T00:00:00+00:00", "2026-11-04T00:00:00+00:00")
    ledger = (tmp_path / "forward_test_trades.csv").read_text().strip().splitlines()
    assert len(ledger) == 2  # header + one trade; restart refused


def test_admiral_min_is_not_a_fail():
    from alpha_engine.mf_screener import screen_fund

    fund = {
        "symbol": "VFIAX",
        "name": "Vanguard 500 Admiral",
        "index_fund": True,
        "expense_ratio": 0.0004,
        "load": 0,
        "b_12b1": 0,
        "min_initial": 3000,
        "aum": 1_000_000_000_000,
        "turnover": 0.04,
        "tracking_error": 0.0005,
        "track_record_years": 20,
        "nav_freshness_hours": 24,
    }
    result = screen_fund(fund)
    assert "min_initial" not in result["failed_gates"]
    assert result["passed"] is True
