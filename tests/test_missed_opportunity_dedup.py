"""Tests for deduplication in `alpha_engine.missed_opportunity_analyzer`."""
from __future__ import annotations

import json
from datetime import datetime, timezone

import alpha_engine.missed_opportunity_analyzer as moa


def test_dedup_wrong_and_missed_entries():
    wrong_dups = [
        {
            "symbol": "BTCUSDT", "strategy": "Momentum",
            "entry_price": 60000.0, "exit_price": 58000.0,
            "exit_date": "2026-11-14", "timestamp": "2026-11-14T02:00:00+00:00",
        },
        {
            "symbol": "BTCUSDT", "strategy": "Momentum",
            "entry_price": 60000.0, "exit_price": 58000.0,
            "exit_date": "2026-11-14", "timestamp": "2026-11-14T01:00:00+00:00",
        },
        {
            "symbol": "ETHUSDT", "strategy": "Momentum",
            "entry_price": 3000.0, "exit_price": 2900.0,
            "exit_date": "2026-11-14", "timestamp": "2026-11-14T03:00:00+00:00",
        },
    ]
    deduped_wrong = moa._dedup_wrong_entries(wrong_dups)
    assert len(deduped_wrong) == 2
    assert deduped_wrong[0]["timestamp"] == "2026-11-14T01:00:00+00:00"

    missed_dups = [
        {"symbol": "XYZUSDT", "timestamp": "2026-11-15T05:10:00+00:00"},
        {"symbol": "XYZUSDT", "timestamp": "2026-11-15T05:50:00+00:00"},
        {"symbol": "XYZUSDT", "timestamp": "2026-11-15T06:10:00+00:00"},
    ]
    deduped_missed = moa._dedup_missed_entries(missed_dups)
    assert len(deduped_missed) == 2


def test_run_analysis_twice_does_not_bloat_logs(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    (data_dir / "active_picks.json").write_text("[]", encoding="utf-8")
    (data_dir / "dynamic_universe.json").write_text(
        json.dumps({"core_symbols": ["BTCUSDT"], "dynamic_symbols": []}),
        encoding="utf-8",
    )
    (data_dir / "closed_picks.json").write_text(
        json.dumps([{
            "symbol": "SOLUSDT",
            "strategy": "Breakout",
            "signal_type": "BUY",
            "exit_reason": "SL_HIT",
            "exit_date": today,
            "entry_price": 150.0,
            "exit_price": 140.0,
            "pnl_pct": -6.67,
        }]),
        encoding="utf-8",
    )

    monkeypatch.setattr(moa, "ACTIVE_PICKS_PATH", data_dir / "active_picks.json")
    monkeypatch.setattr(moa, "CLOSED_PICKS_PATH", data_dir / "closed_picks.json")
    monkeypatch.setattr(moa, "DYNAMIC_UNIVERSE_PATH", data_dir / "dynamic_universe.json")
    monkeypatch.setattr(moa, "MISSED_GAINERS_LOG", data_dir / "missed_gainers_log.json")
    monkeypatch.setattr(moa, "WRONG_GUESSES_LOG", data_dir / "wrong_guesses_log.json")
    monkeypatch.setattr(moa, "IMPROVEMENT_REPORT", data_dir / "hourly_improvement_report.json")
    monkeypatch.setattr(
        moa, "fetch_binance_tickers",
        lambda: [{"symbol": "NEWUSDT", "priceChangePercent": "25.0",
                  "quoteVolume": "8000000", "lastPrice": "1.25"}],
    )

    moa.run_analysis()
    moa.run_analysis()

    wrong_log = json.loads((data_dir / "wrong_guesses_log.json").read_text(encoding="utf-8"))
    missed_log = json.loads((data_dir / "missed_gainers_log.json").read_text(encoding="utf-8"))
    assert len(wrong_log) == 1
    assert len(missed_log) == 1
