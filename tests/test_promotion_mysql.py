"""
Tests for log_outcome_to_mysql in genome.progressive_promotion
"""

from unittest.mock import MagicMock

import sys
import importlib.util
from pathlib import Path

import pytest

# Import directly to avoid genome.__init__ pulling in pandas/heavy deps
_spec = importlib.util.spec_from_file_location(
    "genome.progressive_promotion",
    Path(__file__).resolve().parent.parent / "genome" / "progressive_promotion.py",
)
_mod = importlib.util.module_from_spec(_spec)
sys.modules["genome.progressive_promotion"] = _mod
_spec.loader.exec_module(_mod)
log_outcome_to_mysql = _mod.log_outcome_to_mysql


def test_log_outcome_inserts_row():
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    pick = {
        "symbol": "BTCUSDT", "direction": "LONG",
        "entry_price": 65000.0, "tp": 68000.0, "sl": 63000.0,
        "strategy_id": "test_strat", "opened_at": "2026-03-04T12:00:00",
    }
    log_outcome_to_mysql(mock_conn, pick, "WON", 68000.0, 4.61)
    mock_cursor.execute.assert_called_once()
    args = mock_cursor.execute.call_args
    assert "at_signal_outcomes" in args[0][0]
    assert "dna_genome" in args[0][1]


def test_log_outcome_rounds_pnl():
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    pick = {
        "symbol": "ETHUSDT", "direction": "SHORT",
        "entry_price": 3500.0, "tp": 3200.0, "sl": 3600.0,
        "strategy_id": "eth_strat", "opened_at": "2026-03-04T14:00:00",
    }
    log_outcome_to_mysql(mock_conn, pick, "LOST", 3600.0, -2.857142857)
    args = mock_cursor.execute.call_args
    params = args[0][1]
    # pnl_pct should be rounded to 4 decimal places
    assert params[7] == round(-2.857142857, 4)


def test_log_outcome_commits():
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    pick = {
        "symbol": "SOLUSDT", "direction": "LONG",
        "entry_price": 100.0, "tp": 110.0, "sl": 95.0,
        "strategy_id": "sol_strat", "opened_at": "2026-03-04T16:00:00",
    }
    log_outcome_to_mysql(mock_conn, pick, "WON", 110.0, 10.0)
    mock_conn.commit.assert_called_once()


def test_log_outcome_missing_fields_use_defaults():
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    pick = {"symbol": "XRPUSDT", "direction": "LONG", "entry_price": 0.5}
    log_outcome_to_mysql(mock_conn, pick, "WON", 0.55, 10.0)
    args = mock_cursor.execute.call_args
    params = args[0][1]
    # strategy_id defaults to "unknown" when missing
    assert params[9] == "unknown"


def test_log_outcome_infers_non_crypto_asset_class():
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    pick = {
        "symbol": "AAPL", "direction": "LONG",
        "entry_price": 100.0, "tp": 110.0, "sl": 95.0,
        "strategy_id": "equity_strat", "opened_at": "2026-03-04T16:00:00",
    }
    log_outcome_to_mysql(mock_conn, pick, "WON", 110.0, 10.0)
    params = mock_cursor.execute.call_args[0][1]
    assert params[10] == "EQUITY"
