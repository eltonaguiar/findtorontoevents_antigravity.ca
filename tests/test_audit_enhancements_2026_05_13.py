"""Tests for the 2026-05-13 audit enhancements scaffolding.

Covers:
  - tools/predictor_ic_reproducer.py (pure-function IC helpers)
  - alpha_engine/breaker_namespaces.py (TTL'd state schema)
  - alpha_engine/concentration_cap.py (per-symbol cap + HHI)
  - alpha_engine/per_asset_class_predictor.py (verified-IC scoring)

These are deterministic, no-network, no-large-fixture tests.
"""
from __future__ import annotations
import json
import os
import sys
import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from alpha_engine import breaker_namespaces as bn
from alpha_engine import concentration_cap as cc
from alpha_engine import per_asset_class_predictor as pacp
from tools import predictor_ic_reproducer as ic


# ---- IC reproducer ---------------------------------------------------------

def test_rank_handles_ties():
    assert ic._rank([1.0, 2.0, 3.0]) == [1.0, 2.0, 3.0]
    assert ic._rank([5.0, 5.0, 5.0]) == [2.0, 2.0, 2.0]
    assert ic._rank([3.0, 1.0, 2.0]) == [3.0, 1.0, 2.0]


def test_pearson_perfect_correlation():
    xs = [1.0, 2.0, 3.0, 4.0, 5.0]
    ys = [2.0, 4.0, 6.0, 8.0, 10.0]
    assert abs(ic._pearson(xs, ys) - 1.0) < 1e-9


def test_pearson_perfect_anti_correlation():
    xs = [1.0, 2.0, 3.0, 4.0, 5.0]
    ys = [5.0, 4.0, 3.0, 2.0, 1.0]
    assert abs(ic._pearson(xs, ys) + 1.0) < 1e-9


def test_spearman_monotonic_nonlinear():
    xs = [1.0, 2.0, 3.0, 4.0, 5.0]
    ys = [1.0, 4.0, 9.0, 16.0, 25.0]
    assert ic._spearman(xs, ys) == pytest.approx(1.0, abs=1e-9)


def test_ic_insufficient_n_does_not_throw():
    picks = [{"elite_score": 1.0, "pnl_pct": 0.01}]
    rec = ic._ic_for_feature(picks, "elite_score")
    assert rec["verdict"] == "INSUFFICIENT_N"
    assert rec["spearman_rho"] is None


def test_ic_drops_nan_rows():
    picks = ([{"elite_score": float("nan"), "pnl_pct": 1.0}] * 5
             + [{"elite_score": i, "pnl_pct": i} for i in range(40)])
    rec = ic._ic_for_feature(picks, "elite_score")
    assert rec["n"] == 40
    assert rec["spearman_rho"] is not None
    assert rec["spearman_rho"] > 0.95


def test_matic_ghost_filter_matches_known_pattern():
    assert ic._is_matic_ghost({"source_system": "quan_engine", "symbol": "MATICUSDT"})
    assert ic._is_matic_ghost({"source_system": "QUAN_ENGINE", "symbol": "maticusdt"})
    assert not ic._is_matic_ghost({"source_system": "quan_engine", "symbol": "BTCUSDT"})
    assert not ic._is_matic_ghost({"source_system": "alpha_engine", "symbol": "MATICUSDT"})


# ---- breaker_namespaces ----------------------------------------------------

def test_breaker_namespace_write_then_read(tmp_path):
    p = tmp_path / "state.json"
    bn.write_namespace("drift_breaker_state", {"level": "GREEN", "max_picks": 10},
                       ttl_seconds=3600, path=p)
    out = bn.read_namespace("drift_breaker_state", path=p)
    assert out == {"level": "GREEN", "max_picks": 10}


def test_breaker_namespace_missing_returns_none(tmp_path):
    p = tmp_path / "state.json"
    assert bn.read_namespace("nope", path=p) is None


def test_breaker_namespace_expired_returns_none(tmp_path):
    """The exact bug scenario from feedback_circuit_breaker_stale_state_leak."""
    p = tmp_path / "state.json"
    write_time = datetime(2026, 1, 1, tzinfo=timezone.utc)
    read_time = write_time + timedelta(hours=115)  # 115h stale, matches incident
    bn.write_namespace("drift_breaker_state", {"level": "GREEN", "max_picks": 0},
                       ttl_seconds=3600, path=p, now=write_time)
    # Read after TTL — must be None, NOT the leaked max_picks=0
    out = bn.read_namespace("drift_breaker_state", path=p, now=read_time)
    assert out is None, "stale state must not leak — would re-trigger 115h lockout bug"


def test_breaker_namespace_purge_expired(tmp_path):
    p = tmp_path / "state.json"
    write_time = datetime(2026, 1, 1, tzinfo=timezone.utc)
    bn.write_namespace("stale_one", {"x": 1}, ttl_seconds=60, path=p, now=write_time)
    bn.write_namespace("fresh_one", {"y": 2}, ttl_seconds=3600, path=p,
                       now=write_time + timedelta(seconds=30))
    read_time = write_time + timedelta(minutes=10)
    removed = bn.purge_expired(path=p, now=read_time)
    assert removed == 1
    remaining = bn.list_namespaces(path=p, now=read_time)
    assert remaining == {"fresh_one": "fresh"}


def test_breaker_namespace_atomic_no_partial_state(tmp_path):
    """write_namespace must be atomic: never leaves a half-written file."""
    p = tmp_path / "state.json"
    bn.write_namespace("a", {"v": 1}, ttl_seconds=60, path=p)
    bn.write_namespace("b", {"v": 2}, ttl_seconds=60, path=p)
    raw = json.loads(p.read_text(encoding="utf-8"))
    assert set(raw["namespaces"].keys()) == {"a", "b"}
    assert raw["namespaces"]["a"]["data"] == {"v": 1}


def test_breaker_namespace_corrupt_file_returns_empty(tmp_path):
    p = tmp_path / "state.json"
    p.write_text("{not valid json", encoding="utf-8")
    assert bn.read_namespace("anything", path=p) is None
    assert bn.list_namespaces(path=p) == {}


def test_breaker_namespace_rejects_non_int_ttl(tmp_path):
    p = tmp_path / "state.json"
    with pytest.raises(ValueError):
        bn.write_namespace("x", {"a": 1}, ttl_seconds=0, path=p)
    with pytest.raises(TypeError):
        bn.write_namespace("x", "not a dict", ttl_seconds=60, path=p)  # type: ignore[arg-type]


# ---- concentration_cap -----------------------------------------------------

def _pick(ac, sym):
    return {"asset_class": ac, "symbol": sym}


def test_concentration_cap_allows_when_below_min_active():
    active = [_pick("COMMODITY", "CT=F")] * 3
    allow, reason = cc.passes_concentration_cap("COMMODITY", "CT=F", active)
    assert allow is True
    assert reason == ""


def test_concentration_cap_blocks_commodity_ctf_over_emission():
    """Exact bug scenario from PR #961 falsification: CT=F = 75.6% of COMMODITY."""
    active = [_pick("COMMODITY", "CT=F")] * 75 + [_pick("COMMODITY", "KC=F")] * 24
    # n=99 COMMODITY, CT=F at 75/99=75.8%. New CT=F pick → 76/100=76% > 30 cap.
    allow, reason = cc.passes_concentration_cap("COMMODITY", "CT=F", active)
    assert allow is False
    assert "75" in reason or "76" in reason
    assert "30%" in reason


def test_concentration_cap_allows_diversified_class():
    active = ([_pick("CRYPTO", "BTCUSDT")] * 10
              + [_pick("CRYPTO", "ETHUSDT")] * 8
              + [_pick("CRYPTO", "SOLUSDT")] * 7)
    allow, _ = cc.passes_concentration_cap("CRYPTO", "ADAUSDT", active)
    assert allow is True


def test_concentration_cap_unknown_class_passes_through():
    """Unknown asset class must not block — default-permissive."""
    active = [_pick("FOO", "X")] * 50
    allow, _ = cc.passes_concentration_cap("FOO", "X", active)
    assert allow is True


def test_concentration_cap_only_counts_same_class():
    active = ([_pick("COMMODITY", "CT=F")] * 50
              + [_pick("CRYPTO", "BTCUSDT")] * 100)
    # Only 50 COMMODITY picks; CT=F is 100% of that class.
    allow, reason = cc.passes_concentration_cap("COMMODITY", "CT=F", active)
    assert allow is False
    assert "COMMODITY" in reason


def test_class_hhi_detects_single_symbol_dominance():
    active = [_pick("COMMODITY", "CT=F")] * 100
    hhi = cc.class_hhi(active, "COMMODITY")
    assert hhi == pytest.approx(10000.0)
    assert cc.class_hhi_verdict(hhi) == "HIGH_CONCENTRATION"


def test_class_hhi_diversified():
    active = []
    for s in "ABCDEFGHIJ":
        active.extend([_pick("CRYPTO", s)] * 10)
    hhi = cc.class_hhi(active, "CRYPTO")
    assert hhi == pytest.approx(1000.0)
    assert cc.class_hhi_verdict(hhi) == "DIVERSIFIED"


# ---- per_asset_class_predictor --------------------------------------------

def test_trust_score_is_highest_weight():
    """For every class profile, trust_score weight >= every other positive weight."""
    for ac, weights in pacp.WEIGHTS_BY_CLASS.items():
        trust_w = weights.get("trust_score", 0.0)
        for feat, w in weights.items():
            assert trust_w >= w, (
                f"{ac}: trust_score weight {trust_w} not >= {feat} weight {w}"
            )


def test_elite_score_weight_is_15_or_less():
    for ac, weights in pacp.WEIGHTS_BY_CLASS.items():
        ew = weights.get("elite_score", 0.0)
        assert ew <= 0.15, f"{ac}: elite_score weight {ew} > 0.15 cap"


def test_positive_weights_sum_to_1():
    for ac, weights in pacp.WEIGHTS_BY_CLASS.items():
        s = sum(weights.values())
        assert abs(s - 1.0) < 1e-9, f"{ac}: weights sum to {s}, not 1.0"


def test_confidence_is_not_a_positive_gate():
    """min_confidence_smart is 0 for every class. Confidence cannot
    block a pick on its own."""
    for ac in ("CRYPTO", "EQUITY", "COMMODITY", "FOREX", "ETF", "BOND", "FUTURES"):
        assert pacp.min_confidence_smart(ac) == 0.0


def test_confidence_penalty_applied():
    """Higher confidence → lower adjusted score, all else equal."""
    low_conf = {"asset_class": "CRYPTO", "trust_score": 80.0,
                "elite_score": 60.0, "confidence": 0.10}
    high_conf = dict(low_conf)
    high_conf["confidence"] = 0.95
    s_low = pacp.per_asset_class_smart_score(low_conf)
    s_high = pacp.per_asset_class_smart_score(high_conf)
    assert s_low > s_high, (
        f"high-confidence pick should score lower (penalty). "
        f"low={s_low} high={s_high}"
    )


def test_per_class_predictor_clamps_to_0_100():
    huge = {"asset_class": "CRYPTO", "trust_score": 99999.0,
            "elite_score": 99999.0, "confidence": 0.0}
    s = pacp.per_asset_class_smart_score(huge)
    assert 0.0 <= s <= 100.0


def test_per_class_predictor_handles_missing_fields():
    """No crash on empty pick. Returns a defined number in [0,100]."""
    s = pacp.per_asset_class_smart_score({"asset_class": "EQUITY"})
    assert isinstance(s, float)
    assert 0.0 <= s <= 100.0


def test_trust_tier_fallback_when_numeric_absent():
    """When trust_score is missing but trust_tier is set, tier maps to
    a numeric proxy (mimo design idea adopted)."""
    proven = {"asset_class": "CRYPTO", "trust_tier": "PROVEN",
              "elite_score": 0.0, "confidence": 0.0}
    untrusted = {"asset_class": "CRYPTO", "trust_tier": "UNTRUSTED",
                 "elite_score": 0.0, "confidence": 0.0}
    s_proven = pacp.per_asset_class_smart_score(proven)
    s_untrusted = pacp.per_asset_class_smart_score(untrusted)
    assert s_proven > s_untrusted


def test_unknown_class_falls_back_to_default():
    weights = pacp.get_weights("MYSTERY_CLASS")
    assert weights == pacp.WEIGHTS_DEFAULT


def test_futures_is_hard_blocked():
    blocked, reason = pacp.is_hard_blocked("FUTURES")
    assert blocked is True
    assert "FUTURES" in reason
    # Even with maxed inputs, FUTURES must score 0
    s = pacp.per_asset_class_smart_score(
        {"asset_class": "FUTURES", "trust_score": 100.0,
         "elite_score": 100.0, "confidence": 0.0}
    )
    assert s == 0.0


def test_non_futures_not_hard_blocked():
    for ac in ("CRYPTO", "EQUITY", "COMMODITY", "FOREX", "ETF", "BOND"):
        blocked, _ = pacp.is_hard_blocked(ac)
        assert blocked is False, f"{ac} should not be hard-blocked"


def test_blend_with_base():
    """blend_with_base=0.5 returns mid-point of new and base."""
    pick = {"asset_class": "EQUITY", "trust_score": 80.0,
            "elite_score": 60.0, "confidence": 0.0}
    new = pacp.per_asset_class_smart_score(pick)
    blended = pacp.per_asset_class_smart_score(pick, base_smart_score=20.0,
                                                blend_with_base=0.5)
    # blended = 0.5*new + 0.5*20
    assert abs(blended - (0.5 * new + 10.0)) < 1e-6


def test_env_flag_default_on_2026_05_13():
    """is_enabled() defaults to True since the 2026-05-13 shadow-mode flip.
    Override: PER_ASSET_CLASS_SCORING_ENABLED=0 fully disables overlay."""
    saved = os.environ.pop("PER_ASSET_CLASS_SCORING_ENABLED", None)
    try:
        assert pacp.is_enabled() is True
    finally:
        if saved is not None:
            os.environ["PER_ASSET_CLASS_SCORING_ENABLED"] = saved


def test_env_flag_explicit_zero_disables():
    os.environ["PER_ASSET_CLASS_SCORING_ENABLED"] = "0"
    try:
        assert pacp.is_enabled() is False
    finally:
        del os.environ["PER_ASSET_CLASS_SCORING_ENABLED"]


def test_shadow_mode_default_on_2026_05_13():
    saved = os.environ.pop("PER_ASSET_CLASS_SCORING_SHADOW", None)
    try:
        assert pacp.is_shadow_mode() is True
    finally:
        if saved is not None:
            os.environ["PER_ASSET_CLASS_SCORING_SHADOW"] = saved


def test_shadow_mode_explicit_zero_disables():
    os.environ["PER_ASSET_CLASS_SCORING_SHADOW"] = "0"
    try:
        assert pacp.is_shadow_mode() is False
    finally:
        del os.environ["PER_ASSET_CLASS_SCORING_SHADOW"]


def test_confidence_in_percent_scale_is_normalized():
    """Tolerate confidence in [0,100] scale by auto-detecting >1.5."""
    p_unit = {"asset_class": "CRYPTO", "trust_score": 80.0,
              "elite_score": 60.0, "confidence": 0.95}
    p_pct = dict(p_unit)
    p_pct["confidence"] = 95.0
    s_unit = pacp.per_asset_class_smart_score(p_unit)
    s_pct = pacp.per_asset_class_smart_score(p_pct)
    assert abs(s_unit - s_pct) < 1e-6


def test_confidence_zero_means_no_penalty():
    p_zero = {"asset_class": "EQUITY", "trust_score": 80.0,
              "elite_score": 60.0, "confidence": 0.0}
    p_one = dict(p_zero)
    p_one["confidence"] = 1.0
    s_zero = pacp.per_asset_class_smart_score(p_zero)
    s_one = pacp.per_asset_class_smart_score(p_one)
    # CRYPTO penalty is 0.08 * 100 = 8 pts max. EQUITY = 0.04 * 100 = 4 pts.
    diff = s_zero - s_one
    assert 3.0 < diff < 5.0, f"EQUITY conf=1 penalty should be ~4pts, got {diff}"


def test_crypto_has_strongest_confidence_penalty():
    """CRYPTO + FOREX should penalize confidence more than EQUITY/COMMODITY
    (per recent_closed IC inversion finding)."""
    pick_crypto = {"asset_class": "CRYPTO", "trust_score": 80.0,
                   "elite_score": 60.0, "confidence": 1.0}
    pick_crypto_zero = dict(pick_crypto); pick_crypto_zero["confidence"] = 0.0
    pick_equity = {"asset_class": "EQUITY", "trust_score": 80.0,
                   "elite_score": 60.0, "confidence": 1.0}
    pick_equity_zero = dict(pick_equity); pick_equity_zero["confidence"] = 0.0
    crypto_penalty = pacp.per_asset_class_smart_score(pick_crypto_zero) - \
                     pacp.per_asset_class_smart_score(pick_crypto)
    equity_penalty = pacp.per_asset_class_smart_score(pick_equity_zero) - \
                     pacp.per_asset_class_smart_score(pick_equity)
    assert crypto_penalty > equity_penalty


# ---- edge_decay_heatmap ----------------------------------------------------

from tools import edge_decay_heatmap as edh  # noqa: E402


def test_edh_metrics_basic():
    m = edh._metrics([{"pnl_pct": 1.0}, {"pnl_pct": -0.5}, {"pnl_pct": 0.5}])
    assert m["n"] == 3
    # 2 wins (+1.0, +0.5) vs 1 loss (-0.5)
    assert m["pf"] == pytest.approx(3.0)
    assert m["wr"] == pytest.approx(2 / 3 * 100, abs=0.01)


def test_edh_metrics_handles_nan():
    m = edh._metrics([{"pnl_pct": float("nan")}, {"pnl_pct": 1.0}])
    assert m["n"] == 2  # n is just len, but NaN excluded from pf/wr math
    assert m["pf"] == 999.0  # only wins, no losses


def test_edh_metrics_zero_picks():
    assert edh._metrics([]) == {"n": 0, "wr": None, "pf": None}


def test_edh_classify_dead_pf_below_threshold():
    by_window = {"90d": {"pf": 1.2}, "30d": {"pf": 0.5}, "7d": {"pf": 0.3}}
    assert edh._classify(by_window) == "dead"


def test_edh_classify_decaying_monotone_drop():
    by_window = {"90d": {"pf": 2.0}, "30d": {"pf": 1.5}, "7d": {"pf": 1.0}}
    assert edh._classify(by_window) == "decaying"


def test_edh_classify_improving_monotone_rise():
    by_window = {"90d": {"pf": 1.0}, "30d": {"pf": 1.5}, "7d": {"pf": 2.0}}
    assert edh._classify(by_window) == "improving"


def test_edh_classify_stable_when_non_monotone():
    by_window = {"90d": {"pf": 1.5}, "30d": {"pf": 1.2}, "7d": {"pf": 1.4}}
    assert edh._classify(by_window) == "stable"


def test_edh_ghost_filter_applied():
    """MATIC ghost rows must drop out of heatmap inputs."""
    assert edh._is_matic_ghost({"source_system": "quan_engine", "symbol": "MATICUSDT"})
    assert not edh._is_matic_ghost({"source_system": "alpha_engine", "symbol": "MATICUSDT"})
