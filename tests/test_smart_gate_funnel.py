"""Tests for the Smart Picks gate funnel evaluator + UEPS unmarked-PnL honesty.

Covers the 2026-10-18 picks-plan P2/P4b work:
- ``evaluate_smart_gate_funnel`` (audit_trail.quality_gates) — the evaluator
  both ``tools/audit_smart_gate_funnel.py`` and
  ``dashboard_generator._build_smart_gate_failure_histogram`` import; it was
  missing from quality_gates (ImportError → silent {} / tool crash), which is
  why smartCount=0 was never explained anywhere.
- ``_build_ueps_kpi_sidecar`` — UEPS picks are not price-marked (B28 sidecar
  bypasses the resolver), so their pnl_pct is a placeholder 0.0; the sidecar
  must report ``unrealized_status="unmarked"`` + null sums instead of 0.0%.
"""
from __future__ import annotations

import copy
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from audit_trail.quality_gates import (  # noqa: E402
    evaluate_smart_gate_funnel,
    passes_smart_gate,
)
from audit_trail.dashboard_generator import (  # noqa: E402
    _build_smart_gate_failure_histogram,
    _build_ueps_kpi_sidecar,
)


def _base_pick(**over):
    """A pick that clears the earliest gates so deeper checks decide."""
    p = {
        "symbol": "XRPUSDT",
        "asset_class": "CRYPTO",
        "direction": "LONG",
        "strategy": "unit_test_strategy",
        "source_system": "unit_test_source",
        "score": 70,
        "confidence": 0.8,
        "status": "OPEN",
        "forward_validated": True,
        "entry_price": 1.0,
        "age_hours": 2.0,
        "pnl_pct": 0.5,
    }
    p.update(over)
    return p


# ── evaluate_smart_gate_funnel contract ──────────────────────────────────────


def test_funnel_returns_bool_str_contract() -> None:
    ok, reason = evaluate_smart_gate_funnel(copy.deepcopy(_base_pick()))
    assert isinstance(ok, bool)
    assert isinstance(reason, str)


def test_funnel_reports_forward_validated_false_annotation() -> None:
    # forward_validated=false is annotated by the gate as _smart_reject_reasons
    pick = _base_pick(forward_validated=False)
    ok, reason = evaluate_smart_gate_funnel(copy.deepcopy(pick))
    assert ok is False
    assert reason == "forward_validated=false"


def test_funnel_never_returns_criteria_not_met_for_annotated_paths() -> None:
    # A pick failing the score floor must carry the exact code, not the fallback
    pick = _base_pick(score=1)
    ok, reason = evaluate_smart_gate_funnel(copy.deepcopy(pick))
    assert ok is False
    assert reason and reason != "evaluator_error"


def test_funnel_matches_passes_smart_gate_decision() -> None:
    # The evaluator must NEVER disagree with the gate it wraps (single source).
    for pick in (
        _base_pick(),
        _base_pick(forward_validated=False),
        _base_pick(score=1),
        _base_pick(asset_class="FOREX", direction="LONG", symbol="EURGBP=X",
                   elite_score=50),
    ):
        ok_eval, _ = evaluate_smart_gate_funnel(copy.deepcopy(pick))
        ok_gate = passes_smart_gate(copy.deepcopy(pick))
        assert ok_eval == ok_gate, f"decision mismatch for {pick['symbol']}"


def test_funnel_does_not_leak_logger_handlers() -> None:
    import logging

    logger = logging.getLogger("audit_trail.quality_gates")
    before = len(logger.handlers)
    evaluate_smart_gate_funnel(copy.deepcopy(_base_pick(forward_validated=False)))
    assert len(logger.handlers) == before


# ── smart-gate failure histogram (payload emitter) ───────────────────────────


def test_histogram_covers_every_active_pick() -> None:
    actives = [
        _base_pick(forward_validated=False),
        _base_pick(score=1),
        _base_pick(symbol="ABCUSDT", forward_validated=True, score=70),
    ]
    hist = _build_smart_gate_failure_histogram(actives)
    assert hist, "histogram must not be empty (was {} while evaluator import failed)"
    total = sum(bucket.get("_total", 0) for bucket in hist.values())
    assert total == len(actives)
    # per-class grouping with a passed counter
    assert all("_passed" in b for b in hist.values())


# ── UEPS sidecar unmarked-PnL honesty (P2) ───────────────────────────────────


def _ueps_pick(**over):
    p = {
        "source_system": "ueps",
        "symbol": "GOOGL",
        "direction": "LONG",
        "entry_price": 100.0,
        "take_profit": 110.0,
        "stop_loss": 95.0,
        "score": 72,
        "confidence": 0.7,
        "age_hours": 3.0,
        "pnl_pct": 0.0,  # placeholder — resolver never marks UEPS picks
        "status": "OPEN",
    }
    p.update(over)
    return p


def test_ueps_all_zero_pnl_is_unmarked_with_null_sums() -> None:
    kpi = _build_ueps_kpi_sidecar([_ueps_pick(), _ueps_pick(symbol="MSFT")])
    agg = kpi["aggregate"]
    assert kpi["status"] == "active"
    assert agg["unrealized_status"] == "unmarked"
    assert agg["sum_unrealized_pnl_pct"] is None
    assert agg["avg_unrealized_pnl_pct"] is None
    assert agg["pnl_marked_positions"] == 0
    assert "not price-marked" in kpi["message"]


def test_ueps_marked_positions_report_real_sums() -> None:
    kpi = _build_ueps_kpi_sidecar(
        [_ueps_pick(pnl_pct=3.5), _ueps_pick(symbol="MSFT", pnl_pct=1.5)]
    )
    agg = kpi["aggregate"]
    assert agg["unrealized_status"] == "marked"
    assert agg["pnl_marked_positions"] == 2
    assert abs(agg["sum_unrealized_pnl_pct"] - 5.0) < 1e-9


def test_ueps_empty_status_unchanged() -> None:
    kpi = _build_ueps_kpi_sidecar([])
    assert kpi["status"] == "empty"
    assert kpi["open_positions"] == 0
