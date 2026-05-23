"""Regression test for issue #173 — tag-aliasing collision in
``alpha_engine/forward_validator.compute_all_strategy_stats``.

Before the fix, two picks sharing a ``strategy`` tag but emitted by
different ``source_system`` feeders were silently summed into a single
row, producing inflated winners and deflated losers that contaminated
``strategy_performance.json`` (and therefore every downstream ML scorer,
trust gate and audit dashboard reading from it).

The fix mirrors PR #171 (the analogous dashboard fix in
``audit_trail/dashboard_generator.collect_strategy_leaderboard``) and
re-keys aggregation on ``(source_system, strategy)``. Backward compat
is preserved by keeping the top-level dict keyed on bare strategy name
(carrying a merged aggregate for legacy callers like ``auto_tuner``)
and stashing the collision-safe per-system breakdown under a
``by_source_system`` subkey on each entry.

This test:
  1. Feeds two synthetic closed picks — same strategy tag, different
     source_system, opposite PnL.
  2. Asserts the by-name row still exists (legacy shape).
  3. Asserts the per-(sys, strat) rows exist in ``by_source_system``
     with independent metrics — proving the collision no longer
     collapses them into one entry.

Related:
  - Issue #173
  - PR #171 (dashboard fix, same pattern)
  - PR #160 (forensic: fear_greed_contrarian / claude_gainer_st tag collision)
"""
from __future__ import annotations

from alpha_engine.forward_validator import compute_all_strategy_stats


def _make_pick(source_system: str, strategy: str, pnl_pct: float, symbol: str = "BTCUSDT") -> dict:
    return {
        "symbol": symbol,
        "strategy": strategy,
        "source_system": source_system,
        "pnl_pct": pnl_pct,
        "exit_reason": "TP_HIT" if pnl_pct > 0 else "SL_HIT",
        "hold_days": 1,
        "mfe": max(pnl_pct, 0.0),
        "mae": min(pnl_pct, 0.0),
    }


def test_collision_two_source_systems_same_strategy_tag():
    """Two picks, same strategy tag, different source_system, opposite PnL.

    The collision-safe aggregation must report independent per-system
    metrics so that a winning feeder's numbers never cross-contaminate
    a losing feeder's numbers (or vice versa).
    """
    closed = [
        _make_pick("SYS_A", "shared_tag", +1.0),
        _make_pick("SYS_B", "shared_tag", -1.0),
    ]

    perf = compute_all_strategy_stats(closed)

    # The by-name (legacy) row still exists — one entry, merged aggregate.
    assert "shared_tag" in perf, (
        "Legacy by-name row missing — this would break every consumer that "
        "looks up strategies by bare name (ml_strategy_reviver, auto_tuner, etc.)"
    )
    legacy = perf["shared_tag"]
    assert legacy["closed_picks"] == 2

    # The collision-safe per-(source_system, strategy) rows must exist.
    assert "by_source_system" in legacy, (
        "Fix for issue #173 not applied — ``by_source_system`` subkey is "
        "missing. compute_all_strategy_stats is still aggregating on bare "
        "strategy name and will silently sum two feeder systems together."
    )
    by_sys = legacy["by_source_system"]
    assert set(by_sys.keys()) == {"SYS_A", "SYS_B"}, (
        f"Expected independent rows for SYS_A and SYS_B, got: {sorted(by_sys.keys())}"
    )

    # SYS_A had the winning pick; SYS_B had the losing pick.
    sys_a = by_sys["SYS_A"]
    sys_b = by_sys["SYS_B"]
    assert sys_a["closed_picks"] == 1
    assert sys_a["wins"] == 1
    assert sys_a["losses"] == 0
    assert sys_b["closed_picks"] == 1
    assert sys_b["wins"] == 0
    assert sys_b["losses"] == 1
    # Opposite PnL proves no cross-contamination.
    assert sys_a["total_pnl_pct"] > 0
    assert sys_b["total_pnl_pct"] < 0


def test_single_source_system_backward_compat():
    """A strategy emitted by a single feeder still produces a legacy
    by-name row with identical numbers, and the ``by_source_system``
    subkey has a single entry that matches the by-name row exactly.
    """
    closed = [
        _make_pick("SYS_A", "solo_tag", +2.0),
        _make_pick("SYS_A", "solo_tag", -1.0),
    ]

    perf = compute_all_strategy_stats(closed)

    assert "solo_tag" in perf
    row = perf["solo_tag"]
    assert row["closed_picks"] == 2
    assert row["wins"] == 1
    assert row["losses"] == 1

    # Collision-safe subkey still emitted for the single feeder.
    assert "by_source_system" in row
    assert list(row["by_source_system"].keys()) == ["SYS_A"]
    solo = row["by_source_system"]["SYS_A"]
    assert solo["closed_picks"] == 2
    assert solo["wins"] == 1
    assert solo["losses"] == 1
