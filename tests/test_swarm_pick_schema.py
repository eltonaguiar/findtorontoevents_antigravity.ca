"""Tests for tools/swarm/swarm_pick_schema.py validator + tier derivation."""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

import pytest

from tools.swarm.swarm_pick_schema import (
    SchemaError,
    append_picks,
    derive_consensus_tier,
    new_pick_id,
    update_pattern_tags,
    validate_model_vote,
    validate_pick,
    validate_store,
)


def _good_vote(**override):
    base = {
        "name": "MOMENTUM_TECH",
        "role": "trend-following",
        "underlying_model": "claude-opus-4-7",
        "vote": "LONG",
        "confidence_0_100": 75,
        "timeframe": "4H",
        "justification_summary": "trend intact",
    }
    base.update(override)
    return base


def _good_pick(**override):
    base = {
        "pick_id": new_pick_id(),
        "created_at": "2026-05-12T20:00:00-05:00",
        "session_id": "test_session",
        "account": "theswarm",
        "symbol": "BINANCE:LINKUSDT",
        "direction": "LONG",
        "entry": 10.0,
        "tp": 11.0,
        "sl": 9.0,
        "qty": 100,
        "qty_unit": "asset_units",
        "timeframe": "4H",
        "asset_class": "CRYPTO",
        "consensus_tier": "unanimous",
        "models_consulted": [_good_vote()],
        "models_agreed": 1,
        "models_voted": 1,
        "consensus_score": 1.0,
        "regime_at_entry": {"btc_regime": "RANGE", "vol_regime": "MID"},
        "outcome": None,
        "pattern_tags": [],
    }
    base.update(override)
    return base


def test_valid_pick_passes():
    validate_pick(_good_pick())


def test_long_inverted_tp_sl_rejected():
    p = _good_pick(tp=9.0, sl=11.0)  # inverted
    with pytest.raises(SchemaError, match="side-sanity"):
        validate_pick(p)


def test_short_sanity_enforced():
    p = _good_pick(direction="SHORT", entry=10.0, tp=9.0, sl=11.0)
    validate_pick(p)  # SHORT: sl>entry>tp -> valid
    p_bad = _good_pick(direction="SHORT", entry=10.0, tp=11.0, sl=9.0)
    with pytest.raises(SchemaError, match="side-sanity"):
        validate_pick(p_bad)


def test_missing_underlying_model_rejected():
    vote = _good_vote()
    del vote["underlying_model"]
    p = _good_pick(models_consulted=[vote])
    with pytest.raises(SchemaError, match="underlying_model"):
        validate_pick(p)


def test_invalid_account_rejected():
    p = _good_pick(account="random_unknown_acct")
    with pytest.raises(SchemaError, match="account"):
        validate_pick(p)


def test_invalid_vote_rejected():
    p = _good_pick(models_consulted=[_good_vote(vote="MAYBE")])
    with pytest.raises(SchemaError, match="vote"):
        validate_pick(p)


def test_confidence_out_of_range_rejected():
    p = _good_pick(models_consulted=[_good_vote(confidence_0_100=150)])
    with pytest.raises(SchemaError, match="confidence"):
        validate_pick(p)


def test_consensus_score_out_of_range_rejected():
    p = _good_pick(consensus_score=1.5)
    with pytest.raises(SchemaError, match="consensus_score"):
        validate_pick(p)


def test_duplicate_pick_ids_rejected():
    p1 = _good_pick()
    p2 = _good_pick()
    p2["pick_id"] = p1["pick_id"]
    with pytest.raises(SchemaError, match="duplicate"):
        validate_store([p1, p2])


def test_tier_derivation():
    assert derive_consensus_tier(1.0, 5) == "unanimous"
    assert derive_consensus_tier(0.95, 3) == "unanimous"
    assert derive_consensus_tier(0.94, 5) == "strong"
    assert derive_consensus_tier(0.67, 3) == "strong"
    assert derive_consensus_tier(0.50, 4) == "moderate"
    assert derive_consensus_tier(0.50, 2) == "moderate"
    assert derive_consensus_tier(0.40, 5) == "single"
    assert derive_consensus_tier(0.0, 5) == "control"
    # too-few-voters gets demoted
    assert derive_consensus_tier(1.0, 1) == "single"
    assert derive_consensus_tier(0.95, 2) == "moderate"


def test_outcome_exit_reason_validated():
    p = _good_pick(outcome={"exit_reason": "BAD_REASON"})
    with pytest.raises(SchemaError, match="exit_reason"):
        validate_pick(p)
    p_ok = _good_pick(outcome={"exit_reason": "TP_HIT", "exit_price": 11.0})
    validate_pick(p_ok)


def test_append_picks_idempotent(tmp_path):
    store = tmp_path / "store.json"
    p1 = _good_pick()
    p2 = _good_pick()
    r1 = append_picks(store, [p1, p2])
    assert r1 == {"added": 2, "skipped": 0, "total": 2}
    # re-append same picks → no-op
    r2 = append_picks(store, [p1, p2])
    assert r2 == {"added": 0, "skipped": 2, "total": 2}
    # append new pick → adds
    p3 = _good_pick()
    r3 = append_picks(store, [p3])
    assert r3 == {"added": 1, "skipped": 0, "total": 3}


def test_append_picks_validates_on_add(tmp_path):
    store = tmp_path / "store.json"
    bad = _good_pick(direction="LONG", tp=9.0, sl=11.0)  # inverted
    with pytest.raises(SchemaError, match="side-sanity"):
        append_picks(store, [bad])
    # store should not be created on failed validate
    assert not store.exists()


def test_update_pattern_tags(tmp_path):
    import json as _json
    store = tmp_path / "store.json"
    p1 = _good_pick(asset_class="CRYPTO", consensus_tier="unanimous",
                    regime_at_entry={"btc_regime": "RANGE", "vol_regime": "MID"})
    p2 = _good_pick(asset_class="EQUITY", consensus_tier="strong",
                    regime_at_entry={"btc_regime": "BULL", "vol_regime": "LOW"})
    append_picks(store, [p1, p2])
    patterns = tmp_path / "patterns.json"
    patterns.write_text(_json.dumps({
        "winning": [{"tier": "unanimous", "class": "CRYPTO", "regime": "RANGE"}],
        "losing": [{"tier": "strong", "class": "EQUITY", "regime": "BULL"}],
        "sparse": [],
    }))
    result = update_pattern_tags(store, patterns)
    assert result["tagged"] == 2
    assert result["winning"] == 1
    assert result["losing"] == 1
    # re-run is idempotent (no further changes)
    result2 = update_pattern_tags(store, patterns)
    assert result2["tagged"] == 0
    # verify tags landed
    loaded = _json.loads(store.read_text())
    crypto = next(p for p in loaded if p["asset_class"] == "CRYPTO")
    equity = next(p for p in loaded if p["asset_class"] == "EQUITY")
    assert crypto["pattern_tags"] == ["winning_cell"]
    assert equity["pattern_tags"] == ["losing_cell"]
