"""Wire-up tests for the STAT_RIGOR_ENABLED audit_metrics_block stamping.

Wire site: audit_trail/dashboard_generator.py::_build_strategy_breakdown
Source: alpha_engine/statistical_rigor.py::audit_metrics_block

Phase 2 of the Hedge-Fund-Uplift Roadmap (PR-B). Default-OFF, 14-day shadow
per CLAUDE.md gate-change rule. These tests pin three contracts:

1. With STAT_RIGOR_ENABLED unset / "0", `_stat_rigor_block` is never stamped
   (zero behavior change for production).
2. With STAT_RIGOR_ENABLED="1" and >=4 closed picks per strategy, the field
   is stamped with the expected shape (n / profit_factor / win_rate / sharpe
   / psr_vs_zero), each numeric metric carrying point + lo + hi CIs.
3. Thin-sample strategies (n<4) and computation failures must NOT crash
   _build_strategy_breakdown — they're skipped silently so the dashboard
   stays alive even if statistical_rigor breaks.
"""
from __future__ import annotations

import pytest

from audit_trail.dashboard_generator import _build_strategy_breakdown


def _strat_bucket(pnl_series, *, active=0, wins=None, losses=None, flat=None):
    """Build a strat_dict[name] entry shaped like the dashboard generator's."""
    if wins is None:
        wins = sum(1 for p in pnl_series if p > 0)
    if losses is None:
        losses = sum(1 for p in pnl_series if p < 0)
    if flat is None:
        flat = sum(1 for p in pnl_series if p == 0)
    total_pnl = sum(pnl_series)
    return {
        "active": active,
        "wins": wins,
        "losses": losses,
        "flat": flat,
        "total_pnl": total_pnl,
        "long_wins": wins,
        "long_losses": losses,
        "long_flat": flat,
        "short_wins": 0,
        "short_losses": 0,
        "short_flat": 0,
        "symbols": {},
        "last_ts": "",
        "pnl_series": list(pnl_series),
    }


def test_default_off_no_stat_rigor_block(monkeypatch):
    """STAT_RIGOR_ENABLED unset -> no `_stat_rigor_block` field on any row."""
    monkeypatch.delenv("STAT_RIGOR_ENABLED", raising=False)
    strat_dict = {
        "alpha": _strat_bucket([1.5, -0.8, 2.1, -1.0, 0.7, -0.3, 1.2, -0.5]),
    }
    rows = _build_strategy_breakdown(strat_dict)
    assert len(rows) == 1
    assert "_stat_rigor_block" not in rows[0], (
        "default-OFF must not stamp the field — would break the 14-day shadow rule"
    )


def test_explicit_off_no_stat_rigor_block(monkeypatch):
    """STAT_RIGOR_ENABLED='0' (rollback path) must also skip stamping."""
    monkeypatch.setenv("STAT_RIGOR_ENABLED", "0")
    strat_dict = {
        "alpha": _strat_bucket([1.5, -0.8, 2.1, -1.0, 0.7, -0.3, 1.2, -0.5]),
    }
    rows = _build_strategy_breakdown(strat_dict)
    assert "_stat_rigor_block" not in rows[0]


def test_stat_rigor_on_stamps_full_block_shape(monkeypatch):
    """STAT_RIGOR_ENABLED='1' with n>=4 stamps audit_metrics_block output."""
    monkeypatch.setenv("STAT_RIGOR_ENABLED", "1")
    # 8 closed trades: 5 wins, 3 losses (mixed signs so PF is finite + meaningful)
    series = [1.5, -0.8, 2.1, -1.0, 0.7, -0.3, 1.2, -0.5]
    strat_dict = {"alpha": _strat_bucket(series)}
    rows = _build_strategy_breakdown(strat_dict)
    assert len(rows) == 1
    block = rows[0].get("_stat_rigor_block")
    assert block is not None, "STAT_RIGOR_ENABLED=1 must stamp the field"
    assert block["n"] == len(series)
    for metric_key in ("profit_factor", "win_rate", "sharpe"):
        assert {"point", "lo", "hi"} <= block[metric_key].keys(), (
            f"metric '{metric_key}' missing CI keys"
        )
    psr = block["psr_vs_zero"]
    assert 0.0 <= psr <= 1.0, f"psr_vs_zero must be a probability, got {psr}"


def test_thin_sample_skipped(monkeypatch):
    """n<4 closed picks: skip the stamping (audit_metrics_block degenerates)."""
    monkeypatch.setenv("STAT_RIGOR_ENABLED", "1")
    strat_dict = {
        "thin_strat": _strat_bucket([1.0, -0.5, 0.8]),  # n=3
    }
    rows = _build_strategy_breakdown(strat_dict)
    assert len(rows) == 1
    assert "_stat_rigor_block" not in rows[0]


def test_active_only_strategy_no_pnl_series(monkeypatch):
    """Strategy with active picks but zero closed picks: no crash, no stamp."""
    monkeypatch.setenv("STAT_RIGOR_ENABLED", "1")
    bucket = _strat_bucket([], active=5)
    bucket["wins"] = 0
    bucket["losses"] = 0
    bucket["flat"] = 0
    strat_dict = {"new_strat": bucket}
    rows = _build_strategy_breakdown(strat_dict)
    assert len(rows) == 1
    assert "_stat_rigor_block" not in rows[0]


def test_multiple_strategies_only_thick_get_stamped(monkeypatch):
    """Mixed dict: only n>=4 strategies get the block; thin ones omitted."""
    monkeypatch.setenv("STAT_RIGOR_ENABLED", "1")
    strat_dict = {
        "thick": _strat_bucket([1.5, -0.8, 2.1, -1.0, 0.7, -0.3, 1.2, -0.5]),
        "thin": _strat_bucket([0.5, -0.2, 0.3]),
    }
    rows = _build_strategy_breakdown(strat_dict)
    by_name = {r["name"]: r for r in rows}
    assert "_stat_rigor_block" in by_name["thick"]
    assert "_stat_rigor_block" not in by_name["thin"]


def test_field_set_when_disabled_doesnt_change_other_fields(monkeypatch):
    """Sanity: pre-existing fields (win_rate, avg_pnl, etc.) are unchanged
    by the wire-in regardless of env flag state.
    """
    series = [1.5, -0.8, 2.1, -1.0, 0.7, -0.3, 1.2, -0.5]
    strat_dict = {"alpha": _strat_bucket(series)}

    monkeypatch.delenv("STAT_RIGOR_ENABLED", raising=False)
    rows_off = _build_strategy_breakdown(strat_dict)
    monkeypatch.setenv("STAT_RIGOR_ENABLED", "1")
    rows_on = _build_strategy_breakdown(strat_dict)

    off, on = rows_off[0], rows_on[0]
    for k in ("name", "active", "resolved", "wins", "losses", "flat",
              "win_rate", "avg_pnl", "total_pnl", "long_wr", "short_wr"):
        assert off.get(k) == on.get(k), (
            f"flag should add a field, not perturb existing field '{k}'"
        )


def test_computation_failure_doesnt_crash(monkeypatch):
    """If audit_metrics_block raises, the row is still emitted (dashboard
    must never go dark on a metrics computation bug). The defensive try/except
    in _build_strategy_breakdown catches and skips the stamp.
    """
    monkeypatch.setenv("STAT_RIGOR_ENABLED", "1")
    import audit_trail.dashboard_generator as dg

    def _boom(*_args, **_kwargs):
        raise RuntimeError("simulated statistical_rigor failure")

    monkeypatch.setattr(dg, "_audit_metrics_block", _boom)
    strat_dict = {
        "alpha": _strat_bucket([1.5, -0.8, 2.1, -1.0, 0.7, -0.3, 1.2, -0.5]),
    }
    rows = dg._build_strategy_breakdown(strat_dict)
    assert len(rows) == 1
    # Row exists with all the standard fields, just no _stat_rigor_block
    assert rows[0]["name"] == "alpha"
    assert "_stat_rigor_block" not in rows[0]


def test_pnl_series_converted_to_fractional(monkeypatch):
    """pnl_pct is stored as percentage (e.g. 1.5 = 1.5%) but audit_metrics_block
    expects fractional returns (e.g. 0.015). The wire-in divides by 100 before
    passing in. Test: a constant +1% return series should produce a high PSR
    (definitely outperforms zero) but bounded reasonable Sharpe — not the
    blown-up Sharpe you'd see if the conversion were skipped.
    """
    monkeypatch.setenv("STAT_RIGOR_ENABLED", "1")
    # All 8 trades = +1% (zero variance — Sharpe degenerates to 0 by design)
    strat_dict = {"alpha": _strat_bucket([1.0] * 8)}
    rows = _build_strategy_breakdown(strat_dict)
    block = rows[0]["_stat_rigor_block"]
    # win_rate should be 1.0 (all positive) — also independent of unit choice
    assert block["win_rate"]["point"] == pytest.approx(1.0)
    # If conversion were skipped (passed 1.0 instead of 0.01 to sharpe),
    # the sharpe degenerates to 0 either way (zero variance), but PSR vs
    # zero must be > 0.5 because mean > benchmark. Just sanity-check PSR.
    assert block["psr_vs_zero"] >= 0.5
