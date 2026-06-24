#!/usr/bin/env python3
"""
Regression tests for tools/strategy_kill_switch.py

Covers the 2026-06-21 dedup-key bug fix (PR #622 follow-up):
  - PRIMARY rows are unique by trading_picks.id (PK) - no in-source dedup.
  - SECONDARY cross-source dedup against PRIMARY uses (symbol, closed_at, status).
  - pnl_pct canonicalized via Decimal('0.0001').quantize for residual-compare safety.

Critical regression: 3 distinct trades sharing (strategy, status, pnl_pct) at different
id values MUST be counted as 3 (pre-fix the dedup key collapsed them to n=1).
"""
from __future__ import annotations

import sys
from decimal import Decimal
from pathlib import Path

import pytest

# Ensure repo root is on path
REPO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO))

import tools.strategy_kill_switch as sks


# ---------------------------------------------------------------------------
# Row builders (mirror what fetch_strategy_stats now SELECTs)
# ---------------------------------------------------------------------------

def _primary(rid, status, pnl, symbol="AAPL", closed_at="2026-06-01T10:00:00",
             strategy="test_strat", asset_class="EQUITY"):
    return {
        "id": rid,
        "asset_class": asset_class,
        "strategy": strategy,
        "status": status,
        "pnl_pct": pnl,
        "symbol": symbol,
        "closed_at": closed_at,
    }


def _secondary(symbol, closed_at, status, pnl, strategy="test_strat",
               asset_class="EQUITY", pick_id=None):
    """at_pick_outcomes row. at_pick_outcomes has no ``closed_at`` - the SQL query
    aliases its ``resolved_at`` to that key for fingerprint uniformity with primary.
    """
    return {
        "id": pick_id,
        "asset_class": asset_class,
        "strategy": strategy,
        "status": status,
        "pnl_pct": pnl,
        "symbol": symbol,
        "closed_at": closed_at,  # alias of resolved_at at the SQL layer
    }


# ---------------------------------------------------------------------------
# Regression: in-source dedup on trading_picks MUST NOT collapse distinct ids
# ---------------------------------------------------------------------------

class TestDedupBugRegression:
    """The original 2026-06-13 bug: key f"{ac}|{strat}|{status}|{pnl_pct}" collapsed
    3 distinct trading_picks rows into n=1 whenever they happened to share the same
    resolved profit percentage. Post-fix (2026-06-21) trading_picks.id is canonical.
    """

    def test_three_distinct_id_same_strategy_status_pnl_count_as_three(self):
        """3 distinct trades, same (strategy, status, pnl_pct), different ids -> n=3."""
        rows = [
            _primary(rid=1, status="WON", pnl=5.0, symbol="AAPL"),
            _primary(rid=2, status="WON", pnl=5.0, symbol="MSFT"),
            _primary(rid=3, status="WON", pnl=5.0, symbol="GOOGL"),
        ]
        stats = sks._aggregate_strategy_buckets(
            primary_rows=rows, secondary_rows=[], min_trades=1
        )
        bucket = next(b for b in stats if b["strategy"] == "test_strat")
        assert bucket["n"] == 3, (
            f"REGRESSION: 3 distinct trades collapsed to n={bucket['n']} (expected 3). "
            "Pre-fix dedup key 'asset_class|strategy|status|pnl_pct' over-deduped."
        )
        assert bucket["wins"] == 3
        assert bucket["total_pnl"] == pytest.approx(15.0)  # 3 x 5.0
        assert bucket["wr"] == pytest.approx(100.0)

    def test_realistic_crypto_3_wins_same_pnl_different_ids(self):
        """A realistic crypto scenario: 3 winning trades that all hit the standard
        5% TP. Pre-fix the dedup key would have counted this as n=1."""
        rows = [
            _primary(rid=100, status="WON", pnl=5.0, symbol="BTCUSDT",
                     strategy="rsi_pullback", asset_class="CRYPTO"),
            _primary(rid=101, status="WON", pnl=5.0, symbol="ETHUSDT",
                     strategy="rsi_pullback", asset_class="CRYPTO"),
            _primary(rid=102, status="WON", pnl=5.0, symbol="SOLUSDT",
                     strategy="rsi_pullback", asset_class="CRYPTO"),
        ]
        stats = sks._aggregate_strategy_buckets(
            primary_rows=rows, secondary_rows=[], min_trades=1
        )
        bucket = next(b for b in stats if b["strategy"] == "rsi_pullback")
        assert bucket["n"] == 3
        assert bucket["wins"] == 3
        assert bucket["wr"] == pytest.approx(100.0)
        assert bucket["total_pnl"] == pytest.approx(15.0)
        assert bucket["asset_class"] == "CRYPTO"

    def test_5_distinct_losers_share_pnl_negative_double_counted_now(self):
        """Defensive check: distinctive losers that share pnl_pct are still 5."""
        rows = [
            _primary(rid=i, status="LOST", pnl=-2.0, symbol=f"SYM_{i}")
            for i in range(5)
        ]
        stats = sks._aggregate_strategy_buckets(
            primary_rows=rows, secondary_rows=[], min_trades=1
        )
        bucket = next(b for b in stats if b["strategy"] == "test_strat")
        assert bucket["n"] == 5
        assert bucket["wins"] == 0
        assert bucket["total_pnl"] == pytest.approx(-10.0)


# ---------------------------------------------------------------------------
# SECONDARY cross-source dedup against PRIMARY uses (symbol, closed_at, status)
# ---------------------------------------------------------------------------

class TestCrossSourceDedup:
    """A secondary at_pick_outcomes row matches a primary trading_picks row when
    their (symbol, closed_at, status) triples agree; primary wins.
    """

    def test_secondary_matching_primary_signature_dropped(self):
        primary = [_primary(rid=1, status="WON", pnl=5.0,
                            symbol="AAPL", closed_at="2026-06-01T10:00:00")]
        secondary = [_secondary(symbol="AAPL", closed_at="2026-06-01T10:00:00",
                                status="WON", pnl=5.0)]
        # tp_strat_counts["test_strat"] = 1 (<20), so secondary IS eligible.
        # The only remaining gate is the cross-source dedup.
        stats = sks._aggregate_strategy_buckets(
            primary_rows=primary, secondary_rows=secondary, min_trades=1
        )
        bucket = next(b for b in stats if b["strategy"] == "test_strat")
        # Secondary dropped - only the primary's WIN counts.
        assert bucket["n"] == 1
        assert bucket["wins"] == 1
        assert bucket["total_pnl"] == pytest.approx(5.0)

    def test_secondary_with_different_closed_at_included(self):
        primary = [_primary(rid=1, status="WON", pnl=5.0,
                            symbol="AAPL", closed_at="2026-06-01T10:00:00")]
        secondary = [_secondary(symbol="AAPL", closed_at="2026-06-01T11:00:00",
                                status="WON", pnl=5.0)]  # DIFFERENT timestamp
        stats = sks._aggregate_strategy_buckets(
            primary_rows=primary, secondary_rows=secondary, min_trades=1
        )
        bucket = next(b for b in stats if b["strategy"] == "test_strat")
        assert bucket["n"] == 2  # primary + secondary
        assert bucket["total_pnl"] == pytest.approx(10.0)

    def test_secondary_with_different_symbol_included(self):
        primary = [_primary(rid=1, status="WON", pnl=5.0,
                            symbol="AAPL", closed_at="2026-06-01T10:00:00")]
        secondary = [_secondary(symbol="MSFT", closed_at="2026-06-01T10:00:00",
                                status="WON", pnl=5.0)]  # DIFFERENT symbol
        stats = sks._aggregate_strategy_buckets(
            primary_rows=primary, secondary_rows=secondary, min_trades=1
        )
        bucket = next(b for b in stats if b["strategy"] == "test_strat")
        assert bucket["n"] == 2

    def test_secondary_dropped_when_strategy_has_20plus_primary(self):
        """Legacy supplement gate preserved: a strategy with >=20 primary entries
        does NOT admit any secondary records regardless of fingerprint."""
        primary = [_primary(rid=i, status="WON", pnl=5.0,
                            symbol=f"SYM_{i}", strategy="saturated_strat")
                   for i in range(20)]
        secondary = [_secondary(symbol="AAPL", closed_at="2026-06-01T10:00:00",
                                status="WON", pnl=5.0, strategy="saturated_strat")]
        stats = sks._aggregate_strategy_buckets(
            primary_rows=primary, secondary_rows=secondary, min_trades=1
        )
        bucket = next(b for b in stats if b["strategy"] == "saturated_strat")
        assert bucket["n"] == 20

    def test_secondary_case_normalized_symbol(self):
        """Symbol normalization: 'aapl' and 'AAPL' should be treated as the same
        trade identity (cross-source fingerprint)."""
        primary = [_primary(rid=1, status="WON", pnl=5.0,
                            symbol="AAPL", closed_at="2026-06-01T10:00:00")]
        secondary = [_secondary(symbol="aapl", closed_at="2026-06-01T10:00:00",
                                status="WON", pnl=5.0)]  # case-different symbol
        stats = sks._aggregate_strategy_buckets(
            primary_rows=primary, secondary_rows=secondary, min_trades=1
        )
        bucket = next(b for b in stats if b["strategy"] == "test_strat")
        assert bucket["n"] == 1  # dedup'd via symbol normalization


# ---------------------------------------------------------------------------
# pnl_pct canonicalization (Decimal('0.0001').quantize)
# ---------------------------------------------------------------------------

class TestPnlCanonicalization:
    def test_canonical_rounds_float_repr_drift(self):
        # 0.1 + 0.2 in float == 0.30000000000000004. Decimal canonicalizes to 0.3.
        assert sks._canonical_pnl(0.1 + 0.2) == pytest.approx(0.3)

    def test_canonical_truncates_beyond_4_decimals(self):
        assert sks._canonical_pnl(1.234567) == pytest.approx(1.2346)

    def test_canonical_negative_truncates(self):
        assert sks._canonical_pnl(-1.234567) == pytest.approx(-1.2346)

    def test_canonical_handles_bad_input_as_zero(self):
        assert sks._canonical_pnl("not-a-number") == 0.0
        assert sks._canonical_pnl(None) == 0.0
        assert sks._canonical_pnl({}) == 0.0

    def test_canonical_handles_decimal_input(self):
        # Already-Decimal input passes through quantization.
        assert sks._canonical_pnl(Decimal("1.234567")) == pytest.approx(1.2346)
        assert sks._canonical_pnl(Decimal("3.14")) == pytest.approx(3.14)

    def test_canonical_handles_zero(self):
        assert sks._canonical_pnl(0) == 0.0
        assert sks._canonical_pnl(0.0) == 0.0

    def test_canonical_handles_float_inf_as_zero(self):
        # Decimal('inf') raises InvalidOperation; fall back to 0.0.
        assert sks._canonical_pnl(float('inf')) == 0.0


# ---------------------------------------------------------------------------
# End-to-end realistic scenarios
# ---------------------------------------------------------------------------

class TestAggregateEndToEnd:

    def test_min_trades_filter_still_works(self):
        """Sanity: a bucket with n<min_trades is dropped from the result."""
        rows = [_primary(rid=i, status="WON", pnl=5.0, symbol=f"SYM_{i}")
                for i in range(3)]  # only 3 trades
        stats = sks._aggregate_strategy_buckets(
            primary_rows=rows, secondary_rows=[], min_trades=10
        )
        # min_trades=10 - bucket below threshold is filtered out.
        assert all(b["strategy"] != "test_strat" for b in stats)

    def test_wr_round_to_2_decimals(self):
        """WR rounding is 2 decimals (legacy behavior preserved)."""
        # 1 WIN, 2 LOST = 33.33% WR.
        rows = [
            _primary(rid=1, status="WON", pnl=5.0, symbol="W"),
            _primary(rid=2, status="LOST", pnl=-2.0, symbol="L1"),
            _primary(rid=3, status="LOST", pnl=-2.0, symbol="L2"),
        ]
        stats = sks._aggregate_strategy_buckets(
            primary_rows=rows, secondary_rows=[], min_trades=1
        )
        bucket = next(b for b in stats if b["strategy"] == "test_strat")
        assert bucket["n"] == 3
        assert bucket["wins"] == 1
        assert bucket["wr"] == pytest.approx(33.33)

    def test_output_sorted_by_class_then_n_desc(self):
        """Output should be sorted (asset_class, -n) as legacy."""
        rows = [
            _primary(rid=1, status="WON", pnl=1.0, symbol="Z", strategy="z_strat",
                     asset_class="EQUITY"),
            _primary(rid=2, status="WON", pnl=1.0, symbol="A", strategy="a_strat",
                     asset_class="CRYPTO"),
            _primary(rid=3, status="WON", pnl=1.0, symbol="B", strategy="b_strat",
                     asset_class="EQUITY"),
        ]
        stats = sks._aggregate_strategy_buckets(
            primary_rows=rows, secondary_rows=[], min_trades=1
        )
        # Check the sort order: by asset_class alphabetically, then by -n
        asset_classes = [b["asset_class"] for b in stats]
        assert asset_classes == sorted(asset_classes)


# ---------------------------------------------------------------------------
# Stale-fingerprint dedup contract (proves the BUG is gone)
# ---------------------------------------------------------------------------

class TestStaleFingerprintBug:
    """The actual bug from PR #622 — explicitly prove it can't recur."""

    def test_pre_fix_dedup_key_would_have_collapsed_to_one(self):
        """Reverse test: demonstrates that the EXACT pre-fix key would have collapsed
        these rows. Post-fix we now count each id-distinct row."""
        # 3 distinct trades, all happen to resolve at +5.0 (same TP target).
        rows = [
            _primary(rid=10, status="WON", pnl=5.0, symbol="A"),
            _primary(rid=20, status="WON", pnl=5.0, symbol="B"),
            _primary(rid=30, status="WON", pnl=5.0, symbol="C"),
        ]
        # Simulate pre-fix behavior locally (so the test is self-documenting).
        pre_fix_seen = set()
        pre_fix_count = 0
        for r in rows:
            pre_fix_key = (
                f"{r['asset_class']}|{r['strategy']}|{r['status']}|{r['pnl_pct']}"
            )
            if pre_fix_key not in pre_fix_seen:
                pre_fix_seen.add(pre_fix_key)
                pre_fix_count += 1
        # Sanity: pre-fix WOULD have collapsed to 1.
        assert pre_fix_count == 1

        # Post-fix: actual code counts all 3 distinct ids.
        stats = sks._aggregate_strategy_buckets(
            primary_rows=rows, secondary_rows=[], min_trades=1
        )
        bucket = next(b for b in stats if b["strategy"] == "test_strat")
        assert bucket["n"] == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
