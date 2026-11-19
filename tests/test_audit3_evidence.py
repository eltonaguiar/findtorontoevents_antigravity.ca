"""Deterministic tests for the audit3 P1 evidence registry."""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from alpha_engine.audit3_evidence import (  # noqa: E402
    CANONICAL_STATUSES,
    build,
    build_registry,
    class_from_filename,
    class_is_mismatch,
    default_json_sources,
    derive_asset_class,
    find_stats,
    ingest_json,
    load_hypotheses,
    normalize_hypothesis_status,
    recompute,
    stats_from_obj,
)


# ───────────────────────────────────────────────────────────── asset class ──
def test_symbol_derivation_beats_the_stored_column():
    # The live defect: bt_backtest_runs labels all 285 rows CRYPTO.
    assert derive_asset_class("NZDUSD=X", "CRYPTO") == "FOREX"
    assert derive_asset_class("BTC-USD") == "CRYPTO"
    assert derive_asset_class("fetusdt") == "CRYPTO"
    assert derive_asset_class("CT=F") == "COMMODITY"
    assert derive_asset_class("ES=F") == "FUTURES"
    assert derive_asset_class("SPY") == "ETF"
    # ETF is a wrapper: a proxy claim keeps its economic class.
    assert derive_asset_class("SPY", "EQUITY") == "EQUITY"
    assert derive_asset_class("TLT", "BOND") == "BOND"
    assert derive_asset_class("GLD", "COMMODITY") == "COMMODITY"
    assert derive_asset_class("AAPL") == "EQUITY"
    # Price/liquidity is not in the row, so a penny claim is the only evidence.
    assert derive_asset_class("XYZ", "PENNY_STOCK") == "PENNY_STOCK"
    assert derive_asset_class(None, "CRYPTO") == "CRYPTO"
    assert derive_asset_class("", None) == "UNKNOWN"


def test_class_hints_from_names_when_no_symbol_or_column():
    assert class_from_filename("btc_utc_hour_backtest") == "CRYPTO"
    assert class_from_filename("cheap_stock_cross_momentum") == "PENNY_STOCK"
    assert class_from_filename("ipo_post_listing_momentum_long") == "EQUITY"
    # Word boundaries: these substrings must not trigger a class.
    assert class_from_filename("carry_trade_momentum") is None
    assert class_from_filename("solution_engine") is None


def test_mismatch_ignores_blank_and_unknown_claims():
    assert class_is_mismatch("CRYPTO", "FOREX") is True
    assert class_is_mismatch("CRYPTO", "CRYPTO") is False
    assert class_is_mismatch(None, "FOREX") is False
    assert class_is_mismatch("UNKNOWN", "FOREX") is False
    assert class_is_mismatch("", "FOREX") is False


# ──────────────────────────────────────────────────────── hypothesis enum ──
def test_hypothesis_spellings_collapse_to_one_enum():
    cases = {
        "forward-shadow": ("FORWARD_SHADOW", True),
        "FORWARD_OBSERVATION": ("FORWARD_OBSERVING", True),
        "FORWARD_ACCRUING": ("FORWARD_OBSERVING", True),
        "REGISTERED-UNTESTED": ("REGISTERED_UNTESTED", True),
        "PRE-REGISTERED": ("PRE_REGISTERED", True),
        "UNTESTED_DATA_GAP": ("REGISTERED_UNTESTED", True),
        "KILLED": ("REFUTED", True),
        "SUPPORTED": ("TESTED_PASS", True),
        "NULL": ("UNKNOWN", True),
    }
    for raw, (want, exact) in cases.items():
        got, got_exact = normalize_hypothesis_status(raw)
        assert got == want, (raw, got, want)
        assert got_exact is exact, (raw, got_exact)

    # Free text falls back through a prefix rule and reports that it did.
    got, exact = normalize_hypothesis_status("REJECTED - only 0 scored windows (need 3)")
    assert (got, exact) == ("REFUTED", False)
    assert normalize_hypothesis_status("total nonsense") == ("UNKNOWN", False)


def test_real_registry_normalises_to_a_small_enum():
    hyp = load_hypotheses()
    assert hyp["available"] is True
    assert hyp["total"] >= 50
    assert sum(hyp["canonical_counts"].values()) == hyp["total"]
    assert len(hyp["canonical_counts"]) <= len(CANONICAL_STATUSES)
    # Every canonical key must be in the declared enum.
    assert set(hyp["canonical_counts"]) <= set(CANONICAL_STATUSES)
    # The raw file is messy; that is the point of the normalisation.
    assert hyp["n_raw_spellings"] > hyp["n_canonical"]
    for row in hyp["unmapped"]:
        assert row["count"] >= 1 and row["canonical"] in CANONICAL_STATUSES


# ──────────────────────────────────────────────────────────── stats alias ──
def test_stats_normalise_ratio_and_percent_units():
    got = stats_from_obj({"n": 970, "wr_pct": 37.42, "pf_net": 1.1755,
                          "avg_net_bps": 19.54, "total_net_pct": 189.568})
    assert got["n"] == 970
    assert abs(got["wr"] - 0.3742) < 1e-9
    assert abs(got["pf"] - 1.1755) < 1e-9
    assert abs(got["avg_net_bp"] - 19.54) < 1e-9

    # Already-ratio win rate is left alone; drawdown normalises either way.
    assert stats_from_obj({"n": 10, "wr": 0.55, "mdd_pct": 0.18})["wr"] == 0.55
    assert stats_from_obj({"n": 10, "mdd": 0.18})["mdd_pct"] == 18.0
    assert stats_from_obj({"n": 10, "mdd": 22.5})["mdd_pct"] == 22.5

    # n is mandatory: a win rate with no sample is not evidence.
    assert stats_from_obj({"wr": 0.55, "pf": 2.0}) is None
    assert stats_from_obj(None) is None


def test_find_stats_descends_into_nested_containers():
    payload = {"method": {"x": 1},
               "results": {"overall": {"n": 10, "wr": 0.6, "pf": 1.4}}}
    stats, path = find_stats(payload)
    assert stats["n"] == 10
    assert "results" in path


def test_recompute_only_claims_gross_numbers():
    out = recompute([1.0, -0.5, 2.0, -1.0, 0.25, -1.0, 1.5, -0.5, 0.75, -1.25])
    assert out["n"] == 10
    assert out["wr"] == 0.5
    assert out["pf"] is not None and out["pf"] > 0
    assert "gross" in out["cost_basis"] or "not a net" in out["cost_basis"]


# ─────────────────────────────────────────────────────────────── ingestion ──
def test_bundle_json_yields_one_record_per_strategy(tmp_path):
    pnls = [{"pnl_pct": 1.0}, {"pnl_pct": -0.5}, {"pnl_pct": 0.4}, {"pnl_pct": -0.9},
            {"pnl_pct": 2.0}, {"pnl_pct": -1.0}, {"pnl_pct": 0.6}, {"pnl_pct": -0.2},
            {"pnl_pct": 1.4}, {"pnl_pct": -0.7}, {"pnl_pct": 0.3}, {"pnl_pct": -0.1}]
    payload = {
        "generated_at": "2026-05-17T13:17:57Z",
        "alpha_vix": {"strategy": "alpha_vix",
                      "results": {"n_trades": 604, "win_rate_pct": 52.0,
                                  "profit_factor": 1.3, "sharpe_annualized": 0.8},
                      "trades": pnls},
        "beta_sector": {"strategy": "beta_sector",
                        "results": {"n_trades": 657, "win_rate_pct": 48.0,
                                    "profit_factor": 0.95},
                        "trades": pnls},
    }
    path = tmp_path / "equity_baby_backtest.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    recs = ingest_json(path)
    assert len(recs) == 2
    by_name = {r["strategy"]: r for r in recs}
    alpha = by_name["alpha_vix"]
    assert alpha["asset_class_derived"] == "EQUITY"
    assert alpha["n"] == 604
    assert abs(alpha["wr"] - 0.52) < 1e-9
    assert len(alpha["provenance"]["sha256"]) == 64
    assert alpha["provenance"]["path"].endswith("equity_baby_backtest.json")
    # 12 trades, 6 wins -> recomputed WR is checkable against the stated 52%.
    assert alpha["recomputed"]["n"] == 12
    assert alpha["recomputed"]["wr"] == 0.5


def test_ingest_json_survives_non_json_and_unknown_shapes(tmp_path):
    bad = tmp_path / "broken_backtest.json"
    bad.write_text("not json at all", encoding="utf-8")
    assert ingest_json(bad) == []

    empty = tmp_path / "empty_backtest.json"
    empty.write_text(json.dumps({"note": "no metrics here"}), encoding="utf-8")
    assert ingest_json(empty) == []


def test_oversized_file_is_skipped_not_parsed(tmp_path, monkeypatch):
    import alpha_engine.audit3_evidence as mod
    monkeypatch.setattr(mod, "MAX_FILE_MB", 0)
    path = tmp_path / "big_backtest.json"
    path.write_text(json.dumps({"n": 1}), encoding="utf-8")
    assert ingest_json(path) == []


# ────────────────────────────────────────────────────────────── registry ──
def _rec(**kw):
    base = {
        "evidence_id": kw.get("evidence_id", "abc"),
        "surface": "backtest_json",
        "strategy": "s1",
        "symbol": "BTC-USD",
        "asset_class_derived": "CRYPTO",
        "asset_class_claimed": "CRYPTO",
        "class_mismatch": False,
        "n": 100,
        "recomputed": None,
        "trial_count_N": None,
    }
    base.update(kw)
    return base


def test_registry_summary_counts_truth_not_claims():
    recs = [
        _rec(evidence_id="a", strategy="s1", n=100),
        _rec(evidence_id="b", strategy="s2", symbol="NZDUSD=X",
             asset_class_derived="FOREX", asset_class_claimed="CRYPTO",
             class_mismatch=True, n=50),
        _rec(evidence_id="c", strategy="s3", n=25, recomputed={"n": 25}),
        _rec(evidence_id="c", strategy="s3", n=25),  # duplicate id collapses
    ]
    reg = build_registry(recs, sources=[{"path": "x.json", "records": 3}],
                         db_info={"connected": False, "tables": {}})
    s = reg["summary"]
    assert s["n_records"] == 3
    assert s["n_class_mismatches"] == 1
    assert s["n_strategies"] == 3
    assert s["n_retestable_with_trade_log"] == 1
    assert s["total_trades_covered"] == 175
    assert reg["class_mismatches"][0]["claimed"] == "CRYPTO"
    assert reg["class_mismatches"][0]["derived"] == "FOREX"
    assert reg["doctrine"]["name"] == "innocent-until-proven-guilty"
    assert any("32.7M" in g for g in reg["known_gaps"])


def test_registry_handles_no_records_without_crashing():
    reg = build_registry([], sources=[], db_info={"connected": False})
    assert reg["summary"]["n_records"] == 0
    assert reg["records"] == []


# ─────────────────────────────────────────────────────────── real payloads ──
def test_default_sources_are_bounded_and_exist():
    paths = default_json_sources()
    assert len(paths) >= 10
    for p in paths:
        assert p.exists()
        name = p.name.lower()
        assert "backtest" in name or "strategy_bt" in name, name


def test_real_repo_payloads_ingest_end_to_end():
    reg = build(use_db=False)
    s = reg["summary"]
    assert s["n_records"] >= 50, s
    assert s["n_strategies"] >= 20, s
    assert s["n_sources"] >= 10, s
    # The dataframe-shaped sources must all be represented.
    surfaces = s["by_surface"]
    assert surfaces.get("backtest_json", 0) == s["n_records"]
    # Every record carries provenance and a derived class in the enum.
    allowed = {"CRYPTO", "EQUITY", "ETF", "FOREX", "COMMODITY", "FUTURES",
               "BOND", "PENNY_STOCK", "MEMECOIN", "UNKNOWN"}
    for r in reg["records"]:
        assert r["provenance"].get("path"), r
        assert r["provenance"].get("sha256"), r
        assert r["asset_class_derived"] in allowed, r
        assert isinstance(r["notes"], list)
