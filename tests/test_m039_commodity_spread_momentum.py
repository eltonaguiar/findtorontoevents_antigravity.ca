"""Tests for tools/research/commodity_spread_momentum.py (M-039)."""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.research.commodity_spread_momentum import (
    analyze_spread_picks,
    run_spread_analysis,
    SPREAD_PAIRS,
)


def _make_picks(symbol: str, n_won: int, n_lost: int, pnl_won=0.02, pnl_lost=-0.01) -> list[dict]:
    from datetime import datetime, timezone
    ts = datetime.now(timezone.utc).isoformat()
    picks = []
    for _ in range(n_won):
        picks.append({"symbol": symbol, "status": "WIN", "pnl_pct": pnl_won, "closed_at": ts})
    for _ in range(n_lost):
        picks.append({"symbol": symbol, "status": "LOSS", "pnl_pct": pnl_lost, "closed_at": ts})
    return picks


class TestAnalyzeSpreadPicks:
    def test_promising_when_long_beats_short(self):
        picks = (
            _make_picks("CL=F", 20, 5, pnl_won=0.03, pnl_lost=-0.01) +
            _make_picks("NG=F", 5, 20, pnl_won=0.01, pnl_lost=-0.03)
        )
        pair = {"name": "CL_NG", "long_symbol": "CL=F", "short_symbol": "NG=F",
                "description": "test", "economic_prior": "test"}
        result = analyze_spread_picks(picks, pair, lookback_days=365, min_n=10)
        assert result["verdict"] == "PROMISING"
        assert result["synthetic_spread_pnl"] > 0.005

    def test_negative_when_short_beats_long(self):
        picks = (
            _make_picks("CL=F", 5, 20, pnl_won=0.01, pnl_lost=-0.03) +
            _make_picks("NG=F", 20, 5, pnl_won=0.03, pnl_lost=-0.01)
        )
        pair = {"name": "CL_NG", "long_symbol": "CL=F", "short_symbol": "NG=F",
                "description": "test", "economic_prior": "test"}
        result = analyze_spread_picks(picks, pair, lookback_days=365, min_n=10)
        assert result["verdict"] == "NEGATIVE"

    def test_insufficient_data_when_below_min_n(self):
        picks = (
            _make_picks("CL=F", 3, 2) +
            _make_picks("NG=F", 3, 2)
        )
        pair = {"name": "CL_NG", "long_symbol": "CL=F", "short_symbol": "NG=F",
                "description": "test", "economic_prior": "test"}
        result = analyze_spread_picks(picks, pair, lookback_days=365, min_n=10)
        assert result["verdict"] == "INSUFFICIENT_DATA"

    def test_empty_picks_returns_insufficient(self):
        pair = SPREAD_PAIRS[0]
        result = analyze_spread_picks([], pair, lookback_days=90, min_n=10)
        assert result["verdict"] == "INSUFFICIENT_DATA"
        assert result["long"]["n"] == 0
        assert result["short"]["n"] == 0

    def test_spread_pnl_equals_long_minus_short(self):
        picks = (
            _make_picks("CL=F", 10, 10, pnl_won=0.04, pnl_lost=-0.02) +
            _make_picks("NG=F", 10, 10, pnl_won=0.01, pnl_lost=-0.01)
        )
        pair = {"name": "CL_NG", "long_symbol": "CL=F", "short_symbol": "NG=F",
                "description": "test", "economic_prior": "test"}
        result = analyze_spread_picks(picks, pair, lookback_days=365, min_n=10)
        expected_long_pnl = (10*0.04 + 10*(-0.02)) / 20
        expected_short_pnl = (10*0.01 + 10*(-0.01)) / 20
        assert abs(result["synthetic_spread_pnl"] - (expected_long_pnl - expected_short_pnl)) < 1e-6


class TestRunSpreadAnalysis:
    def test_output_has_required_keys(self):
        picks = (
            _make_picks("CL=F", 15, 5) + _make_picks("NG=F", 15, 5) +
            _make_picks("GC=F", 15, 5) + _make_picks("SI=F", 15, 5) +
            _make_picks("CT=F", 15, 5) + _make_picks("KC=F", 15, 5)
        )
        result = run_spread_analysis(picks, lookback_days=365)
        assert "generated_at" in result
        assert "config" in result
        assert "pairs" in result
        assert "summary" in result
        assert len(result["pairs"]) == len(SPREAD_PAIRS)

    def test_all_pairs_appear_in_output(self):
        result = run_spread_analysis([], lookback_days=90)
        pair_names = {p["pair"] for p in result["pairs"]}
        for pair in SPREAD_PAIRS:
            assert pair["name"] in pair_names

    def test_summary_categories_mutually_exclusive(self):
        picks = (
            _make_picks("CL=F", 20, 5, pnl_won=0.05, pnl_lost=-0.01) +
            _make_picks("NG=F", 20, 15, pnl_won=0.005, pnl_lost=-0.04)
        )
        result = run_spread_analysis(picks, lookback_days=365)
        all_in_summary = (
            result["summary"]["promising"] +
            result["summary"]["negative"] +
            result["summary"]["flat"] +
            result["summary"]["insufficient_data"]
        )
        # Each pair appears in exactly one category
        assert len(all_in_summary) == len(SPREAD_PAIRS)
        assert len(set(all_in_summary)) == len(all_in_summary)


import pytest
