#!/usr/bin/env python3
"""
Mutation Framework — Four-Axis Strategy Mutation (EAGLE2 synthesis)
=====================================================================
  Axis 1: Invert (LONG ↔ SHORT)
  Axis 2: Symbol rotation (drop bottom-quartile by WR)
  Axis 3: Regime gate (profitable HMM/regime states only)
  Axis 4: Parameter stress (EAGLE2 blackboxai — safe perturbation proxy)

Each mutation re-runs purged walk-forward before adoption.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Tuple

import numpy as np

logger = logging.getLogger(__name__)


class MutationAxis(Enum):
    INVERT = "invert"
    SYMBOL_ROTATION = "symbol_rotation"
    REGIME_GATE = "regime_gate"
    PARAMETER = "parameter"


@dataclass
class MutationResult:
    axis: MutationAxis
    strategy_name: str
    original_pf: float
    original_wr: float
    original_n: int
    mutated_pf: float
    mutated_wr: float
    mutated_n: int
    improvement: float
    verdict: str  # ADOPT / CONSIDER / REJECT / INSUFFICIENT_DATA
    details: Dict = field(default_factory=dict)


def compute_pf(pnls: List[float]) -> float:
    wins = sum(1 for p in pnls if p > 0)
    losses = sum(1 for p in pnls if p < 0)
    return wins / losses if losses > 0 else (999.0 if wins > 0 else 0.0)


def compute_wr(pnls: List[float]) -> float:
    total = sum(1 for p in pnls if p != 0)
    wins = sum(1 for p in pnls if p > 0)
    return wins / total if total > 0 else 0.0


def purged_walk_forward(
    trades: List[Dict],
    n_folds: int = 5,
    purge_pct: float = 0.05,
    embargo_pct: float = 0.10,
) -> Dict:
    """Purged walk-forward with embargo on closed-trade PnL series."""
    pnls = np.array([t.get("pnl", 0) or t.get("pnl_pct", 0) or 0 for t in trades])
    n = len(pnls)

    if n < 15:
        return {"verdict": "INSUFFICIENT_DATA", "avg_test_pf": 0.0, "folds_profitable": 0}

    fold_size = n // n_folds
    purge_n = max(1, int(fold_size * purge_pct))
    embargo_n = max(1, int(fold_size * embargo_pct))

    fold_results = []
    for i in range(n_folds):
        test_start = i * fold_size
        test_end = (i + 1) * fold_size if i < n_folds - 1 else n

        train_indices = list(range(0, max(0, test_start - purge_n))) + list(
            range(min(n, test_end + embargo_n), n)
        )
        test_indices = list(range(test_start, test_end))

        test_pnls = pnls[test_indices]
        fold_results.append({"test_pf": compute_pf(test_pnls.tolist())})

    avg_test_pf = float(np.mean([f["test_pf"] for f in fold_results]))
    folds_profitable = sum(1 for f in fold_results if f["test_pf"] >= 1.0)

    return {
        "verdict": "PASS" if avg_test_pf >= 1.0 and folds_profitable >= 3 else "FAIL",
        "avg_test_pf": avg_test_pf,
        "folds_profitable": folds_profitable,
        "folds_total": n_folds,
    }


def mutate_invert(trades: List[Dict]) -> List[Dict]:
    inverted = []
    for t in trades:
        t_inv = t.copy()
        pnl = t.get("pnl", 0) or t.get("pnl_pct", 0) or 0
        t_inv["pnl"] = -pnl
        t_inv["pnl_pct"] = t_inv["pnl"]
        inverted.append(t_inv)
    return inverted


def mutate_symbol_rotation(
    trades: List[Dict], drop_pct: float = 0.25
) -> Tuple[List[Dict], List[str]]:
    symbol_stats: Dict[str, Dict[str, int]] = defaultdict(lambda: {"wins": 0, "losses": 0})
    for t in trades:
        sym = t.get("symbol", "unknown")
        pnl = t.get("pnl", 0) or t.get("pnl_pct", 0) or 0
        if pnl > 0:
            symbol_stats[sym]["wins"] += 1
        elif pnl < 0:
            symbol_stats[sym]["losses"] += 1

    symbol_wr = {}
    for sym, s in symbol_stats.items():
        total = s["wins"] + s["losses"]
        symbol_wr[sym] = s["wins"] / total if total > 0 else 0.0

    sorted_syms = sorted(symbol_wr.items(), key=lambda x: x[1])
    cutoff = max(1, len(sorted_syms) // int(1 / drop_pct))
    drop_syms = {s[0] for s in sorted_syms[:cutoff]}

    filtered = [t for t in trades if t.get("symbol") not in drop_syms]
    return filtered, list(drop_syms)


def mutate_parameter_perturb(
    trades: List[Dict], scale_pnl: float = 0.85
) -> Tuple[List[Dict], Dict]:
    stressed = []
    for t in trades:
        row = t.copy()
        pnl = float(row.get("pnl", 0) or row.get("pnl_pct", 0) or 0)
        row["pnl"] = pnl * scale_pnl
        row["pnl_pct"] = row["pnl"]
        row["mutation_axis"] = "parameter_stress"
        stressed.append(row)
    return stressed, {"scale_pnl": scale_pnl}


def mutate_regime_gate(trades: List[Dict]) -> Tuple[List[Dict], List[str]]:
    regime_pnls: Dict[str, List[float]] = defaultdict(list)
    for t in trades:
        regime = t.get("regime", t.get("market_regime", "UNKNOWN"))
        pnl = t.get("pnl", 0) or t.get("pnl_pct", 0) or 0
        regime_pnls[regime].append(pnl)

    profitable = [
        r for r, pnls in regime_pnls.items()
        if compute_pf(pnls) >= 1.0 and len(pnls) >= 3
    ]
    if not profitable:
        return [], []

    filtered = [
        t for t in trades
        if t.get("regime", t.get("market_regime", "UNKNOWN")) in profitable
    ]
    return filtered, profitable


def run_mutation(strategy_name: str, trades: List[Dict], axis: MutationAxis) -> MutationResult:
    original_pnls = [t.get("pnl", 0) or t.get("pnl_pct", 0) or 0 for t in trades]
    original_pf = compute_pf(original_pnls)
    original_wr = compute_wr(original_pnls)
    original_n = len(trades)

    if axis == MutationAxis.INVERT:
        mutated = mutate_invert(trades)
        details: Dict = {}
    elif axis == MutationAxis.SYMBOL_ROTATION:
        mutated, dropped = mutate_symbol_rotation(trades)
        details = {"dropped_symbols": dropped}
    elif axis == MutationAxis.REGIME_GATE:
        mutated, regimes = mutate_regime_gate(trades)
        details = {"profitable_regimes": regimes}
    elif axis == MutationAxis.PARAMETER:
        mutated, details = mutate_parameter_perturb(trades)
    else:
        return MutationResult(
            axis=axis, strategy_name=strategy_name,
            original_pf=0, original_wr=0, original_n=0,
            mutated_pf=0, mutated_wr=0, mutated_n=0,
            improvement=0, verdict="REJECT",
        )

    if len(mutated) < 10:
        return MutationResult(
            axis=axis, strategy_name=strategy_name,
            original_pf=original_pf, original_wr=original_wr, original_n=original_n,
            mutated_pf=0, mutated_wr=0, mutated_n=len(mutated),
            improvement=0, verdict="INSUFFICIENT_DATA", details=details,
        )

    wf = purged_walk_forward(mutated)
    mutated_pnls = [t.get("pnl", 0) or t.get("pnl_pct", 0) or 0 for t in mutated]
    mutated_wr = compute_wr(mutated_pnls)
    improvement = wf["avg_test_pf"] - original_pf

    if wf["verdict"] == "PASS" and improvement > 0.05:
        verdict = "ADOPT"
    elif wf["avg_test_pf"] >= 1.0 and improvement > 0:
        verdict = "CONSIDER"
    else:
        verdict = "REJECT"

    return MutationResult(
        axis=axis, strategy_name=strategy_name,
        original_pf=original_pf, original_wr=original_wr, original_n=original_n,
        mutated_pf=wf["avg_test_pf"], mutated_wr=mutated_wr, mutated_n=len(mutated),
        improvement=improvement, verdict=verdict, details=details,
    )


def run_full_mutation_scan(
    trades_by_strategy: Dict[str, List[Dict]],
    min_n: int = 10,
    max_pf: float = 1.0,
) -> List[MutationResult]:
    results: List[MutationResult] = []
    for strat_name, trades in trades_by_strategy.items():
        pnls = [t.get("pnl", 0) or t.get("pnl_pct", 0) or 0 for t in trades]
        if len(trades) < min_n or compute_pf(pnls) >= max_pf:
            continue
        for axis in MutationAxis:
            result = run_mutation(strat_name, trades, axis)
            results.append(result)
            if result.verdict in ("ADOPT", "CONSIDER"):
                logger.info(
                    "MUTATION %s %s: %s PF %.2f -> %.2f",
                    axis.value, strat_name, result.verdict,
                    result.original_pf, result.mutated_pf,
                )
    return sorted(results, key=lambda r: r.improvement, reverse=True)
