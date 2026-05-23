"""Regression test for the elite-scorer confidence tier-string coercion fix
(2026-05-22). Upstream pick generators emit `confidence` as a string tier
('HIGH'/'MEDIUM'/'LOW'); the old `float(...)` call raised ValueError and the
catch-all assigned a silent fallback elite_score=25. `coerce_confidence` now
maps tier strings to numeric midpoints.
"""
import importlib.util
from pathlib import Path

import pytest

_SPEC = importlib.util.spec_from_file_location(
    "elite_scorer_under_test",
    Path(__file__).resolve().parents[1] / "alpha_engine" / "elite_scorer.py",
)


def _load():
    mod = importlib.util.module_from_spec(_SPEC)
    try:
        _SPEC.loader.exec_module(mod)
    except Exception as exc:  # pragma: no cover - env-dependent heavy import
        pytest.skip(f"elite_scorer import failed: {type(exc).__name__}")
    return mod


def test_numeric_confidence_passthrough():
    cc = _load().coerce_confidence
    assert cc(0.72) == pytest.approx(0.72)
    assert cc(1) == pytest.approx(1.0)
    assert cc("0.65") == pytest.approx(0.65)


def test_tier_strings_map_to_numbers():
    cc = _load().coerce_confidence
    # The exact bug: 'LOW' / 'MEDIUM' previously raised ValueError -> score 25.
    assert cc("LOW") == pytest.approx(0.50)
    assert cc("MEDIUM") == pytest.approx(0.68)
    assert cc("HIGH") == pytest.approx(0.80)
    # case-insensitive
    assert cc("low") == pytest.approx(0.50)
    assert cc(" High ") == pytest.approx(0.80)


def test_unparseable_returns_default_not_crash():
    cc = _load().coerce_confidence
    assert cc("not-a-tier", default=0.0) == 0.0
    assert cc(None, default=0.0) == 0.0
    assert cc("", default=0.5) == 0.5
