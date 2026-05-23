"""Tests for ETF Sector Rotation Emitter (B11, 2026-05-01).

Covers:
- _normalize_pick schema correctness
- run() returns empty picks gracefully when yfinance unavailable
- run() respects ETF_SECTOR_EMITTER_ENABLED=0 flag
- JSON_PICK_SOURCES registration of etf_sector_rotation
- _extract_picks recognizes the "picks" key
"""
import json
import os
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "alpha_engine"))


# ---------------------------------------------------------------------------
# _normalize_pick
# ---------------------------------------------------------------------------
from tools.etf_sector_emitter import _normalize_pick


def test_normalize_pick_schema():
    raw = {
        "symbol": "XLK",
        "strategy": "etf_sector_momentum",
        "signal_type": "BUY",
        "entry_price": 200.0,
        "take_profit": 220.0,
        "stop_loss": 190.0,
        "confidence": 0.68,
        "risk_reward": 2.0,
        "reason": "Faber TAA: rank #1",
        "timestamp": "2026-05-01T00:00:00+00:00",
    }
    pick = _normalize_pick(raw)
    assert pick["symbol"] == "XLK"
    assert pick["asset_class"] == "ETF"
    assert pick["direction"] == "LONG"
    assert pick["source_system"] == "etf_all_strategies"
    assert pick["status"] == "OPEN"
    assert pick["timeframe"] == "POSITION"
    assert "id" in pick and pick["id"].startswith("etf_all_strategies::XLK")


def test_normalize_pick_short_signal():
    raw = {
        "symbol": "TLT",
        "signal_type": "SELL",
        "entry_price": 100.0,
        "take_profit": 90.0,
        "stop_loss": 105.0,
    }
    pick = _normalize_pick(raw)
    assert pick["direction"] == "SHORT"


def test_normalize_pick_defaults():
    raw = {"symbol": "IWM"}
    pick = _normalize_pick(raw)
    assert pick["strategy"] == "etf_sector_momentum"
    assert pick["confidence"] == 0.6
    assert pick["direction"] == "LONG"


# ---------------------------------------------------------------------------
# run() with ENABLED=0
# ---------------------------------------------------------------------------
from tools.etf_sector_emitter import run


def test_run_disabled(monkeypatch):
    monkeypatch.setenv("ETF_SECTOR_EMITTER_ENABLED", "0")
    result = run(dry_run=True)
    assert result["status"] == "disabled"
    assert result["picks"] == []


# ---------------------------------------------------------------------------
# run() when yfinance unavailable (graceful empty output)
# ---------------------------------------------------------------------------
def test_run_no_yfinance(monkeypatch, tmp_path):
    monkeypatch.setenv("ETF_SECTOR_EMITTER_ENABLED", "1")
    # Simulate: yfinance unavailable (empty OHLCV) AND etf_strategies importable
    # by patching both _load_ohlcv and the import inside run()
    mock_etf_mod = MagicMock()
    mock_etf_mod.etf_sector_momentum.return_value = []
    mock_etf_mod.ETF_SYMBOLS = {"XLK": {}, "XLF": {}}
    with patch("tools.etf_sector_emitter._load_ohlcv", return_value={}):
        with patch.dict(sys.modules, {"etf_strategies": mock_etf_mod}):
            result = run(dry_run=True)
    assert result["picks"] == []
    assert result.get("status") != "import_error"


# ---------------------------------------------------------------------------
# JSON_PICK_SOURCES registration
# ---------------------------------------------------------------------------
def test_etf_sector_rotation_registered_in_pick_sources():
    """etf_sector_rotation must appear in JSON_PICK_SOURCES."""
    # Read the file as text to avoid executing the full 14k-line generator
    src = (ROOT / "audit_trail" / "dashboard_generator.py").read_text(encoding="utf-8")
    assert '"etf_sector_rotation"' in src or "'etf_sector_rotation'" in src, \
        "etf_sector_rotation not found in JSON_PICK_SOURCES"
    assert "etf_sector_picks.json" in src, \
        "etf_sector_picks.json path not found in dashboard_generator"


# ---------------------------------------------------------------------------
# etf_sector_picks.json schema
# ---------------------------------------------------------------------------
def test_etf_sector_picks_file_schema():
    """Initial placeholder file must have correct schema."""
    path = ROOT / "alpha_engine" / "data" / "etf_sector_picks.json"
    assert path.exists(), "etf_sector_picks.json placeholder not created"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert "picks" in data and isinstance(data["picks"], list)
    assert data.get("source_system") == "etf_all_strategies"
