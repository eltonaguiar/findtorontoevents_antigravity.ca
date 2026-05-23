from __future__ import annotations

import json

from alpha_engine import prediction_market_consensus as pmc


def test_aggregate_signals_preserves_wallet_audit_metadata_in_consensus_pick() -> None:
    wallet_picks = [
        {
            "symbol": "ETHUSDT",
            "direction": "LONG",
            "confidence": 0.91,
            "strategy": "copy_pm_wallet_one",
            "source_system": "copy_trader_polymarket",
            "history_wr_bayes": 0.81,
            "history_trades": 12,
            "forward_wr": 0.78,
            "forward_trades": 9,
            "trader_label": "wallet_one",
            "entry_price": 2500.0,
            "take_profit": 2580.0,
            "stop_loss": 2460.0,
        }
    ]
    reverse_picks = [
        {
            "symbol": "ETHUSDT",
            "direction": "LONG",
            "confidence": 0.84,
            "strategy": "polymarket_prediction",
            "source_system": "polymarket_prediction",
            "entry_price": 2500.0,
            "take_profit": 2580.0,
            "stop_loss": 2460.0,
        }
    ]

    picks = pmc.aggregate_signals(wallet_picks, reverse_picks, [])

    assert len(picks) == 1
    pick = picks[0]
    assert pick["strategy"] == "prediction_market_consensus"
    assert pick["type_label"] == "🔮 PM Consensus"
    assert pick["trader_label"] == "wallet_one"
    assert pick["source_count"] == 2
    assert pick["history_wr_bayes"] == 0.81
    assert pick["history_trades"] == 12
    assert pick["forward_wr"] == 0.78
    assert pick["forward_trades"] == 9
    assert pick["source_systems"] == ["copy_trader_polymarket", "polymarket_prediction"]


def test_merge_into_active_picks_removes_legacy_prediction_market_agent_rows(tmp_path) -> None:
    active_path = tmp_path / "active_picks.json"
    active_path.write_text(
        json.dumps(
            [
                {
                    "symbol": "BTCUSDT",
                    "direction": "SHORT",
                    "strategy": "prediction_market_consensus",
                    "source_system": "prediction_market_agents",
                },
                {
                    "symbol": "ETHUSDT",
                    "direction": "LONG",
                    "strategy": "super_signals",
                    "source_system": "super_signals",
                },
            ]
        ),
        encoding="utf-8",
    )

    original_path = pmc.ACTIVE_PICKS_PATH
    try:
        pmc.ACTIVE_PICKS_PATH = active_path
        merged = pmc.merge_into_active_picks(
            [
                {
                    "symbol": "BTCUSDT",
                    "direction": "LONG",
                    "strategy": "prediction_market_consensus",
                    "source_system": "prediction_market_consensus",
                    "confidence": 0.85,
                    "entry_price": 68000.0,
                    "take_profit": 72000.0,
                    "stop_loss": 66000.0,
                }
            ]
        )
        data = json.loads(active_path.read_text(encoding="utf-8"))
    finally:
        pmc.ACTIVE_PICKS_PATH = original_path

    assert merged == 1
    assert len(data) == 2
    assert not any(
        row.get("source_system") == "prediction_market_agents"
        and row.get("strategy") == "prediction_market_consensus"
        for row in data
    )
    assert any(
        row.get("source_system") == "prediction_market_consensus"
        and row.get("symbol") == "BTCUSDT"
        and row.get("direction") == "LONG"
        for row in data
    )
