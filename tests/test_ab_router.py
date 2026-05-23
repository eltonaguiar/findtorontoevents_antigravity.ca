"""Tests for ml_gatekeeper.ab_router — Phase B of leakage-purge.

Covers:
- Deterministic routing (same pick_id always to same arm)
- Approximate 50/50 split over 10k picks
- Leakage feature masking
- Default-OFF (enabled=False -> all OLD)
- Outcome recording + summary stats
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ml_gatekeeper.ab_router import ABRouter, LEAKAGE_FEATURES


def test_routing_is_deterministic():
    r = ABRouter(enabled=True)
    a1 = r.route("pick_001")
    a2 = r.route("pick_001")
    a3 = r.route("pick_001")
    assert a1 == a2 == a3


def test_routing_split_is_approximately_50_50():
    r = ABRouter(enabled=True, traffic_split=0.5)
    counts = {"OLD": 0, "NEW": 0}
    for i in range(10000):
        counts[r.route(f"pick_{i}")] += 1
    ratio = counts["NEW"] / 10000
    assert 0.45 < ratio < 0.55, f"Split too skewed: {ratio}"


def test_leakage_features_masked_for_new_arm():
    r = ABRouter(enabled=True, traffic_split=1.0)  # all NEW
    features = {
        "momentum_10d": 0.05,
        "volume_ratio": 1.3,
        "forward_wr": 0.72,        # LEAKAGE
        "strat_fwd_wr": 0.68,      # LEAKAGE
        "eb_forward_wr": 0.55,     # LEAKAGE
        "age_hours": 48.0,         # LEAKAGE
        "rsi": 65,
    }
    result = r.score("pick_x", features, "test")
    assert result.arm == "NEW"
    assert set(result.features_masked) == set(LEAKAGE_FEATURES)
    for f in LEAKAGE_FEATURES:
        assert f not in result.features_used


def test_default_off_uses_old_path():
    r = ABRouter(enabled=False)
    features = {"momentum_10d": 0.05, "forward_wr": 0.72}
    result = r.score("pick_y", features, "test")
    assert result.arm == "OLD"
    assert result.model_version == "old_leaky"
    assert result.features_masked == []


def test_summary_returns_z_test_when_sample_sufficient():
    r = ABRouter(enabled=True, traffic_split=0.5)
    # Simulate 60 OLD + 60 NEW resolved trades
    for i in range(60):
        r._counts["OLD"] += 1
        r.record_outcome(f"p{i}", "OLD", won=(i < 30))  # 50% WR
    for i in range(60):
        r._counts["NEW"] += 1
        r.record_outcome(f"q{i}", "NEW", won=(i < 40))  # 67% WR
    s = r.summary()
    assert "z_test" in s
    assert "p_value" in s["z_test"]
    assert s["arms"]["OLD"]["win_rate"] == 0.5
    assert s["arms"]["NEW"]["win_rate"] == pytest_approx(40 / 60)


def test_summary_returns_note_when_sample_thin():
    r = ABRouter(enabled=True)
    for i in range(5):
        r._counts["OLD"] += 1
        r.record_outcome(f"p{i}", "OLD", won=True)
    s = r.summary()
    assert "note" in s["z_test"]


def test_log_path_creation_and_write(tmp_path):
    log = tmp_path / "subdir" / "ab.jsonl"
    r = ABRouter(enabled=True, traffic_split=1.0, log_path=str(log))
    r.score("pick_log_001", {"x": 1.0}, "s1")
    assert log.exists()
    line = log.read_text(encoding="utf-8").strip()
    assert "pick_log_001" in line
    assert '"arm": "NEW"' in line


# Local approx helper (avoid pytest dep on caller side)
def pytest_approx(value, rel=1e-3):
    class _Approx:
        def __init__(self, v):
            self.v = v
        def __eq__(self, other):
            return abs(other - self.v) / max(abs(self.v), 1e-9) < rel
    return _Approx(value)
