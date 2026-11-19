#!/usr/bin/env python3
"""Shared confidence recalibration utility.

Addresses the systematic confidence inversion discovered in the audit:
  CRYPTO: conf>=0.9 -> 14.4% WR, conf 0.5-0.6 -> 60.3% WR
  EQUITY: 0.85-0.90 -> 20% WR (WORST), >0.90 -> 67% WR
  FOREX: peak 0.75-0.80 (49% WR), 0.70-0.75 = DANGER (25% WR)
  COMMODITY: peak 0.70-0.75 (48% WR)

This module provides a single function that any pick generator can call to
recalibrate confidence BEFORE emitting. It mirrors the logic in
score_booster._calibrate_confidence but returns a calibrated confidence
value (not a score adjustment).

Usage:
    from alpha_engine.confidence_recalibrator import recalibrate_confidence
    calibrated = recalibrate_confidence(raw_conf, asset_class)
"""
from __future__ import annotations

from typing import Any


def recalibrate_confidence(conf: float, asset_class: str) -> float:
    """Recalibrate raw confidence to a calibrated value.

    Returns a calibrated confidence in [0, 1] that reflects actual win rates.
    If conf is invalid (<=0 or >1), returns it unchanged.
    """
    if conf <= 0 or conf > 1.0:
        return conf

    ac = str(asset_class or "").upper().strip()

    if ac == "CRYPTO":
        # Inverted: high conf = low WR. Map to calibrated values.
        if conf > 0.85:
            return 0.55  # was 14.4% WR
        elif conf > 0.80:
            return 0.60
        elif conf >= 0.60:
            return conf  # moderate conf is honest
        elif conf >= 0.50:
            return 0.65  # was 60.3% WR
        else:
            return 0.60

    elif ac == "EQUITY":
        # Bipolar: 0.85-0.90 is worst, >0.90 recovers
        if 0.85 <= conf <= 0.90:
            return 0.50  # was 20% WR
        elif conf > 0.90:
            return 0.75  # recovers
        elif conf >= 0.70:
            return conf
        elif conf >= 0.55:
            return 0.65
        else:
            return 0.60

    elif ac == "FOREX":
        # Low ceiling; trust moderate confidence only
        if conf >= 0.85:
            return 0.60
        elif conf >= 0.80:
            return 0.70
        elif conf >= 0.75:
            return 0.75  # peak
        elif conf >= 0.70:
            return 0.55  # danger zone
        else:
            return 0.60

    elif ac == "COMMODITY":
        # Peak 0.70-0.75
        if conf >= 0.80:
            return 0.65
        elif conf >= 0.75:
            return 0.72
        elif conf >= 0.70:
            return 0.75  # peak
        elif conf >= 0.60:
            return 0.65
        else:
            return 0.60

    # Default: no recalibration
    return conf


def recalibrate_pick(pick: dict) -> dict:
    """Recalibrate confidence in a pick dict in-place. Returns the pick."""
    conf = pick.get("confidence")
    ac = pick.get("asset_class") or pick.get("assetClass") or pick.get("class")
    if conf is not None and ac:
        try:
            pick["confidence"] = round(recalibrate_confidence(float(conf), str(ac)), 3)
            pick["confidence_raw"] = conf  # preserve original
            pick["confidence_recalibrated"] = True
        except (TypeError, ValueError):
            pass
    return pick


if __name__ == "__main__":
    # Self-test
    test_cases = [
        (0.95, "CRYPTO", 0.55),
        (0.55, "CRYPTO", 0.65),
        (0.87, "EQUITY", 0.50),
        (0.92, "EQUITY", 0.75),
        (0.75, "FOREX", 0.75),
        (0.72, "FOREX", 0.55),
        (0.72, "COMMODITY", 0.75),
    ]
    for conf, ac, expected in test_cases:
        result = recalibrate_confidence(conf, ac)
        status = "OK" if abs(result - expected) < 0.01 else "FAIL"
        print(f"  {status}: recalibrate({conf}, {ac}) = {result} (expected {expected})")