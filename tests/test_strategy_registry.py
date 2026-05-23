import json
import pytest
from pathlib import Path

from strategy_registry.registry import StrategyRegistry


@pytest.fixture
def tmp_dirs(tmp_path):
    incoming = tmp_path / "incoming"
    failed = tmp_path / "failed"
    master = tmp_path / "master.json"
    incoming.mkdir()
    failed.mkdir()
    return incoming, failed, master


def test_process_valid_envelope(tmp_dirs):
    incoming, failed, master = tmp_dirs
    envelope = {
        "strategy_id": "test_001",
        "name": "Test Strategy",
        "type": "rule",
        "source_system": "alpha_engine",
        "backtest_results": {
            "tier_1": {"passed": True, "sharpe_ratio": 1.2, "win_rate": 60, "trades": 40},
        },
        "tags": {"symbol_scope": "single_symbol"},
        "generated_at": "2026-03-04T12:00:00Z",
    }
    (incoming / "test.json").write_text(json.dumps(envelope))

    reg = StrategyRegistry(incoming_dir=incoming, failed_dir=failed, master_path=master)
    processed = reg.process_all()
    assert processed == 1
    assert master.exists()

    data = json.loads(master.read_text())
    assert "test_001" in data["strategies"]
    assert not (incoming / "test.json").exists()


def test_invalid_envelope_moves_to_failed(tmp_dirs):
    incoming, failed, master = tmp_dirs
    (incoming / "bad.json").write_text('{"name": "broken"}')

    reg = StrategyRegistry(incoming_dir=incoming, failed_dir=failed, master_path=master)
    processed = reg.process_all()
    assert processed == 0
    assert (failed / "bad.json").exists()
