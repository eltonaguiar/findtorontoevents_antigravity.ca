"""
Logic-level test for the ML-2 fix in alpha_engine/ml_ranker.py:score_signal.

The fix wires the previously-fitted self.calibrator into score_signal's
post-ensemble step. We can't easily fixture a full MLRanker (requires a
trained model file, sklearn pipeline state, training data on disk), so
this test asserts the BRANCH LOGIC the production code now executes:

    if self.calibrator is not None:
        try:
            _cal = float(self.calibrator.predict([win_prob])[0])
            if not (win_prob > 0.5 and _cal <= 0.0):
                win_prob = _cal
        except Exception:
            pass  # keep raw

Three behaviors must hold:

  1. Calibrated probability replaces raw when both are positive.
  2. Calibrated probability does NOT replace raw if it would collapse a
     positive prediction (raw > 0.5, _cal <= 0).
  3. Any error from the calibrator is swallowed; raw value is preserved.
"""
from __future__ import annotations

import os
import sys

import pytest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)


def _apply(calibrator, win_prob: float) -> float:
    """Mirror of the inline branch in ml_ranker.py:score_signal."""
    if calibrator is not None:
        try:
            _cal = float(calibrator.predict([win_prob])[0])
            if not (win_prob > 0.5 and _cal <= 0.0):
                win_prob = _cal
        except Exception:
            pass
    return win_prob


class _StubCalibrator:
    """Mimic IsotonicRegression's predict() for fixed mappings."""

    def __init__(self, mapping):
        self.mapping = mapping

    def predict(self, xs):
        return [self.mapping(x) for x in xs]


def test_calibrator_replaces_raw_when_safe():
    """Calibrator outputs a positive number; raw must be replaced."""
    cal = _StubCalibrator(lambda x: x * 0.8)  # 0.7 -> 0.56
    out = _apply(cal, 0.7)
    assert out == pytest.approx(0.56)


def test_calibrator_does_not_collapse_positive_prediction():
    """Raw > 0.5 but calibrator returns 0.0 -> must keep raw."""
    cal = _StubCalibrator(lambda x: 0.0)
    out = _apply(cal, 0.6)
    assert out == pytest.approx(0.6), "Calibrator collapse must not silently zero a positive raw"


def test_calibrator_negative_collapse_blocked():
    """Calibrator returns a negative on a positive raw -> must keep raw."""
    cal = _StubCalibrator(lambda x: -0.05)
    out = _apply(cal, 0.65)
    assert out == pytest.approx(0.65)


def test_calibrator_can_lower_low_raw():
    """Raw <= 0.5: even a 0.0 calibrated value is allowed (low confidence is fine)."""
    cal = _StubCalibrator(lambda x: 0.0)
    out = _apply(cal, 0.4)
    assert out == pytest.approx(0.0)


def test_calibrator_exception_keeps_raw():
    """If predict() raises, raw must survive (do-no-harm fallback)."""
    class _Boom:
        def predict(self, xs):
            raise RuntimeError("fitted on different feature shape")

    out = _apply(_Boom(), 0.55)
    assert out == pytest.approx(0.55)


def test_no_calibrator_passthrough():
    """When self.calibrator is None, raw is returned unchanged."""
    assert _apply(None, 0.5) == pytest.approx(0.5)
    assert _apply(None, 0.123) == pytest.approx(0.123)


def test_with_real_isotonic_regression():
    """End-to-end with the actual sklearn IsotonicRegression that
    score_signal would use at train time."""
    pytest.importorskip("sklearn")
    from sklearn.isotonic import IsotonicRegression

    cal = IsotonicRegression(out_of_bounds="clip")
    # Trivial monotone fit: raw 0.1->0.2, 0.5->0.6, 0.9->0.95
    cal.fit([0.1, 0.5, 0.9], [0.2, 0.6, 0.95])

    # Mid-range: calibrated value lifts raw 0.5 toward 0.6
    out = _apply(cal, 0.5)
    assert 0.55 <= out <= 0.65


def test_meta_label_gate_decision_is_on_calibrated_value():
    """Meta-label gate at META_LABEL_PROBABILITY_GATE decides take/skip
    based on the value we return. With calibration applied, a raw 0.62
    that calibrates down to 0.45 should now be considered low-confidence
    instead of slipping past a 0.55 gate. This documents the *purpose*
    of ML-2."""
    META_GATE = 0.55
    cal = _StubCalibrator(lambda x: x * 0.7)  # 0.62 -> 0.434
    raw = 0.62
    pre_fix_decision = raw >= META_GATE              # would have passed
    post_fix_value = _apply(cal, raw)
    post_fix_decision = post_fix_value >= META_GATE  # now correctly suppressed
    assert pre_fix_decision is True
    assert post_fix_decision is False
