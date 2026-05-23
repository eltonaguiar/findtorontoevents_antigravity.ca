"""Tests for H-002 PEAD shadow runner (tools/pead_shadow_runner.py).

Validates:
- Gate-off: equity_pead_signals returns [] when EQUITY_PEAD_ENABLED not set
- Runner main() runs without crashing (dry-run, gate-on)
- _prune_old_entries removes entries older than threshold
- _prune_old_entries keeps recent entries
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "alpha_engine"))


class TestPeadGateOff:
    def test_pead_signals_empty_when_gate_off(self, monkeypatch):
        """equity_pead_signals must return [] when EQUITY_PEAD_ENABLED is unset."""
        monkeypatch.delenv("EQUITY_PEAD_ENABLED", raising=False)
        from alpha_engine.equity_pead_strategy import equity_pead_signals
        result = equity_pead_signals()
        assert result == []

    def test_pead_signals_empty_when_gate_zero(self, monkeypatch):
        monkeypatch.setenv("EQUITY_PEAD_ENABLED", "0")
        from alpha_engine.equity_pead_strategy import equity_pead_signals
        result = equity_pead_signals()
        assert result == []


class TestPeadShadowRunnerPrune:
    def test_prune_removes_old_entries(self):
        from tools.pead_shadow_runner import _prune_old_entries

        old_ts = (datetime.now(timezone.utc) - timedelta(days=100)).isoformat()
        recent_ts = datetime.now(timezone.utc).isoformat()

        old_entry = json.dumps({"symbol": "AAPL", "_runner_ts": old_ts})
        new_entry = json.dumps({"symbol": "MSFT", "_runner_ts": recent_ts})

        result = _prune_old_entries([old_entry, new_entry])
        assert len(result) == 1
        assert "MSFT" in result[0]

    def test_prune_keeps_recent_entries(self):
        from tools.pead_shadow_runner import _prune_old_entries

        recent_ts = datetime.now(timezone.utc).isoformat()
        entry = json.dumps({"symbol": "NVDA", "_runner_ts": recent_ts})
        result = _prune_old_entries([entry])
        assert len(result) == 1

    def test_prune_tolerates_missing_ts(self):
        from tools.pead_shadow_runner import _prune_old_entries

        entry = json.dumps({"symbol": "TSLA"})  # no _runner_ts
        result = _prune_old_entries([entry])
        assert len(result) == 1  # kept defensively

    def test_prune_skips_blank_lines(self):
        from tools.pead_shadow_runner import _prune_old_entries

        result = _prune_old_entries(["", "   ", "\n"])
        assert result == []


class TestPeadShadowRunnerMain:
    def test_main_dry_run_gate_on_returns_zero(self, monkeypatch, tmp_path):
        """main(dry_run=True) with gate-on must succeed (exit 0), no file written."""
        monkeypatch.setenv("EQUITY_PEAD_ENABLED", "1")
        from tools import pead_shadow_runner

        with patch(
            "alpha_engine.equity_pead_strategy.equity_pead_signals",
            return_value=[],
        ):
            rc = pead_shadow_runner.main(dry_run=True)

        assert rc == 0

    def test_main_dry_run_no_file_created(self, monkeypatch, tmp_path):
        """dry_run must not create the shadow log."""
        monkeypatch.setenv("EQUITY_PEAD_ENABLED", "1")
        shadow_log = tmp_path / "pead_shadow_log.jsonl"
        from tools import pead_shadow_runner

        with patch(
            "alpha_engine.equity_pead_strategy.equity_pead_signals",
            return_value=[],
        ):
            pead_shadow_runner.main(dry_run=True, output_path=shadow_log)

        assert not shadow_log.exists()

    def test_main_writes_signal_to_log(self, monkeypatch, tmp_path):
        """When signals are returned they must be appended to the shadow log."""
        monkeypatch.setenv("EQUITY_PEAD_ENABLED", "1")
        shadow_log = tmp_path / "pead_shadow_log.jsonl"
        from tools import pead_shadow_runner

        fake_signal = {
            "symbol": "AAPL",
            "strategy": "equity_pead",
            "signal_type": "BUY",
            "direction": "LONG",
            "asset_class": "EQUITY",
            "entry_price": 185.0,
            "take_profit": 196.1,
            "stop_loss": 179.45,
            "confidence": 0.62,
            "risk_reward": 2.0,
            "hold_days": 30,
            "earnings_surprise_pct": 7.5,
            "earnings_date": "2026-05-15",
            "days_since_earnings": 2,
            "_h002_shadow": True,
            "_pead_signal": True,
        }

        with patch(
            "alpha_engine.equity_pead_strategy.equity_pead_signals",
            return_value=[fake_signal],
        ):
            rc = pead_shadow_runner.main(dry_run=False, output_path=shadow_log)

        assert rc == 0
        assert shadow_log.exists()
        lines = [ln for ln in shadow_log.read_text().splitlines() if ln.strip()]
        assert len(lines) == 1
        record = json.loads(lines[0])
        assert record["symbol"] == "AAPL"
        assert "_runner_ts" in record
        assert record["_h002_shadow"] is True
