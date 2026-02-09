"""
Stress Testing

Test strategies against:
- Historical crisis periods
- Synthetic shocks
- Parameter sensitivity
- Slippage sensitivity
- Universe changes
"""
import logging
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from .metrics import PerformanceMetrics, StrategyMetrics

logger = logging.getLogger(__name__)


# Historical crisis periods (approximate dates)
CRISIS_PERIODS = {
    "covid_crash": ("2020-02-19", "2020-03-23"),
    "covid_recovery": ("2020-03-24", "2020-08-31"),
    "fed_tightening_2022": ("2022-01-01", "2022-10-12"),
    "svb_crisis": ("2023-03-08", "2023-03-20"),
    "vix_explosion_2018": ("2018-01-26", "2018-02-08"),
    "trade_war_2019": ("2019-05-01", "2019-06-03"),
    "q4_2018_selloff": ("2018-10-01", "2018-12-24"),
    "rate_shock_2023": ("2023-07-01", "2023-10-31"),
}

# Bull market periods
BULL_PERIODS = {
    "post_covid_bull": ("2020-04-01", "2021-12-31"),
    "ai_rally_2023": ("2023-01-01", "2023-07-31"),
    "bull_2017": ("2017-01-01", "2017-12-31"),
    "bull_2019": ("2019-06-04", "2020-02-18"),
}


class StressTester:
    """
    Stress test strategies against various scenarios.
    
    Tests the "3-Windows Rule": a real strategy must work across
    pre-2020, covid era, and post-2022 rate-shift periods.
    """

    def __init__(self):
        self.crisis_periods = CRISIS_PERIODS
        self.bull_periods = BULL_PERIODS

    def test_crisis_periods(
        self,
        returns: pd.Series,
        benchmark_returns: Optional[pd.Series] = None,
    ) -> Dict[str, Dict]:
        """
        Test strategy performance during known crisis periods.
        """
        results = {}

        for name, (start, end) in self.crisis_periods.items():
            try:
                mask = (returns.index >= start) & (returns.index <= end)
                period_returns = returns[mask]

                if len(period_returns) < 3:
                    continue

                bench = None
                if benchmark_returns is not None:
                    bench_mask = (benchmark_returns.index >= start) & (benchmark_returns.index <= end)
                    bench = benchmark_returns[bench_mask]

                metrics = PerformanceMetrics.compute_all(period_returns, bench)
                results[name] = {
                    "period": f"{start} to {end}",
                    "total_return": metrics.total_return,
                    "max_drawdown": metrics.max_drawdown,
                    "sharpe": metrics.sharpe_ratio,
                    "benchmark_return": metrics.benchmark_return if bench is not None else None,
                    "alpha": metrics.alpha if bench is not None else None,
                    "n_days": len(period_returns),
                }
            except Exception as e:
                logger.warning(f"Crisis test failed for {name}: {e}")

        return results

    def test_bull_periods(
        self,
        returns: pd.Series,
        benchmark_returns: Optional[pd.Series] = None,
    ) -> Dict[str, Dict]:
        """Test strategy performance during bull markets."""
        results = {}

        for name, (start, end) in self.bull_periods.items():
            try:
                mask = (returns.index >= start) & (returns.index <= end)
                period_returns = returns[mask]

                if len(period_returns) < 5:
                    continue

                bench = None
                if benchmark_returns is not None:
                    bench_mask = (benchmark_returns.index >= start) & (benchmark_returns.index <= end)
                    bench = benchmark_returns[bench_mask]

                metrics = PerformanceMetrics.compute_all(period_returns, bench)
                results[name] = {
                    "period": f"{start} to {end}",
                    "total_return": metrics.total_return,
                    "sharpe": metrics.sharpe_ratio,
                    "benchmark_return": metrics.benchmark_return if bench is not None else None,
                    "n_days": len(period_returns),
                }
            except Exception:
                pass

        return results

    def three_windows_test(
        self,
        returns: pd.Series,
        benchmark_returns: Optional[pd.Series] = None,
    ) -> Dict:
        """
        The "3-Windows Rule": test across three distinct market eras.
        If it only works in one era, it's not a strategy — it's a story.
        
        Windows:
        1. Pre-2020 (normal low-rate environment)
        2. 2020-2021 (covid + stimulus)
        3. 2022+ (rate hikes + inflation)
        """
        windows = {
            "pre_2020_normal": ("2015-01-01", "2019-12-31"),
            "covid_stimulus": ("2020-01-01", "2021-12-31"),
            "rate_hike_era": ("2022-01-01", "2025-12-31"),
        }

        results = {}
        sharpes = []

        for name, (start, end) in windows.items():
            mask = (returns.index >= start) & (returns.index <= end)
            window_returns = returns[mask]

            if len(window_returns) < 30:
                results[name] = {"status": "insufficient_data", "n_days": len(window_returns)}
                continue

            bench = None
            if benchmark_returns is not None:
                bench = benchmark_returns[(benchmark_returns.index >= start) & (benchmark_returns.index <= end)]

            metrics = PerformanceMetrics.compute_all(window_returns, bench)
            results[name] = {
                "total_return": metrics.total_return,
                "annual_return": metrics.annual_return,
                "sharpe": metrics.sharpe_ratio,
                "max_drawdown": metrics.max_drawdown,
                "n_days": len(window_returns),
            }
            sharpes.append(metrics.sharpe_ratio)

        # Assessment
        if len(sharpes) >= 2:
            all_positive = all(s > 0 for s in sharpes)
            min_sharpe = min(sharpes)
            max_sharpe = max(sharpes)
            consistency = min_sharpe / max_sharpe if max_sharpe > 0 else 0

            results["assessment"] = {
                "all_windows_positive": all_positive,
                "min_sharpe": min_sharpe,
                "max_sharpe": max_sharpe,
                "sharpe_consistency": consistency,
                "verdict": "PASS" if all_positive and min_sharpe > 0.3 else "FAIL",
            }

        return results

    def slippage_sensitivity(
        self,
        returns: pd.Series,
        slippage_levels_bps: List[int] = None,
        trades_per_year: int = 200,
    ) -> Dict:
        """
        Test how returns degrade with increasing slippage.
        Many "edges" vanish here.
        """
        if slippage_levels_bps is None:
            slippage_levels_bps = [0, 5, 10, 20, 50, 100]

        results = {}
        n_years = len(returns) / 252
        trades_total = trades_per_year * n_years

        for bps in slippage_levels_bps:
            # Approximate slippage drag as annual cost
            annual_slippage_cost = (bps / 10000) * 2 * trades_per_year  # 2x for round trip
            daily_drag = annual_slippage_cost / 252

            adjusted_returns = returns - daily_drag
            metrics = PerformanceMetrics.compute_all(adjusted_returns)

            results[f"{bps}bps"] = {
                "annual_return": metrics.annual_return,
                "sharpe": metrics.sharpe_ratio,
                "total_return": metrics.total_return,
                "annual_cost": annual_slippage_cost,
            }

        # Find breakeven slippage
        base_sharpe = results.get("0bps", {}).get("sharpe", 0)
        breakeven = None
        for bps in slippage_levels_bps:
            if results.get(f"{bps}bps", {}).get("sharpe", 1) <= 0:
                breakeven = bps
                break

        results["breakeven_slippage_bps"] = breakeven
        results["base_sharpe"] = base_sharpe

        return results

    def parameter_stability(
        self,
        returns_by_params: Dict[str, pd.Series],
    ) -> Dict:
        """
        Test if results are stable across parameter variations.
        If small parameter changes cause big performance swings → overfit.
        """
        sharpes = {}
        returns_vals = {}

        for param_name, ret in returns_by_params.items():
            metrics = PerformanceMetrics.compute_all(ret)
            sharpes[param_name] = metrics.sharpe_ratio
            returns_vals[param_name] = metrics.total_return

        sharpe_list = list(sharpes.values())
        return_list = list(returns_vals.values())

        return {
            "sharpes": sharpes,
            "returns": returns_vals,
            "sharpe_mean": np.mean(sharpe_list),
            "sharpe_std": np.std(sharpe_list),
            "sharpe_cv": np.std(sharpe_list) / np.mean(sharpe_list) if np.mean(sharpe_list) != 0 else float("inf"),
            "all_positive_sharpe": all(s > 0 for s in sharpe_list),
            "verdict": "STABLE" if np.std(sharpe_list) < 0.5 * abs(np.mean(sharpe_list)) else "UNSTABLE",
        }
