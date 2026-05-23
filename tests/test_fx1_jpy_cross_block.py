"""FX1 JPY-cross block tests for multi_asset_copytrader.

Per AA-7 mutation analysis 2026-05-13: 5 JPY-cross pairs on
multi_asset_copytrader showed catastrophic WR (1.9%-10.8%) on n=484 terminal
picks. 4-engine swarm consensus 2026-05-13 confirmed surgical block.

Tests verify:
- All 5 JPY-cross pairs in BLOCKED_ASSET_STRATEGY_SYMBOL_TRIPLES
- Non-JPY majors (EURGBP/GBPUSD/AUDUSD/USDCHF) are NOT blocked
- Block is in passes_active_gate path
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from audit_trail.quality_gates import BLOCKED_ASSET_STRATEGY_SYMBOL_TRIPLES


JPY_CROSSES_BLOCKED = {
    ("FOREX", "multi_asset_copytrader", "EURJPY=X"),
    ("FOREX", "multi_asset_copytrader", "USDJPY=X"),
    ("FOREX", "multi_asset_copytrader", "GBPJPY=X"),
    ("FOREX", "multi_asset_copytrader", "AUDJPY=X"),
    ("FOREX", "multi_asset_copytrader", "CADJPY=X"),
}

NON_JPY_MAJORS_KEPT = {
    ("FOREX", "multi_asset_copytrader", "EURGBP=X"),
    ("FOREX", "multi_asset_copytrader", "GBPUSD=X"),
    ("FOREX", "multi_asset_copytrader", "AUDUSD=X"),
    ("FOREX", "multi_asset_copytrader", "USDCHF=X"),
}


def test_all_5_jpy_crosses_blocked():
    for triple in JPY_CROSSES_BLOCKED:
        assert triple in BLOCKED_ASSET_STRATEGY_SYMBOL_TRIPLES, (
            f"FX1 surgical block missing: {triple}"
        )


def test_non_jpy_majors_not_blocked():
    for triple in NON_JPY_MAJORS_KEPT:
        assert triple not in BLOCKED_ASSET_STRATEGY_SYMBOL_TRIPLES, (
            f"FX1 must preserve non-JPY-major edge: {triple} should NOT be blocked"
        )


def test_fx1_block_total_count():
    forex_blocks = [t for t in BLOCKED_ASSET_STRATEGY_SYMBOL_TRIPLES if t[0] == "FOREX"]
    assert len(forex_blocks) >= 5, (
        f"Expected at least 5 FOREX triples (JPY-crosses), got {len(forex_blocks)}"
    )


def test_passes_active_gate_uses_triples():
    """passes_active_gate must reference BLOCKED_ASSET_STRATEGY_SYMBOL_TRIPLES."""
    src = (ROOT / "audit_trail" / "quality_gates.py").read_text(encoding="utf-8")
    assert "BLOCKED_ASSET_STRATEGY_SYMBOL_TRIPLES" in src
    idx_def = src.find("BLOCKED_ASSET_STRATEGY_SYMBOL_TRIPLES = {")
    idx_use_in_gate = src.find("(asset_class, strategy, _ghost_sym) in BLOCKED_ASSET_STRATEGY_SYMBOL_TRIPLES")
    assert 0 < idx_def < idx_use_in_gate, (
        "expected struct definition before consumer in passes_active_gate"
    )


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
