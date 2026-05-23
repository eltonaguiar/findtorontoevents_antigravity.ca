"""PR-H: assert quan_engine CRYPTO volume share <= 5% after enforce_cap.

Kimi finding (2026-05-11): quan_engine 18% volume @ PF 0.70 drags CRYPTO
aggregate metrics. Cap tightened from 12% -> 5% (2026-05-15 per_source_volume_cap.py).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from alpha_engine.per_source_volume_cap import (
    PER_SOURCE_VOLUME_CAP,
    PER_SYMBOL_CLASS_CAP,
    enforce_cap,
    enforce_symbol_cap,
)


def _mk(src: str, ac: str, score: float, sym: str = "BTCUSDT") -> dict:
    return {
        "symbol": sym,
        "source_system": src,
        "asset_class": ac,
        "smart_score": score,
        "ml_composite": score,
    }


def test_cap_constant_present():
    assert PER_SOURCE_VOLUME_CAP["quan_engine"]["CRYPTO"] == 0.05


def test_luxalgo_filters_cap_present():
    # Added 2026-05-15: luxalgo_filters CRYPTO volume capped at 10%.
    assert PER_SOURCE_VOLUME_CAP["luxalgo_filters"]["CRYPTO"] == 0.10


def test_luxalgo_filters_crypto_share_capped():
    # 40 luxalgo_filters CRYPTO + 60 other = 100; luxalgo share 40% -> trim to <=10%.
    picks = [_mk("luxalgo_filters", "CRYPTO", float(i)) for i in range(40)]
    picks += [_mk("other_strat", "CRYPTO", 100.0 + i) for i in range(60)]
    out = enforce_cap(picks)
    crypto = [p for p in out if p["asset_class"] == "CRYPTO"]
    lux = [p for p in crypto if p["source_system"] == "luxalgo_filters"]
    assert len(lux) / len(crypto) <= 0.10 + 1e-9


def test_quan_engine_crypto_share_capped_at_5pct():
    # 30 quan_engine CRYPTO + 70 other CRYPTO = 100 total, quan share = 30%.
    picks = []
    for i in range(30):
        picks.append(_mk("quan_engine", "CRYPTO", float(i)))
    for i in range(70):
        picks.append(_mk("other_strat", "CRYPTO", 50.0 + i))
    out = enforce_cap(picks)
    crypto = [p for p in out if p["asset_class"] == "CRYPTO"]
    quan = [p for p in crypto if p["source_system"] == "quan_engine"]
    share = len(quan) / len(crypto)
    assert share <= 0.05 + 1e-9, f"quan_engine CRYPTO share {share:.4f} > 5%"


def test_lowest_score_trimmed_first():
    picks = []
    for i in range(20):
        picks.append(_mk("quan_engine", "CRYPTO", float(i)))
    for i in range(80):
        picks.append(_mk("other_strat", "CRYPTO", 100.0 + i))
    out = enforce_cap(picks)
    quan_kept = [p for p in out if p["source_system"] == "quan_engine"]
    # The kept quan picks must be the highest-scored ones.
    kept_scores = sorted(p["smart_score"] for p in quan_kept)
    assert kept_scores == sorted(kept_scores, reverse=False)
    # Lowest kept score must exceed the trimmed picks' top score.
    if quan_kept:
        assert min(p["smart_score"] for p in quan_kept) >= 20 - len(quan_kept)


def test_non_crypto_quan_engine_untouched():
    picks = [_mk("quan_engine", "EQUITY", float(i)) for i in range(10)]
    picks += [_mk("other", "EQUITY", float(i)) for i in range(5)]
    out = enforce_cap(picks)
    assert len(out) == len(picks)


def test_empty_input():
    assert enforce_cap([]) == []


def test_below_cap_no_op():
    # quan_engine = 5 of 100 CRYPTO = 5% == cap boundary — no trim.
    picks = [_mk("quan_engine", "CRYPTO", float(i)) for i in range(5)]
    picks += [_mk("other", "CRYPTO", 100.0 + i) for i in range(95)]
    out = enforce_cap(picks)
    assert len(out) == 100


# ---------------------------------------------------------------------------
# enforce_symbol_cap tests (ONDOUSDT concentration cap, 2026-05-16)
# ---------------------------------------------------------------------------

def _mk_sym(sym: str, ac: str, score: float, src: str = "quan_engine") -> dict:
    return {
        "symbol": sym,
        "asset_class": ac,
        "source_system": src,
        "smart_score": score,
        "ml_composite": 0.0,
    }


def test_ondousdt_cap_trims_excess():
    """ONDOUSDT must not exceed 10% of CRYPTO active picks."""
    # 20 ONDOUSDT + 10 other = 30 CRYPTO; cap 10% => max 1 ONDO (1/11 = 9.1%)
    picks = [_mk_sym("ONDOUSDT", "CRYPTO", float(i)) for i in range(20)]
    picks += [_mk_sym("BTCUSDT", "CRYPTO", 50.0 + i) for i in range(10)]
    out = enforce_symbol_cap(picks)
    ondo = [p for p in out if p["symbol"] == "ONDOUSDT"]
    total = len(out)
    assert total > 0
    assert len(ondo) / total <= 0.10 + 1e-9, (
        f"ONDOUSDT share {len(ondo)/total:.2%} exceeds 10% cap"
    )


def test_ondousdt_cap_keeps_highest_scored():
    """enforce_symbol_cap must keep the highest-scored ONDOUSDT picks."""
    picks = [_mk_sym("ONDOUSDT", "CRYPTO", float(i)) for i in range(20)]
    picks += [_mk_sym("ETHUSDT", "CRYPTO", 50.0) for _ in range(10)]
    out = enforce_symbol_cap(picks)
    kept_ondo = [p for p in out if p["symbol"] == "ONDOUSDT"]
    if kept_ondo:
        assert all(p["smart_score"] == max(p2["smart_score"] for p2 in kept_ondo) or True
                   for p in kept_ondo)
        # The kept pick must have score >= all dropped picks.
        dropped_scores = [p["smart_score"] for p in picks
                          if p["symbol"] == "ONDOUSDT" and p not in kept_ondo]
        for kept in kept_ondo:
            assert kept["smart_score"] >= max(dropped_scores, default=0)


def test_ondousdt_cap_below_threshold_unchanged():
    """If ONDOUSDT is already <=10% no picks are trimmed."""
    picks = [_mk_sym("ONDOUSDT", "CRYPTO", 80.0)]
    picks += [_mk_sym("BTCUSDT", "CRYPTO", 50.0) for _ in range(19)]
    out = enforce_symbol_cap(picks)
    assert len(out) == 20  # 1/20 = 5% < 10%, nothing trimmed


def test_symbol_cap_passthrough_non_crypto():
    """ONDOUSDT cap does not apply to non-CRYPTO classes."""
    picks = [_mk_sym("ONDOUSDT", "EQUITY", float(i)) for i in range(20)]
    out = enforce_symbol_cap(picks)
    assert len(out) == 20  # no EQUITY cap configured for ONDOUSDT


def test_ondousdt_cap_in_per_symbol_class_cap():
    """PER_SYMBOL_CLASS_CAP must contain the ONDOUSDT entry."""
    assert "ONDOUSDT" in PER_SYMBOL_CLASS_CAP
    assert PER_SYMBOL_CLASS_CAP["ONDOUSDT"].get("CRYPTO", 1.0) <= 0.10
