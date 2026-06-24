"""B5 (Forward-Track Cell Selector, 2026-06-24) invariants."""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tools.select_forward_track_candidates import (
    DEFAULT_TF_MAP,
    INTRABAR_EXIT_REASONS,
    PF_CAP,
    TF_RE,
    bucket_rows,
    emit_strategy_module,
    extract_tf,
    filter_and_rank,
    load_pick_funnel,
    strategy_base,
)


# ─── A. TF extraction ─────────────────────────────────────────────────────────
@pytest.mark.parametrize(
    "name, expected_tf",
    [
        ("ml_enhanced_RENDERUSDT_4h_D",          "4h"),
        ("ml_enhanced_TRXUSDT_1h_D",              "1h"),
        ("ml_enhanced_FETUSDT_15m_B",            "15m"),
        ("ml_enhanced_INJUSDT_1d_A",             "1d"),
        ("cta_donchian_55",                      "1d"),       # DEFAULT_TF_MAP exact lookup
        ("luxalgo_confluence",                   "4h"),       # DEFAULT_TF_MAP exact lookup
        ("ml_enhanced_BTCUSDT",                  "1d"),
        ("prediction_market_consensus",          "n/a"),
        ("completely_unknown_xyz_strategy",      "UNKNOWN"),
    ],
)
def test_a_extract_tf(name: str, expected_tf: str) -> None:
    assert extract_tf(name) == expected_tf, f"{name!r}: expected {expected_tf}, got {extract_tf(name)}"


def test_a_extract_tf_empty() -> None:
    assert extract_tf("") == "UNKNOWN"
    assert extract_tf(None) == "UNKNOWN"  # type: ignore[arg-type]


# ─── B. strategy_base ─────────────────────────────────────────────────────────
@pytest.mark.parametrize(
    "name, expected",
    [
        ("ml_enhanced_RENDERUSDT_4h_D", "ml_enhanced_RENDERUSDT_D"),
        ("ml_enhanced_TRXUSDT_1h_D",    "ml_enhanced_TRXUSDT_D"),
        ("ml_enhanced_BTCUSDT",         "ml_enhanced_BTCUSDT"),
        ("cta_donchian_55",             "cta_donchian_55"),
        ("luxalgo_confluence",          "luxalgo_confluence"),
        ("",                            ""),
    ],
)
def test_b_strategy_base(name: str, expected: str) -> None:
    assert strategy_base(name) == expected


# ─── C. PF / WR corner cases ──────────────────────────────────────────────────
def test_c_pf_cap_when_losses_zero_and_wins_positive() -> None:
    """PF must cap at PF_CAP when losses=0 and wins>0 (no division-by-zero blowup)."""
    rows = [
        {"pick_id": "p1", "symbol": "BTCUSDT", "strategy": "ml_enhanced_BTCUSDT", "asset_class": "CRYPTO",
         "pnl_pct": 1.5, "exit_reason": "TP_HIT", "status": "CLOSED",
         "closed_at": "2026-06-01", "source_system": "alpha_engine"},
        {"pick_id": "p2", "symbol": "BTCUSDT", "strategy": "ml_enhanced_BTCUSDT", "asset_class": "CRYPTO",
         "pnl_pct": 0.8, "exit_reason": "TP_HIT", "status": "CLOSED",
         "closed_at": "2026-06-02", "source_system": "alpha_engine"},
    ]
    cells = bucket_rows(rows, cell_mode="tier_b")
    assert len(cells) == 1
    c = list(cells.values())[0]
    assert c["wins"] == 2
    assert c["losses"] == 0
    assert c["pf"] == PF_CAP, f"PF must cap at {PF_CAP} on wins only; got {c['pf']}"
    assert c["wr"] == 1.0


def test_c_pf_zero_when_no_intrabar_outcomes() -> None:
    rows = [
        {"pick_id": "p1", "symbol": "AAPL", "strategy": "stocks_rsi2_pullback", "asset_class": "EQUITY",
         "pnl_pct": 0.5, "exit_reason": "TIME_EXIT", "status": "CLOSED",
         "closed_at": "2026-06-01", "source_system": "alpha_engine"},
    ]
    cells = bucket_rows(rows, cell_mode="tier_b")
    c = list(cells.values())[0]
    assert c["n_intrabar"] == 0
    assert c["wr"] == 0.0
    assert c["pf"] == 0.0


def test_c_wr_excludes_time_exits_and_unresolved() -> None:
    """TIME_EXIT rows should NOT count toward intrabar wr; only TP_HIT/SL_HIT do."""
    rows = [
        {"pick_id": "tp1", "symbol": "X", "strategy": "cta_donchian_55", "asset_class": "EQUITY",
         "pnl_pct": 1.0, "exit_reason": "TP_HIT", "status": "CLOSED",
         "closed_at": "2026-06-01", "source_system": "a"},
        {"pick_id": "te1", "symbol": "X", "strategy": "cta_donchian_55", "asset_class": "EQUITY",
         "pnl_pct": 5.0, "exit_reason": "TIME_EXIT", "status": "CLOSED",
         "closed_at": "2026-06-02", "source_system": "a"},
        {"pick_id": "sl1", "symbol": "X", "strategy": "cta_donchian_55", "asset_class": "EQUITY",
         "pnl_pct": -1.0, "exit_reason": "SL_HIT", "status": "CLOSED",
         "closed_at": "2026-06-03", "source_system": "a"},
    ]
    cells = bucket_rows(rows, cell_mode="tier_b")
    c = list(cells.values())[0]
    assert c["wins"] == 1
    assert c["losses"] == 1
    assert c["time_exits"] == 1
    assert c["n_intrabar"] == 2
    assert c["wr"] == 0.5
    # PF = 1.0 / 1.0 = 1.0
    assert c["pf"] == pytest.approx(1.0, 0.001)


# ─── D. Filter + rank ─────────────────────────────────────────────────────────
def test_d_filter_drops_sparse_and_underperforming_cells() -> None:
    rows = []
    # Build n=40 wins (60%) / pf=1.5 cell  -> should pass min-n=30, wr=0.5, pf=1.0
    for i in range(40):
        rows.append({"pick_id": f"good_{i}", "symbol": "S", "strategy": "cta_donchian_55", "asset_class": "EQUITY",
                     "pnl_pct": 0.5 if i < 24 else -0.5, "exit_reason": "TP_HIT" if i < 24 else "SL_HIT",
                     "status": "CLOSED", "closed_at": f"2026-06-{(i % 28) + 1:02d}",
                     "source_system": "a"})
    # Build n=5 wins / n=5 losses (50%) cell  -> should fail min-n=30
    for i in range(10):
        rows.append({"pick_id": f"sparse_{i}", "symbol": "S", "strategy": "luxalgo_confluence", "asset_class": "EQUITY",
                     "pnl_pct": 1.0 if i < 5 else -1.0, "exit_reason": "TP_HIT" if i < 5 else "SL_HIT",
                     "status": "CLOSED", "closed_at": "2026-06-10", "source_system": "a"})
    cells = bucket_rows(rows, cell_mode="tier_b")
    survivors = filter_and_rank(cells, min_n=30, min_wr=0.50, min_pf=1.0, top_k=25)
    assert len(survivors) == 1
    assert survivors[0]["strategy_base"] == "cta_donchian_55"
    assert survivors[0]["n_intrabar"] == 40
    assert survivors[0]["wr"] == 0.6  # 24/40
    assert survivors[0]["pf"] == pytest.approx((24 * 0.5) / (16 * 0.5), 0.001)  # 1.5


def test_d_rank_tiebreaker_is_recency() -> None:
    """Two cells with identical scores must sort by last_seen desc.

    Uses tier_a so each symbol is its own cell (otherwise tier_b merges them).
    """
    rows = [
        # old cell (symbol X)
        {"pick_id": f"old_{i}", "symbol": "X", "strategy": "luxalgo_confluence", "asset_class": "EQUITY",
         "pnl_pct": 1.0, "exit_reason": "TP_HIT", "status": "CLOSED",
         "closed_at": "2026-01-01", "source_system": "a"} for i in range(60)
    ] + [
        # newer cell (symbol Y)  -> should win tie-break by last_seen desc
        {"pick_id": f"new_{i}", "symbol": "Y", "strategy": "luxalgo_confluence", "asset_class": "EQUITY",
         "pnl_pct": 1.0, "exit_reason": "TP_HIT", "status": "CLOSED",
         "closed_at": "2026-06-23", "source_system": "a"} for i in range(60)
    ]
    # tier_a: one cell per symbol -> we have two distinct cells to rank
    cells_a = bucket_rows(rows, cell_mode="tier_a")
    survivors_a = filter_and_rank(cells_a, min_n=30, min_wr=0.5, min_pf=1.0, top_k=10)
    assert len(survivors_a) == 2
    # rank 0 = newer cell by tiebreaker; rank 1 = older cell
    assert survivors_a[0]["last_seen"] == "2026-06-23"
    assert survivors_a[1]["last_seen"] == "2026-01-01"
    assert survivors_a[0]["symbol"] == "Y"
    assert survivors_a[1]["symbol"] == "X"
    # tier_b sanity: the two rows merge into one cell with combined last_seen = newer
    cells_b = bucket_rows(rows, cell_mode="tier_b")
    survivors_b = filter_and_rank(cells_b, min_n=30, min_wr=0.5, min_pf=1.0, top_k=10)
    assert len(survivors_b) == 1
    assert survivors_b[0]["n_intrabar"] == 120
    assert survivors_b[0]["last_seen"] == "2026-06-23"
def test_d_unknown_tf_excluded_from_survivors() -> None:
    rows = [
        {"pick_id": f"u_{i}", "symbol": "Z", "strategy": "completely_unknown_strategy_xyz", "asset_class": "EQUITY",
         "pnl_pct": 1.0, "exit_reason": "TP_HIT", "status": "CLOSED",
         "closed_at": "2026-06-01", "source_system": "a"} for i in range(40)
    ]
    cells = bucket_rows(rows, cell_mode="tier_b")
    assert all(c["timeframe"] == "UNKNOWN" for c in cells.values())
    survivors = filter_and_rank(cells, min_n=30, min_wr=0.5, min_pf=1.0, top_k=10)
    assert survivors == []


def test_d_top_k_caps_survivors() -> None:
    rows = []
    for strat in ["cta_donchian_55", "luxalgo_confluence", "futures_momentum", "rsi_vwap_contrarian"]:
        for i in range(60):
            rows.append({"pick_id": f"{strat}_{i}", "symbol": "X", "strategy": strat, "asset_class": "EQUITY",
                         "pnl_pct": 1.0, "exit_reason": "TP_HIT", "status": "CLOSED",
                         "closed_at": "2026-06-01", "source_system": "a"})
    cells = bucket_rows(rows, cell_mode="tier_b")
    survivors = filter_and_rank(cells, min_n=30, min_wr=0.5, min_pf=1.0, top_k=2)
    assert len(survivors) == 2


# ─── E. Cell-key modes ────────────────────────────────────────────────────────
def test_e_tier_a_vs_tier_b_cell_counts() -> None:
    rows = [
        {"pick_id": f"a_{i}", "symbol": "AAPL", "strategy": "stocks_rsi2_pullback",
         "asset_class": "EQUITY", "pnl_pct": 1.0, "exit_reason": "TP_HIT",
         "status": "CLOSED", "closed_at": "2026-06-01", "source_system": "x"} for i in range(40)
    ] + [
        {"pick_id": f"b_{i}", "symbol": "MSFT", "strategy": "stocks_rsi2_pullback",
         "asset_class": "EQUITY", "pnl_pct": 1.0, "exit_reason": "TP_HIT",
         "status": "CLOSED", "closed_at": "2026-06-01", "source_system": "x"} for i in range(40)
    ]
    tier_a = bucket_rows(rows, cell_mode="tier_a")
    tier_b = bucket_rows(rows, cell_mode="tier_b")
    assert len(tier_a) == 2  # one per symbol
    assert len(tier_b) == 1  # merged
    sb = list(tier_b.keys())[0]
    assert list(tier_b.values())[0]["n_intrabar"] == 80


# ─── F. emit_strategy_module ──────────────────────────────────────────────────
def test_f_emit_module_structure() -> None:
    sample = [{
        "cell_key": ["CRYPTO", "cta_donchian_55", "1d"],
        "asset_class": "CRYPTO",
        "strategy_base": "cta_donchian_55",
        "symbols": ["BTCUSDT", "ETHUSDT"],
        "timeframe": "1d",
        "n_intrabar": 60,
        "wr": 0.6, "pf": 1.5, "score": 11.0, "last_seen": "2026-06-23",
    }]
    src = emit_strategy_module(sample, cohort_tag="b5_test", utc_stamp="20260624T153000Z")
    assert "FwdTrack_" in src
    assert "COHORT_TAG = \"b5_test\"" in src
    assert "GENERATED_AT = \"20260624T153000Z\"" in src
    assert "from paper_trading.strategies.base_strategy import BaseStrategy" in src
    assert "BTCUSDT" in src and "ETHUSDT" in src
    assert "interval=\"1d\"" in src


def test_f_emit_module_handles_missing_symbols() -> None:
    """emit_strategy_module must not crash if a cell has no symbols list."""
    sample = [{
        "cell_key": ["EQUITY", "smart_empty", "1d"],
        "asset_class": "EQUITY",
        "strategy_base": "smart_empty",
        "symbols": [],
        "timeframe": "1d",
        "n_intrabar": 50,
        "wr": 0.55, "pf": 1.1, "score": 4.0, "last_seen": "2026-06-23",
    }]
    src = emit_strategy_module(sample, cohort_tag="x", utc_stamp="20260624T153000Z")
    assert "FwdTrack_smart_empty_1d" in src
    assert "symbols = []" in src


# ─── G. load_pick_funnel discoverability ──────────────────────────────────────
def test_g_load_pick_funnel_real() -> None:
    rows = load_pick_funnel(Path("/home/eaguiar2015/findtorontoevents_antigravity.ca/audit_dashboard/data/pick_funnel_90d.json"))
    assert isinstance(rows, list)
    assert len(rows) > 0
    assert "strategy" in rows[0]
    assert "asset_class" in rows[0]


def test_g_load_pick_funnel_raises_when_missing() -> None:
    with pytest.raises(FileNotFoundError):
        load_pick_funnel(Path("/nonexistent/pick_funnel_90d.json"))


# ─── H. live-data smoke test (no survivors likely) ────────────────────────────
def test_h_live_data_smoke_run_only_no_write() -> None:
    """Live pick_funnel_90d.json should produce a sane cell dict without raising.
    It does NOT need to yield survivors (we expect PF<1.0 across all cells today).
    """
    rows = load_pick_funnel(Path("/home/eaguiar2015/findtorontoevents_antigravity.ca/audit_dashboard/data/pick_funnel_90d.json"))
    cells_b = bucket_rows(rows, cell_mode="tier_b")
    assert len(cells_b) > 0
    # score formula sanity: if a cell has 0 intrabar results, score must be 0.0
    for c in cells_b.values():
        assert c["score"] >= 0.0
        assert c["wr"] >= 0.0 and c["wr"] <= 1.0
        assert c["pf"] >= 0.0
    # Just ensure filter-and-rank does not raise
    filter_and_rank(cells_b, min_n=30, min_wr=0.5, min_pf=1.0, top_k=10)
    # cohort is most likely empty (PF<1.0 across the board on 2026-06-24 dataset)
    survivors = filter_and_rank(cells_b, min_n=30, min_wr=0.5, min_pf=1.0, top_k=10)
    assert isinstance(survivors, list)
    # if there ARE survivors, score must be > 0
    for s in survivors:
        assert s["score"] > 0.0
        assert s["n_intrabar"] >= 30
        assert s["wr"] > 0.5
        assert s["pf"] > 1.0
