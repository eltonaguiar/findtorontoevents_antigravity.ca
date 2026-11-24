"""Canonical resolved-closed view: one denominator, attributed exclusions.

The failure this guards against is real and was measured: /audit said ETF was
n=52 / WR 1.9% while audit3 said n=584 / WR 43.1% on the same day, and neither
page published which rows it was counting. These tests pin the properties that
make the two surfaces comparable.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from alpha_engine.resolved_closed_view import (  # noqa: E402
    CLASS_COST_BPS,
    DEFAULT_COST_BPS,
    SCHEMA,
    build_view,
    canonical_row,
    class_rollup,
    cost_bps,
    coverage_statement,
    default_exclusion_reason,
    load_sidecar,
    payload_block,
    write_view,
)


def _pick(**kw):
    base = {
        "symbol": "SPY", "asset_class": "ETF", "direction": "LONG",
        "strategy": "etf_momentum", "source_system": "alpha_engine",
        "entry_price": 500.0, "pnl_pct": 1.0, "status": "WON",
        "exit_reason": "TAKE_PROFIT", "closed_at": "2026-11-01T00:00:00Z",
    }
    base.update(kw)
    return base


def test_net_is_gross_minus_class_cost():
    row = canonical_row(_pick(pnl_pct=1.0, asset_class="CRYPTO"))
    assert row["pnl_gross_pct"] == 1.0
    assert row["cost_bps"] == CLASS_COST_BPS["CRYPTO"]
    assert row["pnl_net_pct"] == round(1.0 - CLASS_COST_BPS["CRYPTO"] / 100.0, 6)


def test_unknown_class_falls_back_to_default_cost():
    assert cost_bps("NOT_A_CLASS") == DEFAULT_COST_BPS
    assert cost_bps(None) == DEFAULT_COST_BPS


def test_explicit_strategy_cost_overrides_class_cost():
    row = canonical_row(_pick(pnl_pct=2.0, strategy="luxalgo_confluence"),
                        strategy_cost_bps={"luxalgo_confluence": 100.0})
    assert row["cost_bps"] == 100.0
    assert row["pnl_net_pct"] == 1.0


def test_mirror_duplicates_are_one_economic_trade():
    rows = [_pick(), _pick(), _pick(symbol="QQQ")]
    view = build_view(rows, generated_at="2026-11-19T00:00:00Z")
    assert view["counts"]["kept_rows"] == 2
    assert view["counts"]["excluded_by_reason"]["mirror_duplicate"] == 1


def test_exclusions_are_attributed_not_silent():
    rows = [
        _pick(),
        _pick(symbol="AAA", pnl_pct=0.5),
        _pick(symbol="BBB", _auto_expired=True),
        _pick(symbol="CCC", paper_trade=True),
        _pick(symbol="DDD", pnl_pct=None),
        _pick(symbol="EEE", exit_reason="RESOLVE_FAILED_BREAKEVEN"),
    ]
    view = build_view(rows, generated_at="2026-11-19T00:00:00Z",
                      validity=lambda p: not (p.get("_auto_expired") or p.get("paper_trade")
                                              or p.get("pnl_pct") is None
                                              or str(p.get("exit_reason", "")).startswith("RESOLVE_FAILED")))
    assert view["counts"]["kept_rows"] == 2
    reasons = view["counts"]["excluded_by_reason"]
    assert reasons["auto_expired"] == 1
    assert reasons["paper_trade"] == 1
    assert reasons["no_numeric_pnl"] == 1
    assert reasons["resolver_breakeven_fallback"] == 1
    assert sum(reasons.values()) == view["counts"]["excluded_rows"]


def test_default_exclusion_reason_classifies_the_common_cases():
    assert default_exclusion_reason(_pick(_auto_expired=True)) == "auto_expired"
    assert default_exclusion_reason(_pick(paper_trade=True)) == "paper_trade"
    assert default_exclusion_reason(_pick(pnl_pct=None)) == "no_numeric_pnl"
    assert default_exclusion_reason(_pick(status="OPEN")) == "not_resolved"
    assert default_exclusion_reason(_pick(exit_reason="STALE_EXIT")) == "non_performance_exit"
    assert default_exclusion_reason(_pick()) is None


def test_class_rollup_matches_hand_arithmetic():
    rows = [
        canonical_row(_pick(pnl_pct=2.0)),
        canonical_row(_pick(symbol="QQQ", pnl_pct=-1.0)),
        canonical_row(_pick(symbol="IWM", pnl_pct=0.005)),
    ]
    roll = class_rollup(rows)
    etf = roll["ETF"]
    assert etf["n"] == 3 and etf["wins"] == 1 and etf["losses"] == 1 and etf["flat"] == 1
    assert etf["win_rate_pct"] == 50.0
    assert etf["profit_factor"] == 2.0
    assert etf["mean_gross_pct"] == round((2.0 - 1.0 + 0.005) / 3, 4)


def test_canonical_row_keeps_identity_fields_for_downstream_dedupe():
    """Two trades that differ only in entry price must stay two rows.

    audit3's loader dedupes on `id` when present, else on
    (strategy, symbol, direction, closed_at, pnl). Without entry_price in the
    canonical row those two trades collapse — an end-to-end run lost 24 of 3,500
    rows exactly this way, so the field is load-bearing, not decoration.
    """
    a = canonical_row(_pick(entry_price=500.0, pnl_pct=1.0))
    b = canonical_row(_pick(entry_price=501.0, pnl_pct=1.0))
    assert a["entry_price"] == 500.0 and b["entry_price"] == 501.0
    assert (a["strategy"], a["symbol"], a["closed_at"], a["pnl_pct"]) == \
           (b["strategy"], b["symbol"], b["closed_at"], b["pnl_pct"])
    assert "id" in a


def test_rows_hash_changes_when_the_book_changes():
    a = build_view([_pick()], generated_at="2026-11-19T00:00:00Z")
    b = build_view([_pick(), _pick(symbol="QQQ")], generated_at="2026-11-19T00:00:00Z")
    assert a["rows_sha256"] != b["rows_sha256"]
    assert len(a["rows_sha256"]) == 64


def test_coverage_statement_names_the_denominator():
    view = build_view([_pick(), _pick(symbol="QQQ", _auto_expired=True)],
                      generated_at="2026-11-19T00:00:00Z",
                      validity=lambda p: not p.get("_auto_expired"))
    txt = coverage_statement(view, {"total_closed_picks": 4})
    assert "canonical resolved book is 1 rows" in txt
    assert "4 closed records" in txt
    assert "auto expired 1" in txt
    assert "25.0%" in txt


def test_sidecar_roundtrip_and_hash_verification(tmp_path):
    view = build_view([_pick()], generated_at="2026-11-19T00:00:00Z")
    block = payload_block(view)
    assert "rows" not in block and block["rows_count"] == 1
    payload = tmp_path / "dashboard_data.json"
    payload.write_text(json.dumps({"resolved_closed_picks_net": block}), encoding="utf-8")
    write_view(tmp_path / block["rows_file"], view)

    loaded = load_sidecar(payload, block)
    assert loaded is not None and loaded["schema"] == SCHEMA
    assert len(loaded["rows"]) == 1

    # A payload describing rows the sidecar does not contain must be refused.
    tampered = dict(block, rows_sha256="0" * 64)
    assert load_sidecar(payload, tampered) is None


def test_sidecar_missing_returns_none_instead_of_raising(tmp_path):
    payload = tmp_path / "dashboard_data.json"
    payload.write_text("{}", encoding="utf-8")
    assert load_sidecar(payload, {"rows_file": "nope.json"}) is None


def _book(n=120):
    return [_pick(symbol=f"S{i:03d}", entry_price=100.0 + i, pnl_pct=0.5)
            for i in range(n)]


def test_audit3_reports_canonical_only_when_the_hash_verifies(tmp_path):
    """Mode must be a recorded fact, not a row-count coincidence.

    A 3,500-row export slice and a 3,500-row canonical book have the same size, so
    comparing counts cannot tell whether the hash-verified view was used. An
    end-to-end run against a tampered block still reported "canonical" until the
    load stage started recording it.
    """
    from alpha_engine import audit3_tribunal as t

    view = build_view(_book(), generated_at="2026-11-19T00:00:00Z")
    block = payload_block(view)
    payload = tmp_path / "dashboard_data.json"
    payload.write_text(json.dumps({
        "generated_at": view["generated_at"],
        "picks": {"recent_closed": _book()},
        "resolved_closed_picks_net": block,
    }), encoding="utf-8")
    write_view(tmp_path / block["rows_file"], view)

    rows, _ = t.load_rows(str(payload))
    assert len(rows) == view["counts"]["kept_rows"]
    assert t.LAST_DENOMINATOR["mode"] == "canonical"

    tampered = dict(block, rows_sha256="0" * 64)
    payload.write_text(json.dumps({
        "generated_at": view["generated_at"],
        "picks": {"recent_closed": _book()},
        "resolved_closed_picks_net": tampered,
    }), encoding="utf-8")
    t.load_rows(str(payload))
    assert t.LAST_DENOMINATOR["mode"] == "payload_slice"
    assert t.LAST_DENOMINATOR["reason"] == "sidecar_missing_or_hash_mismatch"
