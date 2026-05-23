"""Regression test for dashboard aggregation collision (Agent F, PR follow-up to #160).

See ``docs/forensics/fear_greed_contrarian_collapse_2026-04-13.md``:
the ``st_fear_greed_contrarian`` "80.9% WR / 584 wins" figure in the dashboard
was NOT produced by the real paper-trading strategy — it was ``claude_gainer_st``
picks sharing the same ``strategy`` tag, aggregated in
``collect_strategy_leaderboard`` under that one key.

Root cause: aggregation was keyed on ``strategy`` alone. Two feeder systems
emitting picks with the same strategy name collapsed into one leaderboard row,
cross-contaminating WR / PnL / PF / wins.

Fix: re-key the aggregation on ``(source_system, strategy)`` tuple so each
feeder system's performance is reported separately.

This test builds a synthetic ledger with two picks sharing ``strategy="X"``
but different ``source_system`` values, runs ``collect_strategy_leaderboard``,
and asserts the two systems are NOT summed under one row.
"""

from __future__ import annotations

from audit_trail import dashboard_generator


def _mk_pick(symbol: str, strategy: str, source_system: str, pnl_pct: float) -> dict:
    return {
        "id": f"{source_system}::{symbol}::{strategy}",
        "symbol": symbol,
        "strategy": strategy,
        "source_system": source_system,
        "direction": "LONG",
        "entry_price": 100.0,
        "exit_price": 100.0 * (1.0 + pnl_pct / 100.0),
        "pnl_pct": pnl_pct,
        "status": "CLOSED",
        "outcome": "WON" if pnl_pct > 0 else "LOST",
        "timestamp": "2026-04-13T00:00:00Z",
        "closed_at": "2026-04-13T01:00:00Z",
        "asset_class": "CRYPTO",
        "confidence": 0.65,
    }


def test_leaderboard_does_not_collide_same_strategy_across_source_systems() -> None:
    """Two systems emitting the same strategy tag must not be summed together.

    Pick A: SYS_A / X / +1.0% (win)
    Pick B: SYS_B / X / -1.0% (loss)

    Before fix: one leaderboard row "X" with fwd_trades=2, fwd_wins=1,
                fwd_losses=1, fwd_wr=50.0, fwd_total_pnl=0.0 — wrong, the
                real "X" under SYS_A is 100% WR while under SYS_B it's 0%.
    After fix:  two rows, one per ``(source_system, strategy)`` tuple, each
                reporting its own metrics.
    """
    pick_a = _mk_pick("AAAUSDT", "X", "SYS_A", +1.0)
    pick_b = _mk_pick("BBBUSDT", "X", "SYS_B", -1.0)

    # collect_strategy_leaderboard(active, closed)
    leaderboard = dashboard_generator.collect_strategy_leaderboard([], [pick_a, pick_b])

    # Find all rows tagged strategy "X"
    x_rows = [r for r in leaderboard if r.get("strategy") == "X"]

    assert len(x_rows) >= 2, (
        f"Expected at least 2 leaderboard rows for strategy 'X' (one per source_system); "
        f"got {len(x_rows)}. Rows: {x_rows}"
    )

    # Partition by source_system
    by_sys: dict[str, dict] = {}
    for row in x_rows:
        src = row.get("source_system") or ""
        if src in ("SYS_A", "SYS_B"):
            by_sys[src] = row

    assert "SYS_A" in by_sys, (
        f"No leaderboard row for (SYS_A, X). Rows were: {x_rows}"
    )
    assert "SYS_B" in by_sys, (
        f"No leaderboard row for (SYS_B, X). Rows were: {x_rows}"
    )

    row_a = by_sys["SYS_A"]
    row_b = by_sys["SYS_B"]

    # SYS_A row should reflect ONLY pick_a (100% WR, +1.0% PnL)
    assert row_a["fwd_trades"] == 1, (
        f"SYS_A/X should have fwd_trades=1 (only pick_a); got {row_a['fwd_trades']}. "
        f"This indicates pick_b was summed into SYS_A's row."
    )
    assert row_a["fwd_wins"] == 1
    assert row_a["fwd_losses"] == 0
    assert row_a["fwd_wr"] == 100.0
    assert abs(row_a["fwd_total_pnl"] - 1.0) < 1e-6

    # SYS_B row should reflect ONLY pick_b (0% WR, -1.0% PnL)
    assert row_b["fwd_trades"] == 1, (
        f"SYS_B/X should have fwd_trades=1 (only pick_b); got {row_b['fwd_trades']}. "
        f"This indicates pick_a was summed into SYS_B's row."
    )
    assert row_b["fwd_wins"] == 0
    assert row_b["fwd_losses"] == 1
    assert row_b["fwd_wr"] == 0.0
    assert abs(row_b["fwd_total_pnl"] - (-1.0)) < 1e-6
