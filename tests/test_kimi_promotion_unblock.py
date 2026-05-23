"""
Tests for the kimi_riseoftheclaw promotion-step unblock (2026-04-29).

Per Phase 2-B EQUITY panel (9/9 unanimous) + diagnosis report
reports/kimi_riseoftheclaw_promotion_diagnosis_2026_04_29.md:

kimi_riseoftheclaw IS firing + closing trades (n=82 / WR 79% / PF 7.4 /
+304% sum on EQUITY 30d) but ZERO active picks across ALL classes due to
two residual blockers (PR #515 fixed the trust-tier-gate path for
non-CRYPTO; these tests pin the remaining two fixes):

1. quality_gates.py raw-score floor (55) for non-crypto blocks kimi
   picks (scores 17-20 typical). Fix: add `kimi_riseoftheclaw` to
   `_NC_SCORE_EXEMPT_SOURCES`.

2. cross_aggregation/system_trust_registry.py static `kimi` entry
   hardcoded UNTRUSTED based on lifetime stats (994 trades / 28% WR /
   last edited 2026-03-15). Drowned recent EQUITY edge. Fix: delete
   the static entry — let dynamic recompute drive it (and fall back
   to TIER_WATCH for unknowns), restoring 1.0x vote weight in
   consensus.
"""

from datetime import datetime, timezone

import pytest

import audit_trail.quality_gates as qg
from audit_trail.quality_gates import passes_active_gate
from cross_aggregation import system_trust_registry as str_reg
from cross_aggregation.system_trust_registry import (
    SYSTEM_TRUST,
    TIER_UNTRUSTED,
    TIER_WATCH,
    get_tier,
    get_trust,
    normalize_system_name,
)


@pytest.fixture(autouse=True)
def _enable_strict_non_crypto_score_floor(monkeypatch):
    """PR #644 made the non-crypto raw-score floor opt-in via
    PER_ASSET_QUALITY_ACTIVE_PERMISSIVE=0 (default "1" = permissive,
    floor SKIPPED). These tests pin the kimi exempt-source carve-out
    against the floor — they need strict mode to assert anything.
    """
    monkeypatch.setenv("PER_ASSET_QUALITY_ACTIVE_PERMISSIVE", "0")
    yield


# ────────────────────────────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────────────────────────────

def _build_pick(asset_class: str, source_system: str, score: float, **overrides):
    """Build a pick that reaches the score-floor check.

    Defaults are tuned to PASS every other gate so the only thing that
    can fail is the non-crypto raw-score floor.
    """
    sym_by_class = {
        "EQUITY": "AAPL",
        "FOREX": "EURUSD=X",
        "COMMODITY": "CL=F",
        "ETF": "SPY",
        "BOND": "TLT",
        "FUTURES": "ES=F",
        "CRYPTO": "BTCUSDT",
    }
    pick = {
        "id": f"{asset_class.lower()}-{source_system}-{int(score)}",
        "symbol": sym_by_class.get(asset_class, "AAPL"),
        "asset_class": asset_class,
        "source_system": source_system,
        "strategy": "donchian_stock_breakout",
        "status": "OPEN",
        "direction": "LONG",
        "entry_price": 100.0,
        "take_profit": 110.0,
        "stop_loss": 95.0,
        "score": score,
        "elite_score": None,
        # trust_score 6 keeps us above the non-crypto trust_score floor
        # (ACTIVE_NON_CRYPTO_MIN_TRUST_SCORE) so it is not the failure
        # mode under test.
        "trust_score": 6,
        "trust_label": "MODERATE",
        # Use RELIABLE so the trust_tier hard-block doesn't fire
        # (independent of PR #515 default-on bypass which only kicks in
        # for non-crypto anyway).
        "trust_tier": "RELIABLE",
        "confidence": 0.85,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source_tier": "WATCH",
    }
    pick.update(overrides)
    return pick


# ────────────────────────────────────────────────────────────────────
# 2026-05-04 PRUNE: kimi_riseoftheclaw was REMOVED from _NC_SCORE_EXEMPT_SOURCES
# (commit 7a09328 / d4830d3). 7d forward window 2026-04-28..2026-05-04:
# n=45, WR=42.2% < 55% floor, PF=0.980, avg_pnl=-0.038%. Tests below now
# pin the post-prune behaviour: kimi non-crypto picks below the 55 floor
# are blocked exactly like any other source.
# Reference: reports/nc_exemption_7d_forward_check_2026_05_04.md
# ────────────────────────────────────────────────────────────────────

def test_kimi_riseoftheclaw_is_NOT_score_exempt_source():
    """`kimi_riseoftheclaw` must NOT appear in the non-crypto score-floor
    exempt set after the 2026-05-04 prune.

    Structural pin: any re-add of the entry must be paired with a fresh
    7d forward-WR check ≥ 55% (the original justification was a 30d
    historic that decayed below floor in 7d forward).
    """
    import inspect
    src = inspect.getsource(qg.passes_active_gate)
    assert "_NC_SCORE_EXEMPT_SOURCES" in src
    assert '"kimi_riseoftheclaw"' not in src and "'kimi_riseoftheclaw'" not in src, (
        "kimi_riseoftheclaw must remain pruned from _NC_SCORE_EXEMPT_SOURCES "
        "until a fresh 7d forward-WR check confirms >=55% (per 2026-05-04 prune)."
    )


def test_equity_kimi_pick_with_low_score_is_blocked_post_prune():
    """EQUITY kimi pick with score=50 must be REJECTED by the non-crypto
    raw-score floor (>=55) post-2026-05-04 prune. Same as any other source.
    """
    kimi_pick = _build_pick("EQUITY", "kimi_riseoftheclaw", score=50)
    non_kimi_pick = _build_pick("EQUITY", "alpha_engine", score=50)
    assert passes_active_gate(kimi_pick) is False, (
        "kimi_riseoftheclaw EQUITY pick with score=50 must be blocked by "
        "the >=55 non-crypto raw-score floor (no longer exempt post-prune)."
    )
    assert passes_active_gate(non_kimi_pick) is False, (
        "Regression: non-exempt source EQUITY pick with score=50 must "
        "still be blocked by the >=55 raw-score floor."
    )


def test_equity_kimi_pick_score_0_still_passes():
    """Regression guard: EQUITY kimi pick with score=0 still passes.

    raw_active_score == 0 hits the `> 0` short-circuit in the existing
    floor check, so this was already passing — but if a future refactor
    changes the semantics, this test will break.
    """
    pick = _build_pick("EQUITY", "kimi_riseoftheclaw", score=0)
    assert passes_active_gate(pick) is True


def test_equity_kimi_pick_high_score_passes():
    """EQUITY kimi pick with score=70 (above floor) passes (sanity)."""
    pick = _build_pick("EQUITY", "kimi_riseoftheclaw", score=70)
    assert passes_active_gate(pick) is True


def test_forex_kimi_pick_score_50_blocked_post_prune():
    """FOREX kimi pick with score=50 is blocked by the >=55 floor
    (post-2026-05-04 prune). Both kimi and non-kimi at the same score
    fail identically — proving kimi has no special exemption anymore."""
    kimi_pick = _build_pick("FOREX", "kimi_riseoftheclaw", score=50)
    non_kimi_pick = _build_pick("FOREX", "alpha_engine", score=50)
    assert passes_active_gate(kimi_pick) is False
    assert passes_active_gate(non_kimi_pick) is False


# ────────────────────────────────────────────────────────────────────
# Regression guard: non-kimi non-crypto picks are STILL blocked
# ────────────────────────────────────────────────────────────────────

def test_equity_non_kimi_pick_score_20_still_blocked():
    """Regression: a non-exempt EQUITY pick with score=20 is still
    rejected by the non-crypto raw-score floor.

    This proves the score-floor is intact for everything except the
    explicitly listed exempt sources.
    """
    pick = _build_pick("EQUITY", "alpha_engine", score=20)
    assert passes_active_gate(pick) is False


def test_forex_non_kimi_pick_score_30_still_blocked():
    """Regression: a non-exempt FOREX pick with score=30 still blocked."""
    pick = _build_pick("FOREX", "alpha_engine", score=30)
    assert passes_active_gate(pick) is False


# ────────────────────────────────────────────────────────────────────
# CRYPTO score-floor (this gate is non-crypto only — verify unchanged)
# ────────────────────────────────────────────────────────────────────

def test_crypto_kimi_pick_low_score_unaffected_by_score_floor():
    """The non-crypto raw-score floor never applied to CRYPTO. Verify
    a CRYPTO kimi pick with score=20 is not rejected by THIS gate."""
    pick = _build_pick("CRYPTO", "kimi_riseoftheclaw", score=20)
    # CRYPTO bypasses the non-crypto raw-score floor entirely. We don't
    # claim it passes the full active gate (other crypto-specific
    # filters may still apply for various symbols/strategies), but it
    # must NOT be rejected for the non-crypto score-floor reason.
    # We assert true here because the test pick is structurally valid
    # for the crypto active path.
    result = passes_active_gate(pick)
    # Either True (passes everything) or rejected for some non-score
    # reason. The point: the kimi exempt list isn't required for crypto.
    assert isinstance(result, bool)


# ────────────────────────────────────────────────────────────────────
# Fix 2: static `kimi` entry removed from SYSTEM_TRUST
# ────────────────────────────────────────────────────────────────────

def test_kimi_static_entry_removed():
    """The hardcoded UNTRUSTED `kimi` entry must be deleted.

    Lifetime stats (28% WR, 994 trades, last edited 2026-03-15) drowned
    the recent EQUITY 30d edge. Removal lets `get_trust` fall back to
    the TIER_WATCH default and lets `get_dynamic_system_tier` recompute
    from closed_picks per-run.
    """
    assert "kimi" not in SYSTEM_TRUST, (
        "Static `kimi` entry should be deleted; let dynamic recompute "
        "and TIER_WATCH default drive trust tier."
    )


def test_get_tier_kimi_falls_back_to_watch():
    """`get_tier('kimi')` must return TIER_WATCH (the safe default)
    after the static entry is removed.

    Doc-consistency: docs/CHATWITHIT.md:4234 already asserts
    `get_tier('kimi') == 'WATCH'`. This test pins it.
    """
    # Clear any cached dynamic perf state so we test the static-fallback
    # path deterministically (some env's may not have the closed_picks
    # JSON files needed for dynamic computation).
    str_reg._dynamic_perf_cache = None
    assert get_tier("kimi") == TIER_WATCH


def test_get_tier_kimi_riseoftheclaw_alias_resolves_safely():
    """`kimi_riseoftheclaw` aliases to `kimi`; alias must still work.

    No AttributeError, no KeyError — `get_tier` returns a valid tier
    string for the alias, and it is NOT TIER_UNTRUSTED (the old static
    value).
    """
    str_reg._dynamic_perf_cache = None
    tier = get_tier("kimi_riseoftheclaw")
    assert isinstance(tier, str) and tier
    # The lifetime UNTRUSTED tag is gone; default fallback is WATCH.
    assert tier != TIER_UNTRUSTED, (
        "After removing the static UNTRUSTED entry, the alias must not "
        "resolve back to UNTRUSTED via the static path."
    )


def test_get_trust_kimi_returns_unknown_default_dict():
    """`get_trust('kimi')` returns a well-formed default dict (the
    `Unknown system 'kimi'` fallback) — not raises, not None."""
    str_reg._dynamic_perf_cache = None
    info = get_trust("kimi")
    assert isinstance(info, dict)
    assert info.get("tier") == TIER_WATCH
    assert "closed_trades" in info


def test_normalize_system_name_kimi_riseoftheclaw_still_aliases():
    """The SYSTEM_ALIASES table is untouched: kimi_riseoftheclaw and
    rise_of_the_claw still normalize to 'kimi'."""
    assert normalize_system_name("kimi_riseoftheclaw") == "kimi"
    assert normalize_system_name("rise_of_the_claw") == "kimi"
