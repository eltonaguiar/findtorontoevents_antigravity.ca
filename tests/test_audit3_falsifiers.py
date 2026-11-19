"""Falsifier tests promised in the design debate.

Each test states an observation that MUST be impossible. If any of these passes,
the corresponding gate is decoration rather than a filter.
"""
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from alpha_engine.audit3_tribunal import (  # noqa: E402
    apply_selection_alpha_gate,
    build_report,
    deflated_sharpe,
)


def _rows(n, pnl, **kw):
    return [{"id": f"x-{i}", "asset_class": kw.get("ac", "CRYPTO"),
             "strategy": kw.get("strategy", "s1"), "direction": "LONG",
             "symbol": kw.get("symbol", "BTCUSDT"), "source_system": "alpha_engine",
             "status": "WON" if pnl > 0 else "LOST", "pnl_pct": pnl,
             "closed_at": f"2026-11-{1 + i % 18:02d}T00:00:00+00:00"}
            for i in range(n)]


# (a) provenance must change when the denominator changes
def test_provenance_id_changes_with_the_denominator():
    rows = _rows(50, 1.0)
    cov_a = {"denominator": {"mode": "canonical"}, "scored_rows": 50,
             "total_closed_picks": 50}
    cov_b = {"denominator": {"mode": "payload_slice"}, "scored_rows": 50,
             "total_closed_picks": 500}
    a = build_report(rows, "x.json", None, coverage=cov_a)["provenance"]
    b = build_report(rows, "x.json", None, coverage=cov_b)["provenance"]
    assert a["id"] != b["id"], "same provenance id for different populations"
    assert a["population"] == "canonical" and b["population"] == "payload_slice"


# (b) a clearly losing cell cannot be promoted
def test_a_negative_expectancy_cell_cannot_reach_proven_or_candidate():
    rows = _rows(200, -1.5)
    for i, r in enumerate(rows):
        r["pnl_pct"] = -1.5 if i % 2 == 0 else -0.5     # mean -1.0%, has variance
        r["symbol"] = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"][i % 4]
    pod = {"path": "m.json", "available": True,
           "pods": [{"id": "POD-X", "status": "pre_registered", "strategies": ["s1"],
                     "asset_classes": ["CRYPTO"]}]}
    cell = build_report(rows, "x.json", None, confirmatory=pod)["cells"][0]
    assert cell["verdict"] not in ("PROVEN_T2", "CANDIDATE"), cell["verdict"]


# (c) a strategy identical to buy-and-hold has zero selection alpha and cannot be proven
def test_zero_selection_alpha_cannot_prove_a_cell():
    cell = {"asset_class": "CRYPTO", "strategy": "s1", "direction": "LONG",
            "verdict": "PROVEN_T2", "n": 300, "reasons": []}
    # alpha == 0 with a symmetric interval is exactly the buy-and-hold case
    alpha = {"by_strategy": {"CRYPTO/s1/LONG": {"n": 300, "alpha_ci": [-0.4, 0.4]}}}
    apply_selection_alpha_gate([cell], alpha)
    assert cell["verdict"] != "PROVEN_T2"
    assert cell["alpha_gate"]["status"] == "unproven"


# (d) multiplicity must bite: one trial is undefined, a null series never clears,
#     and more trials can only lower the deflated Sharpe.
def test_dsr_is_undefined_with_one_trial_and_null_series_cannot_clear():
    assert deflated_sharpe([0.5, -0.2, 0.7, -0.1, 0.4] * 40, 1) is None
    null = [1.0, -1.0] * 200
    for trials in (2, 10, 658):
        d = deflated_sharpe(null, trials)
        assert d is None or d["dsr"] < 0.95, f"null series cleared DSR at {trials} trials"
    strong = [0.5, -0.2, 0.7, -0.1, 0.4] * 40
    few = deflated_sharpe(strong, 2)
    many = deflated_sharpe(strong, 658)
    assert few and many and many["dsr"] <= few["dsr"] + 1e-9
