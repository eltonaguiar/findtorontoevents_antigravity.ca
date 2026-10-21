"""Fail-closed blocklist gate for the multi-asset copy-trader scraper.

Regression for operator directive #4: the scraper writes its own JSON files
(bypassing forward_validator.save_active_picks()), so it must apply the canonical
strategy_blocklist gate on its OWN emit path, and fail CLOSED when the gate
cannot be loaded (log ERROR + drop all rows, never emit unfiltered).
"""

import json

import pytest

scraper = pytest.importorskip("copy_trader_intel.multi_asset_copytrader_scraper")


def _pick(
    strategy="forex_rsi2_mean_reversion",
    symbol="EURUSD=X",
    asset_class="FOREX",
    source_system="copy_trader_intel",
):
    return {
        "strategy": strategy,
        "symbol": symbol,
        "asset_class": asset_class,
        "source_system": source_system,
        "direction": "LONG",
        "entry_price": 1.08,
        "take_profit": 1.09,
        "stop_loss": 1.07,
        "confidence": 0.8,
    }


def test_gate_loads_canonical_blocklist():
    is_blocked_pick, pick_block_reason = scraper._load_blocklist_gate()
    assert callable(is_blocked_pick)
    assert callable(pick_block_reason)
    # retired forex_rsi2_mean_reversion must be blocked
    assert is_blocked_pick(_pick()) is True


def test_save_results_filters_blocked_forex_rsi2(monkeypatch, tmp_path):
    monkeypatch.setattr(scraper, "DATA_DIR", tmp_path)
    results = {"forex_rsi2": [_pick()]}
    path, all_picks, _meta, filtered = scraper.save_results(results)

    assert all_picks == []
    out = json.loads(path.read_text(encoding="utf-8"))
    assert out["total_picks"] == 0
    assert out["picks"] == []


def test_save_results_allows_unblocked_pick(monkeypatch, tmp_path):
    monkeypatch.setattr(scraper, "DATA_DIR", tmp_path)
    unblocked = _pick("brand_new_strategy_xyz", "BTCUSDT", "CRYPTO")
    path, all_picks, _meta, filtered = scraper.save_results({"new": [unblocked]})

    assert len(all_picks) == 1
    out = json.loads(path.read_text(encoding="utf-8"))
    assert out["total_picks"] == 1
    assert out["picks"] == [unblocked]


def test_save_results_fails_closed_when_gate_import_fails(monkeypatch, tmp_path, capsys):
    def _boom():
        raise ImportError("synthetic blocklist import failure")

    monkeypatch.setattr(scraper, "_load_blocklist_gate", _boom)
    monkeypatch.setattr(scraper, "DATA_DIR", tmp_path)

    results = {"forex_rsi2": [_pick()]}
    path, all_picks, _meta, filtered = scraper.save_results(results)

    # Fail-closed: NOTHING emitted, and an ERROR is logged.
    assert all_picks == []
    out = json.loads(path.read_text(encoding="utf-8"))
    assert out["total_picks"] == 0
    assert out["picks"] == []
    captured = capsys.readouterr()
    assert "FAIL-CLOSED" in captured.out
