"""
Tests for wf_verdict=FAILING hard-block in passes_active_gate().

Background: Copilot deep-dive (copilot/deep-dive-subagents-bad-classes) and
GitHub Cloud agent independent confirmation found that picks tagged
wf_verdict=FAILING by alpha_engine/walkforward_validator.py have empirically
catastrophic realized performance:
  - n=1194 closed (smoke 2026-04-28)
  - WR=35.6%
  - PF=0.742
  - Cumulative pnl_pct=-224.8%

These picks were currently passing all active gates. The fix: block FAILING
explicitly while preserving passes for all other verdict values (STRONG,
VIABLE, MARGINAL, WEAK, DECAYING, MISSING/None).
"""

from datetime import datetime, timezone

from audit_trail.quality_gates import passes_active_gate


def _base_pick(**overrides):
    """Construct a pick that would otherwise pass all active-gate checks."""
    pick = {
        "id": "test-wf-1",
        "symbol": "BTCUSDT",
        "asset_class": "CRYPTO",
        "source_system": "pm_whale_signals",
        "strategy": "pm_whale_0xeee92f",
        "status": "OPEN",
        "direction": "LONG",
        "entry_price": 100.0,
        "take_profit": 110.0,
        "stop_loss": 95.0,
        "score": 70,
        "elite_score": None,
        "trust_score": 7,
        "trust_label": "MODERATE",
        "confidence": 0.80,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source_tier": "PROVEN",
    }
    pick.update(overrides)
    return pick


def test_failing_verdict_is_rejected():
    """A pick with wf_verdict=FAILING must NOT pass the active gate."""
    pick = _base_pick(wf_verdict="FAILING")
    assert passes_active_gate(pick) is False


def test_failing_verdict_lowercase_is_rejected():
    """Normalization: 'failing' should match the same hard-block."""
    pick = _base_pick(wf_verdict="failing")
    assert passes_active_gate(pick) is False


def test_strong_verdict_passes():
    """A pick with wf_verdict=STRONG must continue to pass (no false-rejects)."""
    pick = _base_pick(wf_verdict="STRONG")
    assert passes_active_gate(pick) is True


def test_viable_verdict_passes():
    """VIABLE picks must continue to pass."""
    pick = _base_pick(wf_verdict="VIABLE")
    assert passes_active_gate(pick) is True


def test_marginal_verdict_passes():
    """MARGINAL picks must continue to pass — only FAILING is blocked."""
    pick = _base_pick(wf_verdict="MARGINAL")
    assert passes_active_gate(pick) is True


def test_weak_verdict_passes():
    """WEAK picks must pass — gate only blocks FAILING explicitly."""
    pick = _base_pick(wf_verdict="WEAK")
    assert passes_active_gate(pick) is True


def test_missing_verdict_defaults_to_pass():
    """Missing wf_verdict (None) must NOT silently block — 15.7% of the corpus
    has no walk-forward verdict and would otherwise be false-rejected."""
    pick = _base_pick()
    pick.pop("wf_verdict", None)
    assert passes_active_gate(pick) is True


def test_empty_string_verdict_passes():
    """Empty-string wf_verdict (some emitters) must default to pass."""
    pick = _base_pick(wf_verdict="")
    assert passes_active_gate(pick) is True


def test_none_verdict_passes():
    """Explicit None wf_verdict must default to pass."""
    pick = _base_pick(wf_verdict=None)
    assert passes_active_gate(pick) is True


def test_wf_verdict_failing_block_default_enabled(monkeypatch):
    """Env unset → block defaults to ON (preserves PR's intended default-on behavior).

    Per 4/5 external-AI consensus on PR #480
    (reports/external_ai_review_pr480_wf_verdict_2026_04_28.md), the kill-switch
    env-var WF_VERDICT_FAILING_BLOCK_ENABLED defaults to "1" so unset = blocked.
    """
    monkeypatch.delenv("WF_VERDICT_FAILING_BLOCK_ENABLED", raising=False)
    pick = _base_pick(wf_verdict="FAILING")
    assert passes_active_gate(pick) is False


def test_wf_verdict_failing_block_disabled(monkeypatch):
    """Env="0" → fast rollback: FAILING pick passes the gate.

    Allows ops to disable the block within ~minutes if WR drops on the next 7
    days of fresh picks, without requiring a code change / deploy.
    """
    monkeypatch.setenv("WF_VERDICT_FAILING_BLOCK_ENABLED", "0")
    pick = _base_pick(wf_verdict="FAILING")
    assert passes_active_gate(pick) is True
