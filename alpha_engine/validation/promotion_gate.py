"""
Promotion Gate (Mercury 2 / Multi-Asset)

Implements fast production gates:
- minimum trade count
- posterior probability Sharpe > 0
- deflated Sharpe
- correlation gate
- Gini concentration gate

Outputs: alpha_engine/data/promotion_gate_report.json
"""

from __future__ import annotations

import argparse
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
import pandas as pd

from .metrics import PerformanceMetrics

try:
    from .sharpe_metrics import deflated_sharpe_ratio as _sm_dsr, probabilistic_sharpe_ratio as _sm_psr
    _SHARPE_METRICS_AVAILABLE = True
except ImportError:
    _SHARPE_METRICS_AVAILABLE = False


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _norm_cdf(z: float) -> float:
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def _posterior_prob_sharpe_gt_zero(sharpe: float, n_trades: int) -> float:
    if n_trades <= 2:
        return 0.5
    # Approximate SE(Sharpe)
    se = math.sqrt(max(1e-12, (1.0 + 0.5 * sharpe * sharpe) / (n_trades - 1)))
    z = sharpe / se
    return float(_norm_cdf(z))


def _gini(values: List[float]) -> float:
    if not values:
        return 0.0
    x = np.array([abs(v) for v in values], dtype=float)
    if np.allclose(x.sum(), 0):
        return 0.0
    x_sorted = np.sort(x)
    n = len(x_sorted)
    cum = np.cumsum(x_sorted)
    g = (n + 1 - 2 * np.sum(cum) / cum[-1]) / n
    return float(g)


def _strategy_symbol_vectors(strategy_results: Dict[str, Any]) -> Dict[str, Dict[str, float]]:
    vecs: Dict[str, Dict[str, float]] = {}
    for strategy, payload in strategy_results.items():
        per_symbol = payload.get("per_symbol", {})
        sym_map: Dict[str, float] = {}
        for symbol, sp in per_symbol.items():
            agg = sp.get("aggregate_oos", {})
            val = agg.get("total_pnl_pct")
            if val is None:
                continue
            try:
                sym_map[symbol] = float(val)
            except Exception:
                continue
        if sym_map:
            vecs[strategy] = sym_map
    return vecs


def _pairwise_corr(a: Dict[str, float], b: Dict[str, float]) -> float:
    common = sorted(set(a.keys()) & set(b.keys()))
    if len(common) < 3:
        return 0.0
    va = np.array([a[s] for s in common], dtype=float)
    vb = np.array([b[s] for s in common], dtype=float)
    if np.std(va) == 0 or np.std(vb) == 0:
        return 0.0
    return float(np.corrcoef(va, vb)[0, 1])


def run_gate(
    walk_forward_path: Path,
    institutional_path: Path,
    out_path: Path,
    min_trades: int = 50,
    posterior_threshold: float = 0.95,
    dsr_threshold: float = 1.64,
    corr_threshold: float = 0.75,
    gini_threshold: float = 0.40,
) -> Dict[str, Any]:
    wf = _load(walk_forward_path)
    inst = _load(institutional_path)
    strategies = wf.get("strategies", {})
    rows = inst.get("multiple_testing", {}).get("rows", [])
    row_map = {r.get("strategy"): r for r in rows if isinstance(r, dict)}

    pair_pnls = []
    pair_trade_returns: list = []
    for _, pv in inst.get("portfolio_risk", {}).get("pairs", {}).items():
        if not isinstance(pv, dict):
            continue
        try:
            pair_pnls.append(float(pv.get("pnl_sum", 0.0)))
        except Exception:
            pass
        # Reconstruct per-trade returns from CVaR proxy fields when available
        trades_n = int(pv.get("trades", 0))
        wr = float(pv.get("win_rate", 0.0))
        avg_r = float(pv.get("r_multiple", 0.0))
        var95 = float(pv.get("var_95", -0.015))
        if trades_n > 0:
            wins = round(wr * trades_n)
            losses = trades_n - wins
            win_ret = abs(var95) * avg_r if avg_r > 0 else abs(var95) * 0.5
            pair_trade_returns.extend([win_ret] * wins + [var95] * losses)
    gini_concentration = _gini(pair_pnls)

    # Portfolio-level DSR and PSR from sharpe_metrics (returns-based, complements scalar DSR in decisions)
    portfolio_sm_dsr = None
    portfolio_sm_psr = None
    if _SHARPE_METRICS_AVAILABLE and len(pair_trade_returns) >= 10:
        try:
            ret_series = pd.Series(pair_trade_returns, dtype=float)
            portfolio_sm_dsr = round(float(_sm_dsr(ret_series, risk_free_rate=0.0, freq="daily")), 4)
            portfolio_sm_psr = round(float(_sm_psr(ret_series, risk_free_rate=0.0, target_sharpe=0.0, freq="daily")), 4)
        except Exception:
            pass

    vecs = _strategy_symbol_vectors(strategies)
    strategy_max_corr: Dict[str, float] = {}
    for s1, v1 in vecs.items():
        mx = 0.0
        for s2, v2 in vecs.items():
            if s1 == s2:
                continue
            c = abs(_pairwise_corr(v1, v2))
            mx = max(mx, c)
        strategy_max_corr[s1] = round(mx, 4)

    decisions = []
    for strategy, payload in strategies.items():
        agg = payload.get("aggregate_oos", {})
        trades = int(agg.get("total_trades", 0))
        sharpe = float(agg.get("sharpe", 0.0))
        wr = float(agg.get("win_rate", 0.0))
        pf = float(agg.get("profit_factor", 0.0))
        bh_sig = bool(row_map.get(strategy, {}).get("significant_5pct_bh", False))
        bonf_sig = bool(row_map.get(strategy, {}).get("significant_5pct_bonf", False))

        posterior_prob = _posterior_prob_sharpe_gt_zero(sharpe, trades)
        try:
            dsr = float(
                PerformanceMetrics.compute_deflated_sharpe(
                    sharpe=sharpe,
                    n_trials=max(1, len(strategies)),
                    n_observations=max(5, trades),
                    skewness=0.0,
                    kurtosis=3.0,
                )
            )
        except Exception:
            dsr = 0.0

        max_corr = float(strategy_max_corr.get(strategy, 0.0))

        checks = {
            "min_trades": trades >= min_trades,
            "bh_or_bonf_significant": (bh_sig or bonf_sig),
            "posterior_prob_sharpe_gt_zero": posterior_prob >= posterior_threshold,
            "deflated_sharpe": dsr >= dsr_threshold,
            "correlation_gate": max_corr <= corr_threshold,
            "gini_concentration_gate": gini_concentration <= gini_threshold,
            "basic_quality": (wr >= 55.0 and pf >= 1.5 and sharpe > 0),
        }
        gate_score = sum(1 for v in checks.values() if v)
        passed = gate_score == len(checks)
        status = "PRODUCTION_CANDIDATE" if passed else ("PROBATION" if gate_score >= 4 else "REJECT")

        decisions.append(
            {
                "strategy": strategy,
                "trades": trades,
                "win_rate": wr,
                "profit_factor": pf,
                "sharpe": sharpe,
                "posterior_prob_sharpe_gt_zero": round(posterior_prob, 4),
                "deflated_sharpe": round(dsr, 4),
                "max_abs_correlation": round(max_corr, 4),
                "checks": checks,
                "gate_score": gate_score,
                "gate_max": len(checks),
                "status": status,
            }
        )

    decisions.sort(key=lambda x: (x["gate_score"], x["sharpe"], x["profit_factor"]), reverse=True)

    report = {
        "generated_at": _now_iso(),
        "inputs": {
            "walk_forward": str(walk_forward_path),
            "institutional_report": str(institutional_path),
        },
        "thresholds": {
            "min_trades": min_trades,
            "posterior_prob_sharpe_gt_zero": posterior_threshold,
            "deflated_sharpe": dsr_threshold,
            "max_abs_correlation": corr_threshold,
            "gini_concentration": gini_threshold,
        },
        "global": {
            "gini_concentration": round(gini_concentration, 4),
            "n_strategies": len(decisions),
            "production_candidates": sum(1 for d in decisions if d["status"] == "PRODUCTION_CANDIDATE"),
            "probation": sum(1 for d in decisions if d["status"] == "PROBATION"),
            "reject": sum(1 for d in decisions if d["status"] == "REJECT"),
            "portfolio_deflated_sharpe_sm": portfolio_sm_dsr,
            "portfolio_prob_sharpe_sm": portfolio_sm_psr,
        },
        "decisions": decisions,
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Run strategy promotion gate checks.")
    parser.add_argument("--walk-forward", default="alpha_engine/data/walk_forward_results.json")
    parser.add_argument("--institutional", default="alpha_engine/data/institutional_backtest_report.json")
    parser.add_argument("--output", default="alpha_engine/data/promotion_gate_report.json")
    parser.add_argument("--min-trades", type=int, default=50)
    args = parser.parse_args()

    report = run_gate(
        walk_forward_path=Path(args.walk_forward),
        institutional_path=Path(args.institutional),
        out_path=Path(args.output),
        min_trades=args.min_trades,
    )
    print("Promotion gate completed")
    print(f"Production candidates: {report['global']['production_candidates']}")
    print(f"Output: {args.output}")


if __name__ == "__main__":
    main()

