"""audit2 Phase B — the per-class verdict panel reconciles against class_rollup().

The panel is a browser table fed by a payload block. Its whole justification is
that it COPIES the canonical rollup rather than computing its own statistics —
/audit and /audit3 once disagreed 3x on ETF while both being arithmetically
correct, purely because each had its own denominator and metric code.

So the load-bearing assertion is equality, not plausibility: for every class,
the panel's n / mean net / PF / win rate must EQUAL class_rollup()'s output on
the same rows. If somebody later recomputes a statistic in the renderer, or
rounds differently, this fails.

Fixture-driven: no live fetch, no DB, no network.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
import sys

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from alpha_engine.resolved_closed_view import (  # noqa: E402
    build_view,
    class_rollup,
    is_performance_scored_row,
)
from tools.build_audit2_per_class_panel import (  # noqa: E402
    MIN_N_FOR_VERDICT,
    build_per_class_verdicts,
)


# ── fixtures ─────────────────────────────────────────────────────────────────
def _pick(symbol, cls, pnl, direction="LONG", strategy="S1", status="TIME_EXIT",
          exit_reason="TIME_EXIT", entry=100.0):
    return {
        "symbol": symbol, "asset_class": cls, "pnl_pct": pnl,
        "direction": direction, "strategy": strategy, "status": status,
        "exit_reason": exit_reason, "entry_price": entry,
        "closed_at": "2026-11-01T00:00:00+00:00",
    }


def _rows(picks):
    """The canonical rows for a fixture, through the same predicate production uses."""
    return build_view(picks, generated_at="2026-11-20T00:00:00+00:00",
                      validity=is_performance_scored_row)["rows"]


BASE_PICKS = [
    # CRYPTO: 4 rows, mixed wins and losses
    _pick("BTC-USD", "CRYPTO", 2.5, strategy="A"),
    _pick("ETH-USD", "CRYPTO", -1.0, strategy="B", entry=200.0),
    _pick("SOL-USD", "CRYPTO", 0.8, strategy="A", entry=50.0),
    _pick("ADA-USD", "CRYPTO", -0.4, strategy="B", entry=1.0),
    # EQUITY: 2 rows
    _pick("AAPL", "EQUITY", 1.2, strategy="C", entry=150.0),
    _pick("MSFT", "EQUITY", -0.6, strategy="C", entry=300.0),
]


def _ledger(classes, cells, mode="canonical", generated_at="2026-11-20T01:57:23Z"):
    return {
        "schema": "audit3.v1",
        "generated_at": generated_at,
        "source": "fixture",
        "classes": classes,
        "cells": cells,
        "coverage": {"denominator": {"mode": mode}, "scored_rows": 6},
        "summary": {},
        "provenance": {},
    }


BASE_CLASSES = [
    {"asset_class": "CRYPTO", "verdict": "KILL", "n": 4, "net_ci_pct": [-1.0, 0.5],
     "net_expectancy_pct": 0.475},
    {"asset_class": "EQUITY", "verdict": "WEAK", "n": 2, "net_ci_pct": [-0.2, 0.4],
     "net_expectancy_pct": 0.3},
]
BASE_CELLS = [
    {"asset_class": "CRYPTO", "strategy": "A", "direction": "LONG", "n": 25},
    {"asset_class": "CRYPTO", "strategy": "B", "direction": "LONG", "n": 5},
    {"asset_class": "EQUITY", "strategy": "C", "direction": "LONG", "n": 2},
]


# ── B4: the reconcile test ───────────────────────────────────────────────────
def test_panel_numbers_equal_class_rollup_exactly():
    rows = _rows(BASE_PICKS)
    rollup = class_rollup(rows)
    panel = build_per_class_verdicts(_ledger(BASE_CLASSES, BASE_CELLS), rows)
    by_class = {e["asset_class"]: e for e in panel["classes"]}

    assert set(by_class) == set(rollup), "panel and rollup must cover the same classes"
    for cls, roll in rollup.items():
        e = by_class[cls]
        assert e["n"] == roll["n"], cls
        assert e["mean_net_pct"] == roll["mean_net_pct"], cls
        assert e["profit_factor"] == roll["profit_factor"], cls
        assert e["win_rate_pct"] == roll["win_rate_pct"], cls
        assert e["mean_cost_bps"] == roll["mean_cost_bps"], cls
        assert e["wins"] == roll["wins"] and e["losses"] == roll["losses"], cls


def test_panel_is_deterministic_and_serialisable():
    rows = _rows(BASE_PICKS)
    a = build_per_class_verdicts(_ledger(BASE_CLASSES, BASE_CELLS), rows)
    b = build_per_class_verdicts(_ledger(BASE_CLASSES, BASE_CELLS), rows)
    assert a == b
    # The ledger is written with allow_nan=False — the block must survive that.
    json.dumps(a, allow_nan=False)


def test_renderer_copies_instead_of_recomputing():
    """Guard on the JS itself: the panel must not compute a mean or a ratio.

    Cheap, static check — it fails if someone adds arithmetic over n / wins /
    losses in the panel renderer, which is exactly the drift this phase exists
    to prevent.
    """
    js = (REPO_ROOT / "audit_dashboard" / "audit2.js").read_text(encoding="utf-8")
    start = js.index("function renderPerClass")
    # Bound the slice to this function: the next top-level `function` ends it.
    rest = js[start:]
    end = rest.find("\nfunction ", 1)
    body = rest if end < 0 else rest[:end]
    # No arithmetic over the rollup fields inside the renderer.
    assert not re.search(r"mean_net_pct\s*[*/+-]", body)
    assert not re.search(r"profit_factor\s*[*/+-]", body)
    assert not re.search(r"\b(wins|losses|n)\s*[*/]\s*\w", body)
    # Normalise away comments, tags and string literals, then require that no
    # division survives anywhere in the renderer — formatting is the only job.
    code = re.sub(r"//[^\n]*", "", body)
    code = re.sub(r"/\*[\s\S]*?\*/", "", code)
    code = re.sub(r"</?[a-zA-Z][^>]*>?", "", code)
    code = re.sub(r"'[^'\n]*'|\"[^\"\n]*\"", "''", code)
    assert "/" not in code, code
    # And it reads the payload block rather than the raw ledger fields.
    assert "per_class_verdicts" in body


# ── B2: the awkward cases ───────────────────────────────────────────────────
def test_tiny_n_is_inconclusive_not_a_verdict_word():
    rows = _rows([_pick("AAPL", "EQUITY", 1.0)])  # n = 1
    ledger = _ledger([{"asset_class": "EQUITY", "verdict": "PROVEN_T2", "n": 1,
                       "net_ci_pct": [0.1, 0.2]}], [])
    panel = build_per_class_verdicts(ledger, rows)
    e = panel["classes"][0]
    assert e["n"] < MIN_N_FOR_VERDICT
    assert e["verdict_word"] == "inconclusive"
    assert e["verdict"] == "PROVEN_T2"  # the tribunal's word is preserved, not overwritten
    assert "too few rows" in e["verdict_note"]


def test_class_in_rollup_but_missing_from_tribunal_gets_no_verdict():
    rows = _rows(BASE_PICKS)  # has EQUITY
    ledger = _ledger([BASE_CLASSES[0]], BASE_CELLS)  # only CRYPTO has a verdict
    panel = build_per_class_verdicts(ledger, rows)
    by_class = {e["asset_class"]: e for e in panel["classes"]}
    assert "EQUITY" in by_class, "a class present in one source must not be dropped"
    eq = by_class["EQUITY"]
    assert eq["in_rollup"] is True and eq["in_tribunal"] is False
    assert eq["verdict"] is None
    assert eq["verdict_word"] == "no verdict"
    assert eq["net_ci_pct"] is None
    assert eq["n"] is not None  # the rollup side still renders


def test_class_in_tribunal_but_missing_from_rollup_gets_n_from_tribunal():
    ledger = _ledger(
        BASE_CLASSES + [{"asset_class": "BOND", "verdict": "WEAK", "n": 35,
                         "net_ci_pct": [-0.1, 0.2]}],
        BASE_CELLS + [{"asset_class": "BOND", "strategy": "D", "direction": "LONG", "n": 12}],
    )
    rows = _rows(BASE_PICKS)  # no BOND rows
    panel = build_per_class_verdicts(ledger, rows)
    bond = {e["asset_class"]: e for e in panel["classes"]}["BOND"]
    assert bond["in_rollup"] is False and bond["in_tribunal"] is True
    assert bond["n"] == 35          # falls back to the tribunal's n
    assert bond["mean_net_pct"] is None  # never invented
    assert bond["verdict_word"] == "WEAK"
    assert bond["n_cells"] == 1


def test_no_losses_profit_factor_is_null_not_a_crash():
    rows = _rows([
        _pick("BTC-USD", "CRYPTO", 2.0, strategy="A"),
        _pick("ETH-USD", "CRYPTO", 1.0, strategy="B", entry=200.0),
    ])
    roll = class_rollup(rows)["CRYPTO"]
    assert roll["profit_factor"] is None  # no loss mass → undefined, by contract
    assert roll["losses"] == 0
    panel = build_per_class_verdicts(
        _ledger([{"asset_class": "CRYPTO", "verdict": "WEAK", "n": 2}], []), rows)
    e = panel["classes"][0]
    assert e["profit_factor"] is None
    json.dumps(panel, allow_nan=False)  # renders as "∞"/"n/a" in JS, never NaN


def test_empty_payload_renders_explicit_empty_state():
    panel = build_per_class_verdicts(_ledger([], []), [])
    assert panel["classes"] == []
    assert panel["rows_counted"] == 0
    assert panel["mode"] == "canonical"
    # The JS empty-state path is a string, not a broken table.
    js = (REPO_ROOT / "audit_dashboard" / "audit2.js").read_text(encoding="utf-8")
    assert "per-class panel is empty" in js
    assert "per-class panel not in this payload" in js


def test_mode_and_generated_at_are_carried_for_the_caption():
    panel = build_per_class_verdicts(
        _ledger([], [], mode="payload_slice", generated_at="2026-11-20T05:00:00Z"), [])
    assert panel["mode"] == "payload_slice"
    assert panel["generated_at"] == "2026-11-20T05:00:00Z"


def test_provenance_names_a_source_for_every_rendered_field():
    panel = build_per_class_verdicts(_ledger(BASE_CLASSES, BASE_CELLS),
                                     _rows(BASE_PICKS))
    src = panel["classes"][0]["field_sources"]
    for field in ("n", "mean_net_pct", "win_rate_pct", "profit_factor",
                  "net_ci_pct", "verdict", "n_cells"):
        assert field in src and src[field], field
