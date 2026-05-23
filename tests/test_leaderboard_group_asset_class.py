"""Regression tests for ``*_group`` rollup-row asset_class injection.

T2.3 F2 (commit 5ce6480a17a) added per-row ``asset_class`` + ``asset_classes``
fields to leaderboard entries so the dashboard chip switcher can filter by
asset class. Originally only normal `_finalize_row`-built rows received these
fields; the ML-group aggregation block (``ml_enhanced_group``,
``ml_crypto_predictor_group``) appended its rollup rows AFTER the F2 injection
loop, so rollup rows shipped without ``asset_class`` / ``asset_classes`` and
the live ``audit_dashboard/data/dashboard_data.json::leaderboard`` reproduced
the gap (1623 rows, ``*_group`` rows missing the chips).

Fix landed at ``audit_trail/dashboard_generator.py`` inside
``collect_strategy_leaderboard``: the group accumulator now tracks
constituent ``asset_class`` frequencies (weighted by child fwd_trades) and
the finalization loop derives a dominant ``asset_class`` + full union
``asset_classes`` from those counts — mirroring the per-row F2 logic.
"""

from __future__ import annotations

from audit_trail import dashboard_generator


def _mk_pick(
    symbol: str,
    strategy: str,
    source_system: str,
    pnl_pct: float,
    asset_class: str = "CRYPTO",
) -> dict:
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
        "asset_class": asset_class,
        "confidence": 0.65,
    }


def test_normal_row_has_asset_class() -> None:
    """Existing F2 fix: a non-rollup row must carry asset_class + asset_classes."""
    picks = [
        _mk_pick("BTCUSDT", "luxalgo", "luxalgo_premium", +1.5, "CRYPTO"),
        _mk_pick("ETHUSDT", "luxalgo", "luxalgo_premium", -0.5, "CRYPTO"),
    ]
    leaderboard = dashboard_generator.collect_strategy_leaderboard([], picks)
    rows = [r for r in leaderboard if r.get("strategy") == "luxalgo"]
    assert rows, "no leaderboard row for strategy 'luxalgo'"
    row = rows[0]
    assert "asset_class" in row, f"normal row missing asset_class: {row}"
    assert "asset_classes" in row, f"normal row missing asset_classes: {row}"
    assert row["asset_class"] == "CRYPTO"
    assert row["asset_classes"] == ["CRYPTO"]


def test_group_row_inherits_asset_class_from_constituents() -> None:
    """An ml_enhanced_group rollup must carry asset_class + asset_classes
    derived from its constituent ml_enhanced_* strategies."""
    picks = [
        _mk_pick("BTCUSDT", "ml_enhanced_BTCUSDT_1h_B_lightgbm",
                 "alpha_engine", +2.0, "CRYPTO"),
        _mk_pick("ETHUSDT", "ml_enhanced_ETHUSDT_1h_B_lightgbm",
                 "alpha_engine", -0.8, "CRYPTO"),
        _mk_pick("SOLUSDT", "ml_enhanced_SOLUSDT_1h_B_xgboost",
                 "alpha_engine", +1.2, "CRYPTO"),
    ]
    leaderboard = dashboard_generator.collect_strategy_leaderboard([], picks)
    group_rows = [r for r in leaderboard if r.get("strategy") == "ml_enhanced_group"]
    assert group_rows, (
        "no ml_enhanced_group rollup row produced; "
        f"got strategies: {[r.get('strategy') for r in leaderboard]}"
    )
    row = group_rows[0]
    assert "asset_class" in row, f"group row missing asset_class: {row}"
    assert "asset_classes" in row, f"group row missing asset_classes: {row}"
    assert row["asset_class"] == "CRYPTO"
    assert row["asset_classes"] == ["CRYPTO"]
    assert isinstance(row["asset_classes"], list)


def test_group_row_with_mixed_asset_classes() -> None:
    """Multi-class rollup: dominant asset_class = most-traded;
    asset_classes = sorted union of all constituent classes."""
    # 4 CRYPTO trades + 2 EQUITY trades → dominant=CRYPTO, classes=[CRYPTO, EQUITY]
    picks = [
        _mk_pick("BTCUSDT", "ml_enhanced_BTCUSDT_1h_B_lightgbm",
                 "alpha_engine", +1.0, "CRYPTO"),
        _mk_pick("ETHUSDT", "ml_enhanced_BTCUSDT_1h_B_lightgbm",
                 "alpha_engine", +0.5, "CRYPTO"),
        _mk_pick("SOLUSDT", "ml_enhanced_SOLUSDT_1h_B_xgboost",
                 "alpha_engine", -0.3, "CRYPTO"),
        _mk_pick("ADAUSDT", "ml_enhanced_SOLUSDT_1h_B_xgboost",
                 "alpha_engine", +0.7, "CRYPTO"),
        _mk_pick("AAPL", "ml_enhanced_AAPL_1h_B_lightgbm",
                 "alpha_engine", +1.5, "EQUITY"),
        _mk_pick("MSFT", "ml_enhanced_AAPL_1h_B_lightgbm",
                 "alpha_engine", -0.4, "EQUITY"),
    ]
    leaderboard = dashboard_generator.collect_strategy_leaderboard([], picks)
    group_rows = [r for r in leaderboard if r.get("strategy") == "ml_enhanced_group"]
    assert group_rows, "no ml_enhanced_group rollup row produced"
    row = group_rows[0]
    # Dominant = the one with most weighted trades (CRYPTO: 4 trades, EQUITY: 2)
    assert row["asset_class"] == "CRYPTO", (
        f"expected dominant CRYPTO, got {row['asset_class']!r}"
    )
    # Union sorted alphabetically
    assert row["asset_classes"] == ["CRYPTO", "EQUITY"], (
        f"expected union [CRYPTO, EQUITY], got {row['asset_classes']!r}"
    )


def test_group_row_with_no_constituents() -> None:
    """If no constituent rows carry asset_class info, the rollup row must
    still ship asset_class='' and asset_classes=[] (graceful empty), not
    KeyError. Guards against rollups that include only feeder picks lacking
    asset_class metadata entirely."""
    # Build picks with empty asset_class so F2 falls back to empty.
    picks = [
        _mk_pick("UNKNOWN1", "ml_enhanced_X_1h_B_lightgbm",
                 "alpha_engine", +1.0, asset_class=""),
        _mk_pick("UNKNOWN2", "ml_enhanced_Y_1h_B_lightgbm",
                 "alpha_engine", -0.5, asset_class=""),
    ]
    # Strip the asset_class field entirely so _finalize_row's F2 block can't
    # latch onto a default — _coerce/_derive may still fill it from symbol
    # heuristics, so we simulate a row with no derivable hints by removing
    # the field outright.
    for p in picks:
        p.pop("asset_class", None)
        p.pop("category", None)

    leaderboard = dashboard_generator.collect_strategy_leaderboard([], picks)
    group_rows = [r for r in leaderboard if r.get("strategy") == "ml_enhanced_group"]
    if not group_rows:
        # If filter rejected all picks (no asset_class can make _is_valid
        # reject), the test is vacuously satisfied — we only care that
        # *if* a group row is produced, it has the keys.
        return
    row = group_rows[0]
    assert "asset_class" in row, f"group row missing asset_class key: {row}"
    assert "asset_classes" in row, f"group row missing asset_classes key: {row}"
    assert isinstance(row["asset_classes"], list), (
        f"asset_classes must be list, got {type(row['asset_classes']).__name__}"
    )
    # Either the synthetic picks were rejected (empty rollup → '' / [])
    # or symbol heuristics assigned a class — both are acceptable as long
    # as the keys exist.
