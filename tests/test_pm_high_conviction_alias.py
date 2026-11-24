"""Regression tests for the pm_high_conviction alias gate in
audit_trail.dashboard_generator._prepare_prediction_market_consensus_signal.

Finding (2026-11-16): the virtual `pm_high_conviction` label path bypassed the
high-conviction validation gate that source-derived rows pass — a pre-set
`high_conviction` flag or a `consensus_data.high_conviction` alias (producer
rule is loose: `consensus_score >= X or num_sources >= 3`) short-circuited the
`source_count >= 3 and fwd_wr >= 55 and fwd_trades >= 8 and consensus_bias >= 0`
criteria via the old `if pick.get("high_conviction") is None:` skip. Alias rows
must pass the SAME validation as source rows (no gate skip). The gate's fwd_wr
comparison is percent-stated while producers emit 0..1 fractions
(alpha_engine/prediction_market_consensus._pick_first_wr_fraction), so the
comparison normalises units.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from audit_trail.dashboard_generator import (
    _prepare_prediction_market_consensus_signal as prepare,
)


def _criteria_pass_row(**overrides):
    row = {
        "source_count": 3,
        "forward_wr": 0.62,
        "forward_trades": 12,
        "consensus_data": {"source_category_count": 3, "consensus_score": 0.5},
    }
    row.update(overrides)
    return row


def test_source_row_passing_criteria_gets_label():
    out = prepare(_criteria_pass_row())
    assert out["high_conviction"] is True


def test_source_row_failing_criteria_gets_no_label():
    out = prepare(_criteria_pass_row(source_count=2))
    assert out["high_conviction"] is False


def test_consensus_data_alias_cannot_bypass_gate():
    row = _criteria_pass_row(source_count=1, forward_wr=0, forward_trades=0)
    row["consensus_data"] = {
        "high_conviction": True,
        "source_category_count": 1,
    }
    out = prepare(row)
    assert out["high_conviction"] is False, (
        "consensus_data.high_conviction must not skip the criteria gate"
    )


def test_preset_flag_cannot_bypass_gate():
    row = _criteria_pass_row(source_count=1, forward_wr=0.1, forward_trades=1)
    row["high_conviction"] = True
    out = prepare(row)
    assert out["high_conviction"] is False, (
        "a pre-set high_conviction flag must not skip the criteria gate"
    )


def test_upstream_label_confirms_gate_passing_row():
    row = _criteria_pass_row()
    row["high_conviction"] = True
    row["consensus_data"]["high_conviction"] = True
    out = prepare(row)
    assert out["high_conviction"] is True


def test_explicit_upstream_false_opts_out():
    row = _criteria_pass_row()
    row["high_conviction"] = False
    out = prepare(row)
    assert out["high_conviction"] is False


def test_fraction_wr_normalised_to_percent():
    # 1.0 is a 100% WR fraction in producer payloads (150-trade wallet rows),
    # not "1 percent" — the percent-stated gate must see 100.0.
    row = _criteria_pass_row(forward_wr=1.0, forward_trades=150)
    out = prepare(row)
    assert out["high_conviction"] is True


def test_alias_and_source_rows_share_validation():
    """Same underlying data, with and without an upstream alias claim, must get
    the same verdict — the alias can never flip the gate outcome upward."""
    base = _criteria_pass_row(source_count=3, forward_wr=0.40, forward_trades=10)
    claimed = dict(base)
    claimed["high_conviction"] = True
    claimed["consensus_data"] = dict(base["consensus_data"], high_conviction=True)
    assert prepare(dict(claimed))["high_conviction"] == prepare(dict(base))["high_conviction"]
