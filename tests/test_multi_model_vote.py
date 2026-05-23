"""Tests for tools/ai_attribution/multi_model_vote.py (M-051)."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from tools.ai_attribution.multi_model_vote import (  # noqa: E402
    _parse_vote, consensus, gather_votes,
)


class FakeClient:
    """Injectable stand-in for swarm_v2 LLMClient — no network."""

    # provider -> canned reply
    REPLIES = {
        "deepseek": '{"vote":"LONG","confidence":72,"rationale":"uptrend"}',
        "groq": 'sure: {"vote":"LONG","confidence":60,"rationale":"momentum"}',
        "cerebras": '{"vote":"SHORT","confidence":55,"rationale":"overbought"}',
        "openrouter": "no json here",          # junk -> skipped
        "deadkey": None,                        # unavailable
    }

    def __init__(self, provider=None, model=None, timeout=60.0):
        self.provider = provider
        self.model = f"{provider}-model"
        self.available = provider in self.REPLIES and provider != "deadkey"

    def complete(self, prompt, system=None, max_tokens=4000, temperature=0.2):
        return self.REPLIES.get(self.provider)


def test_parse_vote_plain_json():
    v = _parse_vote('{"vote":"LONG","confidence":80,"rationale":"x"}')
    assert v == {"vote": "LONG", "confidence": 80, "rationale": "x"}


def test_parse_vote_embedded_json():
    v = _parse_vote('here is my call {"vote":"short","confidence":40,"rationale":"y"}')
    assert v["vote"] == "SHORT" and v["confidence"] == 40


def test_parse_vote_clamps_confidence():
    assert _parse_vote('{"vote":"PASS","confidence":999}')["confidence"] == 100
    assert _parse_vote('{"vote":"PASS","confidence":-5}')["confidence"] == 0


def test_parse_vote_rejects_junk():
    assert _parse_vote("no json") is None
    assert _parse_vote('{"vote":"MAYBE"}') is None   # invalid vote
    assert _parse_vote(None) is None


def test_gather_votes_fans_to_providers_and_skips_bad():
    votes = gather_votes(
        "BTCUSDT", "CRYPTO", "4H",
        providers=("deepseek", "groq", "cerebras", "openrouter", "deadkey"),
        llm_factory=FakeClient,
    )
    # openrouter junk + deadkey unavailable -> 3 genuine votes
    assert len(votes) == 3
    models = {v["underlying_model"] for v in votes}
    assert models == {"deepseek-model", "groq-model", "cerebras-model"}
    for v in votes:
        assert set(v) == {"name", "role", "underlying_model", "vote",
                          "confidence_0_100", "timeframe",
                          "justification_summary"}
        assert v["vote"] in {"LONG", "SHORT", "PASS"}


def test_consensus_majority_and_score():
    votes = gather_votes("BTCUSDT", "CRYPTO", "4H",
                         providers=("deepseek", "groq", "cerebras"),
                         llm_factory=FakeClient)
    c = consensus(votes)
    assert c["direction"] == "LONG"        # 2 LONG vs 1 SHORT
    assert c["models_agreed"] == 2
    assert c["models_voted"] == 3
    assert 0 < c["consensus_score"] <= 1


def test_consensus_empty():
    c = consensus([])
    assert c == {"direction": "PASS", "models_agreed": 0,
                 "models_voted": 0, "consensus_score": 0.0}


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
