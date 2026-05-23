"""
ALPHA_ENGINE -- Meta-Ensemble with Sharpe-Weighted Blending
============================================================
When multiple strategies produce signals for the same symbol, this module
resolves conflicts by weighting each strategy's vote proportional to its
historical Sharpe ratio.

Implements v1.5 planned item: "Meta-ensemble with Sharpe-weighted blending"

How it works:
  1. Loads strategy performance from strategy_performance.json
  2. Computes a weight for each strategy based on its Sharpe ratio
  3. For overlapping signals (same symbol), blends confidence scores
  4. Strategies with negative Sharpe get near-zero weight (0.01)
  5. Outputs a single consensus signal per (symbol, direction) pair

Weight formula:
  w_i = max(sharpe_i, 0.01) / sum(max(sharpe_j, 0.01) for all j)

Usage:
  from meta_ensemble import MetaEnsembleBlender
  blender = MetaEnsembleBlender()
  blended = blender.blend(signals)
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from collections import defaultdict


def load_strategy_performance(data_dir: Optional[str | Path] = None) -> dict:
    """Load strategy performance data."""
    if data_dir is None:
        data_dir = Path(__file__).resolve().parent / "data"
    else:
        data_dir = Path(data_dir)

    try:
        perf_path = data_dir / "strategy_performance.json"
        if perf_path.exists():
            with open(perf_path) as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def load_monte_carlo_results(data_dir: Optional[str | Path] = None) -> dict:
    """Load Monte Carlo results for additional Sharpe data."""
    if data_dir is None:
        data_dir = Path(__file__).resolve().parent / "data"
    else:
        data_dir = Path(data_dir)

    try:
        mc_path = data_dir / "monte_carlo_results.json"
        if mc_path.exists():
            with open(mc_path) as f:
                mc_data = json.load(f)
            results = {}
            for name, info in mc_data.get("strategies", {}).items():
                results[name] = info
            for r in mc_data.get("strategy_rankings", []):
                name = r.get("strategy", "")
                if name and name not in results:
                    results[name] = r
            return results
    except Exception:
        pass
    return {}


class MetaEnsembleBlender:
    """
    Sharpe-weighted meta-ensemble for signal blending.

    Resolves conflicts when multiple strategies generate signals for the
    same symbol by weighting votes proportional to historical Sharpe ratio.
    """

    def __init__(
        self,
        data_dir: Optional[str | Path] = None,
        min_weight: float = 0.01,  # Floor weight for negative-Sharpe strategies
        min_trades: int = 5,       # Minimum trades for valid Sharpe
        default_sharpe: float = 0.0,  # Sharpe for unknown strategies
    ):
        self.data_dir = data_dir
        self.min_weight = min_weight
        self.min_trades = min_trades
        self.default_sharpe = default_sharpe

        # Load performance data
        self._perf = load_strategy_performance(data_dir)
        self._mc = load_monte_carlo_results(data_dir)

    def get_strategy_sharpe(self, strategy_name: str) -> float:
        """
        Look up Sharpe ratio for a strategy from multiple sources.

        Priority: strategy_performance.json > monte_carlo_results.json > default
        """
        # Check strategy_performance
        if strategy_name in self._perf:
            sp = self._perf[strategy_name]
            trades = sp.get("closed_picks", 0) or 0
            if trades >= self.min_trades:
                sharpe = sp.get("sharpe", None)
                if sharpe is not None:
                    return float(sharpe)

                # Compute from win_rate and profit_factor if Sharpe not available
                wr = sp.get("win_rate", 0) or 0
                pf = sp.get("profit_factor", 0) or 0
                if wr > 0 and pf > 0:
                    # Rough Sharpe proxy from PF: Sharpe ≈ (PF - 1) * sqrt(trades) / 2
                    return (pf - 1) * math.sqrt(min(trades, 100)) / 2

        # Check Monte Carlo results
        if strategy_name in self._mc:
            mc = self._mc[strategy_name]
            sharpe = mc.get("sharpe", None)
            if sharpe is not None:
                return float(sharpe)

        return self.default_sharpe

    def compute_weights(self, strategy_names: List[str]) -> Dict[str, float]:
        """
        Compute Sharpe-weighted allocation for a set of strategies.

        Returns normalized weights summing to 1.0.
        Negative-Sharpe strategies get min_weight floor.
        """
        if not strategy_names:
            return {}

        raw_weights = {}
        for name in strategy_names:
            sharpe = self.get_strategy_sharpe(name)
            # Floor at min_weight to prevent zero-weight (still allows signal)
            raw_weights[name] = max(sharpe, self.min_weight)

        total = sum(raw_weights.values())
        if total <= 0:
            # All strategies have zero/negative Sharpe -- equal weight
            equal = 1.0 / len(strategy_names)
            return {name: equal for name in strategy_names}

        return {name: w / total for name, w in raw_weights.items()}

    def blend(self, signals: List[Dict]) -> List[Dict]:
        """
        Blend overlapping signals using Sharpe-weighted voting.

        Groups signals by (symbol, direction), then for each group:
        1. Compute Sharpe weights for contributing strategies
        2. Blend confidence as weighted average
        3. Use the best entry/TP/SL from the highest-weighted strategy
        4. Return one signal per (symbol, direction)

        Parameters
        ----------
        signals : list[dict]
            Each dict should have: symbol, direction, strategy, confidence,
            entry_price, take_profit, stop_loss, reason

        Returns
        -------
        list[dict] : Blended signals (one per symbol-direction pair)
        """
        if not signals:
            return []

        # Group by (symbol, direction)
        groups: Dict[Tuple[str, str], List[Dict]] = defaultdict(list)
        for sig in signals:
            key = (sig.get("symbol", ""), sig.get("direction", ""))
            groups[key].append(sig)

        blended = []
        for (symbol, direction), group_sigs in groups.items():
            if len(group_sigs) == 1:
                # Single strategy -- pass through with weight info
                sig = dict(group_sigs[0])
                strat = sig.get("strategy", "unknown")
                sig["ensemble_weight"] = 1.0
                sig["ensemble_strategies"] = [strat]
                sig["ensemble_count"] = 1
                blended.append(sig)
                continue

            # Multiple strategies -- blend
            strategy_names = [s.get("strategy", f"unknown_{i}") for i, s in enumerate(group_sigs)]
            weights = self.compute_weights(strategy_names)

            # Weighted confidence
            total_weight = sum(weights.get(s.get("strategy", f"unknown_{i}"), self.min_weight)
                               for i, s in enumerate(group_sigs))
            if total_weight == 0:
                total_weight = 1.0

            blended_confidence = sum(
                float(s.get("confidence", 0.5)) * weights.get(s.get("strategy", f"unknown_{i}"), self.min_weight)
                for i, s in enumerate(group_sigs)
            ) / total_weight

            # Use entry/TP/SL from the highest-weighted strategy
            best_idx = max(
                range(len(group_sigs)),
                key=lambda i: weights.get(group_sigs[i].get("strategy", f"unknown_{i}"), 0),
            )
            best_sig = group_sigs[best_idx]

            reasons = [s.get("reason", "") for s in group_sigs if s.get("reason")]
            weight_details = ", ".join(
                f"{s.get('strategy', '?')}={weights.get(s.get('strategy', f'unknown_{i}'), 0):.2f}"
                for i, s in enumerate(group_sigs)
            )

            out = {
                "symbol": symbol,
                "direction": direction,
                "confidence": round(min(blended_confidence, 0.95), 3),
                "entry_price": best_sig.get("entry_price", 0),
                "take_profit": best_sig.get("take_profit", 0),
                "stop_loss": best_sig.get("stop_loss", 0),
                "strategy": f"meta_ensemble({len(group_sigs)})",
                "reason": (
                    f"Meta-Ensemble: {len(group_sigs)} strategies agree on {direction} {symbol}. "
                    f"Sharpe weights: [{weight_details}]. "
                    f"Blended confidence: {blended_confidence:.1%}"
                ),
                "ensemble_weight": round(max(weights.values()), 3),
                "ensemble_strategies": strategy_names,
                "ensemble_count": len(group_sigs),
                "ensemble_weights": {k: round(v, 4) for k, v in weights.items()},
            }
            blended.append(out)

        return blended

    def get_strategy_report(self) -> Dict:
        """Generate a report of all known strategies with their Sharpe and weight."""
        all_strats = set(list(self._perf.keys()) + list(self._mc.keys()))
        if not all_strats:
            return {"strategies": [], "note": "no performance data loaded"}

        weights = self.compute_weights(list(all_strats))
        report = []
        for name in sorted(all_strats, key=lambda n: self.get_strategy_sharpe(n), reverse=True):
            sharpe = self.get_strategy_sharpe(name)
            trades = 0
            if name in self._perf:
                trades = self._perf[name].get("closed_picks", 0) or 0

            report.append({
                "strategy": name,
                "sharpe": round(sharpe, 3),
                "trades": trades,
                "weight": round(weights.get(name, 0), 4),
            })

        return {"strategies": report, "total": len(report)}


# -- CLI Test ------------------------------------------------------

if __name__ == "__main__":
    print("=== Meta-Ensemble Blender Tests ===\n")

    blender = MetaEnsembleBlender()

    # Print strategy report
    report = blender.get_strategy_report()
    print(f"  Known strategies: {report['total']}")
    if report.get("strategies"):
        for s in report["strategies"][:5]:
            print(f"    {s['strategy']}: Sharpe={s['sharpe']}, weight={s['weight']:.4f}, trades={s['trades']}")
        if report["total"] > 5:
            print(f"    ...+{report['total'] - 5} more")

    # Test blending
    test_signals = [
        {
            "symbol": "BTCUSDT", "direction": "BUY", "strategy": "ema_stack",
            "confidence": 0.75, "entry_price": 50000, "take_profit": 52000,
            "stop_loss": 49000, "reason": "EMA aligned",
        },
        {
            "symbol": "BTCUSDT", "direction": "BUY", "strategy": "connors_rsi2",
            "confidence": 0.82, "entry_price": 50100, "take_profit": 52500,
            "stop_loss": 48800, "reason": "RSI(2) oversold bounce",
        },
        {
            "symbol": "BTCUSDT", "direction": "SELL", "strategy": "vix_spike_reversal",
            "confidence": 0.60, "entry_price": 50000, "take_profit": 48000,
            "stop_loss": 51000, "reason": "VIX spike",
        },
        {
            "symbol": "ETHUSDT", "direction": "BUY", "strategy": "keltner_rsi_confluence",
            "confidence": 0.70, "entry_price": 3000, "take_profit": 3200,
            "stop_loss": 2900, "reason": "Keltner breakout",
        },
    ]

    blended = blender.blend(test_signals)
    print(f"\n  Blended {len(test_signals)} signals → {len(blended)} consensus signals")
    for sig in blended:
        print(f"    {sig['direction']} {sig['symbol']}: conf={sig['confidence']}, "
              f"n={sig['ensemble_count']}, strategy={sig['strategy']}")

    # Test empty
    assert blender.blend([]) == []

    # Test single signal passthrough
    single = blender.blend([test_signals[0]])
    assert len(single) == 1
    assert single[0]["ensemble_count"] == 1

    print("\n[OK] All self-tests passed!")
