"""Wire-up tests for the MEASUREMENT_HYGIENE_V1 rollout flag.

Sub-project 1 / Task 1 (Measurement Fix plan). The flag defaults to OFF and
must guarantee byte-identical output when OFF. Opt-in only via exact "1".
Per CLAUDE.md: default-OFF, opt-in via MEASUREMENT_HYGIENE_V1=1.

When ON it enables (net-of-cost, overlap-aware compounding, benchmark columns,
and the 4 quick-fix gates) — those are covered by later tasks in the plan;
task 1 only establishes the flag constant with the correct default.
"""
from __future__ import annotations

import importlib
import os

import pytest


@pytest.fixture(autouse=True)
def _restore_env(monkeypatch):
    """Always restore MEASUREMENT_HYGIENE_V1 to its un-set state between tests."""
    monkeypatch.delenv("MEASUREMENT_HYGIENE_V1", raising=False)
    yield


def _reload_dg():
    import audit_trail.dashboard_generator as dg
    importlib.reload(dg)
    return dg


# ─────────────────────────────────────────────────────────────────
# Default-OFF guarantees: constant exists and is False by default
# ─────────────────────────────────────────────────────────────────

def test_measurement_hygiene_flag_default_off():
    """Without MEASUREMENT_HYGIENE_V1 the flag must exist and be OFF."""
    dg = _reload_dg()
    assert hasattr(dg, "MEASUREMENT_HYGIENE_V1"), \
        "MEASUREMENT_HYGIENE_V1 constant must exist on dashboard_generator"
    assert dg.MEASUREMENT_HYGIENE_V1 is False, \
        "Flag must default to OFF when env var is absent"


def test_measurement_hygiene_flag_explicit_zero_off(monkeypatch):
    """MEASUREMENT_HYGIENE_V1=0 is explicitly OFF, same as unset."""
    monkeypatch.setenv("MEASUREMENT_HYGIENE_V1", "0")
    dg = _reload_dg()
    assert dg.MEASUREMENT_HYGIENE_V1 is False


def test_measurement_hygiene_flag_empty_off(monkeypatch):
    """Empty string env value is treated as OFF."""
    monkeypatch.setenv("MEASUREMENT_HYGIENE_V1", "")
    dg = _reload_dg()
    assert dg.MEASUREMENT_HYGIENE_V1 is False


def test_measurement_hygiene_flag_garbage_off(monkeypatch):
    """Anything other than literal '1' must be treated as OFF (defensive)."""
    monkeypatch.setenv("MEASUREMENT_HYGIENE_V1", "true")
    dg = _reload_dg()
    assert dg.MEASUREMENT_HYGIENE_V1 is False, \
        "Only literal '1' enables the flag; 'true' must be treated as OFF"


def test_measurement_hygiene_flag_opt_in(monkeypatch):
    """The flag turns ON only when the env var is exactly '1'."""
    monkeypatch.setenv("MEASUREMENT_HYGIENE_V1", "1")
    dg = _reload_dg()
    assert dg.MEASUREMENT_HYGIENE_V1 is True
