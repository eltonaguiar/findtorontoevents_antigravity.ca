"""Tests for M-046: Pick payload schema validator (tools/validation/validate_pick_schema.py).

Verifies:
1. Valid pick passes all checks
2. Missing required field flagged
3. score out of range flagged
4. confidence out of range flagged
5. Invalid asset_class flagged
6. Invalid direction flagged
7. entry_price = 0 flagged
8. Multiple violations returned in one call
"""
import json
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from tools.validation.validate_pick_schema import _validate_pick, validate_file


def _valid_pick(**overrides):
    base = {
        "symbol": "BTCUSDT",
        "asset_class": "CRYPTO",
        "source_system": "quan_engine",
        "strategy": "test_strategy",
        "score": 75,
        "confidence": 0.85,
        "status": "OPEN",
        "direction": "LONG",
        "entry_price": 50000.0,
        "take_profit": 55000.0,
        "stop_loss": 48000.0,
        "timestamp": "2026-05-17T00:00:00Z",
    }
    base.update(overrides)
    return base


def test_valid_pick_no_violations():
    """A fully valid pick must produce zero violations."""
    violations = _validate_pick(_valid_pick(), 0)
    assert violations == [], f"Unexpected violations: {violations}"


def test_missing_required_field():
    """A pick missing 'strategy' must be flagged."""
    pick = _valid_pick()
    del pick["strategy"]
    violations = _validate_pick(pick, 0)
    assert any("strategy" in v for v in violations)


def test_score_out_of_range_high():
    """score > 100 must be flagged."""
    violations = _validate_pick(_valid_pick(score=150), 0)
    assert any("score" in v for v in violations)


def test_score_out_of_range_low():
    """score < 0 must be flagged."""
    violations = _validate_pick(_valid_pick(score=-1), 0)
    assert any("score" in v for v in violations)


def test_confidence_out_of_range():
    """confidence > 1.0 must be flagged."""
    violations = _validate_pick(_valid_pick(confidence=1.5), 0)
    assert any("confidence" in v for v in violations)


def test_invalid_asset_class():
    """Unknown asset_class must be flagged."""
    violations = _validate_pick(_valid_pick(asset_class="MEME"), 0)
    assert any("asset_class" in v for v in violations)


def test_invalid_direction():
    """Direction other than LONG/SHORT must be flagged."""
    violations = _validate_pick(_valid_pick(direction="SIDEWAYS"), 0)
    assert any("direction" in v for v in violations)


def test_entry_price_zero():
    """entry_price of 0 must be flagged."""
    violations = _validate_pick(_valid_pick(entry_price=0.0), 0)
    assert any("entry_price" in v for v in violations)


def test_multiple_violations():
    """Multiple problems in one pick must return multiple violation strings."""
    pick = _valid_pick(score=200, asset_class="INVALID", direction="NOPE")
    violations = _validate_pick(pick, 0)
    assert len(violations) >= 3


def test_validate_file_clean(tmp_path):
    """validate_file on a file of valid picks must return (n, 0)."""
    picks = [_valid_pick(symbol=f"PICK{i}") for i in range(3)]
    p = tmp_path / "picks.json"
    p.write_text(json.dumps(picks), encoding="utf-8")
    passed, failed = validate_file(str(p))
    assert passed == 3
    assert failed == 0


def test_validate_file_with_violations(tmp_path):
    """validate_file on a file with one bad pick must return (n-1, 1)."""
    picks = [_valid_pick(symbol="GOOD"), _valid_pick(symbol="BAD", score=999)]
    p = tmp_path / "picks.json"
    p.write_text(json.dumps(picks), encoding="utf-8")
    passed, failed = validate_file(str(p))
    assert passed == 1
    assert failed == 1
