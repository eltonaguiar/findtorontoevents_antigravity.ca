from __future__ import annotations

from audit_trail import dashboard_generator


def test_normalize_pick_falls_back_to_source_system_for_source_and_system() -> None:
    raw = {
        "symbol": "BNBUSDT",
        "direction": "LONG",
        "entry_price": 100.0,
        "take_profit": 110.0,
        "stop_loss": 95.0,
        "strategy": "tsmom_volscaled",
    }

    norm = dashboard_generator._normalize_pick(raw, "tsmom_strategy", "OPEN")

    assert norm["source_system"] == "tsmom_strategy"
    assert norm["source"] == "tsmom_strategy"
    assert norm["system"] == "tsmom_strategy"


def test_normalize_pick_uses_unknown_when_no_source_lineage_exists() -> None:
    raw = {
        "symbol": "BTCUSDT",
        "direction": "LONG",
        "entry_price": 68000.0,
        "take_profit": 70000.0,
        "stop_loss": 66800.0,
        "strategy": "anonymous_signal",
    }

    norm = dashboard_generator._normalize_pick(raw, "", "OPEN")

    assert norm["source_system"] == ""
    assert norm["source"] == "unknown"
    assert norm["system"] == "unknown"


def test_normalize_pick_prefers_explicit_raw_source_and_system() -> None:
    raw = {
        "symbol": "ETHUSDT",
        "direction": "SHORT",
        "entry_price": 2500.0,
        "take_profit": 2400.0,
        "stop_loss": 2550.0,
        "strategy": "explicit_lineage",
        "source": "manual_research",
        "system": "discretionary_overlay",
        "source_system": "alpha_engine",
    }

    norm = dashboard_generator._normalize_pick(raw, "alpha_engine", "OPEN")

    assert norm["source_system"] == "alpha_engine"
    assert norm["source"] == "manual_research"
    assert norm["system"] == "discretionary_overlay"


def test_normalize_pick_counts_closed_loss_with_zero_reported_pnl_as_loss() -> None:
    raw = {
        "symbol": "MARA",
        "direction": "LONG",
        "entry_price": 8.94,
        "final_return_pct": 0,
        "outcome": "LOSS",
        "exit_reason": "removed_from_consensus",
    }

    norm = dashboard_generator._normalize_pick(raw, "goldmine_stocks", "CLOSED")

    assert norm["status"] == "LOST"
    assert norm["pnl_pct"] < 0
