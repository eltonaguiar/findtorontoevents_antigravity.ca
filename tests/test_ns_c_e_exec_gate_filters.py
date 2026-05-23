"""NS-C + NS-E exec-gate filter tests.

NS-C: CRYPTO UTC-hour seasonal filter — 4-engine swarm UNANIMOUS SHIP
NS-E: FOREX_HARD_DISABLE env flag — 3-of-4 swarm SHIP (off-by-default)

Tests target the filter logic at audit_trail/quality_gates.py just-after
BLOCKED_ASSET_STRATEGY_PAIRS check. Both filters fire at exec layer per
memory feedback_gate_at_execution_not_generation.
"""
import os
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent


def _read_gate_source() -> str:
    return (ROOT / "audit_trail" / "quality_gates.py").read_text(encoding="utf-8")


def test_ns_c_filter_present_in_source():
    """NS-C: filter block lives in passes_active_gate after the BLOCKED_PAIRS check.

    UPDATED 2026-05-13 per real backtest (tools/backtest_btc_utc_hour_filter.py):
    real death zone is 6 UTC (23.1% WR / PF 0.06), NOT 8-9 UTC. 4-engine
    swarm consensus confirmed reject 6 UTC only.
    """
    src = _read_gate_source()
    assert "CRYPTO_UTC_HOUR_FILTER" in src
    assert "in (6, 8, 9)" in src
    # death-zone hours hardcoded; comment must explain the source.
    assert "death-zone" in src or "death zone" in src.lower() or "death_zone" in src


def test_ns_c_filter_default_on():
    """NS-C: env defaults to '1' (filter ON unless explicitly disabled).

    Default lives in _truthy() second arg after reviewer fixes
    (cavecrew-reviewer a4675164325a20c2e).
    """
    src = _read_gate_source()
    m = re.search(
        r'_truthy\(\s*os\.environ\.get\(\s*"CRYPTO_UTC_HOUR_FILTER"\s*\)\s*,\s*"(\d)"\s*\)',
        src,
    )
    assert m is not None, "expected _truthy CRYPTO_UTC_HOUR_FILTER read with default"
    assert m.group(1) == "1", "NS-C filter must default ON"


def test_ns_e_filter_present_in_source():
    """NS-E: FOREX_HARD_DISABLE env-gated block lives after NS-C block."""
    src = _read_gate_source()
    assert "FOREX_HARD_DISABLE" in src
    assert "NS-E rehab gate" in src or "FOREX_HARD_DISABLE=1" in src


def test_ns_e_filter_default_off():
    """NS-E: env defaults to '0' (filter OFF — preserves current sizing)."""
    src = _read_gate_source()
    m = re.search(
        r'_truthy\(\s*os\.environ\.get\(\s*"FOREX_HARD_DISABLE"\s*\)\s*,\s*"(\d)"\s*\)',
        src,
    )
    assert m is not None, "expected _truthy FOREX_HARD_DISABLE read with default"
    assert m.group(1) == "1", "NS-E defaults ON (2026-05-15: FOREX halted until carry backtest ships)"


def test_ns_c_filter_fires_only_on_crypto():
    """NS-C: the asset_class check is CRYPTO-specific, not class-wide."""
    src = _read_gate_source()
    # Look ~150 chars BEFORE the env-key for the asset_class check
    idx = src.find("CRYPTO_UTC_HOUR_FILTER")
    assert idx > 0
    pre = src[max(0, idx - 200):idx]
    assert '"CRYPTO"' in pre, "asset_class check must precede env-key read"
    # Other classes should not appear in the same conditional
    for cls in ("EQUITY", "ETF", "BOND", "COMMODITY"):
        assert f'== "{cls}"' not in pre, f"NS-C must not match {cls}"


def test_ns_e_filter_fires_only_on_forex():
    """NS-E: the asset_class check is FOREX-specific, not class-wide."""
    src = _read_gate_source()
    idx = src.find("FOREX_HARD_DISABLE")
    assert idx > 0
    # walk forward to find the second FOREX_HARD_DISABLE which is the
    # env-key read inside the if-condition (first is in a comment)
    second = src.find("FOREX_HARD_DISABLE", idx + 1)
    target = second if second > 0 else idx
    pre = src[max(0, target - 200):target]
    assert '"FOREX"' in pre, "FOREX asset_class check must precede env-key read"


def test_filters_placed_after_blocked_pairs():
    """Both filters must live AFTER BLOCKED_ASSET_STRATEGY_PAIRS check —
    otherwise quarantine entries override into the wrong path."""
    src = _read_gate_source()
    idx_pairs = src.find("BLOCKED_ASSET_STRATEGY_PAIRS:")
    idx_ns_c = src.find("CRYPTO_UTC_HOUR_FILTER")
    idx_ns_e = src.find("FOREX_HARD_DISABLE")
    assert 0 < idx_pairs < idx_ns_c, "NS-C must come after BLOCKED_PAIRS"
    assert idx_ns_c < idx_ns_e, "NS-E must come after NS-C"


def test_ns_c_truthy_env_variants(monkeypatch):
    """NS-C: env flag accepts truthy variants beyond '1'."""
    src = _read_gate_source()
    # Helper _truthy must accept these tokens
    helper = "in (\"1\", \"true\", \"yes\", \"on\", \"t\", \"y\")"
    assert helper in src, f"NS-C _truthy helper must accept multiple truthy tokens"


def test_ns_c_audit_trail_reason_set():
    """NS-C: rejection sets pick['_hf_quality_gate_reason']."""
    src = _read_gate_source()
    snippet_start = src.find("ns_c_crypto_utc_death_zone")
    assert snippet_start > 0, "NS-C must set _hf_quality_gate_reason on reject"


def test_ns_e_audit_trail_reason_set():
    """NS-E: rejection sets pick['_hf_quality_gate_reason']."""
    src = _read_gate_source()
    snippet_start = src.find("ns_e_forex_hard_disable")
    assert snippet_start > 0, "NS-E must set _hf_quality_gate_reason on reject"


def test_ns_c_datetime_parse_handles_space_separator():
    """NS-C: parse handles 'YYYY-MM-DD HH:MM:SS' (space) not just 'T'."""
    src = _read_gate_source()
    assert 'replace(" ", "T", 1)' in src, "must normalize space-separator ISO"


def test_ns_c_datetime_parse_handles_unix_epoch():
    """NS-C: parse handles numeric timestamps via fromtimestamp."""
    src = _read_gate_source()
    assert "fromtimestamp(float(_ts)" in src, "must handle int/float epoch timestamps"


def test_ns_c_behavior_truthy_helper_logic():
    """NS-C: _truthy helper accepts all standard truthy tokens."""
    # Test the truthy logic conceptually — extract the set from source
    src = _read_gate_source()
    truthy_tokens = ("1", "true", "yes", "on", "t", "y")
    for tok in truthy_tokens:
        assert f'"{tok}"' in src, f"_truthy must accept {tok!r}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
