"""Tests for the JSON positions/returns ledger."""
import json

from combined_book import ledger

STARTING = {
    "put_write": 0.40,
    "trend": 0.35,
    "quality_value": 0.19,
    "cash": 0.06,
}


def test_init_ledger_writes_file(tmp_path):
    p = tmp_path / "ledger.json"
    doc = ledger.init_ledger(STARTING, p, capital=100_000.0, date_closed="2026-09-30")
    assert doc["capital"] == 100_000.0
    assert doc["start_date"] == "2026-09-30"
    assert doc["starting_positions"] == STARTING
    assert json.loads(p.read_text(encoding="utf-8"))["currency"] == "USD"


def test_append_month_row_updates_cash(tmp_path):
    p = tmp_path / "ledger.json"
    doc = ledger.init_ledger(STARTING, p)
    ledger.append_month_row(doc, "2026-10", 0.01, STARTING)
    assert len(doc["monthly_returns"]) == 1
    assert abs(doc["cash"] - 100_000.0 * 1.01) < 1e-6


def test_round_trip_save_load(tmp_path):
    p = tmp_path / "ledger.json"
    doc = ledger.init_ledger(STARTING, p)
    ledger.append_month_row(doc, "2026-10", 0.01, STARTING)
    ledger.save_ledger(doc, p)
    loaded = ledger.load_ledger(p)
    assert loaded["starting_positions"] == STARTING
    assert loaded["monthly_returns"][0]["month"] == "2026-10"
