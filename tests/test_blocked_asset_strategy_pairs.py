"""Pin the 2026-05-12 PR-C quarantine of baby_strats:crypto_soc_* draggers.

Three named draggers from
``reports/baby_strats_overfit_quarantine_proposal_2026_05_10.md``:
  crypto_soc_proxy_decoupling     decay -32.2% (severity 5.73)
  crypto_soc_delta_divergence     decay -21.6% (severity 4.93)
  crypto_soc_orderflow_absorption decay -14.8% (severity 4.76)

These are the canonical base-name pair entries. Per-strategy block applied via
``audit_trail.quality_gates.BLOCKED_ASSET_STRATEGY_PAIRS``. Surgical, not
source-system kill — fully reversible per
``docs/STRATEGY_INVESTIGATION_BEFORE_KILL.md`` Stage-5 reversal.
"""

from __future__ import annotations

import pytest

from audit_trail.quality_gates import (
    BLOCKED_ASSET_STRATEGY_PAIRS,
    passes_active_gate,
    passes_smart_gate,
)


_BASE_PAIRS = (
    ("CRYPTO", "crypto_soc_proxy_decoupling"),
    ("CRYPTO", "crypto_soc_delta_divergence"),
    ("CRYPTO", "crypto_soc_orderflow_absorption"),
)


def _baseline_crypto_pick(strategy: str) -> dict:
    """Minimal CRYPTO pick that satisfies upstream gates so that
    ``BLOCKED_ASSET_STRATEGY_PAIRS`` is the deciding factor."""
    return {
        "id": "test-pair-block",
        "symbol": "BTCUSDT",
        "asset_class": "CRYPTO",
        "strategy": strategy,
        "source_system": "baby_strats",
        "direction": "LONG",
        "status": "OPEN",
        "score": 80,
        "trust_tier": "RELIABLE",
        "wf_verdict": "PASS",
        "confidence": 0.50,
        "elite_grade": "A",
        "forward_validated": True,
        "entry_price": 100.0,
        "take_profit": 102.0,
        "stop_loss": 99.0,
        "pnl_pct": 0.0,
    }


def test_blocked_asset_strategy_pairs_constant_present_with_three_base_names():
    """All three base-name baby_strats:crypto_soc_* pairs must be enumerated."""
    for pair in _BASE_PAIRS:
        assert pair in BLOCKED_ASSET_STRATEGY_PAIRS, (
            f"missing PR-C pair {pair!r} — restore per "
            "reports/baby_strats_overfit_quarantine_proposal_2026_05_10.md"
        )


def test_passes_active_gate_rejects_crypto_soc_proxy_decoupling():
    """Active gate must reject CRYPTO + crypto_soc_proxy_decoupling."""
    pick = _baseline_crypto_pick("crypto_soc_proxy_decoupling")
    assert passes_active_gate(pick) is False


def test_passes_smart_gate_rejects_crypto_soc_delta_divergence():
    """Smart gate must reject CRYPTO + crypto_soc_delta_divergence."""
    pick = _baseline_crypto_pick("crypto_soc_delta_divergence")
    assert passes_smart_gate(pick) is False


@pytest.mark.parametrize("strategy", [p[1] for p in _BASE_PAIRS])
def test_equity_with_crypto_soc_strategy_not_in_blocklist(strategy):
    """Surgical per-(class, strategy) block: EQUITY tuples must not be present.
    This protects against accidental over-broad bans if the same strategy name
    were ever emitted on EQUITY (it isn't today; this is a regression pin)."""
    assert ("EQUITY", strategy) not in BLOCKED_ASSET_STRATEGY_PAIRS
