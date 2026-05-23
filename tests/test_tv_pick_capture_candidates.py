"""Tests for M-051 candidate-attribution wiring in tv_pick_capture.

Proves a captured TV fill inherits the matching candidate's
``models_consulted`` by bare-symbol when the fill carries none of its own —
so the AI Leaderboard ranks the engines that voted the placed trade.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tools.swarm.tv_pick_capture import (  # noqa: E402
    _bare_symbol,
    load_candidate_attribution,
    normalize_tv_fill,
)


# ---- _bare_symbol --------------------------------------------------------

def test_bare_symbol_strips_exchange_prefix():
    assert _bare_symbol("BINANCE:BTCUSDT") == "BTCUSDT"
    assert _bare_symbol("btcusdt") == "BTCUSDT"
    assert _bare_symbol(None) == ""
    assert _bare_symbol("  NASDAQ:AMD ") == "AMD"


# ---- load_candidate_attribution ------------------------------------------

def test_load_candidate_attribution_builds_symbol_map(tmp_path):
    cands = {
        "candidates": [
            {"symbol": "BINANCE:BTCUSDT",
             "models_consulted": [{"underlying_model": "deepseek-chat"}]},
            {"symbol": "ETHUSDT",
             "models_consulted": [{"underlying_model": "llama-3.3-70b"}]},
        ]
    }
    p = tmp_path / "cands.json"
    p.write_text(json.dumps(cands), encoding="utf-8")
    m = load_candidate_attribution(p)
    assert m["BTCUSDT"] == [{"underlying_model": "deepseek-chat"}]
    assert m["ETHUSDT"] == [{"underlying_model": "llama-3.3-70b"}]


def test_load_candidate_attribution_missing_file_is_empty(tmp_path):
    assert load_candidate_attribution(tmp_path / "nope.json") == {}
    assert load_candidate_attribution(None) == {}


def test_load_candidate_attribution_bad_json_is_empty(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text("{not json", encoding="utf-8")
    assert load_candidate_attribution(p) == {}


def test_load_candidate_attribution_bare_list(tmp_path):
    p = tmp_path / "list.json"
    p.write_text(json.dumps(
        [{"symbol": "SOLUSDT", "models_consulted": [{"underlying_model": "x"}]}]),
        encoding="utf-8")
    m = load_candidate_attribution(p)
    assert m["SOLUSDT"] == [{"underlying_model": "x"}]


# ---- normalize_tv_fill inheritance ---------------------------------------

def test_fill_inherits_attribution_by_bare_symbol():
    cmap = {"BTCUSDT": [{"underlying_model": "deepseek-chat"}]}
    fill = {"symbol": "BINANCE:BTCUSDT", "side": "BUY", "price": 100.0}
    out = normalize_tv_fill(fill, candidate_map=cmap)
    assert out["models_consulted"] == [{"underlying_model": "deepseek-chat"}]


def test_fill_own_attribution_wins_over_candidate_map():
    cmap = {"BTCUSDT": [{"underlying_model": "deepseek-chat"}]}
    fill = {"symbol": "BTCUSDT", "side": "BUY", "price": 100.0,
            "models_consulted": [{"underlying_model": "own"}]}
    out = normalize_tv_fill(fill, candidate_map=cmap)
    assert out["models_consulted"] == [{"underlying_model": "own"}]


def test_fill_no_match_yields_empty_attribution():
    cmap = {"ETHUSDT": [{"underlying_model": "x"}]}
    fill = {"symbol": "BTCUSDT", "side": "BUY", "price": 100.0}
    out = normalize_tv_fill(fill, candidate_map=cmap)
    assert out["models_consulted"] == []


def test_normalize_without_candidate_map_unchanged():
    fill = {"symbol": "BTCUSDT", "side": "BUY", "price": 100.0}
    out = normalize_tv_fill(fill)
    assert out["models_consulted"] == []
