"""Tests for alpha_engine/matrix_symbol_gates.py and sandbox relabels."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

# Ensure repo root on path for alpha_engine
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def test_matrix_block(monkeypatch, tmp_path):
    monkeypatch.setenv("MATRIX_SYMBOL_GATES", "1")
    import alpha_engine.matrix_symbol_gates as msg

    msg.reload_matrix_symbol_gates()
    fake = {
        "block": {"quan_engine": ["BADUSDT"]},
        "allow": {},
    }
    gate_path = tmp_path / "matrix_symbol_gates.json"
    gate_path.write_text(json.dumps(fake), encoding="utf-8")
    monkeypatch.setattr(msg, "_DEFAULT_PATH", gate_path)
    msg.reload_matrix_symbol_gates()

    from alpha_engine.matrix_symbol_gates import matrix_symbol_gate_blocks

    blocked, _ = matrix_symbol_gate_blocks(
        {"source_system": "quan_engine", "symbol": "BADUSDT"}
    )
    assert blocked is True
    ok, _ = matrix_symbol_gate_blocks(
        {"source_system": "quan_engine", "symbol": "GOODUSDT"}
    )
    assert ok is False


def test_matrix_allow_only(monkeypatch, tmp_path):
    monkeypatch.setenv("MATRIX_SYMBOL_GATES", "1")
    import alpha_engine.matrix_symbol_gates as msg

    msg.reload_matrix_symbol_gates()
    fake = {"block": {}, "allow": {"rapid_fire": ["ONLYUSDT"]}}
    gate_path = tmp_path / "matrix_symbol_gates.json"
    gate_path.write_text(json.dumps(fake), encoding="utf-8")
    monkeypatch.setattr(msg, "_DEFAULT_PATH", gate_path)
    msg.reload_matrix_symbol_gates()

    from alpha_engine.matrix_symbol_gates import matrix_symbol_gate_blocks

    blocked, _ = matrix_symbol_gate_blocks(
        {"source_system": "rapid_fire", "symbol": "OTHERUSDT"}
    )
    assert blocked is True


def test_m003_multi_asset_cot_allow_includes_metals():
    """M-003 COMMODITY diversification: multi_asset_cot allow-list must include
    HG=F (copper) and PL=F (platinum) so COT positioning picks for kept metals
    can pass through the matrix gate and dilute CT=F concentration below 40% cap.
    ZW=F (wheat) remains on the block-list and is never in allow."""
    import json
    from pathlib import Path

    gates_path = Path(__file__).resolve().parents[1] / "alpha_engine" / "data" / "matrix_symbol_gates.json"
    data = json.loads(gates_path.read_text(encoding="utf-8"))
    allow = data.get("allow", {}).get("multi_asset_cot", [])
    block = data.get("block", {}).get("multi_asset_cot", [])
    assert "HG=F" in allow, "M-003: HG=F must be in multi_asset_cot allow-list"
    assert "PL=F" in allow, "M-003: PL=F must be in multi_asset_cot allow-list"
    assert "CT=F" in allow, "CT=F must remain in multi_asset_cot allow-list"
    assert "ZW=F" not in allow, "ZW=F must NOT be in allow-list (it is in block)"
    assert "ZW=F" in block, "ZW=F must remain blocked for multi_asset_cot"


def test_sandbox_relabel_curated(monkeypatch, tmp_path):
    monkeypatch.setenv("SANDBOX_MUTATION_EXPERIMENTS", "1")
    import alpha_engine.sandbox_mutation_experiments as sb

    cfg = {
        "experiments": [
            {
                "id": "claude_gainer_st_curated",
                "parent_strategies": ["claude_gainer_st"],
                "allowed_symbols": ["BTCUSDT"],
                "trust_tier": "SANDBOX",
            }
        ]
    }
    p = tmp_path / "sandbox_mutation_experiments.json"
    p.write_text(json.dumps(cfg), encoding="utf-8")
    monkeypatch.setattr(sb, "_CONFIG_PATH", p)
    sb.reload_sandbox_mutation_experiments()

    pick = {
        "strategy": "claude_gainer_st",
        "symbol": "BTCUSDT",
        "direction": "LONG",
        "source_system": "claude_gainer_st",
        "trade_timeframe": "INTRADAY",
    }
    sb.apply_sandbox_experiment_relabels(pick)
    assert pick["strategy"] == "claude_gainer_st_curated"
    assert pick["trust_tier"] == "SANDBOX"
