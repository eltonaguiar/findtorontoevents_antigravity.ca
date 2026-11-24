#!/usr/bin/env python3
"""dsr_conformance.py — measure whether the estate's DSR implementations agree.

Why this exists
---------------
The programme's binding constraint is multiple-testing debt (146 pre-registered
hypotheses, 0 PROVEN, 0/55 surviving deflation). A deflation gate is only worth
something if the number behind it is the number you think it is. This repo has
**25+ functions named `deflated_sharpe*`** in different modules, with at least three
incompatible conventions:

* probability in [0,1] vs a z-score,
* per-period vs annualised Sharpe,
* raw kurtosis (3.0 = normal) vs excess kurtosis (0.0 = normal),
* and some that take no trial count at all and therefore cannot deflate.

Adding a 26th implementation would deepen the problem. This module is a
**conformance harness**: it drives every importable implementation with the same
fixed battery, at several trial counts, and reports which ones actually move when
the trial count rises. Output is a table plus a JSON artifact, so a disagreement
is a number with a file:line attached rather than an opinion.

Nothing here decides which implementation is "right". It measures two things that
are checkable without that decision:

1. **Deflation sensitivity** — does the value change between N=1 and N=121 trials?
   An implementation that cannot take a trial count scores `IGNORES_N`, which is a
   defect in anything called a *deflated* Sharpe.
2. **Ordering** — among implementations that do deflate, do they rank the same
   scenarios the same way?

Usage::

    python3 tools/dsr_conformance.py                       # table to stdout
    python3 tools/dsr_conformance.py --json reports/dsr_conformance.json
    python3 tools/dsr_conformance.py --md reports/dsr_conformance.md
"""
from __future__ import annotations

import argparse
import json
import math
import random
import sys
import traceback
from pathlib import Path
from typing import Any, Callable

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:  # allow `python3 tools/dsr_conformance.py`
    sys.path.insert(0, str(REPO))

#: Trial counts the battery is evaluated at. 1 = no multiplicity correction
#: possible; 26 = the "most favourable" count one desk reported; 121 = canonical.
TRIAL_COUNTS = (1, 26, 121, 4987)

SCHEMA = "dsr_conformance.v1"


# --------------------------------------------------------------------- battery
class Scenario:
    """A deterministic return series with a known per-period Sharpe."""

    def __init__(self, name: str, n: int, sr_per_period: float, *,
                 seed: int, kurtosis_style: str = "normal",
                 note: str = "") -> None:
        self.name = name
        self.n = n
        self.target_sr = sr_per_period
        self.seed = seed
        self.kurtosis_style = kurtosis_style
        self.note = note

    def returns(self) -> list[float]:
        """Series standardised to the target per-period Sharpe, deterministically."""
        rng = random.Random(self.seed)
        if self.kurtosis_style == "fat":
            # Student-t-ish: mix of a gaussian and occasional large shocks.
            raw = [rng.gauss(0.0, 1.0) * (3.5 if rng.random() < 0.04 else 1.0)
                   for _ in range(self.n)]
        else:
            raw = [rng.gauss(0.0, 1.0) for _ in range(self.n)]
        mean = sum(raw) / len(raw)
        var = sum((x - mean) ** 2 for x in raw) / (len(raw) - 1)
        sd = math.sqrt(var) or 1.0
        return [((x - mean) / sd) * 1.0 + self.target_sr for x in raw]


#: The battery. The n=2514 / SR 0.04735 case is H-244's real cell shape, so a
#: disagreement here is a disagreement about a number we actually reported.
BATTERY = (
    Scenario("h244_etf_10m_n2514_sr0.047", 2514, 0.04735, seed=244,
             note="H-244 measured cell: daily Sharpe 0.04735 over 2514 days"),
    Scenario("top_pick_n26_sr0.18", 26, 0.18, seed=26,
             note="the n=26 cell used for the most-favourable N reading"),
    Scenario("tiny_n8_sr0.30", 8, 0.30, seed=8,
             note="below most implementations' minimum sample; tests fail-closed"),
    Scenario("fat_tail_n1200_sr0.06", 1200, 0.06, seed=1200, kurtosis_style="fat",
             note="fat tails: raw-vs-excess kurtosis conventions diverge here"),
    Scenario("negative_sr_n600", 600, -0.05, seed=600,
             note="a losing cell must not score as significant anywhere"),
)


# ----------------------------------------------------------- registry of impls
class Impl:
    """One implementation plus the adapter that drives its actual signature."""

    def __init__(self, name: str, path: str, line: int, fn: Callable[..., Any],
                 accepts_n_trials: bool, call: Callable[[list[float], float, int, int], Any],
                 unit: str) -> None:
        self.name = name
        self.path = path
        self.line = line
        self.fn = fn
        self.accepts_n_trials = accepts_n_trials
        self.call = call
        self.unit = unit

    @property
    def where(self) -> str:
        return f"{self.path}:{self.line}"


def _import(module: str, attr: str) -> Callable[..., Any]:
    mod = __import__(module, fromlist=[attr])
    fn = getattr(mod, attr)
    if not callable(fn):
        raise TypeError(f"{module}.{attr} is not callable")
    return fn


def _wrap_probability(value: Any) -> Any:
    """Normalise a dict-returning implementation to its probability field."""
    if isinstance(value, dict):
        for key in ("dsr", "dsr_probability", "probability", "p_value"):
            if key in value:
                return value[key]
        return value
    return value


def build_registry() -> list[Impl]:
    """Discover implementations. Unimportable ones are reported, not hidden."""
    specs: list[tuple[str, str, str, int, bool, Callable[[list[float], float, int, int], Any], str]] = [
        (
            "statistical_rigor",
            "alpha_engine.statistical_rigor", "deflated_sharpe_ratio", 339, True,
            lambda r, sr, n_obs, N: _import("alpha_engine.statistical_rigor",
                                            "deflated_sharpe_ratio")(r, N),
            "probability",
        ),
        (
            "audit3_tribunal",
            "alpha_engine.audit3_tribunal", "deflated_sharpe", 399, True,
            lambda r, sr, n_obs, N: _wrap_probability(
                _import("alpha_engine.audit3_tribunal", "deflated_sharpe")(r, N)),
            "probability|dict",
        ),
        (
            "anti_overfit_validator",
            "alpha_engine.anti_overfit_validator", "deflated_sharpe", 418, True,
            lambda r, sr, n_obs, N: _import("alpha_engine.anti_overfit_validator",
                                            "deflated_sharpe")(sr, N, r),
            "probability",
        ),
        (
            "crypto_ml_edge",
            "crypto_ml_edge.validation", "deflated_sharpe_ratio", 301, True,
            lambda r, sr, n_obs, N: _import("crypto_ml_edge.validation",
                                            "deflated_sharpe_ratio")(sr, N, n_obs),
            "probability",
        ),
        (
            "deflated_sharpe_deprecated",
            "alpha_engine.deflated_sharpe", "deflated_sharpe_ratio", 179, True,
            lambda r, sr, n_obs, N: _import("alpha_engine.deflated_sharpe",
                                            "deflated_sharpe_ratio")(
                sr, (1.0 + 0.5 * sr * sr) / max(n_obs, 1), N, n_obs, 0.0, 0.0),
            "probability",
        ),
        (
            "validation.sharpe_metrics_CANONICAL",
            "alpha_engine.validation.sharpe_metrics", "deflated_sharpe_ratio", 83, False,
            lambda r, sr, n_obs, N: _import("alpha_engine.validation.sharpe_metrics",
                                            "deflated_sharpe_ratio")(
                _maybe_pandas(r), 0.0, "daily"),
            "t-statistic",
        ),
    ]
    registry: list[Impl] = []
    for name, module, attr, line, accepts, call, unit in specs:
        try:
            fn = _import(module, attr)
        except Exception as exc:  # noqa: BLE001 - unimportable is a reportable state
            registry.append(Impl(name, module.replace(".", "/") + ".py", line,
                                 None, accepts, call, f"UNIMPORTABLE: {type(exc).__name__}"))
            continue
        registry.append(Impl(name, module.replace(".", "/") + ".py", line,
                             fn, accepts, call, unit))
    return registry


def _maybe_pandas(series: list[float]) -> Any:
    try:
        import pandas as pd  # noqa: PLC0415 - optional dependency
        return pd.Series(series)
    except Exception:  # noqa: BLE001
        return series


# ------------------------------------------------------------------ execution
def _per_period_sr(series: list[float]) -> float:
    mean = sum(series) / len(series)
    var = sum((x - mean) ** 2 for x in series) / (len(series) - 1)
    return mean / math.sqrt(var) if var > 0 else 0.0


def _as_float(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(f) or math.isinf(f) else f


def run(registry: list[Impl] | None = None,
        battery: tuple[Scenario, ...] = BATTERY,
        trial_counts: tuple[int, ...] = TRIAL_COUNTS) -> dict:
    registry = registry if registry is not None else build_registry()
    cells: list[dict] = []
    for impl in registry:
        for scenario in battery:
            series = scenario.returns()
            sr = _per_period_sr(series)
            for N in trial_counts:
                cell: dict[str, Any] = {
                    "impl": impl.name, "where": impl.where, "scenario": scenario.name,
                    "n_trials": N, "unit": impl.unit,
                }
                if impl.unit.startswith("UNIMPORTABLE"):
                    cell.update(value=None, status="UNIMPORTABLE", error=impl.unit)
                else:
                    try:
                        cell.update(value=_as_float(impl.call(series, sr, scenario.n, N)),
                                    status="OK", error=None)
                    except Exception as exc:  # noqa: BLE001 - a raise is a finding
                        cell.update(value=None, status="RAISED",
                                    error=f"{type(exc).__name__}: {exc}"[:200])
                        cell["traceback"] = traceback.format_exc(limit=2)
                cells.append(cell)

    verdicts = [verdict_for(impl, cells) for impl in registry]
    return {
        "schema": SCHEMA,
        "battery": [{"name": s.name, "n": s.n, "target_sr_per_period": s.target_sr,
                     "note": s.note} for s in battery],
        "trial_counts": list(trial_counts),
        "verdicts": verdicts,
        "cells": cells,
    }


def verdict_for(impl: Impl, cells: list[dict]) -> dict:
    """Classify one implementation from its own cells."""
    own = [c for c in cells if c["impl"] == impl.name]
    if impl.unit.startswith("UNIMPORTABLE"):
        return {"impl": impl.name, "where": impl.where,
                "verdict": "UNIMPORTABLE", "detail": impl.unit}
    ok = [c for c in own if c["status"] == "OK" and c["value"] is not None]
    if not ok:
        first = next((c.get("error") for c in own if c.get("error")), "no values")
        return {"impl": impl.name, "where": impl.where,
                "verdict": "NEVER_RETURNS", "detail": first}

    def value_at(scenario: str, N: int) -> float | None:
        for c in ok:
            if c["scenario"] == scenario and c["n_trials"] == N:
                return c["value"]
        return None

    # Compare the lowest and highest trial count the implementation actually
    # returns a value for, per scenario. Some implementations legitimately refuse
    # N=1 (no multiplicity correction is possible), and judging them on a pair they
    # declined to produce would mislabel them as trial-blind.
    moved = 0
    compared = 0
    for scenario in {c["scenario"] for c in ok}:
        vals = sorted((c["n_trials"], c["value"]) for c in ok
                      if c["scenario"] == scenario and c["value"] is not None)
        if len(vals) < 2:
            continue
        compared += 1
        if abs(vals[-1][1] - vals[0][1]) > 1e-12:
            moved += 1

    if not impl.accepts_n_trials:
        verdict = "IGNORES_N"
        detail = ("signature takes no trial count, so the value is identical at N=1 and "
                  "N=4987; it cannot deflate regardless of its name")
    elif compared == 0:
        verdict = "UNJUDGEABLE"
        detail = ("answered at only one trial count per scenario, so trial sensitivity "
                  "cannot be measured; drive it with a wider range of trial counts")
    elif moved == 0:
        verdict = "IGNORES_N"
        detail = (f"accepts a trial count but returned the same value at its lowest and "
                  f"highest available trial count for all {compared} comparable scenarios")
    elif verdict_needs_scale_check(ok):
        verdict = "DEFLATES_UNIT_AMBIGUOUS"
        detail = "moves with N, but values exceed 1.0 (a probability cannot) — read as a z-score"
    else:
        verdict = "DEFLATES"
        detail = f"moved with N on {moved}/{compared} scenarios"

    return {
        "impl": impl.name, "where": impl.where, "verdict": verdict, "detail": detail,
        "accepts_n_trials": impl.accepts_n_trials,
        "value_h244_n1": value_at("h244_etf_10m_n2514_sr0.047", 1),
        "value_h244_n121": value_at("h244_etf_10m_n2514_sr0.047", 121),
        "value_negative_cell_n121": value_at("negative_sr_n600", 121),
        "moved_scenarios": f"{moved}/{compared}",
    }


def verdict_needs_scale_check(cells: list[dict]) -> bool:
    """True when any value falls outside [0,1] — i.e. it is not a probability."""
    values = [c["value"] for c in cells if c["value"] is not None]
    return bool(values) and (max(values) > 1.0 + 1e-9 or min(values) < -1e-9)


# --------------------------------------------------------------------- output
def to_markdown(report: dict) -> str:
    lines = [
        "# DSR conformance — does a number called `deflated_sharpe` actually deflate?",
        "",
        f"schema: `{report['schema']}` · trial counts: {report['trial_counts']}",
        "",
        "| implementation | file:line | verdict | N=1 | N=121 | negative cell @N=121 | moved |",
        "|---|---|---|---|---|---|---|",
    ]
    for v in sorted(report["verdicts"], key=lambda x: x["verdict"]):
        def fmt(x: Any) -> str:
            return "—" if x is None else f"{x:.4f}" if isinstance(x, float) else str(x)
        lines.append(
            f"| {v['impl']} | `{v['where']}` | **{v['verdict']}** | "
            f"{fmt(v.get('value_h244_n1'))} | {fmt(v.get('value_h244_n121'))} | "
            f"{fmt(v.get('value_negative_cell_n121'))} | {v.get('moved_scenarios', '—')} |")
    lines += ["", "## Battery", "",
              "| scenario | n | target per-period SR | why |", "|---|---|---|---|"]
    for s in report["battery"]:
        lines.append(f"| {s['name']} | {s['n']} | {s['target_sr_per_period']} | {s['note']} |")
    lines += ["", "## Verdict key", "",
              "* `DEFLATES` — value moves when the trial count rises, stays in [0,1].",
              "* `IGNORES_N` — cannot or does not respond to the trial count. A gate built "
              "on this tests an undeflated Sharpe.",
              "* `DEFLATES_UNIT_AMBIGUOUS` — moves with N but leaves [0,1]; it is a z-score "
              "published under a probability's name.",
              "* `UNJUDGEABLE` — answered at only one trial count, so sensitivity is unmeasurable.",
              "* `NEVER_RETURNS` / `UNIMPORTABLE` — the implementation could not be driven at all.",
              ""]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="DSR conformance harness")
    ap.add_argument("--json", help="write the full report here")
    ap.add_argument("--md", help="write the markdown table here")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args(argv)

    report = run()
    if args.json:
        Path(args.json).parent.mkdir(parents=True, exist_ok=True)
        Path(args.json).write_text(json.dumps(report, indent=2, sort_keys=True) + "\n",
                                   encoding="utf-8")
    if args.md:
        Path(args.md).parent.mkdir(parents=True, exist_ok=True)
        Path(args.md).write_text(to_markdown(report), encoding="utf-8")
    if not args.quiet:
        print(to_markdown(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
