"""
Monte Carlo Simulation for Strategy Validation

Validates whether Alpha Engine strategy results are statistically significant
or could be attributed to random chance. Uses permutation-based Monte Carlo
to build null distributions and compute p-values.

Usage:
    python -m alpha_engine.monte_carlo
"""

import json
import os
import time
from collections import defaultdict

import numpy as np


class MonteCarloValidator:
    """
    Permutation-based Monte Carlo validator for trading strategies.

    Shuffles the actual PnL sequence N times to build a null distribution,
    then checks whether actual results are statistically distinguishable
    from random ordering.
    """

    def __init__(self, n_simulations=10000, confidence_level=0.95):
        self.n_simulations = n_simulations
        self.confidence_level = confidence_level
        self._rng = np.random.default_rng(seed=42)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def validate_strategy(self, closed_picks, strategy_name=None):
        """
        Run Monte Carlo on a strategy's closed picks.

        Args:
            closed_picks: list of pick dicts from closed_picks.json
            strategy_name: if provided, filter to this strategy only

        Returns:
            dict with validation results (fully JSON-serializable)
        """
        if strategy_name:
            picks = [p for p in closed_picks if p.get("strategy") == strategy_name]
        else:
            picks = list(closed_picks)

        n_trades = len(picks)
        label = strategy_name or "portfolio"

        # Edge case: insufficient data
        if n_trades < 5:
            return self._insufficient_data_result(label, n_trades)

        pnl_sequence = np.array(
            [float(p.get("pnl_pct", 0.0)) for p in picks], dtype=np.float64
        )

        actual = self._compute_metrics(pnl_sequence)
        sim_results = self._run_simulations(pnl_sequence)

        mc_stats = self._compute_mc_statistics(actual, sim_results)
        ci = self._compute_confidence_intervals(sim_results)
        verdict = self._determine_verdict(mc_stats["p_value"], n_trades)

        return self._to_serializable({
            "strategy": label,
            "n_trades": n_trades,
            "n_simulations": self.n_simulations,
            "actual": actual,
            "monte_carlo": mc_stats,
            "confidence_intervals": ci,
            "verdict": verdict,
        })

    def validate_all_strategies(self, closed_picks):
        """
        Run Monte Carlo on each strategy separately plus the combined portfolio.

        Returns:
            dict with per-strategy results, portfolio result, and rankings
        """
        # Group picks by strategy
        by_strategy = defaultdict(list)
        for p in closed_picks:
            by_strategy[p.get("strategy", "unknown")].append(p)

        results = {}
        for strat_name in sorted(by_strategy.keys()):
            results[strat_name] = self.validate_strategy(
                by_strategy[strat_name], strategy_name=None
            )
            # Override label since we passed pre-filtered picks without strategy_name
            results[strat_name]["strategy"] = strat_name

        # Combined portfolio
        portfolio = self.validate_strategy(closed_picks, strategy_name=None)
        portfolio["strategy"] = "PORTFOLIO"

        # Rankings by p-value (lowest = most proven)
        rankings = []
        for name, res in results.items():
            rankings.append({
                "strategy": name,
                "n_trades": res["n_trades"],
                "p_value": res["monte_carlo"]["p_value"],
                "verdict": res["verdict"],
                "total_pnl_pct": res["actual"]["total_pnl_pct"],
                "win_rate": res["actual"]["win_rate"],
                "sharpe": res["actual"]["sharpe"],
            })
        rankings.sort(key=lambda x: (x["p_value"], -x["n_trades"]))

        return self._to_serializable({
            "strategies": results,
            "portfolio": portfolio,
            "strategy_rankings": rankings,
            "total_strategies": len(results),
            "proven_count": sum(1 for r in rankings if r["verdict"] == "PROVEN"),
            "likely_valid_count": sum(
                1 for r in rankings if r["verdict"] == "LIKELY_VALID"
            ),
        })

    def generate_report(self, results):
        """Generate human-readable validation report from validate_all_strategies output."""
        lines = []
        lines.append("=" * 72)
        lines.append("MONTE CARLO STRATEGY VALIDATION REPORT")
        lines.append("=" * 72)
        lines.append(
            f"Simulations per strategy: {self.n_simulations:,}"
        )
        lines.append(
            f"Total strategies analyzed: {results.get('total_strategies', 0)}"
        )
        lines.append(
            f"Proven (p<0.01, n>=30): {results.get('proven_count', 0)}"
        )
        lines.append(
            f"Likely Valid (p<0.05, n>=15): {results.get('likely_valid_count', 0)}"
        )
        lines.append("")

        # Portfolio summary
        pf = results.get("portfolio", {})
        if pf:
            lines.append("-" * 72)
            lines.append("PORTFOLIO (ALL STRATEGIES COMBINED)")
            lines.append("-" * 72)
            lines.extend(self._format_single_result(pf))
            lines.append("")

        # Strategy rankings
        rankings = results.get("strategy_rankings", [])
        if rankings:
            lines.append("-" * 72)
            lines.append("STRATEGY RANKINGS (by p-value, lowest = most proven)")
            lines.append("-" * 72)
            lines.append(
                f"{'Rank':<5} {'Strategy':<35} {'Trades':<7} "
                f"{'p-value':<9} {'WR%':<7} {'PnL%':<9} {'Verdict'}"
            )
            lines.append("-" * 95)
            for i, r in enumerate(rankings, 1):
                lines.append(
                    f"{i:<5} {r['strategy']:<35} {r['n_trades']:<7} "
                    f"{r['p_value']:<9.4f} "
                    f"{r['win_rate'] * 100:<7.1f} "
                    f"{r['total_pnl_pct'] * 100:<9.2f} "
                    f"{r['verdict']}"
                )
            lines.append("")

        # Detailed per-strategy results (only non-insufficient)
        strategies = results.get("strategies", {})
        detailed = {
            k: v
            for k, v in strategies.items()
            if v.get("verdict") != "INSUFFICIENT_DATA"
        }
        if detailed:
            lines.append("=" * 72)
            lines.append("DETAILED STRATEGY RESULTS")
            lines.append("=" * 72)
            for name in sorted(detailed.keys()):
                res = detailed[name]
                lines.append("")
                lines.append(f"--- {name} ---")
                lines.extend(self._format_single_result(res))

        lines.append("")
        lines.append("=" * 72)
        lines.append("END OF REPORT")
        lines.append("=" * 72)

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Core simulation engine
    # ------------------------------------------------------------------

    def _run_simulations(self, pnl_sequence):
        """
        Run N permutation simulations of the PnL sequence.

        Returns dict of arrays, each of length n_simulations.
        """
        n = len(pnl_sequence)
        n_sims = self.n_simulations

        # Pre-allocate result arrays
        final_equities = np.empty(n_sims, dtype=np.float64)
        max_drawdowns = np.empty(n_sims, dtype=np.float64)
        win_rates = np.empty(n_sims, dtype=np.float64)
        sharpes = np.empty(n_sims, dtype=np.float64)

        # Generate all shuffled indices at once for speed
        # Each row is a permutation of [0, n)
        for i in range(n_sims):
            shuffled = self._rng.permutation(pnl_sequence)

            # Cumulative equity curve (compounding returns)
            cum_equity = np.cumprod(1.0 + shuffled)
            final_equities[i] = cum_equity[-1] - 1.0  # total return

            # Max drawdown
            running_max = np.maximum.accumulate(cum_equity)
            drawdowns = (running_max - cum_equity) / running_max
            max_drawdowns[i] = np.max(drawdowns)

            # Win rate
            win_rates[i] = np.mean(shuffled > 0)

            # Sharpe (annualized assuming daily-ish trades)
            if np.std(shuffled) > 1e-12:
                sharpes[i] = (np.mean(shuffled) / np.std(shuffled)) * np.sqrt(
                    min(n, 252)
                )
            else:
                sharpes[i] = 0.0

        return {
            "final_equities": final_equities,
            "max_drawdowns": max_drawdowns,
            "win_rates": win_rates,
            "sharpes": sharpes,
        }

    def _compute_metrics(self, pnl_sequence):
        """Compute actual performance metrics from PnL sequence."""
        n = len(pnl_sequence)

        # Total PnL (compounding)
        cum_equity = np.cumprod(1.0 + pnl_sequence)
        total_pnl = cum_equity[-1] - 1.0

        # Win rate
        win_rate = float(np.mean(pnl_sequence > 0))

        # Max drawdown
        running_max = np.maximum.accumulate(cum_equity)
        drawdowns = (running_max - cum_equity) / running_max
        max_dd = float(np.max(drawdowns)) if len(drawdowns) > 0 else 0.0

        # Sharpe ratio
        if np.std(pnl_sequence) > 1e-12:
            sharpe = float(
                (np.mean(pnl_sequence) / np.std(pnl_sequence))
                * np.sqrt(min(n, 252))
            )
        else:
            sharpe = 0.0

        # Profit factor
        gross_profit = float(np.sum(pnl_sequence[pnl_sequence > 0]))
        gross_loss = float(np.abs(np.sum(pnl_sequence[pnl_sequence < 0])))
        if gross_loss > 1e-12:
            profit_factor = gross_profit / gross_loss
        else:
            profit_factor = float("inf") if gross_profit > 0 else 0.0

        return {
            "total_pnl_pct": float(total_pnl),
            "win_rate": win_rate,
            "max_drawdown_pct": max_dd,
            "sharpe": sharpe,
            "profit_factor": float(profit_factor),
        }

    def _compute_mc_statistics(self, actual, sim_results):
        """Compute Monte Carlo statistics and p-value."""
        sim_pnl = sim_results["final_equities"]
        sim_dd = sim_results["max_drawdowns"]

        # p-value: fraction of simulations that achieved >= actual PnL
        # Lower p-value means actual result is less likely due to chance
        p_value = float(np.mean(sim_pnl >= actual["total_pnl_pct"]))

        return {
            "pnl_mean": float(np.mean(sim_pnl)),
            "pnl_std": float(np.std(sim_pnl)),
            "pnl_5th": float(np.percentile(sim_pnl, 5)),
            "pnl_95th": float(np.percentile(sim_pnl, 95)),
            "dd_mean": float(np.mean(sim_dd)),
            "dd_95th": float(np.percentile(sim_dd, 95)),
            "p_value": p_value,
            "is_significant": p_value < 0.05,
        }

    def _compute_confidence_intervals(self, sim_results):
        """Compute 95% confidence intervals from simulation distributions."""
        return {
            "pnl_95ci": (
                float(np.percentile(sim_results["final_equities"], 2.5)),
                float(np.percentile(sim_results["final_equities"], 97.5)),
            ),
            "wr_95ci": (
                float(np.percentile(sim_results["win_rates"], 2.5)),
                float(np.percentile(sim_results["win_rates"], 97.5)),
            ),
            "dd_95ci": (
                float(np.percentile(sim_results["max_drawdowns"], 2.5)),
                float(np.percentile(sim_results["max_drawdowns"], 97.5)),
            ),
        }

    # ------------------------------------------------------------------
    # Verdict and formatting helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _determine_verdict(p_value, n_trades):
        """Determine statistical verdict based on p-value and sample size."""
        if n_trades < 5:
            return "INSUFFICIENT_DATA"
        if p_value < 0.01 and n_trades >= 30:
            return "PROVEN"
        if p_value < 0.05 and n_trades >= 15:
            return "LIKELY_VALID"
        if p_value < 0.10 or n_trades < 15:
            return "INCONCLUSIVE"
        return "LIKELY_RANDOM"

    @staticmethod
    def _insufficient_data_result(label, n_trades):
        """Return a minimal result for strategies with <5 trades."""
        return {
            "strategy": label,
            "n_trades": n_trades,
            "n_simulations": 0,
            "actual": {
                "total_pnl_pct": 0.0,
                "win_rate": 0.0,
                "max_drawdown_pct": 0.0,
                "sharpe": 0.0,
                "profit_factor": 0.0,
            },
            "monte_carlo": {
                "pnl_mean": 0.0,
                "pnl_std": 0.0,
                "pnl_5th": 0.0,
                "pnl_95th": 0.0,
                "dd_mean": 0.0,
                "dd_95th": 0.0,
                "p_value": 1.0,
                "is_significant": False,
            },
            "confidence_intervals": {
                "pnl_95ci": (0.0, 0.0),
                "wr_95ci": (0.0, 0.0),
                "dd_95ci": (0.0, 0.0),
            },
            "verdict": "INSUFFICIENT_DATA",
        }

    def _format_single_result(self, result):
        """Format a single strategy result for the text report."""
        lines = []
        act = result.get("actual", {})
        mc = result.get("monte_carlo", {})
        ci = result.get("confidence_intervals", {})

        lines.append(f"  Trades: {result.get('n_trades', 0)}")
        lines.append(f"  Verdict: {result.get('verdict', 'N/A')}")
        lines.append("")
        lines.append("  Actual Performance:")
        lines.append(f"    Total PnL:      {act.get('total_pnl_pct', 0) * 100:+.2f}%")
        lines.append(f"    Win Rate:       {act.get('win_rate', 0) * 100:.1f}%")
        lines.append(
            f"    Max Drawdown:   {act.get('max_drawdown_pct', 0) * 100:.2f}%"
        )
        lines.append(f"    Sharpe Ratio:   {act.get('sharpe', 0):.3f}")
        pf = act.get("profit_factor", 0)
        pf_str = f"{pf:.2f}" if pf != float("inf") else "INF"
        lines.append(f"    Profit Factor:  {pf_str}")
        lines.append("")
        lines.append("  Monte Carlo Distribution:")
        lines.append(
            f"    PnL Mean:       {mc.get('pnl_mean', 0) * 100:+.2f}% "
            f"(std: {mc.get('pnl_std', 0) * 100:.2f}%)"
        )
        lines.append(
            f"    PnL 5th-95th:   [{mc.get('pnl_5th', 0) * 100:+.2f}%, "
            f"{mc.get('pnl_95th', 0) * 100:+.2f}%]"
        )
        lines.append(
            f"    DD Mean:        {mc.get('dd_mean', 0) * 100:.2f}% "
            f"(95th worst: {mc.get('dd_95th', 0) * 100:.2f}%)"
        )
        lines.append(f"    p-value:        {mc.get('p_value', 1.0):.4f}")
        lines.append(
            f"    Significant:    {'YES' if mc.get('is_significant') else 'NO'}"
        )
        lines.append("")
        lines.append("  95% Confidence Intervals:")
        pnl_ci = ci.get("pnl_95ci", (0, 0))
        wr_ci = ci.get("wr_95ci", (0, 0))
        dd_ci = ci.get("dd_95ci", (0, 0))
        lines.append(
            f"    PnL:  [{pnl_ci[0] * 100:+.2f}%, {pnl_ci[1] * 100:+.2f}%]"
        )
        lines.append(
            f"    WR:   [{wr_ci[0] * 100:.1f}%, {wr_ci[1] * 100:.1f}%]"
        )
        lines.append(
            f"    DD:   [{dd_ci[0] * 100:.2f}%, {dd_ci[1] * 100:.2f}%]"
        )

        return lines

    @staticmethod
    def _to_serializable(obj):
        """Recursively convert numpy types to native Python for JSON serialization."""
        if isinstance(obj, dict):
            return {k: MonteCarloValidator._to_serializable(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [MonteCarloValidator._to_serializable(v) for v in obj]
        if isinstance(obj, tuple):
            return tuple(MonteCarloValidator._to_serializable(v) for v in obj)
        if isinstance(obj, (np.integer,)):
            return int(obj)
        if isinstance(obj, (np.floating,)):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, (np.bool_,)):
            return bool(obj)
        return obj


# ----------------------------------------------------------------------
# Standalone runner
# ----------------------------------------------------------------------


def run_monte_carlo_report():
    """Load closed_picks.json and print Monte Carlo report for all strategies."""
    data_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "data", "closed_picks.json"
    )

    if not os.path.exists(data_path):
        print(f"ERROR: closed_picks.json not found at {data_path}")
        return

    with open(data_path, "r", encoding="utf-8") as f:
        closed_picks = json.load(f)

    if not closed_picks:
        print("No closed picks found. Nothing to validate.")
        return

    print(f"Loaded {len(closed_picks)} closed picks.")

    validator = MonteCarloValidator(n_simulations=10000, confidence_level=0.95)

    start = time.time()
    results = validator.validate_all_strategies(closed_picks)
    elapsed = time.time() - start

    report = validator.generate_report(results)
    print(report)
    print(f"\nCompleted in {elapsed:.2f}s")

    # Also save JSON results
    out_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "data",
        "monte_carlo_results.json",
    )
    # Convert tuples in confidence_intervals to lists for JSON
    serializable = _convert_tuples(results)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(serializable, f, indent=2, default=str)

    print(f"Results saved to {out_path}")


def _convert_tuples(obj):
    """Recursively convert tuples to lists for JSON serialization."""
    if isinstance(obj, dict):
        return {k: _convert_tuples(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_convert_tuples(v) for v in obj]
    return obj


if __name__ == "__main__":
    run_monte_carlo_report()
