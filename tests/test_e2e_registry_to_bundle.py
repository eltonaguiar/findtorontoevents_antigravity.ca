"""End-to-end: envelope -> registry -> bundle-baby -> quality gate."""

import json
import sys
from unittest.mock import MagicMock
import pytest
from pathlib import Path

# Stub incubator.testing to avoid pandas dependency
sys.modules.setdefault("incubator", MagicMock())
sys.modules.setdefault("incubator.testing", MagicMock())

from strategy_registry.registry import StrategyRegistry
from strategy_registry.envelope_schema import validate_envelope
from strategy_registry.adapters.consensus_adapter import consensus_pick_to_envelope
from strategy_registry.adapters.dna_adapter import dna_pick_to_envelope
from bundle_baby_system import BundleBabySystem


@pytest.fixture
def e2e_dirs(tmp_path):
    incoming = tmp_path / "incoming"
    failed = tmp_path / "failed"
    master = tmp_path / "master.json"
    incoming.mkdir()
    failed.mkdir()
    return incoming, failed, master


def test_full_pipeline(e2e_dirs):
    """Envelope -> Registry -> Master file -> Quality gate."""
    incoming, failed, master = e2e_dirs

    # 1. Drop an envelope
    envelope = {
        "strategy_id": "e2e_test_001",
        "name": "E2E Test Strategy",
        "type": "rule",
        "source_system": "test",
        "backtest_results": {
            "tier_1": {"passed": True, "sharpe_ratio": 2.0, "win_rate": 65, "trades": 100, "total_return": 40, "pair": "BTC/USDT", "direction": "LONG"},
        },
        "tags": {"symbol_scope": "single_symbol", "direction_bias": "long_only"},
        "generated_at": "2026-03-04T12:00:00Z",
    }
    (incoming / "e2e.json").write_text(json.dumps(envelope))

    # 2. Registry processes it
    reg = StrategyRegistry(incoming_dir=incoming, failed_dir=failed, master_path=master)
    processed = reg.process_all()
    assert processed == 1

    # 3. Master file has the strategy
    data = json.loads(master.read_text())
    assert "e2e_test_001" in data["strategies"]

    # 4. Quality gate evaluates ELITE stats
    gate = BundleBabySystem.evaluate_gate({
        "forward_trades": 50,
        "forward_win_rate": 65,
        "forward_sharpe": 2.0,
        "forward_max_dd": -5,
        "forward_realized_pnl": 40.0,
    })
    assert gate["status"] == "ELITE"
    assert gate["checks_passed"] == 8


def test_adapter_to_registry_pipeline(e2e_dirs):
    """Consensus pick -> adapter -> envelope -> registry."""
    incoming, failed, master = e2e_dirs

    # 1. Convert a consensus pick to envelope
    pick = {
        "symbol": "BTCUSDT",
        "direction": "LONG",
        "confidence": 0.85,
        "entry_price": 65000,
        "take_profit": 70000,
        "stop_loss": 62000,
        "strategy": "connors_rsi2",
        "source_systems": ["alpha_engine", "mercury2"],
        "agreement_count": 2,
    }
    envelope = consensus_pick_to_envelope(pick)

    # 2. Validate the envelope
    ok, errors = validate_envelope(envelope)
    assert ok, f"Validation errors: {errors}"

    # 3. Write to incoming
    (incoming / "consensus.json").write_text(json.dumps(envelope))

    # 4. Registry processes it
    reg = StrategyRegistry(incoming_dir=incoming, failed_dir=failed, master_path=master)
    processed = reg.process_all()
    assert processed == 1

    # 5. Verify in master
    data = json.loads(master.read_text())
    assert envelope["strategy_id"] in data["strategies"]
    stored = data["strategies"][envelope["strategy_id"]]
    assert stored["type"] == "consensus"
    assert stored["source_system"] == "cross_aggregation"


def test_dna_adapter_to_registry_pipeline(e2e_dirs):
    """DNA pick -> adapter -> envelope -> registry."""
    incoming, failed, master = e2e_dirs

    pick = {
        "symbol": "ETHUSDT",
        "direction": "SHORT",
        "confidence": 0.72,
        "dna_hash": "abc123",
        "strategy": "RSI2_FearGreed",
    }
    envelope = dna_pick_to_envelope(pick)

    ok, errors = validate_envelope(envelope)
    assert ok, f"Validation errors: {errors}"

    (incoming / "dna.json").write_text(json.dumps(envelope))

    reg = StrategyRegistry(incoming_dir=incoming, failed_dir=failed, master_path=master)
    assert reg.process_all() == 1

    data = json.loads(master.read_text())
    assert envelope["strategy_id"] in data["strategies"]
    assert data["strategies"][envelope["strategy_id"]]["type"] == "dna"


def test_quality_gate_status_progression():
    """Verify all gate statuses work correctly."""
    # COLLECTING
    gate = BundleBabySystem.evaluate_gate({"forward_trades": 5})
    assert gate["status"] == "COLLECTING"

    # TESTING
    gate = BundleBabySystem.evaluate_gate({
        "forward_trades": 15, "forward_win_rate": 40, "forward_sharpe": 0.3,
        "forward_max_dd": -25, "forward_realized_pnl": -5,
    })
    assert gate["status"] == "TESTING"

    # MARGINAL
    gate = BundleBabySystem.evaluate_gate({
        "forward_trades": 20, "forward_win_rate": 56, "forward_sharpe": 0.7,
        "forward_max_dd": -15, "forward_realized_pnl": 5,
    })
    assert gate["status"] == "MARGINAL"

    # PROVEN
    gate = BundleBabySystem.evaluate_gate({
        "forward_trades": 30, "forward_win_rate": 60, "forward_sharpe": 1.5,
        "forward_max_dd": -12, "forward_realized_pnl": 20,
    })
    assert gate["status"] == "PROVEN"

    # ELITE
    gate = BundleBabySystem.evaluate_gate({
        "forward_trades": 50, "forward_win_rate": 70, "forward_sharpe": 2.0,
        "forward_max_dd": -5, "forward_realized_pnl": 40,
    })
    assert gate["status"] == "ELITE"
