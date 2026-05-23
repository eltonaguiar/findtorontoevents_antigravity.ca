"""Tests for alpha_engine.hf_quality_gate."""

from pathlib import Path

from alpha_engine.hf_quality_gate import (
    hf_smart_pick_post_score_reason,
    load_hf_quality_gates,
    suggested_kelly_notional_fraction,
)


def test_enabled_by_default():
    # v2 (PR #660, 2026-05-03) flipped enabled -> True as the P0 fix.
    # The previous v1 default (enabled=False) is intentionally retired.
    cfg = load_hf_quality_gates()
    assert cfg.get("enabled") is True


def test_blocks_low_quality_pick_when_enabled():
    # v2 gate is always-enabled; a pick with weak elite_score / RR / stale age
    # must be rejected with an "hf_gate_*" reason rather than passing through
    # like it did under v1's enabled=False default.
    scored = {
        "elite_score": 10,
        "rr_ratio": 0.5,
        "age_hours": 100,
        "trust_tier": "SANDBOX",
        "asset_class": "CRYPTO",
    }
    reason = hf_smart_pick_post_score_reason(scored, {}, cfg=load_hf_quality_gates())
    assert reason is not None
    assert reason.startswith("hf_gate_")


def test_elite_and_rr_when_enabled(tmp_path: Path):
    cfg = {
        "enabled": True,
        "min_elite_score": 80,
        "min_risk_reward": 0.8,
        "max_risk_reward": 2.5,
        "max_signal_age_hours": 4,
        "max_signal_age_hours_copy_trader": 24,
        "min_mtf_agree_numerator": 2,
        "min_mtf_agree_denominator": 3,
        "trust_tier_order": load_hf_quality_gates()["trust_tier_order"],
        "min_trust_tier": "WATCH",
        "require_macro_overlay_when_snapshot_present": False,
        "mtf_strict_if_no_ratio": False,
    }
    base = {
        "elite_score": 85,
        "rr_ratio": 2.0,
        "age_hours": 2,
        "trust_tier": "PROVEN",
        "mtf_agreement_ratio": "3/3",
        "asset_class": "CRYPTO",
    }
    assert hf_smart_pick_post_score_reason(dict(base), {}, cfg=cfg) is None
    assert hf_smart_pick_post_score_reason({**base, "elite_score": 50}, {}, cfg=cfg) == "hf_gate_elite"
    assert hf_smart_pick_post_score_reason({**base, "rr_ratio": 0.5}, {}, cfg=cfg) == "hf_gate_rr_low"
    assert hf_smart_pick_post_score_reason({**base, "rr_ratio": 3.0}, {}, cfg=cfg) == "hf_gate_rr_high"


def test_mtf_ratio_fail():
    cfg = {
        "enabled": True,
        "min_elite_score": 0,
        "min_risk_reward": 0,
        "max_signal_age_hours": 999,
        "trust_tier_order": load_hf_quality_gates()["trust_tier_order"],
        "min_trust_tier": "SANDBOX",
        "min_mtf_agree_numerator": 2,
        "min_mtf_agree_denominator": 3,
        "require_macro_overlay_when_snapshot_present": False,
        "mtf_strict_if_no_ratio": False,
    }
    scored = {
        "elite_score": 90,
        "rr_ratio": 5,
        "age_hours": 1,
        "trust_tier": "PROVEN",
        "mtf_agreement_ratio": "1/3",
        "asset_class": "CRYPTO",
    }
    assert hf_smart_pick_post_score_reason(scored, {}, cfg=cfg) == "hf_gate_mtf"


def test_kelly_fraction_bounded():
    s = {"strat_fwd_wr": 60.0}
    k = suggested_kelly_notional_fraction(s, cfg={"kelly_cap_fraction": 0.25})
    assert 0.01 <= k <= 0.25
