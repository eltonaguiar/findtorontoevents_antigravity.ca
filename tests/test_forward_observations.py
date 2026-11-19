"""Contract tests for alpha_engine/forward_observations.py.

The promotion rule here decides when audit3 may call something PROVEN from live data,
so each clause gets a test that fails if the clause is silently dropped.
"""
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from alpha_engine import forward_observations as F  # noqa: E402

NOW = datetime(2026, 11, 19, 12, 0, tzinfo=timezone.utc)


def _row(**over):
    base = {
        "id": "obs-1",
        "hypothesis_id": "H-119",
        "opened_at": (NOW - timedelta(days=2)).isoformat(),
        "closed_at": (NOW - timedelta(days=1)).isoformat(),
        "symbol": "JUPUSDT",
        "asset_class": "CRYPTO",
        "side": "LONG",
        "entry_px": 1.00,
        "exit_px": 1.02,
        "qty": 100.0,
        "fees": 0.10,
        "funding": 0.0,
        "slippage_bps": 4.0,
        "resolver_version": "intrabar-v3",
        "intrabar_first_touch": True,
        "benchmark_leg_ret": 0.001,
        "regime_ok": True,
        "created_at": NOW.isoformat(),
    }
    base.update(over)
    return base


def _rows(n, **over):
    out = []
    for i in range(n):
        row = _row(**over)
        row["id"] = f"obs-{i}"
        row["symbol"] = f"SYM{i % 7}USDT"
        row["opened_at"] = (NOW - timedelta(days=2 + i % 20, hours=i % 5)).isoformat()
        row["closed_at"] = (NOW - timedelta(days=1 + i % 20, hours=i % 5)).isoformat()
        out.append(row)
    return out


# --------------------------------------------------------------------------- schema
def test_valid_row_has_no_errors():
    assert F.validate(_row(), {"H-119"}) == []


def test_missing_field_is_reported_once_as_a_group():
    row = _row()
    row.pop("benchmark_leg_ret")
    errors = F.validate(row, {"H-119"})
    assert len(errors) == 1 and "benchmark_leg_ret" in errors[0]


def test_dangling_hypothesis_fk_is_rejected():
    errors = F.validate(_row(hypothesis_id="H-999"), {"H-119"})
    assert any("dangling FK" in e for e in errors)


def test_daily_resolved_row_is_not_forward_evidence():
    errors = F.validate(_row(intrabar_first_touch=False), {"H-119"})
    assert any("intrabar_first_touch" in e for e in errors)


def test_closed_before_opened_rejected():
    row = _row(opened_at=NOW.isoformat(), closed_at=(NOW - timedelta(hours=1)).isoformat())
    assert any("precedes" in e for e in F.validate(row, {"H-119"}))


def test_negative_slippage_rejected():
    assert any("slippage_bps" in e for e in F.validate(_row(slippage_bps=-1), {"H-119"}))


def test_zero_qty_rejected_because_return_is_undefined():
    assert any("qty" in e for e in F.validate(_row(qty=0), {"H-119"}))


def test_unknown_side_rejected():
    assert any("side" in e for e in F.validate(_row(side="SIDEWAYS"), {"H-119"}))


# ---------------------------------------------------------------------- cost arithmetic
def test_net_return_charges_fees_funding_and_slippage():
    """gross +1.00%, then (fees 0.20 - funding received 0.10)/100 notional = 0.10%,
    then 5bps slippage = 0.05% -> 0.85% net. A tester that only subtracted fees would
    report 0.90%, which is why the cost definition lives in one function."""
    row = _row(entry_px=100.0, exit_px=101.0, qty=1.0, fees=0.20, funding=-0.10, slippage_bps=5.0)
    assert F.net_returns([row])[0] == pytest.approx(0.01 - 0.001 - 0.0005, abs=1e-12)


def test_short_side_flips_sign():
    row = _row(side="SHORT", entry_px=100.0, exit_px=99.0, qty=1.0, fees=0.0, slippage_bps=0.0)
    assert F.net_returns([row])[0] == pytest.approx(0.01, abs=1e-9)


def test_row_without_usable_prices_is_skipped_not_zero_filled():
    assert F.net_returns([_row(entry_px=0)]) == []


def test_funding_paid_reduces_net():
    paid = F.net_returns([_row(entry_px=100.0, exit_px=101.0, qty=1.0, fees=0.0, funding=0.5, slippage_bps=0)])[0]
    assert paid < 0.01


# ------------------------------------------------------------------------- promotion
def test_no_rows_cannot_promote():
    out = F.promotion([])
    assert out["eligible"] is False and out["n_forward"] == 0


def test_promotion_requires_the_min_n_even_with_a_huge_edge():
    out = F.promotion(_rows(F.PROMOTION_MIN_N - 1))
    assert out["eligible"] is False
    assert any("n_forward" in r for r in out["reasons"])


def test_promotion_clears_at_min_n_with_a_real_edge():
    # Varied outcomes (+3% / -1%), not 100 identical winners: identical rows have zero
    # dispersion, which makes IR undefined and would test the accident, not the rule.
    rows = _rows(F.PROMOTION_MIN_N)
    for i, row in enumerate(rows):
        row["exit_px"] = 1.03 if i % 4 else 0.99
    out = F.promotion(rows)
    assert out["n_forward"] == F.PROMOTION_MIN_N
    assert out["pf_ci_lb"] and out["pf_ci_lb"] > 1.0
    assert out["eligible"] is True, out["reasons"]


def test_promotion_refuses_daily_resolved_rows():
    out = F.promotion(_rows(F.PROMOTION_MIN_N, intrabar_first_touch=False))
    assert out["eligible"] is False
    assert any("intrabar" in r for r in out["reasons"])


def test_promotion_requires_benchmark_coverage():
    rows = _rows(F.PROMOTION_MIN_N)
    for row in rows[:40]:
        row["benchmark_leg_ret"] = None
    out = F.promotion(rows)
    assert out["eligible"] is False
    assert any("benchmark_leg_ret" in r for r in out["reasons"])


def test_losing_rows_do_not_promote():
    rows = _rows(F.PROMOTION_MIN_N, exit_px=0.99)
    out = F.promotion(rows)
    assert out["eligible"] is False
    assert any("CI-LB" in r for r in out["reasons"])


# ----------------------------------------------------------------------------- clock
def test_clock_reports_no_rows_without_inventing_an_eta():
    out = F.clock("H-119", rows=[], now=NOW)
    assert out["status"] == "NO_FORWARD_ROWS"
    assert out["eta_at"] is None and out["eta_days"] is None


def test_clock_extrapolates_from_the_observed_rate():
    rows = _rows(30)
    out = F.clock("H-119", rows=rows, now=NOW)
    assert out["n_forward"] == 30
    assert out["rate_per_day"] > 0
    assert out["eta_days"] and out["eta_days"] > 0


def test_clock_says_gate_met_once_n_is_reached():
    out = F.clock("H-119", rows=_rows(F.PROMOTION_MIN_N), now=NOW)
    assert out["status"] == "N_GATE_MET" and out["remaining"] == 0


# ---------------------------------------------------------------------------- ledger
def test_append_dedupes_and_rejects(tmp_path):
    ledger = tmp_path / "fo.jsonl"
    good = _rows(3)
    bad = _row(id="bad-1", side="SIDEWAYS")
    report = F.append(good + [bad], ledger, known_hypotheses={"H-119"})
    assert report["added"] == 3 and len(report["rejected"]) == 1
    again = F.append(good, ledger, known_hypotheses={"H-119"})
    assert again["added"] == 0 and again["duplicates"] == 3
    rows, errors = F.load(ledger)
    assert len(rows) == 3 and errors == []


def test_verify_flags_dangling_hypothesis_in_an_existing_ledger(tmp_path):
    ledger = tmp_path / "fo.jsonl"
    ledger.write_text('{"id": "x", "hypothesis_id": "H-404"}\n', encoding="utf-8")
    out = F.verify(ledger)
    assert out["ok"] is False
    assert out["violations"]


def test_missing_ledger_is_empty_not_an_error(tmp_path):
    rows, errors = F.load(tmp_path / "nope.jsonl")
    assert rows == [] and errors == []
