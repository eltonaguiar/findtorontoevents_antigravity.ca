"""NS-D ml_crypto_pred LONG-side reject tests.

Per AA-1 autopsy 2026-05-13 + 4/4 swarm consensus on Option A (hard REJECT).
Preserves SHORT side (85.7% WR) while eliminating LONG side (12% WR).
"""
import os
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def _read_gate_source() -> str:
    return (ROOT / "audit_trail" / "quality_gates.py").read_text(encoding="utf-8")


def test_ns_d_filter_present_in_source():
    """NS-D filter block lives in passes_active_gate."""
    src = _read_gate_source()
    assert "ML_CRYPTO_PRED_LONG_REJECT" in src
    assert "ns_d_ml_crypto_pred_long_reject" in src


def test_ns_d_filter_default_on():
    """NS-D env defaults to '1' (filter ON unless explicitly disabled).

    LONG side has 12% WR — must reject by default to capture the PF lift.
    """
    src = _read_gate_source()
    m = re.search(
        r'_truthy\(\s*os\.environ\.get\(\s*"ML_CRYPTO_PRED_LONG_REJECT"\s*\)\s*,\s*"(\d)"\s*\)',
        src,
    )
    assert m is not None, "expected _truthy ML_CRYPTO_PRED_LONG_REJECT read with default"
    assert m.group(1) == "1", "NS-D filter must default ON"


def test_ns_d_handles_both_source_names():
    """NS-D filter must catch both 'ml_crypto_pred' and 'ml_crypto_predictor'."""
    src = _read_gate_source()
    idx = src.find("ML_CRYPTO_PRED_LONG_REJECT")
    assert idx > 0
    after = src[idx:idx + 2000]
    assert '"ml_crypto_pred"' in after
    assert '"ml_crypto_predictor"' in after


def test_ns_d_handles_both_direction_names():
    """NS-D must catch direction=LONG AND direction=BUY."""
    src = _read_gate_source()
    idx = src.find("ML_CRYPTO_PRED_LONG_REJECT")
    after = src[idx:idx + 2000]
    assert '"LONG"' in after
    assert '"BUY"' in after


def test_ns_d_filter_placed_after_ns_c():
    """Order: NS-C (CRYPTO UTC) -> NS-D (ml_crypto_pred LONG) -> NS-E (FOREX)."""
    src = _read_gate_source()
    idx_c = src.find("CRYPTO_UTC_HOUR_FILTER")
    idx_d = src.find("ML_CRYPTO_PRED_LONG_REJECT")
    idx_e = src.find("FOREX_HARD_DISABLE")
    assert 0 < idx_c < idx_d < idx_e, (
        f"expected NS-C ({idx_c}) -> NS-D ({idx_d}) -> NS-E ({idx_e})"
    )


def test_ns_d_audit_trail_reason_set():
    """NS-D rejection sets pick['_hf_quality_gate_reason']."""
    src = _read_gate_source()
    assert src.find("ns_d_ml_crypto_pred_long_reject") > 0


def test_ns_d_preserves_short_side():
    """NS-D must NOT reject SHORT signals (which have 85.7% WR)."""
    src = _read_gate_source()
    idx = src.find("ML_CRYPTO_PRED_LONG_REJECT")
    after = src[idx:idx + 2000]
    # Must NOT match SHORT or SELL in the direction check
    direction_check = re.search(r'_dir_upper\s+in\s+\(([^)]+)\)', after)
    if direction_check:
        directions = direction_check.group(1)
        assert "SHORT" not in directions, "NS-D must NOT reject SHORT"
        assert "SELL" not in directions, "NS-D must NOT reject SELL"


def test_ns_d_behavior_long_picks_rejected():
    """Functional: ml_crypto_pred LONG should fail passes_active_gate.

    Uses environment flag default-ON to verify reject path fires.
    """
    os.environ.pop("ML_CRYPTO_PRED_LONG_REJECT", None)  # use default
    from audit_trail.quality_gates import passes_active_gate

    pick = {
        "source_system": "ml_crypto_pred",
        "direction": "LONG",
        "symbol": "BTCUSDT",
        "asset_class": "CRYPTO",
        "score": 95,
        "confidence": 0.80,
    }
    assert passes_active_gate(pick) is False
    assert pick.get("_hf_quality_gate_reason") == "ns_d_ml_crypto_pred_long_reject"


def test_ns_d_behavior_short_picks_pass():
    """Functional: ml_crypto_pred SHORT should NOT be blocked by NS-D
    (may fail other gates; just check NS-D doesn't claim it)."""
    os.environ.pop("ML_CRYPTO_PRED_LONG_REJECT", None)
    from audit_trail.quality_gates import passes_active_gate

    pick = {
        "source_system": "ml_crypto_pred",
        "direction": "SHORT",
        "symbol": "BTCUSDT",
        "asset_class": "CRYPTO",
        "score": 95,
        "confidence": 0.9,
    }
    # May still fail other gates; key: not for NS-D reason
    result = passes_active_gate(pick)
    if result is False:
        assert pick.get("_hf_quality_gate_reason") != "ns_d_ml_crypto_pred_long_reject"


def test_ns_d_behavior_opt_out():
    """Setting ML_CRYPTO_PRED_LONG_REJECT=0 disables the filter."""
    os.environ["ML_CRYPTO_PRED_LONG_REJECT"] = "0"
    try:
        from audit_trail import quality_gates
        import importlib
        importlib.reload(quality_gates)
        pick = {
            "source_system": "ml_crypto_pred",
            "direction": "LONG",
            "symbol": "BTCUSDT",
            "asset_class": "CRYPTO",
            "score": 95,
        }
        result = quality_gates.passes_active_gate(pick)
        # Could fail for other reasons; just check NS-D didn't fire
        if result is False:
            assert pick.get("_hf_quality_gate_reason") != "ns_d_ml_crypto_pred_long_reject"
    finally:
        os.environ.pop("ML_CRYPTO_PRED_LONG_REJECT", None)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
