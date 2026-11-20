"""A published PF must carry its denominator and cost treatment (2026-11-20).

CRYPTO was simultaneously published at PF 1.31, 0.83 and 0.26 -- every one
arithmetically correct, differing only in population and cost. These tests pin
the rendering rule and that the publishers actually emit it.
"""
from __future__ import annotations

import inspect

from alpha_engine.pf_basis import format_pf, pf_record


def test_label_carries_n_and_cost():
    # audit3 CRYPTO mean_cost_pct=0.0985 -> 9.85bp -> one decimal -> 9.8bp
    assert format_pf(0.8339, 6874, cost_bps=9.85) == "PF 0.83 (n=6,874, net 9.8bp)"


def test_no_measured_cost_makes_no_net_claim():
    assert format_pf(1.3131, 2070, basis="gross") == "PF 1.31 (n=2,070, gross)"
    rec = pf_record(1.3131, 2070, basis="gross")
    assert rec["pf_cost_bps"] is None  # unmeasured is not the same as zero cost
    assert rec["pf_n"] == 2070
    assert rec["pf_label"].endswith("(n=2,070, gross)")


def test_explicit_zero_cost_is_stated_not_omitted():
    assert format_pf(2.0, 10, cost_bps=0.0) == "PF 2.00 (n=10, net 0.0bp)"


def test_non_numbers_render_as_na():
    assert format_pf(None, 5) == "PF n/a (n=5)"
    assert format_pf(float("nan")) == "PF n/a"
    assert format_pf(float("inf"), 3).startswith("PF inf")


def test_record_coerces_string_counts():
    rec = pf_record(0.2628, "22148")
    assert rec["pf_n"] == 22148
    assert rec["pf_basis"] is None
    assert rec["pf_label"] == "PF 0.26 (n=22,148)"


def test_publishers_emit_the_label():
    from alpha_engine import audit3_tribunal, money_ready_verdict

    assert "pf_label" in inspect.getsource(money_ready_verdict._class_stats)
    assert "pf_label" in inspect.getsource(audit3_tribunal.evaluate_cell)
