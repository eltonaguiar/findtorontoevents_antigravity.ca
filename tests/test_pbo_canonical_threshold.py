"""Locks the canonical PBO threshold and the "0.0 is not 'not computed'" rule.

Found 2026-11-20 while claiming workstream A5 ("canonicalise PBO to CSCV,
threshold 0.5, 0.0 must render as 'not computed'").

Two defects are locked here:

1. ``tools/anti_overfit_gate.py`` hard-coded ``PBO_MAX = 0.05``. That is 10x
   stricter than the Bailey & Lopez de Prado definition (PBO >= 0.5 means
   selection is indistinguishable from random) and disagreed with the five
   other PBO consumers in this repo (eagle_gates 0.5, admissibility_pipeline
   0.5, run_anti_overfit_audit 0.5, build_cpcv_pbo_results 0.5,
   anti_overfit_audit_sidecar 0.5). A gate nobody can pass gets deleted or
   gets ``continue-on-error`` re-added -- the failure mode the gate exists to
   prevent. The threshold is now imported from ``tools.pbo_cscv``.

2. A genuine PBO of ``0.0`` means "no overfitting detected" and is a REAL
   measurement. ``None``/``nan`` means "could not be estimated". Python makes
   ``0.0`` falsy, so ``if not pbo`` / ``pbo or fallback`` silently reports a
   perfect selection as unmeasured. These tests pin the distinction.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.anti_overfit_gate import PBO_MAX, check_result  # noqa: E402
from tools.pbo_cscv import (  # noqa: E402
    PBO_CANONICAL_THRESHOLD,
    PBO_NOT_COMPUTED,
)


# ---------------------------------------------------------------------------
# 1. The threshold is canonical, and it is canonical in ONE place.
# ---------------------------------------------------------------------------

def test_canonical_threshold_is_one_half():
    """PBO >= 0.5 is the literature decision point; it is not a tunable."""
    assert PBO_CANONICAL_THRESHOLD == 0.50


def test_gate_uses_the_canonical_threshold_not_a_local_number():
    assert PBO_MAX == PBO_CANONICAL_THRESHOLD


def test_gate_threshold_is_not_the_old_unpassable_value():
    """Regression: 0.05 was 10x stricter than the definition."""
    assert PBO_MAX != 0.05, (
        "anti_overfit_gate.PBO_MAX is back to 0.05. That value is 10x "
        "stricter than Bailey & Lopez de Prado and disagrees with the five "
        "other PBO consumers in this repo. Import "
        "tools.pbo_cscv.PBO_CANONICAL_THRESHOLD instead of hard-coding."
    )


def test_every_pbo_consumer_agrees_on_half():
    """No NEW non-canonical PBO thresholds. Ratchet, not a hard sweep.

    Three decision points exist in the repo today. Two are pre-existing debt in
    modules whose thresholds are load-bearing for pick emission, so they are
    deliberately NOT retuned here without an owner decision:

      build_cpcv_pbo_results.py  pbo < 0.3   -- third, undocumented value
      fundamental_macro_gates.py pbo < 0.05  -- over-strict, blocks emission

    Changing either alters which strategies emit picks. That is a behavioural
    change requiring its own review, not a drive-by edit from a validation
    branch. This test pins the current set so the count cannot silently grow
    while the debt is visible.
    """
    import re

    KNOWN_NON_CANONICAL = {
        ("build_cpcv_pbo_results.py", "0.3"),
        ("fundamental_macro_gates.py", "0.05"),
    }

    found: set[tuple[str, str]] = set()
    for path in list((REPO_ROOT / "tools").glob("*.py")) + list(
        (REPO_ROOT / "alpha_engine").glob("*.py")
    ):
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        # Any literal threshold compared directly against a pbo variable.
        for match in re.finditer(r"pbo\w*\s*(?:<|<=|>=|>)\s*0\.(\d+)", text):
            value = f"0.{match.group(1)}"
            if value in {"0.5", "0.50", "0.7", "0.70"}:
                continue  # canonical, or the documented lenient tier
            found.add((path.name, value))

    new_offenders = sorted(found - KNOWN_NON_CANONICAL)
    assert not new_offenders, (
        "New non-canonical PBO threshold(s) introduced. Import "
        "tools.pbo_cscv.PBO_CANONICAL_THRESHOLD (0.5) instead of hard-coding "
        f"a number: {new_offenders}"
    )


# ---------------------------------------------------------------------------
# 2. 0.0 is a measurement; None/nan is not.
# ---------------------------------------------------------------------------

def _result(pbo, dsr=0.99):
    """A gate result that clears MIN_PICKS, isolating the PBO decision."""
    return {"deflated_sharpe": dsr, "pbo": pbo, "n_picks": 500}


def test_pbo_zero_is_a_pass_not_a_missing_value():
    """A genuine PBO of 0.0 means no overfitting detected -> passes."""
    failures = check_result(_result(0.0))
    pbo_failures = [f for f in failures if "PBO" in f]
    assert pbo_failures == [], (
        "PBO 0.0 was treated as missing/failing. 0.0 is a real measurement "
        f"and must pass. Got: {pbo_failures}"
    )


def test_pbo_zero_is_not_confused_with_not_computed():
    """0.0 must never be reported as NOT_COMPUTED."""
    assert not math.isnan(0.0)
    assert PBO_NOT_COMPUTED != 0.0
    zero_failures = [f for f in check_result(_result(0.0)) if "PBO" in f]
    none_failures = [f for f in check_result(_result(None)) if "PBO" in f]
    assert zero_failures != none_failures, (
        "PBO 0.0 and PBO None produce identical gate output -- they are not "
        "the same fact and must not be reported the same way."
    )


def test_pbo_none_fails_closed_as_not_evaluable():
    failures = check_result(_result(None))
    assert any("NOT EVALUABLE" in f for f in failures), failures


def test_pbo_nan_fails_closed_as_not_evaluable():
    failures = check_result(_result(float("nan")))
    assert any("NOT EVALUABLE" in f for f in failures), failures


def test_pbo_at_threshold_fails():
    """PBO == 0.5 is the decision point; it is a FAIL, not a pass."""
    failures = check_result(_result(0.50))
    assert any("overfit" in f.lower() or ">=" in f for f in failures), failures


def test_pbo_just_below_threshold_passes():
    assert not [f for f in check_result(_result(0.49)) if "PBO" in f]


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
