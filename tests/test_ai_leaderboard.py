"""Tests for tools/ai_attribution/build_ai_leaderboard.py."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from tools.ai_attribution.build_ai_leaderboard import (  # noqa: E402
    build, horizon_for, mine_research_proposers, wilson_ci,
)


def _pick(engine, asset_class, timeframe, pnl_pct, pid="p"):
    """Minimal swarm-pick record."""
    return {
        "pick_id": pid,
        "asset_class": asset_class,
        "timeframe": timeframe,
        "direction": "LONG",
        "symbol": "X",
        "models_consulted": [{"underlying_model": engine, "name": engine,
                              "role": "r", "vote": "LONG",
                              "confidence_0_100": 70, "timeframe": timeframe,
                              "justification_summary": "j"}],
        "outcome": {"pnl_pct": pnl_pct} if pnl_pct is not None else {},
    }


def _write(tmp_path, picks):
    p = tmp_path / "swarm_picks.json"
    p.write_text(json.dumps(picks), encoding="utf-8")
    return p


def test_horizon_buckets():
    assert horizon_for("5m") == "short"
    assert horizon_for("4H") == "medium"
    assert horizon_for("1w") == "long"
    assert horizon_for("weird") == "medium"  # unknown -> medium


def test_wilson_ci_bounds():
    lo, hi = wilson_ci(5, 10)
    assert 0 <= lo <= 50 <= hi <= 100
    assert wilson_ci(0, 0) == (0.0, 0.0)


def test_engine_fanout_and_wr(tmp_path):
    picks = [
        _pick("engine-a", "CRYPTO", "4H", 3.0, "1"),
        _pick("engine-a", "CRYPTO", "4H", -2.0, "2"),
        _pick("engine-a", "CRYPTO", "4H", 5.0, "3"),
        _pick("engine-b", "EQUITY", "1d", -1.0, "4"),
    ]
    payload = build(_write(tmp_path, picks))
    assert payload["totals"]["resolved"] == 4
    assert payload["totals"]["engines"] == 2
    engines = {e["engine"]: e for e in payload["engines"]}
    a = engines["engine-a"]["overall"]
    assert a["n"] == 3 and a["wins"] == 2 and a["losses"] == 1
    assert a["wr"] == pytest.approx(66.7, abs=0.1)
    # PF = win_pnl(8) / loss_pnl(2) = 4.0
    assert a["pf"] == pytest.approx(4.0, abs=0.01)


def test_unresolved_excluded(tmp_path):
    picks = [
        _pick("eng", "CRYPTO", "1h", 2.0, "1"),
        _pick("eng", "CRYPTO", "1h", None, "2"),  # unresolved
    ]
    payload = build(_write(tmp_path, picks))
    eng = payload["engines"][0]["overall"]
    assert eng["n"] == 1  # only the resolved pick counts toward WR/PF
    assert eng["total_picks"] == 2  # both counted as attributed


def test_small_n_is_building_not_ranked(tmp_path):
    payload = build(_write(tmp_path, [_pick("eng", "CRYPTO", "4H", 1.0)]))
    o = payload["engines"][0]["overall"]
    assert o["classification"] == "building"
    assert o["rank_eligible"] is False


def test_horizon_split_in_output(tmp_path):
    picks = [
        _pick("eng", "CRYPTO", "5m", 1.0, "1"),    # short
        _pick("eng", "CRYPTO", "4H", 1.0, "2"),    # medium
        _pick("eng", "CRYPTO", "1w", -1.0, "3"),   # long
    ]
    payload = build(_write(tmp_path, picks))
    hz = payload["engines"][0]["by_horizon"]
    assert set(hz.keys()) == {"short", "medium", "long"}
    assert hz["short"]["n"] == 1


def test_empty_pick_book(tmp_path):
    payload = build(_write(tmp_path, []), research_dir=tmp_path / "none")
    assert payload["totals"]["picks"] == 0
    assert payload["totals"]["resolved"] == 0
    assert payload["totals"]["engines"] == 0
    assert payload["engines"] == []


def _write_research(root, cls, run, candidates):
    d = root / cls / f"run_{run}"
    d.mkdir(parents=True, exist_ok=True)
    (d / "p2_candidates.json").write_text(json.dumps(candidates),
                                          encoding="utf-8")


def test_mine_research_proposers_counts_by_engine(tmp_path):
    _write_research(tmp_path, "bond", "A", [
        {"proposed_by_engine": "cerebras", "asset_class": "BOND"},
        {"proposed_by_engine": "cerebras", "asset_class": "BOND"},
        {"proposed_by_engine": "xai", "asset_class": "BOND"},
    ])
    _write_research(tmp_path, "crypto", "B", [
        {"proposed_by_engine": "cerebras", "asset_class": "CRYPTO"},
    ])
    res = mine_research_proposers(tmp_path)
    assert res["total_candidates"] == 4
    assert res["engines"]["cerebras"]["total"] == 3
    assert res["engines"]["cerebras"]["by_asset_class"] == {"BOND": 2, "CRYPTO": 1}
    assert res["engines"]["xai"]["total"] == 1


def test_mine_research_proposers_missing_dir(tmp_path):
    res = mine_research_proposers(tmp_path / "does_not_exist")
    assert res == {"engines": {}, "total_candidates": 0}


def test_build_includes_research_proposers(tmp_path):
    _write_research(tmp_path / "research", "etf", "C", [
        {"proposed_by_engine": "deepseek", "asset_class": "ETF"},
    ])
    payload = build(_write(tmp_path, [_pick("eng", "CRYPTO", "4H", 1.0)]),
                    research_dir=tmp_path / "research")
    assert payload["totals"]["research_candidates"] == 1
    assert payload["research_proposers"]["deepseek"]["total"] == 1


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
