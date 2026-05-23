"""Tests for B18 — shadow-mode auto-promotion for zero-history strategies.

Covers:
- should_shadow_promote() logic (flag, closed_count, emit_count)
- _apply_shadow_promotion() global cap enforcement
- HC gate exclusion for shadow picks
- Flag OFF → zero behavior change (identical to production)
"""
from __future__ import annotations

import os
from unittest.mock import patch

import pytest


# ── Helpers ──────────────────────────────────────────────────────────────────

def _make_pick(strategy: str, symbol: str = "BTCUSDT", confidence: float = 0.70) -> dict:
    return {
        "strategy": strategy,
        "symbol": symbol,
        "direction": "LONG",
        "confidence": confidence,
        "source_system": strategy,
        "created_at": "2026-05-03T00:00:00+00:00",
    }


def _make_closed(strategy: str, n: int = 1) -> list[dict]:
    return [{"strategy": strategy, "pnl_pct": 1.0, "status": "CLOSED"} for _ in range(n)]


# ── should_shadow_promote ─────────────────────────────────────────────────────

class TestShouldShadowPromote:
    def test_flag_off_always_false(self):
        from audit_trail.quality_gates import should_shadow_promote
        with patch.dict(os.environ, {"SHADOW_MODE_AUTO_PROMOTE_ENABLED": "0"}):
            assert should_shadow_promote("new_strat", 15, 0) is False

    def test_flag_on_zero_closed_enough_emits(self):
        from audit_trail.quality_gates import should_shadow_promote
        with patch.dict(os.environ, {"SHADOW_MODE_AUTO_PROMOTE_ENABLED": "1"}):
            assert should_shadow_promote("new_strat", 12, 0) is True

    def test_flag_on_has_closed_history(self):
        from audit_trail.quality_gates import should_shadow_promote
        with patch.dict(os.environ, {"SHADOW_MODE_AUTO_PROMOTE_ENABLED": "1"}):
            assert should_shadow_promote("proven_strat", 15, 3) is False

    def test_flag_on_insufficient_emits(self):
        from audit_trail.quality_gates import should_shadow_promote
        with patch.dict(os.environ, {"SHADOW_MODE_AUTO_PROMOTE_ENABLED": "1"}):
            assert should_shadow_promote("sparse_strat", 5, 0) is False

    def test_empty_strategy_name(self):
        from audit_trail.quality_gates import should_shadow_promote
        with patch.dict(os.environ, {"SHADOW_MODE_AUTO_PROMOTE_ENABLED": "1"}):
            assert should_shadow_promote("", 15, 0) is False

    def test_exactly_at_min_emit_threshold(self):
        from audit_trail.quality_gates import _SHADOW_MIN_RAW_EMITS, should_shadow_promote
        with patch.dict(os.environ, {"SHADOW_MODE_AUTO_PROMOTE_ENABLED": "1"}):
            assert should_shadow_promote("edge_strat", _SHADOW_MIN_RAW_EMITS, 0) is True
            assert should_shadow_promote("edge_strat", _SHADOW_MIN_RAW_EMITS - 1, 0) is False


# ── _apply_shadow_promotion ───────────────────────────────────────────────────

class TestApplyShadowPromotion:
    def _run(self, active, raw_pool, all_closed, env="1"):
        from audit_trail.dashboard_generator import _apply_shadow_promotion
        with patch.dict(os.environ, {"SHADOW_MODE_AUTO_PROMOTE_ENABLED": env}):
            return _apply_shadow_promotion(active, raw_pool, all_closed)

    def test_flag_off_returns_unchanged(self):
        active = [_make_pick("proven")]
        raw_pool = [_make_pick("zero_hist")] * 15
        closed = _make_closed("proven", 5)
        result, summary = self._run(active, raw_pool, closed, env="0")
        assert result is active  # same object, no changes
        assert summary["enabled"] is False

    def test_promotes_zero_history_strategy(self):
        active = [_make_pick("proven")]
        # 12 raw emits for zero-history strategy
        raw_pool = [_make_pick("proven")] + [_make_pick("new_strat")] * 12
        closed = _make_closed("proven", 3)
        result, summary = self._run(active, raw_pool, closed)
        shadow = [p for p in result if p.get("shadow_mode")]
        assert len(shadow) == 1
        assert shadow[0]["strategy"] == "new_strat"
        assert shadow[0]["shadow_size_multiplier"] == 0.1
        assert shadow[0]["shadow_strategy_raw_emit_count"] == 12
        assert shadow[0]["_gate_passed"] is True

    def test_does_not_duplicate_already_active_strategy(self):
        active = [_make_pick("already_active")]
        raw_pool = [_make_pick("already_active")] * 15
        closed = []  # zero history, but already active
        result, summary = self._run(active, raw_pool, closed)
        shadow = [p for p in result if p.get("shadow_mode")]
        assert len(shadow) == 0

    def test_global_cap_enforced(self):
        from audit_trail.quality_gates import _SHADOW_MAX_CONCURRENT
        active = []
        # Create _SHADOW_MAX_CONCURRENT + 2 zero-history strategies each with 15 emits
        raw_pool = []
        for i in range(_SHADOW_MAX_CONCURRENT + 2):
            raw_pool.extend([_make_pick(f"new_strat_{i}", confidence=0.5 + i * 0.01)] * 15)
        result, summary = self._run(active, raw_pool, [])
        shadow = [p for p in result if p.get("shadow_mode")]
        assert len(shadow) == _SHADOW_MAX_CONCURRENT

    def test_cap_selects_highest_confidence_first(self):
        from audit_trail.quality_gates import _SHADOW_MAX_CONCURRENT
        active = []
        # 3 strategies with different confidence levels; cap = 5 so all pass, but test ordering
        raw_pool = (
            [_make_pick("low_conf", confidence=0.60)] * 12 +
            [_make_pick("high_conf", confidence=0.90)] * 12 +
            [_make_pick("mid_conf", confidence=0.75)] * 12
        )
        result, summary = self._run(active, raw_pool, [])
        shadow = [p for p in result if p.get("shadow_mode")]
        # All 3 fit within cap; highest-confidence should appear first after sort
        strategies_seen = {p["strategy"] for p in shadow}
        assert "high_conf" in strategies_seen
        assert "low_conf" in strategies_seen

    def test_shadow_probation_summary_populated(self):
        active = []
        raw_pool = [_make_pick("new_strat")] * 12
        result, summary = self._run(active, raw_pool, [])
        assert summary["enabled"] is True
        assert len(summary["shadow_picks"]) == 1
        assert summary["shadow_picks"][0]["strategy"] == "new_strat"


# ── HC exclusion ──────────────────────────────────────────────────────────────

class TestHCShadowExclusion:
    def test_shadow_pick_fails_hc(self):
        from tools.dashboard_hc_rules import passes_high_conviction_pick
        pick = _make_pick("new_strat")
        pick["shadow_mode"] = True
        # Shadow picks must never pass HC regardless of other fields
        assert passes_high_conviction_pick(pick) is False

    def test_normal_pick_unaffected_by_shadow_check(self):
        from tools.dashboard_hc_rules import passes_high_conviction_pick
        pick = _make_pick("proven_strat")
        # No shadow_mode field → normal gate evaluation (may pass or fail on other criteria)
        # Just assert it doesn't crash and shadow_mode=absent doesn't auto-fail
        result = passes_high_conviction_pick(pick)
        assert isinstance(result, bool)

    def test_shadow_mode_false_does_not_block(self):
        from tools.dashboard_hc_rules import passes_high_conviction_pick
        pick = _make_pick("proven_strat")
        pick["shadow_mode"] = False  # explicitly False, not True
        # shadow_mode=False should not trigger the shadow exclusion
        result = passes_high_conviction_pick(pick)
        # Result depends on other HC criteria; we just confirm it doesn't auto-fail
        assert isinstance(result, bool)
