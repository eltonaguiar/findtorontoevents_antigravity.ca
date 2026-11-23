#!/usr/bin/env python3
"""Two-hurdle gate — OPT-IN SIDECAR. Does not change production behaviour.

Backlog item D5 (docs/BACKLOG_100_2026-11-23.md).

WHY THIS IS OPT-IN AND NOT WIRED IN
Making the two-hurdle rule the production gate would change the verdict on every
existing pick. That is a decision, not an implementation detail, so this module
ships as a sidecar with an explicit wiring plan rather than a silent behaviour
change. Nothing in `audit_trail/` or `alpha_engine/` imports it yet.

THE RULE
  Hurdle 1 (cash):   annualised net return on committed capital > 4.32% T-bill
  Hurdle 2 (signal): beta-adjusted Jensen-alpha bootstrap CI excludes zero

Hurdle 2 is beta-ADJUSTED on purpose. A raw paired difference (strategy - benchmark)
is non-zero for any change in beta, so a 1.5x index fund passes it while adding no
information. Measured and recorded in commit cd44a8cab33.

## Wiring Plan
Target caller:        `audit_trail/quality_gates.py` -> `passes_active_gate(pick)`
                      as an ADDITIONAL check, not a replacement for the existing
                      blocked-pair rules.
Function to call:     `two_hurdle_gate(strategy_returns, benchmark_returns)`
Prerequisite:         a per-pick return series and a matched benchmark series must
                      exist at gate time. They do not today; picks carry a point
                      PnL, not a series. That gap, not this module, is the blocker.
Expected wire-up:     next audit-quality PR after pick records gain a
                      `return_series` + `benchmark_series` field.
Until then:           callable from tools/ and tests only. Not imported by any
                      production path.
"""
from __future__ import annotations

import importlib.util
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HURDLE_TBILL_APR = 0.0432  # tools/capacity_model.py:49 — 432bp/yr, not the rounded 4.3%
TRADING_DAYS = 252


def _load_pbs():
    """Reuse tools/paired_bootstrap_vs_benchmark.py rather than re-deriving it.

    Deliberate: two copies of a statistical routine drift, and this estate has
    already been burned by seven divergent copies of one registry.
    """
    spec = importlib.util.spec_from_file_location(
        "pbs", ROOT / "tools" / "paired_bootstrap_vs_benchmark.py")
    m = importlib.util.module_from_spec(spec)
    sys.modules["pbs"] = m
    spec.loader.exec_module(m)
    return m


pbs = _load_pbs()


def two_hurdle_gate(
    strategy_returns: list[float],
    benchmark_returns: list[float],
    hurdle_apr: float = HURDLE_TBILL_APR,
    n_boot: int = 10000,
    block: int = 5,
    seed: int = 20261123,
) -> dict:
    """Both hurdles must pass. Thin, opinionated wrapper around the pbs module."""
    return pbs.two_hurdle_gate(
        strategy_returns, benchmark_returns, hurdle_apr=hurdle_apr,
        periods_per_year=TRADING_DAYS, n_boot=n_boot, block=block, seed=seed)


def gate_pick(pick: dict) -> dict:
    """Gate one pick record. Returns a verdict; never mutates the input.

    Required pick fields: `return_series`, `benchmark_series` (paired, equal length).
    A pick missing either is `UNVETTABLE` — not a pass, not a fail. Per
    JUSTIFICATION_RULES D, an unvettable pick is not ranked at all.
    """
    s = pick.get("return_series")
    b = pick.get("benchmark_series")
    if not s or not b:
        return {"verdict": "UNVETTABLE",
                "reason": "missing return_series or benchmark_series",
                "hurdle1_cash_pass": None, "hurdle2_signal_pass": None}
    if len(s) != len(b):
        return {"verdict": "UNVETTABLE",
                "reason": f"unpaired: {len(s)} strategy vs {len(b)} benchmark obs",
                "hurdle1_cash_pass": None, "hurdle2_signal_pass": None}
    return two_hurdle_gate(s, b)


def main() -> int:
    import json
    if len(sys.argv) < 2:
        print("usage: two_hurdle_gate.py <pick.json with return_series+benchmark_series>")
        return 2
    pick = json.loads(Path(sys.argv[1]).read_text())
    r = gate_pick(pick)
    print(json.dumps(r, indent=2))
    return 0 if r["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
