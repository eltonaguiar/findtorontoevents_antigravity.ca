"""
Institutional Backtest Suite

Adds production-grade audit checks on top of existing walk-forward outputs:
- Multiple-hypothesis correction (Benjamini-Hochberg + Bonferroni)
- Fisher combined p-value across robust strategies
- Bootstrap confidence intervals (Sharpe and return)
- Pick-level risk metrics (PoL, SL hit rate, R-multiple proxy, CVaR proxy)
- Cross-asset holdout summary using available strategy buckets
"""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from .metrics import PerformanceMetrics
from .monte_carlo import MonteCarloSimulator

try:
    from .sharpe_metrics import deflated_sharpe_ratio, probabilistic_sharpe_ratio
    _SHARPE_METRICS_AVAILABLE = True
except ImportError:
    _SHARPE_METRICS_AVAILABLE = False


@dataclass
class HypothesisResult:
    strategy: str
    raw_p_value: float
    bh_q_value: float
    bonferroni_p: float
    significant_5pct_bh: bool
    significant_5pct_bonf: bool


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _benjamini_hochberg(p_values: List[float]) -> List[float]:
    n = len(p_values)
    if n == 0:
        return []
    order = np.argsort(p_values)
    ranked = np.array(p_values)[order]
    q_vals = np.zeros(n)
    prev = 1.0
    for i in range(n - 1, -1, -1):
        rank = i + 1
        candidate = ranked[i] * n / rank
        prev = min(prev, candidate)
        q_vals[i] = prev
    out = np.zeros(n)
    out[order] = q_vals
    return out.tolist()


def _bonferroni(p_values: List[float]) -> List[float]:
    n = max(1, len(p_values))
    return [min(1.0, p * n) for p in p_values]


def _fisher_combined_p_value(p_values: List[float]) -> float:
    clean = [max(1e-12, min(1.0, float(p))) for p in p_values]
    if not clean:
        return 1.0
    chi_stat = -2.0 * sum(math.log(p) for p in clean)
    # Wilson-Hilferty approximation for chi-square tail; avoids scipy dependency.
    dof = 2 * len(clean)
    z = ((chi_stat / dof) ** (1.0 / 3.0) - (1.0 - 2.0 / (9.0 * dof))) / math.sqrt(2.0 / (9.0 * dof))
    # Normal tail approximation:
    p = 0.5 * math.erfc(z / math.sqrt(2))
    return max(0.0, min(1.0, p))


def _strategy_hypothesis_table(strategy_results: Dict[str, Any]) -> Tuple[List[HypothesisResult], float]:
    names: List[str] = []
    pvals: List[float] = []
    for strategy, payload in strategy_results.items():
        # Primary: explicit p-value in old report format
        p = payload.get("overall", {}).get("p_value")
        if p is None:
            # Fallback: derive from aggregate OOS win-rate vs 50% null
            agg = payload.get("aggregate_oos", {})
            trades = int(agg.get("total_trades", 0))
            wr = float(agg.get("win_rate", 0.0)) / 100.0
            if trades >= 10:
                wins = wr * trades
                z = (wins - 0.5 * trades) / math.sqrt(max(1e-12, 0.25 * trades))
                p = float(math.erfc(abs(z) / math.sqrt(2)))
        if p is None:
            continue
        pvals.append(float(p))
        names.append(strategy)

    bh = _benjamini_hochberg(pvals)
    bonf = _bonferroni(pvals)
    rows = [
        HypothesisResult(
            strategy=names[i],
            raw_p_value=round(pvals[i], 6),
            bh_q_value=round(bh[i], 6),
            bonferroni_p=round(bonf[i], 6),
            significant_5pct_bh=bh[i] < 0.05,
            significant_5pct_bonf=bonf[i] < 0.05,
        )
        for i in range(len(names))
    ]
    combined = _fisher_combined_p_value(pvals)
    return rows, combined


def _build_trade_returns_from_pair_payload(pair_payload: Dict[str, Any]) -> List[float]:
    if not isinstance(pair_payload, dict):
        return []
    cfg = pair_payload.get("config", {})
    tp = float(cfg.get("tp", 0.03))
    sl = float(cfg.get("sl", -0.015))
    tp_hits = int(pair_payload.get("tp_hits", 0))
    sl_hits = int(pair_payload.get("sl_hits", 0))
    return ([tp] * tp_hits) + ([sl] * sl_hits)


def _portfolio_risk_metrics_from_pairs(pair_results: Dict[str, Any]) -> Dict[str, Any]:
    all_trades: List[float] = []
    pair_stats: Dict[str, Any] = {}
    for pair, payload in pair_results.items():
        if not isinstance(payload, dict):
            continue
        trades = _build_trade_returns_from_pair_payload(payload)
        if not trades:
            continue
        arr = np.array(trades, dtype=float)
        pnl = float(arr.sum())
        pol = float((arr < 0).mean())
        sl_hit_frequency = float((arr == min(arr)).mean()) if len(arr) else 0.0
        avg_win = float(arr[arr > 0].mean()) if (arr > 0).any() else 0.0
        avg_loss = abs(float(arr[arr < 0].mean())) if (arr < 0).any() else 0.0
        r_mult = (avg_win / avg_loss) if avg_loss > 0 else 0.0
        var95 = float(np.percentile(arr, 5))
        cvar95 = float(arr[arr <= var95].mean()) if (arr <= var95).any() else var95

        pair_stats[pair] = {
            "trades": len(trades),
            "pnl_sum": round(pnl, 6),
            "probability_of_loss": round(pol, 4),
            "stop_loss_hit_frequency": round(sl_hit_frequency, 4),
            "r_multiple": round(r_mult, 4),
            "var_95": round(var95, 6),
            "cvar_95": round(cvar95, 6),
        }
        all_trades.extend(trades)

    if not all_trades:
        return {"portfolio": {}, "pairs": pair_stats}

    ser = pd.Series(all_trades)
    perf = PerformanceMetrics.compute_all(ser)
    summary = {
        "n_trades": len(all_trades),
        "win_rate": round(float((ser > 0).mean()), 4),
        "probability_of_loss": round(float((ser < 0).mean()), 4),
        "avg_r_multiple": round(
            (float(ser[ser > 0].mean()) / abs(float(ser[ser < 0].mean()))) if (ser < 0).any() and (ser > 0).any() else 0.0,
            4,
        ),
        "max_drawdown": round(perf.max_drawdown, 6),
        "sharpe": round(perf.sharpe_ratio, 4),
        "sortino": round(perf.sortino_ratio, 4),
        "calmar": round(perf.calmar_ratio, 4),
        "var_95": round(perf.var_95, 6),
        "cvar_95": round(perf.cvar_95, 6),
    }
    if _SHARPE_METRICS_AVAILABLE:
        try:
            dsr = deflated_sharpe_ratio(ser, risk_free_rate=0.0, freq="daily")
            psr = probabilistic_sharpe_ratio(ser, risk_free_rate=0.0, target_sharpe=0.0, freq="daily")
            summary["deflated_sharpe"] = round(float(dsr), 4) if dsr is not None and dsr == dsr else None
            summary["prob_sharpe"] = round(float(psr), 4) if psr is not None and psr == psr else None
        except Exception:
            summary["deflated_sharpe"] = None
            summary["prob_sharpe"] = None
    return {"portfolio": summary, "pairs": pair_stats}


def _cross_asset_holdout(strategy_results: Dict[str, Any]) -> Dict[str, Any]:
    # Lightweight bucketization from strategy names.
    buckets = {
        "crypto": [],
        "stocks": [],
        "etf": [],
        "forex": [],
        "futures": [],
        "commodities": [],
        "other": [],
    }
    for s, payload in strategy_results.items():
        name = s.lower()
        test_wr = float(
            payload.get("test", {}).get("win_rate_pct", payload.get("aggregate_oos", {}).get("win_rate", 0.0))
        )
        if any(k in name for k in ("btc", "eth", "xrp", "sol", "crypto")):
            buckets["crypto"].append(test_wr)
        elif "forex" in name:
            buckets["forex"].append(test_wr)
        elif "etf" in name:
            buckets["etf"].append(test_wr)
        elif "future" in name:
            buckets["futures"].append(test_wr)
        elif "commodity" in name:
            buckets["commodities"].append(test_wr)
        elif any(k in name for k in ("stock", "equity")):
            buckets["stocks"].append(test_wr)
        else:
            buckets["other"].append(test_wr)

    return {
        k: {
            "n_strategies": len(v),
            "avg_test_win_rate_pct": round(mean(v), 2) if v else 0.0,
            "pass_55pct_edge": bool(v and mean(v) >= 55.0),
        }
        for k, v in buckets.items()
    }


def _robust_edge_list(
    hypothesis_rows: List[HypothesisResult], strategy_payloads: Dict[str, Any]
) -> List[str]:
    out: List[str] = []
    for h in hypothesis_rows:
        strat = strategy_payloads.get(h.strategy, {})
        agg = strat.get("aggregate_oos", {})
        if (
            h.significant_5pct_bh
            and float(agg.get("win_rate", 0.0)) >= 55.0
            and float(agg.get("profit_factor", 0.0)) >= 1.5
            and float(agg.get("sharpe", 0.0)) > 0
            and int(agg.get("total_trades", 0)) >= 20
        ):
            out.append(h.strategy)
    return out


def _forex_walk_forward_extension(
    crypto_strategies: Dict[str, Any], forex_results_path: Path
) -> Optional[Dict[str, Any]]:
    """Secondary hypothesis tests + crypto vs forex OOS table (yfinance WF report)."""
    if not forex_results_path.exists():
        return None
    data = _load_json(forex_results_path)
    fs = data.get("strategies") or {}
    if not fs:
        return None
    rows, fisher_fx = _strategy_hypothesis_table(fs)
    robust_fx = _robust_edge_list(rows, fs)
    cmp: List[Dict[str, Any]] = []
    for name in sorted(set(crypto_strategies.keys()) & set(fs.keys())):
        c = (crypto_strategies.get(name) or {}).get("aggregate_oos") or {}
        f = (fs.get(name) or {}).get("aggregate_oos") or {}
        cmp.append(
            {
                "strategy": name,
                "crypto_oos_win_rate": c.get("win_rate"),
                "crypto_oos_trades": c.get("total_trades"),
                "crypto_oos_pf": c.get("profit_factor"),
                "forex_oos_win_rate": f.get("win_rate"),
                "forex_oos_trades": f.get("total_trades"),
                "forex_oos_pf": f.get("profit_factor"),
            }
        )
    return {
        "source_report_type": data.get("report_type"),
        "source_generated_at": data.get("generated_at"),
        "data_source": data.get("data_source"),
        "input_path": str(forex_results_path),
        "symbols": (data.get("parameters") or {}).get("symbols"),
        "fisher_combined_p_value": round(float(fisher_fx), 6),
        "multiple_testing_rows": [asdict(r) for r in rows],
        "significant_after_bh": [h.strategy for h in rows if h.significant_5pct_bh],
        "significant_after_bonferroni": [h.strategy for h in rows if h.significant_5pct_bonf],
        "robust_edge_candidates": robust_fx,
        "crypto_vs_forex_oos": cmp,
    }


def run_suite(
    strategy_results_path: Path,
    pair_results_path: Path,
    output_path: Path,
    n_bootstrap: int,
    forex_strategy_results_path: Optional[Path] = None,
) -> Dict[str, Any]:
    strategy_data = _load_json(strategy_results_path)
    strategy_results = strategy_data.get("strategies", {})
    pair_results = _load_json(pair_results_path)

    hypothesis_rows, fisher_p = _strategy_hypothesis_table(strategy_results)
    risk_block = _portfolio_risk_metrics_from_pairs(pair_results)
    holdout = _cross_asset_holdout(strategy_results)

    all_pair_returns: List[float] = []
    for payload in pair_results.values():
        all_pair_returns.extend(_build_trade_returns_from_pair_payload(payload))
    mc = MonteCarloSimulator(n_simulations=n_bootstrap, random_seed=42)
    mc_result = mc.bootstrap_returns(pd.Series(all_pair_returns), n_sims=n_bootstrap, use_block_bootstrap=True, strategy_type="multi_asset_trend")

    robust_after_bh = _robust_edge_list(hypothesis_rows, strategy_results)

    forex_block: Optional[Dict[str, Any]] = None
    if forex_strategy_results_path is not None:
        forex_block = _forex_walk_forward_extension(strategy_results, forex_strategy_results_path)

    report = {
        "generated_at": _now_iso(),
        "input_files": {
            "strategy_results": str(strategy_results_path),
            "pair_results": str(pair_results_path),
            "forex_strategy_results": str(forex_strategy_results_path)
            if forex_strategy_results_path and forex_strategy_results_path.exists()
            else None,
        },
        "industry_workflow_coverage": {
            "data_split_check": "in-sample / out-of-sample already present in source report",
            "walk_forward_check": "fold-based source metrics ingested",
            "multiple_hypothesis_correction": "BH + Bonferroni applied",
            "bootstrap_ci": "Monte Carlo bootstrap applied on aggregated trade returns",
            "pick_risk_metrics": "PoL / SL hit / R-multiple / VaR / CVaR computed",
            "cross_asset_holdout": "bucketed OOS pass/fail summary generated",
            "forex_walk_forward_merge": "optional yfinance WF report: BH/Bonf on FX + crypto vs forex OOS table",
        },
        "multiple_testing": {
            "strategies_evaluated": len(hypothesis_rows),
            "fisher_combined_p_value": round(float(fisher_p), 6),
            "significant_after_bh": [h.strategy for h in hypothesis_rows if h.significant_5pct_bh],
            "significant_after_bonferroni": [h.strategy for h in hypothesis_rows if h.significant_5pct_bonf],
            "rows": [asdict(r) for r in hypothesis_rows],
        },
        "robust_edge_candidates": robust_after_bh,
        "portfolio_risk": risk_block,
        "bootstrap": mc_result,
        "cross_asset_holdout": holdout,
        "forex_walk_forward": forex_block,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Run institutional backtest suite over existing reports.")
    parser.add_argument(
        "--strategy-results",
        default="alpha_engine/data/walk_forward_results.json",
        help="Path to strategy-level walk-forward report JSON",
    )
    parser.add_argument(
        "--pair-results",
        default="backtest_results/walk_forward_results.json",
        help="Path to pair-level walk-forward report JSON",
    )
    parser.add_argument(
        "--output",
        default="alpha_engine/data/institutional_backtest_report.json",
        help="Output report JSON path",
    )
    parser.add_argument("--bootstrap-sims", type=int, default=3000, help="Bootstrap simulation count")
    parser.add_argument(
        "--forex-results",
        default="alpha_engine/data/forex_walk_forward_results.json",
        help="Forex walk-forward JSON (yfinance); omitted from report if file missing",
    )
    args = parser.parse_args()

    _fx = Path(args.forex_results)
    report = run_suite(
        strategy_results_path=Path(args.strategy_results),
        pair_results_path=Path(args.pair_results),
        output_path=Path(args.output),
        n_bootstrap=args.bootstrap_sims,
        forex_strategy_results_path=_fx if _fx.exists() else None,
    )
    print("Institutional suite completed")
    print(f"Robust edge candidates after BH: {len(report.get('robust_edge_candidates', []))}")
    _fxb = report.get("forex_walk_forward") or {}
    _ov = _fxb.get("crypto_vs_forex_oos") or []
    if _ov:
        print(f"Forex WF merged: {len(_ov)} strategies with crypto+forex OOS rows")
    print(f"Output: {args.output}")


if __name__ == "__main__":
    main()

