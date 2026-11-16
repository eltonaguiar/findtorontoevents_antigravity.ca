"""Tests for tools/build_theory_tracker_sidecar.py (theory/hypothesis tracker sidecar).

Covers the two mandated invariants: empty/missing inputs still emit
empty-but-valid strict JSON, and NaN/Infinity in inputs can never leak into
the sidecar (allow_nan=False hard-rejects). Also checks basic row mapping and
newest-run-per-stem collapse. Run:
    python3 -m pytest tests/test_theory_tracker_sidecar.py -q
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

from tools.build_theory_tracker_sidecar import (
    build_sidecar,
    main,
    write_sidecar,
)


def _strict_load(path: Path) -> dict:
    """Load JSON rejecting NaN/Infinity (json.loads accepts them by default)."""
    def _reject(token):
        raise AssertionError(f"non-strict JSON constant leaked: {token}")
    return json.loads(path.read_text(encoding="utf-8"), parse_constant=_reject)


# ─────────────────────────────────────────────────────── empty-input cases ──
def test_missing_inputs_emit_empty_but_valid_json(tmp_path: Path):
    payload = build_sidecar(
        tmp_path / "nope" / "theory_portfolios.json",
        tmp_path / "nope_reports",
    )
    assert payload["theories"] == []
    assert payload["generated_at"]

    out = tmp_path / "theory_tracker.json"
    write_sidecar(payload, out)
    loaded = _strict_load(out)
    assert loaded["theories"] == []
    assert loaded["generated_at"] == payload["generated_at"]


def test_empty_portfolios_and_no_reports_emit_empty_rows(tmp_path: Path):
    pf = tmp_path / "theory_portfolios.json"
    pf.write_text(json.dumps({"created_at": "2026-01-01", "portfolios": {}, "last_updated": ""}), encoding="utf-8")
    reports = tmp_path / "reports"
    reports.mkdir()
    payload = build_sidecar(pf, reports)
    assert payload["theories"] == []


def test_cli_writes_sidecar_on_missing_inputs(tmp_path: Path, capsys):
    out = tmp_path / "out.json"
    rc = main([
        "--portfolios", str(tmp_path / "missing.json"),
        "--reports-dir", str(tmp_path / "missing_reports"),
        "--out", str(out),
    ])
    assert rc == 0
    assert _strict_load(out)["theories"] == []
    assert "0 theory rows" in capsys.readouterr().out


# ───────────────────────────────────────────────────────── NaN rejection ────
def test_nan_and_inf_in_inputs_never_reach_sidecar(tmp_path: Path):
    pf = tmp_path / "theory_portfolios.json"
    pf.write_text(json.dumps({
        "last_updated": "2026-11-16T00:00:00+00:00",
        "portfolios": {
            "B_news_sentiment": {
                "active_positions": [],
                "closed_positions": [],
                "stats": {"total_trades": float("nan")},
            },
        },
    }), encoding="utf-8")
    reports = tmp_path / "reports"
    reports.mkdir()
    (reports / "h004_inventory_roll_yield_20260519.json").write_text(
        '{"hypothesis_id": "H-004", "verdict": "HARNESS_REJECTED",'
        ' "n_trades": NaN, "run_date": Infinity}',
        encoding="utf-8",
    )

    payload = build_sidecar(pf, reports)
    out = tmp_path / "theory_tracker.json"
    write_sidecar(payload, out)  # allow_nan=False — must not raise, must not emit NaN
    text = out.read_text(encoding="utf-8")
    assert "NaN" not in text and "Infinity" not in text
    loaded = _strict_load(out)
    flat = json.dumps(loaded)
    assert not any(
        isinstance(v, float) and not math.isfinite(v)
        for row in loaded["theories"] for v in row.values()
    )
    assert "HARNESS_REJECTED" in flat


def test_write_sidecar_rejects_nan_payload(tmp_path: Path):
    with pytest.raises(ValueError):
        write_sidecar(
            {"generated_at": "x", "theories": [{"n": float("nan")}]},
            tmp_path / "bad.json",
        )


# ─────────────────────────────────────────────────────── row mapping ────────
def test_portfolio_and_report_rows_mapped_newest_wins(tmp_path: Path):
    pf = tmp_path / "theory_portfolios.json"
    pf.write_text(json.dumps({
        "last_updated": "2026-11-16T02:00:00+00:00",
        "portfolios": {
            "C_technical_confluence": {
                "active_positions": [{"symbol": "BTCUSDT"}],
                "closed_positions": [{"a": 1}, {"b": 2}],
                "stats": {"total_trades": 7},
            },
        },
    }), encoding="utf-8")
    reports = tmp_path / "reports"
    reports.mkdir()
    (reports / "h004_inventory_roll_yield_20260519.json").write_text(
        '{"hypothesis_id": "H-004", "verdict": "OLD", "n_trades": 3722, "run_date": "2026-05-19"}',
        encoding="utf-8",
    )
    (reports / "h004_inventory_roll_yield_20260601.json").write_text(
        '{"hypothesis_id": "H-004", "verdict": "NEW", "n_trades": 4000, "run_date": "2026-06-01"}',
        encoding="utf-8",
    )

    payload = build_sidecar(pf, reports)
    by_name = {r["name"]: r for r in payload["theories"]}
    assert set(by_name) == {"C_technical_confluence", "h004_inventory_roll_yield"}

    port = by_name["C_technical_confluence"]
    assert port["status"] == "active"
    assert port["n"] == 7
    assert port["last_updated"] == "2026-11-16T02:00:00+00:00"

    rep = by_name["h004_inventory_roll_yield"]
    assert rep["hypothesis"] == "H-004"
    assert rep["verdict"] == "NEW"          # newest run per stem wins
    assert rep["n"] == 4000
    assert rep["last_updated"] == "2026-06-01"
