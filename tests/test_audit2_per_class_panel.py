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
    # CRYPTO: 5 rows — UNBALANCED on purpose (3 wins / 2 losses) and with
    # asymmetric magnitude (wins sum to 6.5, losses to -1.4). A balanced set
    # makes a wins/losses swap a no-op: the counts stay equal, and swapping
    # which bucket each P&L lands in preserves both the mean and PF. With an
    # unbalanced class the swap changes the counts, so the sabotage test can
    # actually see it.
    _pick("BTC-USD", "CRYPTO", 2.5, strategy="A"),
    _pick("ETH-USD", "CRYPTO", -1.0, strategy="B", entry=200.0),
    _pick("SOL-USD", "CRYPTO", 0.8, strategy="A", entry=50.0),
    _pick("ADA-USD", "CRYPTO", -0.4, strategy="B", entry=1.0),
    _pick("DOT-USD", "CRYPTO", 3.2, strategy="A", entry=10.0),
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
        "coverage": {"denominator": {"mode": mode}, "scored_rows": 7},
        "summary": {},
        "provenance": {},
    }


BASE_CLASSES = [
    {"asset_class": "CRYPTO", "verdict": "KILL", "n": 5, "net_ci_pct": [-1.0, 0.5],
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


# ── P1-3: correctness, not just consistency ──────────────────────────────────
# test_panel_numbers_equal_class_rollup_exactly asserts panel == class_rollup().
# That is a CONSISTENCY check: if class_rollup() is wrong, both sides are wrong
# together and it stays green. It certifies agreement between two things that
# share an implementation — the same weakness as the Phase A filter-split bug.
#
# Everything below is INDEPENDENT of alpha_engine.resolved_closed_view: the
# reference rollup is plain Python over the raw fixture dicts, and the golden
# snapshot was generated from THAT reference, never from the module under test.

#: Independent literal copy of per-class round-trip cost, in bps. A copy, not
#: an import: if the module's table changes the golden file must be
#: regenerated deliberately, not silently agreed with.
_REF_COST_BPS = {
    "CRYPTO": 9.97, "EQUITY": 5.0, "ETF": 5.0, "FOREX": 2.0, "BOND": 5.0,
    "FUTURES": 15.0, "COMMODITY": 15.0, "MUTUAL_FUND": 8.0,
}
_REF_DEFAULT_COST_BPS = 10.0
_REF_FLAT_EPS = 0.01
_REF_MIN_N = 20

#: The rollup-derived fields the panel renders — the ones with real arithmetic.
_REF_ROLLUP_KEYS = ("n", "wins", "losses", "flat", "win_rate_pct",
                    "profit_factor", "mean_net_pct", "mean_cost_bps")


def _ref_rollup(picks):
    """Per-class rollup from raw picks, sharing no code with the module."""
    acc = {}
    for p in picks:
        cls = str(p.get("asset_class") or "UNKNOWN").upper()
        gross = float(p["pnl_pct"])
        cost = _REF_COST_BPS.get(cls, _REF_DEFAULT_COST_BPS)
        net = gross - cost / 100.0
        a = acc.setdefault(cls, {"n": 0, "wins": 0, "losses": 0, "flat": 0,
                                 "gross": 0.0, "net": 0.0, "cost": 0.0,
                                 "win_sum": 0.0, "loss_sum": 0.0})
        a["n"] += 1
        a["gross"] += gross
        a["net"] += net
        a["cost"] += cost
        if gross > _REF_FLAT_EPS:
            a["wins"] += 1
            a["win_sum"] += gross
        elif gross < -_REF_FLAT_EPS:
            a["losses"] += 1
            a["loss_sum"] += gross
        else:
            a["flat"] += 1

    out = {}
    for cls, a in sorted(acc.items()):
        decided = a["wins"] + a["losses"]
        pf = a["win_sum"] / abs(a["loss_sum"]) if a["loss_sum"] else None
        out[cls] = {
            "n": a["n"],
            "wins": a["wins"],
            "losses": a["losses"],
            "flat": a["flat"],
            "win_rate_pct": round(100.0 * a["wins"] / decided, 2) if decided else None,
            "profit_factor": round(pf, 4) if pf is not None else None,
            "mean_net_pct": round(a["net"] / a["n"], 4),
            "mean_cost_bps": round(a["cost"] / a["n"], 3),
        }
    return out


def _mutated_rollup(picks, mutation):
    """A deliberately broken copy of the reference rollup — the sabotage double.

    Kept in the test file on purpose: if these mutants were caught by the
    module's own equality assertion, the strengthened check would prove
    nothing. Each mutation is a class of bug a reader would not spot by eye.
    """
    acc = {}
    for i, p in enumerate(picks):
        if mutation == "drop_one_row" and i == 0:
            continue
        cls = str(p.get("asset_class") or "UNKNOWN").upper()
        gross = float(p["pnl_pct"])
        cost = _REF_COST_BPS.get(cls, _REF_DEFAULT_COST_BPS)
        net = gross if mutation == "skip_cost" else gross - cost / 100.0
        a = acc.setdefault(cls, {"n": 0, "wins": 0, "losses": 0, "flat": 0,
                                 "net": 0.0, "cost": 0.0,
                                 "win_sum": 0.0, "loss_sum": 0.0})
        a["n"] += 1
        a["net"] += net
        a["cost"] += cost
        if gross > _REF_FLAT_EPS:
            if mutation == "swap_wins_losses":
                a["losses"] += 1
                a["loss_sum"] += gross
            else:
                a["wins"] += 1
                a["win_sum"] += gross
        elif gross < -_REF_FLAT_EPS:
            if mutation == "swap_wins_losses":
                a["wins"] += 1
                a["win_sum"] += gross
            else:
                a["losses"] += 1
                a["loss_sum"] += gross
        else:
            a["flat"] += 1

    out = {}
    for cls, a in sorted(acc.items()):
        decided = a["wins"] + a["losses"]
        pf = a["win_sum"] / abs(a["loss_sum"]) if a["loss_sum"] else None
        out[cls] = {
            "n": a["n"], "wins": a["wins"], "losses": a["losses"], "flat": a["flat"],
            "win_rate_pct": round(100.0 * a["wins"] / decided, 2) if decided else None,
            "profit_factor": round(pf, 4) if pf is not None else None,
            "mean_net_pct": round(a["net"] / a["n"], 4),
            "mean_cost_bps": round(a["cost"] / a["n"], 3),
        }
    return out


def _assert_panel_matches(panel, reference):
    """The strengthened assertion: panel equals an INDEPENDENT computation."""
    by_class = {e["asset_class"]: e for e in panel["classes"]}
    assert set(by_class) == set(reference), "panel and reference must cover the same classes"
    for cls, ref in reference.items():
        for key, expected in ref.items():
            actual = by_class[cls][key]
            assert actual == expected, (
                f"{cls}.{key}: panel {actual!r} != independent reference {expected!r}")


def test_panel_numbers_equal_an_independent_reference():
    rows = _rows(BASE_PICKS)
    panel = build_per_class_verdicts(_ledger(BASE_CLASSES, BASE_CELLS), rows)
    _assert_panel_matches(panel, _ref_rollup(BASE_PICKS))


# ── golden file ─────────────────────────────────────────────────────────────
GOLDEN_PATH = REPO_ROOT / "tests" / "golden" / "audit2_per_class_verdicts.json"
GOLDEN_PROVENANCE = "independent_reference_implementation"

#: Fixed fixture, no randomness, no clock, no network. Carries the awkward
#: cases on purpose: a flat row, a tiny-n class, and a class that exists only
#: in the tribunal block.
GOLDEN_PICKS = [
    _pick("BTC-USD", "CRYPTO", 3.0, strategy="A", entry=100.0),
    _pick("ETH-USD", "CRYPTO", -2.0, strategy="A", entry=200.0),
    _pick("SOL-USD", "CRYPTO", 0.0, strategy="B", entry=50.0),   # flat
    _pick("AAPL", "EQUITY", 1.5, strategy="C", entry=150.0),
    _pick("MSFT", "EQUITY", -0.5, strategy="C", entry=300.0),
    _pick("SPY", "ETF", -1.25, strategy="D", entry=400.0),        # n=1 → inconclusive
]
GOLDEN_CLASSES = [
    {"asset_class": "CRYPTO", "verdict": "KILL", "n": 3, "net_ci_pct": [-1.2, 0.9]},
    {"asset_class": "EQUITY", "verdict": "WEAK", "n": 2, "net_ci_pct": [-0.3, 0.6]},
    {"asset_class": "ETF", "verdict": "PROVEN_T2", "n": 1, "net_ci_pct": [-2.0, -0.5]},
    {"asset_class": "BOND", "verdict": "WEAK", "n": 35, "net_ci_pct": [-0.1, 0.2]},
]
GOLDEN_CELLS = [
    {"asset_class": "CRYPTO", "strategy": "A", "direction": "LONG", "n": 25},
    {"asset_class": "CRYPTO", "strategy": "B", "direction": "LONG", "n": 5},
    {"asset_class": "EQUITY", "strategy": "C", "direction": "LONG", "n": 2},
    {"asset_class": "BOND", "strategy": "D", "direction": "LONG", "n": 12},
]


def _golden_snapshot():
    """The expected rendered pane, derived ONLY from the independent reference."""
    ledger = _ledger(GOLDEN_CLASSES, GOLDEN_CELLS)
    rollup = _ref_rollup(GOLDEN_PICKS)
    tribunal = {str(c["asset_class"]).upper(): c for c in ledger["classes"]}
    cells = {}
    for cell in ledger["cells"]:
        cls = str(cell["asset_class"]).upper()
        slot = cells.setdefault(cls, {"n_cells": 0, "n_cells_tested": 0})
        slot["n_cells"] += 1
        if cell["n"] >= _REF_MIN_N:
            slot["n_cells_tested"] += 1

    entries = {}
    for cls in sorted(set(rollup) | set(tribunal) | set(cells)):
        roll = rollup.get(cls)
        ver = tribunal.get(cls)
        n = roll["n"] if roll else (ver.get("n") if ver else None)
        raw = ver.get("verdict") if ver else None
        if raw is None:
            word = "no verdict"
        elif n is not None and n < _REF_MIN_N:
            word = "inconclusive"
        elif str(raw).upper() == "INSUFFICIENT_N":
            word = "inconclusive"
        else:
            word = str(raw)
        entry = {
            "asset_class": cls,
            "net_ci_pct": ver.get("net_ci_pct") if ver else None,
            "verdict": raw,
            "verdict_word": word,
            "n_cells": cells.get(cls, {}).get("n_cells"),
            "n_cells_tested": cells.get(cls, {}).get("n_cells_tested"),
            "in_rollup": roll is not None,
            "in_tribunal": ver is not None,
        }
        entry["n"] = n
        for key in _REF_ROLLUP_KEYS:
            entry.setdefault(key, None)
        for key, value in (roll or {}).items():
            entry[key] = value
        entries[cls] = entry
    return entries


def test_panel_matches_golden_snapshot():
    """A wrong class_rollup() cannot pass: the snapshot never saw the module."""
    golden = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))
    assert golden["provenance"] == GOLDEN_PROVENANCE, (
        "golden file must be generated from the independent reference, not the module")
    rows = _rows(GOLDEN_PICKS)
    panel = build_per_class_verdicts(_ledger(GOLDEN_CLASSES, GOLDEN_CELLS), rows)
    by_class = {e["asset_class"]: e for e in panel["classes"]}
    assert set(by_class) == set(golden["classes"]), "golden and panel must cover the same classes"
    for cls, expected in golden["classes"].items():
        for key, value in expected.items():
            assert by_class[cls][key] == value, (
                f"{cls}.{key}: panel {by_class[cls][key]!r} != golden {value!r} — "
                "a human must decide which is right")


def _caught_message(panel, reference):
    """Run the strengthened check; return its failure message or None if it passed."""
    try:
        _assert_panel_matches(panel, reference)
    except AssertionError as exc:
        return str(exc)
    return None


def test_sabotage_the_strengthened_check_is_load_bearing():
    """Prove the checks above actually fail on a broken rollup.

    If a mutant passes, the test proves nothing — that would be a finding, not
    a reason to delete the test, so this asserts each mutant is CAUGHT.
    """
    rows = _rows(BASE_PICKS)
    panel = build_per_class_verdicts(_ledger(BASE_CLASSES, BASE_CELLS), rows)

    # Control: the honest reference passes.
    _assert_panel_matches(panel, _ref_rollup(BASE_PICKS))

    for mutation in ("drop_one_row", "swap_wins_losses", "skip_cost"):
        message = _caught_message(panel, _mutated_rollup(BASE_PICKS, mutation))
        assert message is not None, f"mutant {mutation!r} was NOT caught"


def test_sabotage_catches_a_wins_losses_swap():
    """The gap this closes: on a BALANCED fixture a wins/losses swap is a no-op.

    Swapping buckets leaves the counts equal and preserves both the mean and
    the profit factor, so every asserted value is unchanged and the mutant
    passes. BASE_PICKS is deliberately unbalanced (CRYPTO 3 wins / 2 losses,
    asymmetric magnitude), so the swap now moves wins, losses, win rate and PF.
    """
    rows = _rows(BASE_PICKS)
    panel = build_per_class_verdicts(_ledger(BASE_CLASSES, BASE_CELLS), rows)
    swapped = _mutated_rollup(BASE_PICKS, "swap_wins_losses")

    # The fixture really is unbalanced — otherwise this test is vacuous.
    ref_crypto = _ref_rollup(BASE_PICKS)["CRYPTO"]
    assert ref_crypto["wins"] != ref_crypto["losses"], (
        "fixture must be unbalanced or the swap is undetectable")

    # And the swap genuinely changes the statistics it is supposed to corrupt.
    assert swapped["CRYPTO"]["wins"] != ref_crypto["wins"]
    assert swapped["CRYPTO"]["profit_factor"] != ref_crypto["profit_factor"]

    message = _caught_message(panel, swapped)
    assert message is not None, "wins/losses swap was NOT caught"
    assert "CRYPTO" in message
