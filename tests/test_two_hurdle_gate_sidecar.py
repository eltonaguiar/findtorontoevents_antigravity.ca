#!/usr/bin/env python3
"""Tests for the opt-in two-hurdle sidecar (backlog D5).

The critical property beyond correctness: this module must NOT be imported by any
production path. A sidecar that silently becomes load-bearing is not a sidecar.
"""
from __future__ import annotations

import importlib.util
import random
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location(
    "thg", ROOT / "alpha_engine" / "two_hurdle_gate.py")
thg = importlib.util.module_from_spec(_spec)
sys.modules["thg"] = thg
_spec.loader.exec_module(thg)


def _s(n=300, mu=0.0, sd=0.01, seed=7):
    rng = random.Random(seed)
    return [rng.gauss(mu, sd) for _ in range(n)]


# ------------------------------------------------------------ opt-in property
def test_no_production_module_imports_the_sidecar():
    """The Wire-Up Rule's opt-in clause, enforced mechanically.

    If a production path ever imports this without a Wiring Plan update, the
    verdict of every existing pick changes silently. This test fails loudly first.
    """
    offenders = []
    for sub in ("audit_trail", "alpha_engine"):
        for p in (ROOT / sub).rglob("*.py"):
            if p.name == "two_hurdle_gate.py":
                continue
            txt = p.read_text(errors="ignore")
            if "two_hurdle_gate" in txt:
                offenders.append(str(p.relative_to(ROOT)))
    assert offenders == [], (
        f"sidecar imported by production paths {offenders} -- update the Wiring "
        "Plan in alpha_engine/two_hurdle_gate.py before wiring it in")


def test_hurdle_constant_is_432bp():
    assert thg.HURDLE_TBILL_APR == 0.0432


# ------------------------------------------------------------- gate behaviour
def test_pure_beta_fails_signal_hurdle():
    b = _s(mu=0.0010, sd=0.008, seed=11)
    r = thg.two_hurdle_gate(b, b, n_boot=2000)
    assert r["hurdle1_cash_pass"] is True
    assert r["hurdle2_signal_pass"] is False
    assert r["verdict"] == "BETA_ONLY_FAIL_HURDLE_2"


def test_leveraged_beta_fails_signal_hurdle():
    b = _s(mu=0.0010, sd=0.008, seed=12)
    r = thg.two_hurdle_gate([1.75 * x for x in b], b, n_boot=2000)
    assert r["hurdle2_signal_pass"] is False


def test_genuine_alpha_passes():
    b = _s(mu=0.0005, sd=0.010, seed=21)
    rng = random.Random(99)
    s = [x + 0.0012 + rng.gauss(0, 0.002) for x in b]
    r = thg.two_hurdle_gate(s, b, n_boot=2000)
    assert r["verdict"] == "PASS"


# ---------------------------------------------------------------- pick gating
def test_missing_series_is_unvettable_not_a_pass():
    r = thg.gate_pick({"symbol": "XLE"})
    assert r["verdict"] == "UNVETTABLE"
    assert r["hurdle1_cash_pass"] is None


def test_unpaired_lengths_are_unvettable():
    r = thg.gate_pick({"return_series": _s(100), "benchmark_series": _s(99)})
    assert r["verdict"] == "UNVETTABLE"
    assert "unpaired" in r["reason"]


def test_gate_pick_does_not_mutate_input():
    b = _s(200, seed=3)
    pick = {"return_series": list(b), "benchmark_series": list(b)}
    before = (list(pick["return_series"]), list(pick["benchmark_series"]))
    thg.gate_pick(pick)
    assert (pick["return_series"], pick["benchmark_series"]) == before


# ------------------------------------------------------ delegation correctness
def test_delegates_to_the_single_pbs_implementation():
    """No re-derivation: the sidecar must agree with tools/ exactly."""
    b = _s(200, seed=41)
    s = [x + 0.0008 for x in b]
    assert thg.two_hurdle_gate(s, b, n_boot=500) == thg.pbs.two_hurdle_gate(
        s, b, hurdle_apr=thg.HURDLE_TBILL_APR, periods_per_year=thg.TRADING_DAYS,
        n_boot=500, block=5, seed=20261123)
