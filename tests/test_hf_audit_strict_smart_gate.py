"""Tests for audit_trail.hf_strict_smart_gate (/audit optional HF overlay)."""

from datetime import datetime, timezone

from audit_trail.hf_strict_smart_gate import (
    load_hf_audit_smart_strict,
    strict_smart_gate_fail_reason,
)


def test_disabled_by_default():
    cfg = load_hf_audit_smart_strict()
    assert cfg.get("enabled") is False
    pick = {"asset_class": "CRYPTO", "elite_score": 1, "rr": 0.1}
    assert strict_smart_gate_fail_reason(pick, cfg=cfg) is None


def test_enabled_elite_and_rr():
    now = datetime(2026, 4, 2, 12, 0, 0, tzinfo=timezone.utc)
    cfg = {
        "enabled": True,
        "apply_asset_classes": ["CRYPTO"],
        "min_elite_score": 80,
        "min_risk_reward": 2.5,
        "max_signal_age_hours": 4,
        "max_signal_age_hours_copy_trader": 24,
        "min_trust_tier": "WATCH",
        "trust_tier_order": [
            "UNKNOWN",
            "",
            "PROBATION",
            "SANDBOX",
            "WATCH",
            "VALIDATING",
            "RELIABLE",
            "PROVEN",
        ],
        "require_mtf_two_of_three": True,
        "mtf_strict_if_no_ratio": False,
        "require_macro_score_when_snapshot_present": False,
    }
    base = {
        "asset_class": "CRYPTO",
        "elite_score": 85,
        "rr": 3.0,
        "open_time": "2026-04-02T10:00:00+00:00",
        "trust_tier": "PROVEN",
        "mtf_agreement_ratio": "3/3",
    }
    assert strict_smart_gate_fail_reason(dict(base), cfg=cfg, now=now) is None
    assert (
        strict_smart_gate_fail_reason({**base, "elite_score": 50}, cfg=cfg, now=now)
        == "audit_strict_elite"
    )
    assert (
        strict_smart_gate_fail_reason({**base, "rr": 1.0}, cfg=cfg, now=now)
        == "audit_strict_rr"
    )


def test_stale_signal():
    now = datetime(2026, 4, 2, 20, 0, 0, tzinfo=timezone.utc)
    cfg = {
        "enabled": True,
        "apply_asset_classes": ["CRYPTO"],
        "min_elite_score": 0,
        "min_risk_reward": 0,
        "max_signal_age_hours": 4,
        "max_signal_age_hours_copy_trader": 24,
        "min_trust_tier": "SANDBOX",
        "trust_tier_order": load_hf_audit_smart_strict()["trust_tier_order"],
        "require_mtf_two_of_three": False,
        "mtf_strict_if_no_ratio": False,
        "require_macro_score_when_snapshot_present": False,
    }
    pick = {
        "asset_class": "CRYPTO",
        "elite_score": 90,
        "rr": 5,
        "open_time": "2026-04-02T10:00:00+00:00",
        "trust_tier": "PROVEN",
    }
    assert strict_smart_gate_fail_reason(pick, cfg=cfg, now=now) == "audit_strict_stale"
