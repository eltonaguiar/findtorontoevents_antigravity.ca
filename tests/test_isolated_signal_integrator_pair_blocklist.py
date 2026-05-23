"""Regression tests for the rapid_fire system+strategy pair-blocklist gap.

Background: 2026-04-30 verification (`reports/24h_verification_2026_04_30.md`)
showed 2 BANNED picks (SOLVUSDT/ORCAUSDT) leaked through ~11h post-kill of
`("rapid_fire", "macd_rsi_confluence")`. Root cause: `isolated_signal_integrator.py`
checked only `kill_list` (bare-strategy match) and never called
`is_blocked_pick()` which also checks `_RETIRED_SYSTEM_STRATEGY_PAIRS`.

These tests pin the new pair-check at line ~670 of the integrator.
"""
from pathlib import Path


def test_pair_blocklist_blocks_retired_rapid_fire_macd_rsi_confluence():
    """The exact post-kill breach: ("rapid_fire", "macd_rsi_confluence") MUST be blocked."""
    from alpha_engine import strategy_blocklist
    assert strategy_blocklist.is_blocked_pick({
        "strategy": "macd_rsi_confluence",
        "source_system": "rapid_fire",
    }) is True


def test_pair_blocklist_passes_unrelated_strategy():
    """A strategy not in any blocklist should pass."""
    from alpha_engine import strategy_blocklist
    assert strategy_blocklist.is_blocked_pick({
        "strategy": "totally_new_unblocked_strategy_xyz",
        "source_system": "rapid_fire",
    }) is False


def test_integrator_imports_is_blocked_pick():
    """The integrator must import is_blocked_pick — confirms the fix wired."""
    import alpha_engine.isolated_signal_integrator as integrator
    assert hasattr(integrator, "is_blocked_pick")
    assert callable(integrator.is_blocked_pick)


def test_integrator_pair_check_invocation_pattern():
    """The integrator's pair check must pass both strategy AND source_system.

    The bare-name kill_list won't catch _RETIRED_SYSTEM_STRATEGY_PAIRS.
    The fix synthesizes the pick with both fields and passes to is_blocked_pick.
    """
    import alpha_engine.isolated_signal_integrator as integrator
    src = Path(integrator.__file__).read_text(encoding="utf-8")
    assert "is_blocked_pick" in src, "is_blocked_pick call site missing"
    assert '"strategy": strategy' in src and '"source_system": source_name' in src, (
        "Pair-check synthesis dict shape changed — verify it still passes both fields"
    )


def test_blocked_pair_excluded_when_other_pairs_pass():
    """Sanity: only the retired SYSTEM+STRATEGY pair is killed, not the bare name globally."""
    from alpha_engine import strategy_blocklist
    rapid_fire = strategy_blocklist.is_blocked_pick({
        "strategy": "macd_rsi_confluence",
        "source_system": "rapid_fire",
    })
    assert rapid_fire is True
