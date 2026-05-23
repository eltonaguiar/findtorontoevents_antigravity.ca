"""Tests for the regime-conditional mode of tools/edge_stability_harness.py.

`evaluate_by_regime()` stratifies resolved picks by their `regime` label and
runs the per-window stability test inside each cohort — so a regime-dependent
edge is no longer auto-rejected by the global single-sign requirement.

Network-free: monkeypatches the module-level `_load()`.
"""
from __future__ import annotations

import importlib.util
from datetime import date, timedelta
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
_SPEC = importlib.util.spec_from_file_location(
    "edge_stability_harness", REPO / "tools" / "edge_stability_harness.py")
H = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(H)  # type: ignore[union-attr]


def _picks(regime_sep: dict[str, bool], windows: int = 4,
           per_window: int = 110) -> list[dict]:
    """Build a dense regime-tagged ledger.

    regime_sep maps regime -> whether `testscore` cleanly separates winners
    (True) or is pure noise (False) inside that regime.
    """
    base = date(2026, 5, 1)
    rows: list[dict] = []
    for rg, separates in regime_sep.items():
        for w in range(windows):
            d = (base - timedelta(days=w * 14 + 1)).isoformat()
            for i in range(per_window):
                won = i % 2 == 0
                if separates:
                    score = 0.85 if won else 0.15      # stable + separation
                else:
                    score = 0.5 + (0.01 if i % 3 else -0.01)  # noise
                rows.append({
                    "status": "WON" if won else "LOST",
                    "regime": rg,
                    "testscore": score,
                    "resolved_at": d,
                })
    return rows


def test_data_gap_when_no_regime_tags(monkeypatch):
    """Untagged ledger -> DATA_GAP verdict naming the backfill dependency."""
    rows = _picks({"x": True})
    for r in rows:
        r.pop("regime")
    monkeypatch.setattr(H, "_load", lambda: rows)
    out = H.evaluate_by_regime("testscore", 14)
    assert out["verdict"] == "DATA_GAP"
    assert out["regime_admissible"] is False
    assert "Backfill" in out["reason"]


def test_data_gap_with_single_regime(monkeypatch):
    """Only one regime present -> DATA_GAP (need >=2 to be regime-conditional)."""
    monkeypatch.setattr(H, "_load", lambda: _picks({"risk_on": True}))
    out = H.evaluate_by_regime("testscore", 14)
    assert out["verdict"] == "DATA_GAP"


def test_regime_admissible_when_one_cohort_separates(monkeypatch):
    """Edge stable in risk_on, noise in risk_off -> REGIME_ADMISSIBLE."""
    monkeypatch.setattr(
        H, "_load", lambda: _picks({"risk_on": True, "risk_off": False}))
    out = H.evaluate_by_regime("testscore", 14)
    assert out["verdict"] == "REGIME_ADMISSIBLE"
    assert out["regime_admissible"] is True
    assert "risk_on" in out["admissible_regimes"]
    assert "risk_off" not in out["admissible_regimes"]


def test_is_admissible_regime_flag(monkeypatch):
    """is_admissible(regime=True) routes to the regime-conditional verdict."""
    monkeypatch.setattr(
        H, "_load", lambda: _picks({"risk_on": True, "risk_off": False}))
    assert H.is_admissible("testscore", 14, regime=True) is True


def test_is_admissible_default_unchanged(monkeypatch):
    """Default is_admissible() ignores regime — global verdict, no regression."""
    monkeypatch.setattr(
        H, "_load", lambda: _picks({"risk_on": True, "risk_off": False}))
    # default path must still run evaluate() and return a bool
    assert isinstance(H.is_admissible("testscore", 14), bool)
