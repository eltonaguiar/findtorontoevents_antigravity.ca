"""NS-F BTC bear-regime LONG-reject tests.

Per CRYPTO swarm 2026-05-13 (Edge #11): reject CRYPTO LONG picks when BTC
4h regime is bearish. 3/4-engine consensus on universal pattern.
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


def test_ns_f_filter_present_in_source():
    src = _read_gate_source()
    assert "BTC_BEAR_LONG_REJECT" in src
    assert "ns_f_btc_bear_long_reject" in src


def test_ns_f_filter_default_on():
    src = _read_gate_source()
    m = re.search(
        r'_truthy\(\s*os\.environ\.get\(\s*"BTC_BEAR_LONG_REJECT"\s*\)\s*,\s*"(\d)"\s*\)',
        src,
    )
    assert m is not None
    assert m.group(1) == "1", "NS-F must default ON"


def test_ns_f_only_fires_on_crypto():
    src = _read_gate_source()
    idx = src.find("BTC_BEAR_LONG_REJECT")
    pre = src[max(0, idx - 200):idx]
    assert '"CRYPTO"' in pre


def test_ns_f_preserves_short_signals():
    src = _read_gate_source()
    idx = src.find("BTC_BEAR_LONG_REJECT")
    after = src[idx:idx + 2000]
    direction_check = re.search(r'_dir_f\s+in\s+\(([^)]+)\)', after)
    if direction_check:
        directions = direction_check.group(1)
        assert "SHORT" not in directions
        assert "SELL" not in directions


def test_ns_f_bear_detection_multi_variant():
    """BEAR / DOWN / BEARISH variants all caught."""
    src = _read_gate_source()
    idx = src.find("BTC_BEAR_LONG_REJECT")
    after = src[idx:idx + 2000]
    assert '"BEAR"' in after
    assert '"DOWN"' in after
    assert '"BEARISH"' in after


def test_ns_f_filter_placed_after_ns_d():
    src = _read_gate_source()
    idx_d = src.find("ML_CRYPTO_PRED_LONG_REJECT")
    idx_f = src.find("BTC_BEAR_LONG_REJECT")
    idx_e = src.find("FOREX_HARD_DISABLE")
    assert 0 < idx_d < idx_f < idx_e


def test_ns_f_behavior_long_in_bear_rejected():
    os.environ.pop("BTC_BEAR_LONG_REJECT", None)
    import importlib
    from audit_trail import quality_gates
    importlib.reload(quality_gates)

    pick = {
        "source_system": "luxalgo_confluence",
        "direction": "LONG",
        "symbol": "BTCUSDT",
        "asset_class": "CRYPTO",
        "btc_regime": "BEARISH",
        "score": 95,
    }
    assert quality_gates.passes_active_gate(pick) is False
    assert pick.get("_hf_quality_gate_reason") == "ns_f_btc_bear_long_reject"


def test_ns_f_behavior_short_in_bear_not_blocked_by_nsf():
    os.environ.pop("BTC_BEAR_LONG_REJECT", None)
    import importlib
    from audit_trail import quality_gates
    importlib.reload(quality_gates)

    pick = {
        "source_system": "luxalgo_confluence",
        "direction": "SHORT",
        "symbol": "BTCUSDT",
        "asset_class": "CRYPTO",
        "btc_regime": "BEARISH",
        "score": 95,
    }
    result = quality_gates.passes_active_gate(pick)
    if result is False:
        # If rejected, MUST be for a different reason — not NS-F
        assert pick.get("_hf_quality_gate_reason") != "ns_f_btc_bear_long_reject"


def test_ns_f_behavior_long_in_bull_not_blocked():
    os.environ.pop("BTC_BEAR_LONG_REJECT", None)
    import importlib
    from audit_trail import quality_gates
    importlib.reload(quality_gates)

    pick = {
        "source_system": "luxalgo_confluence",
        "direction": "LONG",
        "symbol": "BTCUSDT",
        "asset_class": "CRYPTO",
        "btc_regime": "BULLISH",
        "score": 95,
    }
    result = quality_gates.passes_active_gate(pick)
    if result is False:
        assert pick.get("_hf_quality_gate_reason") != "ns_f_btc_bear_long_reject"


def test_ns_f_behavior_equity_long_unaffected():
    """NS-F is CRYPTO-only; EQUITY LONG in bear regime must NOT be touched."""
    os.environ.pop("BTC_BEAR_LONG_REJECT", None)
    import importlib
    from audit_trail import quality_gates
    importlib.reload(quality_gates)

    pick = {
        "source_system": "value_screener",
        "direction": "LONG",
        "symbol": "AAPL",
        "asset_class": "EQUITY",
        "btc_regime": "BEARISH",
        "score": 95,
    }
    result = quality_gates.passes_active_gate(pick)
    if result is False:
        assert pick.get("_hf_quality_gate_reason") != "ns_f_btc_bear_long_reject"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
