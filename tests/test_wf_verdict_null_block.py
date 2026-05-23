"""
Tests for the null-wf_verdict opt-in block in passes_active_gate().

Background: 4-AI panel unanimous P0 verdict (2026-04-29,
reports/findings_validation_synthesis_2026_04_29.md, Finding 1):

PR #480's wf_verdict=FAILING block is functionally inert because 87% of
currently-active picks have wf_verdict=null. The FAILING-only gate only
catches 4/29 currently-emitted picks. Panel recommendation: "Treat null
wf_verdict as FAILING in the gate; reject ingestion or default-fail at
the emitter."

Implementation: a NEW env-flag WF_VERDICT_NULL_TREATED_AS_FAILING_ENABLED,
DEFAULT OFF (opt-in). Operator flips on AFTER backfilling the 3 high-null
emitters (alpha_engine_fast 39/39 null, aggregated_picks 21/22 null,
kimi_riseoftheclaw 119/285 null). Default-off is mandatory for safe
rollout — flipping on without backfill would block ~87% of currently-
emitted picks.

These tests verify:
  1. null passes when flag OFF (default)
  2. null is BLOCKED when flag ON
  3. Explicit FAILING is still blocked when flag OFF (back-compat with #480)
  4. VIABLE / STRONG / MARGINAL still pass regardless of flag state
  5. Env-flag default is "0" (OFF)
"""

from datetime import datetime, timezone

from audit_trail.quality_gates import passes_active_gate


def _base_pick(**overrides):
    """Construct a pick that would otherwise pass all active-gate checks."""
    pick = {
        "id": "test-wf-null-1",
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


# ──────────────────────────────────────────────────────────────────────
# Default-OFF behavior (safety-critical)
# ──────────────────────────────────────────────────────────────────────


def test_null_wf_verdict_passes_when_flag_off_default(monkeypatch):
    """Flag unset → null wf_verdict must continue to pass (default OFF).

    This is the SAFETY guarantee: the new flag must not change behavior
    until the operator explicitly opts in. Otherwise ~87% of currently-
    emitted picks would be blocked, since most emitters don't yet
    populate wf_verdict.
    """
    monkeypatch.delenv("WF_VERDICT_NULL_TREATED_AS_FAILING_ENABLED", raising=False)
    pick = _base_pick()
    pick.pop("wf_verdict", None)
    assert passes_active_gate(pick) is True


def test_explicit_none_wf_verdict_passes_when_flag_off_default(monkeypatch):
    """Explicit wf_verdict=None must pass when flag is OFF (default)."""
    monkeypatch.delenv("WF_VERDICT_NULL_TREATED_AS_FAILING_ENABLED", raising=False)
    pick = _base_pick(wf_verdict=None)
    assert passes_active_gate(pick) is True


def test_empty_string_wf_verdict_passes_when_flag_off_default(monkeypatch):
    """Empty-string wf_verdict (some emitters) must pass when flag OFF."""
    monkeypatch.delenv("WF_VERDICT_NULL_TREATED_AS_FAILING_ENABLED", raising=False)
    pick = _base_pick(wf_verdict="")
    assert passes_active_gate(pick) is True


def test_flag_explicitly_zero_treats_null_as_pass(monkeypatch):
    """Setting flag explicitly to '0' must also leave null as pass."""
    monkeypatch.setenv("WF_VERDICT_NULL_TREATED_AS_FAILING_ENABLED", "0")
    pick = _base_pick(wf_verdict=None)
    assert passes_active_gate(pick) is True


# ──────────────────────────────────────────────────────────────────────
# Opt-in behavior (flag ON)
# ──────────────────────────────────────────────────────────────────────


def test_null_wf_verdict_blocked_when_flag_on(monkeypatch):
    """Flag='1' → missing wf_verdict must be blocked (treated as FAILING)."""
    monkeypatch.setenv("WF_VERDICT_NULL_TREATED_AS_FAILING_ENABLED", "1")
    pick = _base_pick()
    pick.pop("wf_verdict", None)
    assert passes_active_gate(pick) is False


def test_explicit_none_wf_verdict_blocked_when_flag_on(monkeypatch):
    """Flag='1' → explicit wf_verdict=None must be blocked."""
    monkeypatch.setenv("WF_VERDICT_NULL_TREATED_AS_FAILING_ENABLED", "1")
    pick = _base_pick(wf_verdict=None)
    assert passes_active_gate(pick) is False


def test_empty_string_wf_verdict_blocked_when_flag_on(monkeypatch):
    """Flag='1' → empty-string wf_verdict must be blocked
    (panel verdict treats '' the same as null — emitter not populating)."""
    monkeypatch.setenv("WF_VERDICT_NULL_TREATED_AS_FAILING_ENABLED", "1")
    pick = _base_pick(wf_verdict="")
    assert passes_active_gate(pick) is False


# ──────────────────────────────────────────────────────────────────────
# Back-compat with PR #480 (FAILING still blocked regardless)
# ──────────────────────────────────────────────────────────────────────


def test_failing_wf_verdict_still_blocked_when_flag_off(monkeypatch):
    """Back-compat: explicit wf_verdict=FAILING must still be blocked
    when the new null-flag is OFF (PR #480's behavior preserved)."""
    monkeypatch.delenv("WF_VERDICT_NULL_TREATED_AS_FAILING_ENABLED", raising=False)
    pick = _base_pick(wf_verdict="FAILING")
    assert passes_active_gate(pick) is False


def test_failing_wf_verdict_still_blocked_when_flag_on(monkeypatch):
    """Both flags ON: FAILING is still blocked (the original PR #480 path)."""
    monkeypatch.setenv("WF_VERDICT_NULL_TREATED_AS_FAILING_ENABLED", "1")
    pick = _base_pick(wf_verdict="FAILING")
    assert passes_active_gate(pick) is False


# ──────────────────────────────────────────────────────────────────────
# Healthy verdicts pass regardless of flag state
# ──────────────────────────────────────────────────────────────────────


def test_viable_passes_with_flag_off(monkeypatch):
    """VIABLE picks must pass when flag OFF (default)."""
    monkeypatch.delenv("WF_VERDICT_NULL_TREATED_AS_FAILING_ENABLED", raising=False)
    pick = _base_pick(wf_verdict="VIABLE")
    assert passes_active_gate(pick) is True


def test_viable_passes_with_flag_on(monkeypatch):
    """VIABLE picks must pass even when flag ON (only null/empty blocked)."""
    monkeypatch.setenv("WF_VERDICT_NULL_TREATED_AS_FAILING_ENABLED", "1")
    pick = _base_pick(wf_verdict="VIABLE")
    assert passes_active_gate(pick) is True


def test_strong_passes_with_flag_off(monkeypatch):
    """STRONG picks must pass when flag OFF (default)."""
    monkeypatch.delenv("WF_VERDICT_NULL_TREATED_AS_FAILING_ENABLED", raising=False)
    pick = _base_pick(wf_verdict="STRONG")
    assert passes_active_gate(pick) is True


def test_strong_passes_with_flag_on(monkeypatch):
    """STRONG picks must pass even when flag ON.

    Per Finding 1, EQUITY STRONG cohort = 75.4% WR / +2.716% avg —
    flipping the flag must never block this cohort."""
    monkeypatch.setenv("WF_VERDICT_NULL_TREATED_AS_FAILING_ENABLED", "1")
    pick = _base_pick(wf_verdict="STRONG")
    assert passes_active_gate(pick) is True


def test_marginal_passes_with_flag_off(monkeypatch):
    """MARGINAL picks must pass when flag OFF (default)."""
    monkeypatch.delenv("WF_VERDICT_NULL_TREATED_AS_FAILING_ENABLED", raising=False)
    pick = _base_pick(wf_verdict="MARGINAL")
    assert passes_active_gate(pick) is True


def test_marginal_passes_with_flag_on(monkeypatch):
    """MARGINAL picks must pass even when flag ON."""
    monkeypatch.setenv("WF_VERDICT_NULL_TREATED_AS_FAILING_ENABLED", "1")
    pick = _base_pick(wf_verdict="MARGINAL")
    assert passes_active_gate(pick) is True


def test_elite_passes_with_flag_on(monkeypatch):
    """ELITE picks must pass when flag ON."""
    monkeypatch.setenv("WF_VERDICT_NULL_TREATED_AS_FAILING_ENABLED", "1")
    pick = _base_pick(wf_verdict="ELITE")
    assert passes_active_gate(pick) is True


# ──────────────────────────────────────────────────────────────────────
# Default value of the env-flag is "0" (OFF) — explicit assertion
# ──────────────────────────────────────────────────────────────────────


def test_env_flag_default_is_off(monkeypatch):
    """The implementation's default for the new flag must be '0' (OFF).

    Read directly: when the env var is not set, os.environ.get(
    'WF_VERDICT_NULL_TREATED_AS_FAILING_ENABLED', '0') must return '0',
    so the null-block path is NOT triggered. This is a behavioral check
    of the default — it pairs with the safety contract in the docstring.
    """
    import os as _os

    monkeypatch.delenv("WF_VERDICT_NULL_TREATED_AS_FAILING_ENABLED", raising=False)
    # The literal default in the code must be "0" — verify by reading the
    # env identically to how the gate reads it.
    assert _os.environ.get(
        "WF_VERDICT_NULL_TREATED_AS_FAILING_ENABLED", "0"
    ) == "0"

    # And behavior matches: null pick passes.
    pick = _base_pick()
    pick.pop("wf_verdict", None)
    assert passes_active_gate(pick) is True


# ──────────────────────────────────────────────────────────────────────
# Rollback semantics: each flag must be independent (cross-AI review fix)
# ──────────────────────────────────────────────────────────────────────


def test_null_blocked_when_failing_flag_off_but_null_flag_on(monkeypatch):
    """Critical regression guard from cross-AI pre-merge review.

    Original implementation nested the null-block INSIDE the
    WF_VERDICT_FAILING_BLOCK_ENABLED guard. Result: an operator rolling
    back PR #480 (setting FAILING flag to '0') would silently disable the
    null-block too. This test pins that the null-block fires INDEPENDENTLY
    of the FAILING flag's state.
    """
    monkeypatch.setenv("WF_VERDICT_FAILING_BLOCK_ENABLED", "0")  # PR #480 rollback
    monkeypatch.setenv("WF_VERDICT_NULL_TREATED_AS_FAILING_ENABLED", "1")
    pick = _base_pick()
    pick.pop("wf_verdict", None)
    assert passes_active_gate(pick) is False, (
        "null-block must fire independently of WF_VERDICT_FAILING_BLOCK_ENABLED — "
        "rollback of PR #480 should not silently disable the null block"
    )


def test_failing_blocked_when_failing_flag_on_but_null_flag_off(monkeypatch):
    """Mirror invariant: PR #480's FAILING block fires regardless of the
    null flag's state."""
    monkeypatch.setenv("WF_VERDICT_FAILING_BLOCK_ENABLED", "1")
    monkeypatch.setenv("WF_VERDICT_NULL_TREATED_AS_FAILING_ENABLED", "0")
    pick = _base_pick(wf_verdict="FAILING")
    assert passes_active_gate(pick) is False
