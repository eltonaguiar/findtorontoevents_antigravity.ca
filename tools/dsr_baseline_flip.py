#!/usr/bin/env python3
"""Which class verdicts change when the DSR trial baseline is raised?

``NB_TRIALS_BY_CLASS`` (alpha_engine/money_ready_verdict.py) supplies the
``nb_trials`` that deflates each class's DSR. Three of its entries are still
marked "legacy lower bound" (CRYPTO 14, FOREX 6, COMMODITY 3) while the search
space that produced those classes is far larger -- 629 CRYPTO strategy cells in
the ledger alone. This tool answers the question that legacy note raises:

  if the baseline is raised to the measured search space, does any class verdict
  flip, and in which direction?

Two things make the answer less obvious than it looks:

1. ``_dsr_gate`` no longer uses the per-class number directly -- it goes through
   ``effective_n_trials``, i.e. ``max(local, global_total, family)``. When the
   global trial counter already exceeds a class baseline, editing the dictionary
   changes nothing. The tool reports both the mapped value and the effective one
   so a "fix" that cannot move the gate is visible before it is written.
2. Deflated Sharpe is **monotone decreasing in nb_trials** (``expected_max_sharpe``
   rises with N, the denominator is fixed), so raising a baseline can only turn a
   PASS into a FAIL. A class already failing cannot be rescued by a bigger trial
   count. The tool proves that per class rather than asserting it globally.

Usage:
    python3 tools/dsr_baseline_flip.py
    python3 tools/dsr_baseline_flip.py --picks /tmp/closed_main.json --json
    python3 tools/dsr_baseline_flip.py --md reports/dsr-flip-2026-11-21.md
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
for _p in (str(REPO), str(REPO / "tools")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from alpha_engine.deflated_sharpe import (  # noqa: E402
    deflated_sharpe_ratio,
    returns_stats,
    sharpe_variance,
)
from alpha_engine.money_ready_verdict import (  # noqa: E402
    CANONICAL_ASSET_CLASSES,
    DSR_THRESHOLD,
    NB_TRIALS_BY_CLASS,
)

MIN_RETURNS = 10          # _dsr_gate returns ok=None below this
DEFAULT_PICKS = REPO / "alpha_engine" / "data" / "closed_picks.json"
DEFAULT_LEDGER = REPO / "audit_dashboard" / "data" / "audit3_ledger.json"
DEFAULT_REGISTRY = REPO / "audit_dashboard" / "data" / "pf_registry.json"
REGISTRY_KEY = "by_asset_class_strategy_policy_clean_net"


def load_returns(path: Path) -> dict[str, list[float]]:
    """class -> per-trade net returns. Deduplicated; only resolved rows."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    rows = data if isinstance(data, list) else data.get("picks") or []
    out: dict[str, list[float]] = {}
    seen: set[str] = set()
    for r in rows:
        if not isinstance(r, dict):
            continue
        cls = str(r.get("asset_class") or "").strip().upper()
        if cls not in CANONICAL_ASSET_CLASSES:
            continue
        pnl = r.get("pnl_pct")
        if pnl is None:
            continue
        try:
            val = float(pnl)
        except (TypeError, ValueError):
            continue
        key = str(r.get("dedup_key") or r.get("id") or id(r))
        if key in seen:
            continue
        seen.add(key)
        out.setdefault(cls, []).append(val)
    return out


def ledger_search_space(path: Path) -> dict[str, int]:
    """class -> number of strategy cells the ledger measured for that class."""
    try:
        ledge = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    counts: dict[str, int] = {}
    for cell in ledge.get("cells") or []:
        if not isinstance(cell, dict):
            continue
        cls = str(cell.get("asset_class") or "").strip().upper()
        if cls:
            counts[cls] = counts.get(cls, 0) + 1
    return counts


def registry_cells(path: Path) -> dict[str, int]:
    """class -> distinct policy-clean cells (same book the verdict reads)."""
    try:
        reg = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    counts: dict[str, int] = {}
    for row in reg.get(REGISTRY_KEY) or []:
        if not isinstance(row, dict):
            continue
        cls = str(row.get("asset_class") or "").strip().upper()
        if cls:
            counts[cls] = counts.get(cls, 0) + 1
    return counts


def dsr_at(returns: list[float], n_trials: int) -> float | None:
    """DSR at an arbitrary ``n_trials``.

    Mirrors ``_dsr_gate`` arithmetic exactly (annualised SR by sqrt(252), Lo
    variance, Bailey/Lopez de Prado deflation) so the sweep is comparable to the
    gate. ``self_check`` asserts that equivalence against the real gate.
    """
    if n_trials is None or n_trials < 1 or len(returns) < MIN_RETURNS:
        return None
    arr = [float(x) for x in returns]
    mu = sum(arr) / len(arr)
    var = sum((x - mu) ** 2 for x in arr) / len(arr)
    sd = var ** 0.5
    if sd == 0:
        return None
    sr = mu / sd * (252 ** 0.5)
    stats = returns_stats(arr)
    horizon = len(arr)
    sr_var = sharpe_variance(sr, horizon, stats["skewness"], stats["kurtosis"])
    try:
        score = float(deflated_sharpe_ratio(
            estimated_sharpe=sr,
            sr_variance=sr_var,
            nb_trials=int(n_trials),
            backtest_horizon=horizon,
            skew=stats["skewness"],
            kurtosis=stats["kurtosis"],
        ))
    except (ValueError, ZeroDivisionError):
        return None
    if not math.isfinite(score):
        return None      # fail closed, same contract as _dsr_gate's NaN guard
    return score


def self_check(returns_by_class: dict[str, list[float]]) -> list[str]:
    """Prove ``dsr_at`` reproduces the live gate at the effective baseline."""
    from alpha_engine.money_ready_verdict import _dsr_gate
    from alpha_engine.trial_counter import effective_n_trials

    problems: list[str] = []
    for cls, rets in sorted(returns_by_class.items()):
        live = _dsr_gate(rets, cls)
        if live.get("dsr_score") is None:
            continue
        n_eff = effective_n_trials(NB_TRIALS_BY_CLASS.get(cls), family=cls)
        mine = dsr_at(rets, n_eff)
        if mine is None:
            problems.append(f"{cls}: mirror produced no score at n={n_eff}")
            continue
        delta = abs(mine - float(live["dsr_score"]))
        if delta > 5e-4:
            problems.append(
                f"{cls}: mirror {mine:.4f} != gate {live['dsr_score']} "
                f"at n={n_eff} (delta {delta:.5f})"
            )
    return problems


def breakpoint(returns: list[float], threshold: float = DSR_THRESHOLD,
               upper: int = 10_000_000) -> int | None:
    """Largest nb_trials at which DSR still clears the threshold.

    None when DSR already fails at nb_trials=2 (no rescue possible), or when the
    series is too short to score.
    """
    if dsr_at(returns, 2) is None:
        return None
    if (dsr_at(returns, 2) or 0.0) < threshold:
        return None
    lo, hi = 2, upper
    while lo < hi:
        mid = (lo + hi + 1) // 2
        score = dsr_at(returns, mid)
        if score is not None and score >= threshold:
            lo = mid
        else:
            hi = mid - 1
    return lo


def build_rows(returns_by_class, search_space, registry, ledger) -> list[dict]:
    from alpha_engine.trial_counter import effective_n_trials
    try:
        total_global = int(json.loads(
            (REPO / "reports" / "trial_counter.json").read_text()
        ).get("total") or 0)
    except (OSError, ValueError):
        total_global = 0

    ledger_n = {}
    try:
        ledge = json.loads(DEFAULT_LEDGER.read_text(encoding="utf-8")) if ledger is None else {}
    except (OSError, ValueError):
        ledge = {}
    for c in (ledge.get("classes") or []):
        cls = str(c.get("asset_class") or "").upper()
        if cls and c.get("dsr_n_trials") is not None:
            ledger_n[cls] = int(c["dsr_n_trials"])

    rows: list[dict] = []
    for cls in sorted(set(NB_TRIALS_BY_CLASS) | set(returns_by_class) | set(search_space)):
        rets = returns_by_class.get(cls) or []
        mapped = NB_TRIALS_BY_CLASS.get(cls)
        local = mapped if mapped is not None else 0
        n_now = int(effective_n_trials(local, family=cls))
        measured = max(search_space.get(cls, 0), registry.get(cls, 0))
        n_prop = int(max(n_now, measured))
        estimable = len(rets) >= MIN_RETURNS
        now = dsr_at(rets, n_now) if estimable else None
        prop = dsr_at(rets, n_prop) if estimable else None
        bp = breakpoint(rets) if estimable else None
        rows.append({
            "class": cls,
            "n_returns": len(rets),
            "mapped": mapped,
            "effective_now": n_now,
            "ledger_n": ledger_n.get(cls),
            "measured_cells": measured,
            "proposed": n_prop,
            "estimable": estimable,
            "dsr_now": None if now is None else round(now, 4),
            "dsr_proposed": None if prop is None else round(prop, 4),
            "pass_now": None if now is None else now >= DSR_THRESHOLD,
            "pass_proposed": None if prop is None else prop >= DSR_THRESHOLD,
            "flip": (None if now is None or prop is None
                     else (now >= DSR_THRESHOLD) != (prop >= DSR_THRESHOLD)),
            "breakpoint_n": bp,
            "baseline_moves_gate": n_prop != n_now,
            "global_trials": total_global,
        })
    return rows


def render(rows: list[dict]) -> str:
    head = (f"{'class':<12}{'n':>6}{'mapped':>8}{'eff_now':>9}{'cells':>7}"
            f"{'proposed':>10}{'dsr_now':>9}{'dsr_prop':>10}{'flip':>6}{'bp_n':>9}")
    lines = [head, "-" * len(head)]
    for r in rows:
        lines.append(
            f"{r['class']:<12}{r['n_returns']:>6}{str(r['mapped']):>8}"
            f"{r['effective_now']:>9}{r['measured_cells']:>7}{r['proposed']:>10}"
            f"{('-' if r['dsr_now'] is None else f'{r['dsr_now']:.4f}'):>9}"
            f"{('-' if r['dsr_proposed'] is None else f'{r['dsr_proposed']:.4f}'):>10}"
            f"{('-' if r['flip'] is None else ('YES' if r['flip'] else 'no')):>6}"
            f"{('-' if r['breakpoint_n'] is None else str(r['breakpoint_n'])):>9}"
        )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--picks", default=str(DEFAULT_PICKS))
    ap.add_argument("--ledger", default=str(DEFAULT_LEDGER))
    ap.add_argument("--registry", default=str(DEFAULT_REGISTRY))
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--md", help="write a markdown table to this path")
    args = ap.parse_args(argv)

    returns_by_class = load_returns(Path(args.picks))
    space = ledger_search_space(Path(args.ledger))
    reg = registry_cells(Path(args.registry))
    rows = build_rows(returns_by_class, space, reg, None)

    problems = self_check(returns_by_class)
    if problems:
        print("MIRROR CHECK FAILED -- the sweep is not comparable to the gate:",
              file=sys.stderr)
        for p in problems:
            print(f"  - {p}", file=sys.stderr)
        return 3

    if args.json:
        print(json.dumps({"threshold": DSR_THRESHOLD, "rows": rows}, indent=1))
    else:
        print(f"DSR threshold {DSR_THRESHOLD}; mirror of _dsr_gate verified "
              f"on {len(returns_by_class)} classes")
        print(render(rows))
        print()
        print("monotonicity: DSR falls as nb_trials rises (expected_max_sharpe grows,")
        print("the standard error does not), so a raise can only PASS -> FAIL.")
        print("breakpoint_n = largest trial count that still clears the threshold.")

    if args.md:
        out = [f"# DSR baseline flip sweep ({len(rows)} classes)",
               "",
               f"Threshold {DSR_THRESHOLD}. Mirror of `_dsr_gate` verified against the "
               f"live gate on {len(returns_by_class)} classes.", "",
               "| class | n | mapped | effective now | measured cells | proposed | "
               "DSR now | DSR proposed | flip | breakpoint n |",
               "|---|---|---|---|---|---|---|---|---|---|"]
        for r in rows:
            out.append(
                f"| {r['class']} | {r['n_returns']} | {r['mapped']} | {r['effective_now']} | "
                f"{r['measured_cells']} | {r['proposed']} | "
                f"{'-' if r['dsr_now'] is None else r['dsr_now']} | "
                f"{'-' if r['dsr_proposed'] is None else r['dsr_proposed']} | "
                f"{'-' if r['flip'] is None else ('YES' if r['flip'] else 'no')} | "
                f"{'-' if r['breakpoint_n'] is None else r['breakpoint_n']} |")
        Path(args.md).write_text("\n".join(out) + "\n", encoding="utf-8")
        print(f"\nwrote {args.md}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
