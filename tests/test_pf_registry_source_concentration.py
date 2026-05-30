"""Tests for FINDING_OVERALL#8 — single-source concentration flag on
`pf_registry.json` rows.

The /money-maker-readyv2 audit (2026-05-30) found `crypto_liquidity_wick_
reversal_v1` looked like a unique PF>=1.5/n>=30/WR>=50 edge — but 100% of
the picks came from one source (`battleground`). Skill rule #2: if >60% of
decisive picks come from one source_system, it is concentration, not edge.

These tests cover:
  1. 100% single-source -> flag=True, pct=1.0
  2. 50/50 two-source -> flag=False, pct=0.5
  3. 61% single-source with n>=5 -> flag=True
  4. 59% single-source -> flag=False
  5. n=4 with 100% concentration -> flag=False (n threshold)
  6. Env-var threshold override works
  7. End-to-end: aggregate() emits the fields on every row
"""
from __future__ import annotations

import os
import sys

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from tools import build_pf_registry as bpr  # noqa: E402


def _mkrow(source_system, pnl=0.01, asset_class="CRYPTO",
           strategy="strat_a", symbol="BTCUSDT", direction="LONG",
           status="CLOSED", entry_date="2026-05-01", entry_price=100.0):
    return {
        "source_system": source_system,
        "strategy": strategy,
        "symbol": symbol,
        "direction": direction,
        "status": status,
        "pnl_pct": pnl,
        "entry_date": entry_date,
        "entry_price": entry_price,
        "asset_class": asset_class,
    }


# ---------------------------------------------------------------------------
# Direct concentration helper tests
# ---------------------------------------------------------------------------

def test_100pct_single_source_flags_true():
    out = bpr._compute_source_concentration({"battleground": 30})
    assert out["single_source_pct"] == 1.0
    assert out["is_single_source_artifact"] is True
    assert out["top_source"] == "battleground"


def test_50_50_two_source_flag_false():
    out = bpr._compute_source_concentration({"battleground": 10, "alpha_engine": 10})
    assert out["single_source_pct"] == 0.5
    assert out["is_single_source_artifact"] is False
    assert out["top_source"] in ("battleground", "alpha_engine")


def test_61pct_with_n_ge_5_flags_true():
    # 61/100 -> 0.61, > 0.60 default
    out = bpr._compute_source_concentration({"battleground": 61, "alpha_engine": 39})
    assert out["single_source_pct"] == pytest.approx(0.61, abs=1e-6)
    assert out["is_single_source_artifact"] is True


def test_59pct_flag_false():
    out = bpr._compute_source_concentration({"battleground": 59, "alpha_engine": 41})
    assert out["single_source_pct"] == pytest.approx(0.59, abs=1e-6)
    assert out["is_single_source_artifact"] is False


def test_n_below_min_no_flag_even_at_100pct():
    # n=4, 100% concentration -> flag still False (n threshold)
    out = bpr._compute_source_concentration({"battleground": 4})
    assert out["single_source_pct"] == 1.0
    assert out["is_single_source_artifact"] is False


def test_env_var_threshold_override(monkeypatch):
    # raise threshold to 0.80 — 70% no longer flags
    monkeypatch.setenv("PF_REGISTRY_SOURCE_CONCENTRATION_THRESHOLD", "0.80")
    out = bpr._compute_source_concentration({"battleground": 7, "alpha_engine": 3})
    assert out["single_source_pct"] == pytest.approx(0.7, abs=1e-6)
    assert out["is_single_source_artifact"] is False

    # lower threshold to 0.40 — 50/50 now flags
    monkeypatch.setenv("PF_REGISTRY_SOURCE_CONCENTRATION_THRESHOLD", "0.40")
    out2 = bpr._compute_source_concentration({"battleground": 5, "alpha_engine": 5})
    assert out2["is_single_source_artifact"] is True


def test_empty_counts_returns_nulls():
    out = bpr._compute_source_concentration({})
    assert out["single_source_pct"] is None
    assert out["top_source"] is None
    assert out["is_single_source_artifact"] is False


# ---------------------------------------------------------------------------
# End-to-end: aggregate() attaches fields to every row at every granularity
# ---------------------------------------------------------------------------

def _classify_then_agg(rows, net=False):
    cls = bpr.classify_rows(rows)
    return cls["kept"], bpr.aggregate(cls["kept"], net=net)


def test_aggregate_attaches_fields_to_all_levels():
    # 30 picks, all from `battleground` -> per-strategy + per-class flag True.
    rows = [
        _mkrow("battleground", pnl=0.02, entry_date=f"2026-05-{(i % 28) + 1:02d}",
               entry_price=100.0 + i)
        for i in range(30)
    ]
    _, (csd, css, cs, c, _mdd) = _classify_then_agg(rows)

    # Every row at every granularity must have the new fields.
    for bucket in (csd, css, cs, c):
        assert bucket, "bucket unexpectedly empty"
        for row in bucket:
            assert "single_source_pct" in row
            assert "top_source" in row
            assert "is_single_source_artifact" in row

    # The single per-class row should be 100% battleground, flagged.
    assert len(c) == 1
    assert c[0]["asset_class"] == "CRYPTO"
    assert c[0]["single_source_pct"] == 1.0
    assert c[0]["top_source"] == "battleground"
    assert c[0]["is_single_source_artifact"] is True


def test_aggregate_mixed_sources_not_flagged():
    rows = []
    for i in range(15):
        rows.append(_mkrow("battleground", pnl=0.02,
                           entry_date=f"2026-05-{(i % 28) + 1:02d}",
                           entry_price=100.0 + i))
    for i in range(15):
        rows.append(_mkrow("alpha_engine", pnl=0.01,
                           entry_date=f"2026-04-{(i % 28) + 1:02d}",
                           entry_price=200.0 + i))
    _, (_csd, _css, _cs, c, _mdd) = _classify_then_agg(rows)
    assert len(c) == 1
    assert c[0]["single_source_pct"] == 0.5
    assert c[0]["is_single_source_artifact"] is False


def test_row_source_falls_back_to_origin_file():
    row = {"_origin_file": "battleground/data/closed_picks.json"}
    assert bpr._row_source(row) == "file:battleground"

    row2 = {"_origin_file": "alpha_engine/data/closed_picks_fast.json"}
    assert bpr._row_source(row2) == "file:alpha_engine"

    row3 = {"_origin_file": "/some/path/custom_ledger.json"}
    assert bpr._row_source(row3) == "file:custom_ledger.json"

    row4 = {}
    assert bpr._row_source(row4) == "unknown"

    row5 = {"source_system": "mercury2", "_origin_file": "x.json"}
    assert bpr._row_source(row5) == "mercury2"
