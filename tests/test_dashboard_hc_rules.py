"""Mirror of dashboard passesHighConvictionPick v3 — keep aligned with hc_filter.js.

These tests are intentionally isolated from `config/hc_gate_params.json`. They
encode the v4.2 hybrid contract (per-asset-class FWD WR + Score floors derived
from the 3,500-pick analysis on 2026-04-14). When the live config is bumped
(e.g. v4.3 raising all floors to 70%), these tests should remain stable
because the rule semantics they test — boundary inclusivity, gate ordering,
class-specific thresholds — are independent of the threshold values themselves.

The autouse fixture below pins `dashboard_hc_rules._PARAMS_CACHE` to v4.2
values so the tests are deterministic regardless of what's in the live config.
If you intentionally tighten/loosen the contract, update both the fixture
defaults AND any boundary tests that read those defaults.
"""

import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
_TOOLS = _ROOT / "tools"
if str(_TOOLS) not in sys.path:
    sys.path.insert(0, str(_TOOLS))

import dashboard_hc_rules  # noqa: E402
from dashboard_hc_rules import (  # noqa: E402
    filter_high_conviction_ordered,
    passes_high_conviction_pick,
)


# v4.2 hybrid contract — what these tests were originally written against.
# Pinned here so config drift in production (v4.3+) doesn't break the suite.
_TEST_PARAMS_V42 = {
    "scoreAbsoluteFloor": 40,
    "scoreCompoundFloor": 50,
    "scoreCompoundTrustMin": 8,
    "trustTierBlacklist": ["SANDBOX", "UNPROVEN", "PROBATION", "DEMOTED"],
    "trustScoreMinCrypto": 4,
    "trustScoreMinOther": 5,
    "forwardTradesMin": 5,
    "forwardWRMinPct": 55,
    "forwardWRMinPctCrypto": 40,
    "forwardWRMinPctEquity": 50,
    "forwardWRMinPctForex": 55,
    "scoreFloorCrypto": 45,
    "scoreFloorEquity": 45,
    "scoreFloorForex": 40,
    "forexRelaxedWRMinPct": 50,
    "confidenceMax": 0.90,
    "confidenceFwdTradesMax": 20,
    "confidenceExtremeMax": 0.95,
    "confidenceExtremeFwdTradesMax": 30,
    "confidenceLoBand": 0.85,
    "confidenceHiBand": 0.95,
    "confidenceLoBandFwdTradesMin": 30,
    "longBlockedInBear": True,
    "bearRegimes": ["bear", "trending_down", "crash", "distribution"],
    "shortBlockedInBull": True,
    "bullRegimes": ["bull", "trending_up", "strong_bull"],
    "shortInBullRequiresProven": True,
    "rejectWalkForwardFailing": True,
    "independentGroupsMin": 3,
    "tierSABypassIndependentConsensus": True,
}


@pytest.fixture(autouse=True)
def _pin_v42_params(monkeypatch):
    """Pin params to v4.2 contract for the duration of each test.

    Inherits the live `signalGroups` from config (those don't affect
    threshold tests) and overlays only the threshold-bearing keys.
    """
    live = dict(dashboard_hc_rules.get_hc_gate_params())
    live.update(_TEST_PARAMS_V42)
    monkeypatch.setattr(dashboard_hc_rules, "_PARAMS_CACHE", live, raising=False)
    yield
    # monkeypatch auto-restores on teardown; explicit reset for safety.
    monkeypatch.setattr(dashboard_hc_rules, "_PARAMS_CACHE", None, raising=False)


def _base(**kwargs):
    d = {
        "symbol": "BTCUSDT",
        "asset_class": "CRYPTO",
        "strategy": "keltner",
        "trust_score": 6,
        "strat_fwd_wr": 0.55,
        "strat_fwd_trades": 10,
        "elite_score": 0,
        "trust_tier": "PROVEN",
        "direction": "LONG",
        "regime": "neutral",
        "confidence": 0.5,
        "score": 55,
    }
    d.update(kwargs)
    return d


def test_v3_proven_passes():
    assert passes_high_conviction_pick(_base(trust_tier="PROVEN"))


def test_sandbox_blocked():
    assert not passes_high_conviction_pick(_base(trust_tier="SANDBOX"))


def test_probation_blocked_matches_backend():
    assert not passes_high_conviction_pick(_base(trust_tier="PROBATION"))


def test_crypto_sym_strat():
    assert passes_high_conviction_pick(
        _base(
            symbol="DOTUSDT",
            strategy="st_fear_greed_contrarian_v1",
        )
    )


def test_equity_nvda_symbol():
    assert passes_high_conviction_pick(_base(symbol="NVDA", asset_class="EQUITY", strategy="x"))


def test_fwd_trades_gate():
    assert not passes_high_conviction_pick(_base(strat_fwd_trades=3, trust_tier="PROVEN"))


def test_score_floor():
    assert not passes_high_conviction_pick(_base(score=35, trust_tier="PROVEN"))


def test_short_bull_non_proven():
    assert not passes_high_conviction_pick(
        _base(direction="SHORT", regime="strong_bull", trust_tier="DEVELOPING")
    )


def test_wf_failing_blocked():
    assert not passes_high_conviction_pick(
        _base(wf_verdict="FAILING", trust_tier="PROVEN")
    )


def test_independent_groups_min_three(monkeypatch):
    import dashboard_hc_rules as mod

    base = mod.get_hc_gate_params()
    p = dict(base)
    p["independentGroupsMin"] = 3
    monkeypatch.setattr(mod, "get_hc_gate_params", lambda: p)
    assert mod.passes_high_conviction_pick(
        _base(
            source_systems="alpha_engine, luxalgo_filters, regime_terminal",
        )
    )
    assert not mod.passes_high_conviction_pick(
        _base(
            source_systems="alpha_engine, luxalgo_filters",
        )
    )


def test_stamped_tier_a_path_bypasses_gate8_when_contract_matches(monkeypatch):
    import dashboard_hc_rules as mod

    base = mod.get_hc_gate_params()
    p = dict(base)
    p["independentGroupsMin"] = 3
    p["tierSABypassIndependentConsensus"] = True
    monkeypatch.setattr(mod, "get_hc_gate_params", lambda: p)

    assert mod.passes_high_conviction_pick(
        _base(
            symbol="LINKUSDT",
            strategy="st_fear_greed_contrarian_v1",
            hf_conviction_tier="A",
            source_systems="alpha_engine",
        )
    )


def test_stamped_tier_b_path_still_requires_gate8_consensus(monkeypatch):
    import dashboard_hc_rules as mod

    base = mod.get_hc_gate_params()
    p = dict(base)
    p["independentGroupsMin"] = 3
    p["tierSABypassIndependentConsensus"] = True
    monkeypatch.setattr(mod, "get_hc_gate_params", lambda: p)

    assert not mod.passes_high_conviction_pick(
        _base(
            symbol="BTCUSDT",
            hf_conviction_tier="B",
            source_systems="alpha_engine",
        )
    )


def test_stamped_tier_b_bypass_reason_is_accepted_outside_legacy_contract():
    assert passes_high_conviction_pick(
        _base(
            symbol="ARBUSDT",
            hf_conviction_tier="B",
            hf_conviction_reasons=["bypass_tier_b_3of5_criteria_conf0.82"],
        )
    )


def test_gate9_correlation_registry():
    reg: dict[str, str] = {}
    eth = _base(symbol="ETHUSDT", trust_tier="PROVEN")
    sol = _base(symbol="SOLUSDT", trust_tier="PROVEN")
    assert passes_high_conviction_pick(eth, passed_registry=reg)
    reg["ETHUSDT"] = "LONG"
    assert not passes_high_conviction_pick(sol, passed_registry=reg)


def test_filter_ordered_matches_js_batch():
    rows = filter_high_conviction_ordered(
        [
            _base(symbol="ETHUSDT", trust_tier="PROVEN"),
            _base(symbol="SOLUSDT", trust_tier="PROVEN"),
        ]
    )
    assert len(rows) == 1
    assert rows[0]["symbol"] == "ETHUSDT"


# ---------------------------------------------------------------------------
# FOREX auto-relax + Gate 7b exception + per-asset-class threshold tests
# (2026-04-15: BUG FIX regression tests)
# ---------------------------------------------------------------------------

def _forex_base(**kwargs):
    d = {
        "symbol": "EURUSD=X",
        "asset_class": "FOREX",
        "strategy": "forex_rsi2",
        "trust_score": 5,
        "strat_fwd_wr": 0.60,
        "strat_fwd_trades": 25,
        "elite_score": 0,
        "trust_tier": "PROVEN",
        "direction": "LONG",
        "regime": "neutral",
        "confidence": 0.5,
        "score": 55,
    }
    d.update(kwargs)
    return d


def test_forex_fwd_wr_normal_threshold():
    """FOREX with fwdN >= 20 needs FWD WR >= 55%."""
    assert passes_high_conviction_pick(_forex_base(strat_fwd_wr=0.55, strat_fwd_trades=25))
    assert not passes_high_conviction_pick(_forex_base(strat_fwd_wr=0.54, strat_fwd_trades=25))


def test_forex_auto_relax_fwd_n_below_20():
    """FOREX auto-relax: fwdN < 20 lowers FWD WR threshold from 55% to 50%."""
    # fwdN=15 with FWD WR=52%: would fail at 55% but passes at 50% relaxed threshold
    assert passes_high_conviction_pick(_forex_base(strat_fwd_wr=0.52, strat_fwd_trades=15))
    # fwdN=15 with FWD WR=49%: fails even relaxed 50% threshold
    assert not passes_high_conviction_pick(_forex_base(strat_fwd_wr=0.49, strat_fwd_trades=15))
    # fwdN=19 (boundary -1): still relaxed
    assert passes_high_conviction_pick(_forex_base(strat_fwd_wr=0.51, strat_fwd_trades=19))
    # fwdN=20 (boundary): normal threshold applies, 51% fails
    assert not passes_high_conviction_pick(_forex_base(strat_fwd_wr=0.51, strat_fwd_trades=20))


def test_forex_auto_relax_bypasses_gate7b():
    """FOREX auto-relax bypasses Gate 7b (confidence 0.85-0.95 + fwdN < 30).

    A FOREX pick with fwdN=15 and confidence=0.88 would normally be killed by
    Gate 7b (0.85 <= 0.88 <= 0.95 AND 15 < 30), but the auto-relax flag
    tells Gate 7b to skip since we already acknowledged the small sample.
    """
    # fwdN=15, confidence=0.88: auto-relax active, Gate 7b skipped → PASS
    assert passes_high_conviction_pick(
        _forex_base(strat_fwd_trades=15, confidence=0.88, strat_fwd_wr=0.55)
    )
    # Same but fwdN=25 (auto-relax NOT active): Gate 7b applies, 25 < 30 → FAIL
    assert not passes_high_conviction_pick(
        _forex_base(strat_fwd_trades=25, confidence=0.88, strat_fwd_wr=0.55)
    )


def test_gate7b_applies_to_non_forex():
    """Gate 7b (confidence 0.85-0.95 + fwdN < 30) still applies to CRYPTO/EQUITY."""
    # CRYPTO: confidence=0.88, fwdN=15 → Gate 7b rejects (no auto-relax)
    assert not passes_high_conviction_pick(
        _base(confidence=0.88, strat_fwd_trades=15, trust_tier="PROVEN")
    )
    # CRYPTO: confidence=0.88, fwdN=35 → Gate 7b passes
    assert passes_high_conviction_pick(
        _base(confidence=0.88, strat_fwd_trades=35, trust_tier="PROVEN")
    )


def test_per_class_score_floors():
    """Per-asset-class score floors: CRYPTO >= 45, EQUITY >= 45, FOREX >= 40 (hybrid 2026-04-21).

    Pass cases use trust_score=8 to bypass Gate 2 (scoreCompoundFloor=50 + scoreCompoundTrustMin=8)
    so the test isolates the per-class floor gate rather than tripping Gate 2 first.
    """
    # CRYPTO score=44 fails (floor is 45)
    assert not passes_high_conviction_pick(
        _base(score=44, trust_score=8, trust_tier="PROVEN")
    )
    # CRYPTO score=45 passes
    assert passes_high_conviction_pick(
        _base(score=45, trust_score=8, trust_tier="PROVEN")
    )
    # EQUITY score=44 fails (floor is 45)
    assert not passes_high_conviction_pick(
        _base(asset_class="EQUITY", score=44, trust_score=8, trust_tier="PROVEN")
    )
    # EQUITY score=45 passes
    assert passes_high_conviction_pick(
        _base(asset_class="EQUITY", score=45, trust_score=8, trust_tier="PROVEN")
    )
    # FOREX score=39 fails (floor is 40)
    assert not passes_high_conviction_pick(
        _forex_base(score=39, trust_score=8, trust_tier="PROVEN")
    )
    # FOREX score=40 passes
    assert passes_high_conviction_pick(
        _forex_base(score=40, strat_fwd_trades=25, trust_score=8, trust_tier="PROVEN")
    )


def test_per_class_fwd_wr_floors():
    """Per-asset-class FWD WR floors: CRYPTO >= 40%, EQUITY >= 50%, FOREX >= 55% (hybrid 2026-04-21)."""
    # CRYPTO FWD WR=39% fails (floor is 40%)
    assert not passes_high_conviction_pick(
        _base(strat_fwd_wr=0.39, trust_tier="PROVEN")
    )
    # CRYPTO FWD WR=40% passes
    assert passes_high_conviction_pick(
        _base(strat_fwd_wr=0.40, trust_tier="PROVEN")
    )
    # EQUITY FWD WR=49% fails (floor is 50%)
    assert not passes_high_conviction_pick(
        _base(asset_class="EQUITY", strat_fwd_wr=0.49, trust_tier="PROVEN")
    )
    # EQUITY FWD WR=50% passes
    assert passes_high_conviction_pick(
        _base(asset_class="EQUITY", strat_fwd_wr=0.50, trust_tier="PROVEN")
    )


def test_forex_auto_relax_does_not_bypass_gate7a():
    """FOREX auto-relax bypasses Gate 7b but NOT Gate 7a (extreme confidence).

    Gate 7a rejects when confidence > 0.95 AND fwdN < 30.
    A FOREX pick with fwdN=15 and confidence=0.96 should be rejected by
    Gate 7a even though auto-relax is active, because Gate 7a catches
    overconfidence which is a separate concern from small samples.
    Note: fwdN=35 with confidence=0.96 passes Gate 7a (35 >= 30 = enough
    evidence to trust the confidence) — that is correct, not a bug.
    """
    # fwdN=15, confidence=0.96: auto-relax active but Gate 7a still rejects
    # (0.96 > 0.95 AND 15 < 30)
    assert not passes_high_conviction_pick(
        _forex_base(strat_fwd_trades=15, confidence=0.96, strat_fwd_wr=0.55)
    )
    # fwdN=25, confidence=0.96: no auto-relax (25 >= 20), Gate 7a rejects
    # (0.96 > 0.95 AND 25 < 30)
    assert not passes_high_conviction_pick(
        _forex_base(strat_fwd_trades=25, confidence=0.96, strat_fwd_wr=0.55)
    )
    # fwdN=35, confidence=0.96: Gate 7a does NOT reject (35 >= 30), passes
    assert passes_high_conviction_pick(
        _forex_base(strat_fwd_trades=35, confidence=0.96, strat_fwd_wr=0.55)
    )


def test_forex_gate7b_upper_boundary():
    """FOREX Gate 7b: fwdN=30 with confidence in 0.85-0.95 band should PASS.

    Gate 7b rejects when confidence in [0.85, 0.95] AND fwdN < 30.
    At exactly fwdN=30, the gate should pass (no auto-relax needed since N>=20).
    """
    # fwdN=30, confidence=0.88: meets Gate 7b threshold (30 >= 30) → PASS
    assert passes_high_conviction_pick(
        _forex_base(strat_fwd_trades=30, confidence=0.88, strat_fwd_wr=0.55)
    )
    # fwdN=29, confidence=0.88: fails Gate 7b (29 < 30) and no auto-relax (29 >= 20)
    assert not passes_high_conviction_pick(
        _forex_base(strat_fwd_trades=29, confidence=0.88, strat_fwd_wr=0.55)
    )


def test_forex_relaxed_wr_config_override(monkeypatch):
    """Config override: forexRelaxedWRMinPct can be changed from default 50 to e.g. 45."""
    import dashboard_hc_rules as mod

    base = mod.get_hc_gate_params()
    p = dict(base)
    p["forexRelaxedWRMinPct"] = 45  # relax to 45% instead of default 50%
    monkeypatch.setattr(mod, "get_hc_gate_params", lambda: p)

    # fwdN=15, FWD WR=46%: passes with relaxed 45% threshold
    assert mod.passes_high_conviction_pick(
        _forex_base(strat_fwd_wr=0.46, strat_fwd_trades=15)
    )
    # fwdN=15, FWD WR=44%: fails even relaxed 45% threshold
    assert not mod.passes_high_conviction_pick(
        _forex_base(strat_fwd_wr=0.44, strat_fwd_trades=15)
    )
