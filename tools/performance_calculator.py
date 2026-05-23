#!/usr/bin/env python3
"""
Performance Calculator for KIMI Rise of the Claw.

Calculates trading metrics for dashboard display:
- Total return percentage
- Win rate from closed positions
- Sharpe ratio (risk-adjusted return)
- Maximum drawdown

Author: Claude Sonnet 4.5
Date: 2026-02-16
"""

import logging
from typing import List, Dict
import numpy as np
import pandas as pd
from datetime import datetime

logger = logging.getLogger(__name__)


class PerformanceCalculator:
    """Calculate trading metrics for live competition."""

    @staticmethod
    def calculate_total_return(starting_value: float, current_value: float) -> float:
        """
        Calculate total return percentage.

        Args:
            starting_value: Initial portfolio value
            current_value: Current portfolio value

        Returns:
            Return percentage (e.g., 15.5 for +15.5%)
        """
        if starting_value == 0:
            return 0.0

        return ((current_value - starting_value) / starting_value) * 100

    @staticmethod
    def calculate_win_rate(closed_positions: List[dict]) -> float:
        """
        Calculate win rate from closed positions.

        Args:
            closed_positions: List of closed position dicts with 'pl_percent' field

        Returns:
            Win rate percentage (0-100)
        """
        if not closed_positions:
            return 0.0

        wins = sum(1 for pos in closed_positions if pos.get('pl_percent', 0) > 0)
        total = len(closed_positions)

        return (wins / total) * 100 if total > 0 else 0.0

    @staticmethod
    def calculate_sharpe_ratio(daily_values: List[float], risk_free_rate: float = 0.0) -> float:
        """
        Calculate annualized Sharpe ratio from daily portfolio values.

        Sharpe Ratio = (Average Return - Risk Free Rate) / Std Dev of Returns
        Annualized by multiplying by sqrt(252) (trading days per year)

        Args:
            daily_values: List of daily portfolio values
            risk_free_rate: Annual risk-free rate (default 0.0)

        Returns:
            Annualized Sharpe ratio (rounded to 2 decimal places)
        """
        if len(daily_values) < 30:
            logger.debug(f"Not enough data for Sharpe ({len(daily_values)} days, need 30+)")
            return 0.0

        # Calculate daily returns
        series = pd.Series(daily_values)
        returns = series.pct_change().dropna()

        if len(returns) < 2:
            return 0.0

        # Calculate metrics
        avg_return = returns.mean()
        std_return = returns.std()

        if std_return == 0 or np.isnan(std_return):
            return 0.0

        # Daily risk-free rate (annual / 252)
        daily_rf = risk_free_rate / 252

        # Sharpe ratio
        sharpe = (avg_return - daily_rf) / std_return

        # Annualize by multiplying by sqrt(252)
        annualized_sharpe = sharpe * np.sqrt(252)

        return round(float(annualized_sharpe), 2)

    @staticmethod
    def calculate_max_drawdown(daily_values: List[float]) -> float:
        """
        Calculate maximum drawdown from peak.

        Max Drawdown = (Trough Value - Peak Value) / Peak Value
        Returns negative number (e.g., -12.5 for 12.5% drawdown)

        Args:
            daily_values: List of daily portfolio values

        Returns:
            Max drawdown percentage (negative number)
        """
        if len(daily_values) < 2:
            return 0.0

        series = pd.Series(daily_values)
        rolling_max = series.expanding().max()
        drawdown = (series - rolling_max) / rolling_max

        max_dd = drawdown.min()

        if np.isnan(max_dd):
            return 0.0

        return round(float(max_dd * 100), 2)

    @staticmethod
    def update_daily_values(algo_state: dict, current_value: float):
        """
        Update daily portfolio value history.

        Only records one value per day to prevent inflation from 15-min runs.

        Args:
            algo_state: Algorithm state dict (modified in-place)
            current_value: Current portfolio value
        """
        today = datetime.now().date().isoformat()

        # Initialize daily_values if not present
        if 'daily_values' not in algo_state:
            algo_state['daily_values'] = []

        daily_values = algo_state['daily_values']

        # Check if we already recorded today
        if daily_values and daily_values[-1]['date'] == today:
            # Update today's value
            daily_values[-1]['value'] = current_value
        else:
            # Add new day
            daily_values.append({
                'date': today,
                'value': current_value
            })

    @staticmethod
    def calculate_profit_factor(closed_positions: List[dict]) -> float:
        """
        Calculate profit factor (gross profit / gross loss).

        Args:
            closed_positions: List of closed position dicts with 'pl_value' field

        Returns:
            Profit factor (>1.0 is profitable)
        """
        if not closed_positions:
            return 0.0

        gross_profit = sum(pos['pl_value'] for pos in closed_positions if pos.get('pl_value', 0) > 0)
        gross_loss = abs(sum(pos['pl_value'] for pos in closed_positions if pos.get('pl_value', 0) < 0))

        if gross_loss == 0:
            return float('inf') if gross_profit > 0 else 0.0

        return gross_profit / gross_loss

    @staticmethod
    def calculate_expectancy(closed_positions: List[dict]) -> float:
        """
        Calculate expectancy (average $ per trade).

        Args:
            closed_positions: List of closed position dicts with 'pl_value' field

        Returns:
            Average P&L per trade in dollars
        """
        if not closed_positions:
            return 0.0

        total_pl = sum(pos.get('pl_value', 0) for pos in closed_positions)
        return total_pl / len(closed_positions)

    @staticmethod
    def get_performance_summary(
        starting_value: float,
        current_value: float,
        daily_values: List[float],
        closed_positions: List[dict]
    ) -> Dict:
        """
        Calculate all performance metrics at once.

        Args:
            starting_value: Initial portfolio value
            current_value: Current portfolio value
            daily_values: List of daily values
            closed_positions: List of closed positions

        Returns:
            Dict with all metrics
        """
        calc = PerformanceCalculator

        return {
            'totalReturn': calc.calculate_total_return(starting_value, current_value),
            'winRate': calc.calculate_win_rate(closed_positions),
            'sharpeRatio': calc.calculate_sharpe_ratio(daily_values),
            'maxDrawdown': calc.calculate_max_drawdown(daily_values),
            'profitFactor': calc.calculate_profit_factor(closed_positions),
            'expectancy': calc.calculate_expectancy(closed_positions),
            'totalTrades': len(closed_positions)
        }


if __name__ == '__main__':
    # Test the calculator
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    print("Testing Performance Calculator")
    print("=" * 60)

    calc = PerformanceCalculator()

    # Test total return
    print("\n[Total Return]")
    ret = calc.calculate_total_return(10000, 11500)
    print(f"  $10,000 -> $11,500 = +{ret:.2f}%")

    # Test win rate
    print("\n[Win Rate]")
    closed = [
        {'pl_percent': 5.0, 'pl_value': 50},
        {'pl_percent': -2.0, 'pl_value': -20},
        {'pl_percent': 8.0, 'pl_value': 80},
        {'pl_percent': -3.0, 'pl_value': -30},
        {'pl_percent': 12.0, 'pl_value': 120}
    ]
    win_rate = calc.calculate_win_rate(closed)
    print(f"  3 wins, 2 losses = {win_rate:.1f}% win rate")

    # Test Sharpe ratio
    print("\n[Sharpe Ratio]")
    # Simulate 60 days of portfolio values (growing with volatility)
    np.random.seed(42)
    daily_values = [10000]
    for i in range(59):
        change = np.random.normal(0.001, 0.01)  # 0.1% avg daily return, 1% std
        daily_values.append(daily_values[-1] * (1 + change))

    sharpe = calc.calculate_sharpe_ratio(daily_values)
    print(f"  60 days, {daily_values[0]:.0f} -> {daily_values[-1]:.0f} = Sharpe {sharpe}")

    # Test max drawdown
    print("\n[Max Drawdown]")
    # Simulate drawdown: grow, then drop, then recover
    dd_values = [10000, 10500, 11000, 10200, 9800, 10100, 10800, 11200]
    max_dd = calc.calculate_max_drawdown(dd_values)
    print(f"  Peak $11,000 -> Trough $9,800 = {max_dd:.2f}%")

    # Test profit factor
    print("\n[Profit Factor]")
    pf = calc.calculate_profit_factor(closed)
    print(f"  Gross profit $250 / Gross loss $50 = {pf:.2f}")

    # Test expectancy
    print("\n[Expectancy]")
    exp = calc.calculate_expectancy(closed)
    print(f"  Total P&L $200 / 5 trades = ${exp:.2f} per trade")

    # Test summary
    print("\n[Performance Summary]")
    summary = calc.get_performance_summary(10000, 11500, daily_values, closed)
    for metric, value in summary.items():
        if isinstance(value, float):
            print(f"  {metric}: {value:.2f}")
        else:
            print(f"  {metric}: {value}")

    print("\n" + "=" * 60)
    print("Test complete!")
