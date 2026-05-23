"""Tests for tools/ai_attribution/multi_model_pick_gen.py (M-051)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from tools.ai_attribution.multi_model_pick_gen import (  # noqa: E402
    generate_candidates, write_candidates,
)


def _vote(model, vote, conf=70):
    return {"name": f"{model}_analyst", "role": "trade_voter",
            "underlying_model": model, "vote": vote,
            "confidence_0_100": conf, "timeframe": "4H",
            "justification_summary": "j"}


def _fake_votes_factory(table):
    """Build a vote_fn that returns canned votes per symbol."""
    def _fn(symbol, asset_class, timeframe, context=""):
        return table.get(symbol, [])
    return _fn


def test_emits_candidate_on_majority_agreement():
    table = {
        "BTCUSDT": [_vote("deepseek-chat", "LONG"),
                    _vote("llama-3.3-70b", "LONG"),
                    _vote("gpt-oss", "SHORT")],
    }
    cands = generate_candidates(["BTCUSDT"], "CRYPTO", "4H",
                                vote_fn=_fake_votes_factory(table))
    assert len(cands) == 1
    c = cands[0]
    assert c["direction"] == "LONG"          # 2 LONG vs 1 SHORT
    assert c["models_agreed"] == 2
    assert c["status"] == "CANDIDATE"
    assert len(c["models_consulted"]) == 3
    assert c["pick_id"].startswith("mmcand-")


def test_skips_when_consensus_pass():
    table = {"X": [_vote("a", "PASS"), _vote("b", "PASS")]}
    cands = generate_candidates(["X"], vote_fn=_fake_votes_factory(table))
    assert cands == []


def test_skips_when_below_min_agreement():
    # 3 different votes -> top agreement is 1 < MIN_AGREEMENT(2)
    table = {"X": [_vote("a", "LONG"), _vote("b", "SHORT"), _vote("c", "PASS")]}
    cands = generate_candidates(["X"], vote_fn=_fake_votes_factory(table))
    assert cands == []


def test_skips_symbol_with_no_votes():
    cands = generate_candidates(["DEADSYM"],
                                vote_fn=_fake_votes_factory({}))
    assert cands == []


def test_multiple_symbols():
    table = {
        "A": [_vote("m1", "LONG"), _vote("m2", "LONG")],
        "B": [_vote("m1", "PASS"), _vote("m2", "PASS")],     # skipped
        "C": [_vote("m1", "SHORT"), _vote("m2", "SHORT")],
    }
    cands = generate_candidates(["A", "B", "C"],
                                vote_fn=_fake_votes_factory(table))
    assert {c["symbol"] for c in cands} == {"A", "C"}


def test_write_candidates_sidecar(tmp_path):
    table = {"A": [_vote("m1", "LONG"), _vote("m2", "LONG")]}
    cands = generate_candidates(["A"], vote_fn=_fake_votes_factory(table))
    out = tmp_path / "cand.json"
    write_candidates(cands, out)
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["count"] == 1
    assert payload["schema_version"] == "v1"
    assert "NOT the live" in payload["note"]
    assert payload["candidates"][0]["symbol"] == "A"


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
