import os
import sys

import pytest

ALPHA_DIR = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, ALPHA_DIR)

import hindsight_learner as hl


def test_rank_true_top_filters_and_sorts_positive_returns():
    return_map = {
        "BTCUSDT": {"symbol": "BTCUSDT", "forward_return_pct": 1.2},
        "ETHUSDT": {"symbol": "ETHUSDT", "forward_return_pct": -0.3},
        "SOLUSDT": {"symbol": "SOLUSDT", "forward_return_pct": 2.5},
        "XRPUSDT": {"symbol": "XRPUSDT", "forward_return_pct": 0.0},
        "APTUSDT": {"symbol": "APTUSDT", "forward_return_pct": 0.8},
    }

    top2 = hl._rank_true_top(return_map, top_k=2)
    assert [row["symbol"] for row in top2] == ["SOLUSDT", "BTCUSDT"]

    top5 = hl._rank_true_top(return_map, top_k=5)
    assert [row["symbol"] for row in top5] == ["SOLUSDT", "BTCUSDT", "APTUSDT"]


def test_compute_overlap_metrics_reports_precision_recall_and_capture():
    return_map = {
        "SOLUSDT": {"symbol": "SOLUSDT", "forward_return_pct": 4.0},
        "BTCUSDT": {"symbol": "BTCUSDT", "forward_return_pct": 2.0},
        "ETHUSDT": {"symbol": "ETHUSDT", "forward_return_pct": -1.0},
    }
    true_top = [
        {"symbol": "SOLUSDT", "forward_return_pct": 4.0},
        {"symbol": "BTCUSDT", "forward_return_pct": 2.0},
    ]

    metrics = hl._compute_overlap_metrics(["SOLUSDT", "ETHUSDT"], true_top, return_map)
    assert metrics["overlap_symbols"] == ["SOLUSDT"]
    assert metrics["precision_at_k"] == pytest.approx(0.5)
    assert metrics["recall_at_k"] == pytest.approx(0.5)
    assert metrics["winner_capture_pct"] == pytest.approx(4.0 / 6.0, abs=1e-4)
    assert metrics["our_avg_forward_return_pct"] == pytest.approx(1.5, abs=1e-4)
    assert metrics["true_avg_forward_return_pct"] == pytest.approx(3.0, abs=1e-4)

    empty_metrics = hl._compute_overlap_metrics([], [], {})
    assert empty_metrics["precision_at_k"] == 0.0
    assert empty_metrics["recall_at_k"] == 0.0
    assert empty_metrics["winner_capture_pct"] == 0.0


def test_classify_miss_reason_distinguishes_universe_vs_rank_vs_no_signal():
    snapshot = {
        "top_k": 2,
        "static_universe_symbols": ["BTCUSDT", "ETHUSDT", "SOLUSDT"],
        "top_candidates": [
            {"binance_symbol": "BTCUSDT", "rank": 1},
            {"binance_symbol": "SOLUSDT", "rank": 3},
        ],
    }

    assert hl._classify_miss_reason("WIFUSDT", snapshot) == "out_of_static_universe"
    assert hl._classify_miss_reason("SOLUSDT", snapshot) == "ranked_below_cutoff"
    assert hl._classify_miss_reason("ETHUSDT", snapshot) == "no_long_signal"


def test_load_candidate_picks_dedupes_same_symbol_and_keeps_best_score(tmp_path, monkeypatch):
    first = tmp_path / "first.json"
    second = tmp_path / "second.json"
    first.write_text(
        """
[
  {
    "symbol": "TRX-USD",
    "elite_score": 50,
    "entry_price": 0.25,
    "take_profit": 0.28,
    "stop_loss": 0.24,
    "direction": "BUY",
    "strategy": "alpha_a"
  }
]
""".strip(),
        encoding="utf-8",
    )
    second.write_text(
        """
{
  "picks": [
    {
      "symbol": "TRXUSDT",
      "elite_score": 70,
      "entry_price": 0.251,
      "take_profit": 0.285,
      "stop_loss": 0.245,
      "direction": "LONG",
      "strategy": "alpha_b"
    },
    {
      "symbol": "ETHUSDT",
      "elite_score": 99,
      "direction": "SHORT",
      "strategy": "ignore_short"
    }
  ]
}
""".strip(),
        encoding="utf-8",
    )

    monkeypatch.setattr(hl, "ACTIVE_PICK_FILES", (first, second))
    candidates = hl.load_candidate_picks()

    assert len(candidates) == 1
    assert candidates[0]["binance_symbol"] == "TRXUSDT"
    assert candidates[0]["score"] == 70
    assert set(candidates[0]["strategies"]) == {"alpha_a", "alpha_b"}


def test_analyze_long_path_finds_pullback_entry_and_peak_return():
    bars = [
        {"open_time": 0, "open": 100.0, "high": 101.0, "low": 99.0, "close": 100.0},
        {"open_time": 300000, "open": 100.0, "high": 101.0, "low": 97.0, "close": 99.0},
        {"open_time": 600000, "open": 99.0, "high": 105.0, "low": 98.0, "close": 104.0},
        {"open_time": 900000, "open": 104.0, "high": 112.0, "low": 103.0, "close": 110.0},
        {"open_time": 1200000, "open": 110.0, "high": 111.0, "low": 108.0, "close": 109.0},
    ]

    analysis = hl._analyze_long_path(bars, snapshot_price=100.0, entry_window_ratio=0.5)

    assert analysis["ideal_entry_price"] == pytest.approx(97.0)
    assert analysis["early_pullback_entry_price"] == pytest.approx(97.0)
    assert analysis["entry_improvement_pct"] == pytest.approx(3.0, abs=1e-4)
    assert analysis["snapshot_to_peak_pct"] == pytest.approx(12.0, abs=1e-4)
    assert analysis["time_to_peak_min"] == pytest.approx(15.0, abs=1e-4)
    assert analysis["best_arm_from_snapshot"]
    assert analysis["best_arm_from_pullback"]


def test_simulate_long_arm_is_conservative_when_same_bar_hits_tp_and_sl():
    bars = [
        {"open_time": 0, "open": 100.0, "high": 100.05, "low": 99.95, "close": 100.0},
        {"open_time": 300000, "open": 100.0, "high": 100.04, "low": 99.96, "close": 100.0},
        {"open_time": 600000, "open": 100.0, "high": 101.0, "low": 99.0, "close": 100.2},
    ]

    atr = hl._compute_atr_from_bars(bars)
    result = hl._simulate_long_arm(bars, entry_price=100.0, start_index=2, atr=atr, arm_index=0)

    assert atr > 0
    assert result["outcome"] == "SL_HIT"
    assert result["realized_pnl_pct"] < 0
