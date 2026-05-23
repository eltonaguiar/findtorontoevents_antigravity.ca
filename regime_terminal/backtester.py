"""
Regime-Aware Walk-Forward Backtester.

Implements the RenTech-inspired approach:
  1. Train HMM on N days of history
  2. Predict regime on next M days (out-of-sample)
  3. Slide window forward and repeat
  4. Only enter positions when regime is confirmed (hysteresis)
  5. Position sizing scaled by regime confidence × leverage map
  6. Includes realistic transaction costs and slippage

This is NOT curve-fitting — walk-forward ensures every trade decision
is made on data the model hasn't seen.
"""

import numpy as np
import pandas as pd
from datetime import datetime

from . import config
from .hmm_engine import RegimeDetector


class RegimeBacktester:
    """Walk-forward backtester with regime-based position sizing."""

    def __init__(
        self,
        train_window=None,
        test_window=None,
        transaction_cost_bps=None,
        slippage_bps=None,
    ):
        self.train_window = train_window or config.TRAIN_WINDOW_DAYS
        self.test_window = test_window or config.TEST_WINDOW_DAYS
        self.tx_cost = (transaction_cost_bps or config.TRANSACTION_COST_BPS) / 10000
        self.slippage = (slippage_bps or config.SLIPPAGE_BPS) / 10000

    def walk_forward(self, df, ticker="UNKNOWN"):
        """
        Run walk-forward backtest on a single ticker.

        Process:
          1. For each window: train HMM on [t, t+train), test on [t+train, t+train+test)
          2. During test window: hold position based on predicted regime
          3. Account for costs on every position change

        Returns:
            Dict with trades, metrics, and equity curve.
        """
        n = len(df)
        min_required = self.train_window + self.test_window + 30  # 30 bar warmup
        if n < min_required:
            return {
                "ticker": ticker,
                "error": f"Insufficient data: {n} bars, need {min_required}",
                "trades": [],
                "metrics": {},
            }

        all_trades = []
        equity = [10000.0]  # Start with $10,000
        positions = []  # Track position changes
        current_position = 0.0  # Current leverage (0 = flat)

        # Walk forward
        step = 0
        for start in range(0, n - self.train_window - self.test_window, self.test_window):
            step += 1
            train_end = start + self.train_window
            test_end = min(train_end + self.test_window, n)

            train_df = df.iloc[start:train_end]
            test_df = df.iloc[train_end:test_end]

            if len(test_df) < 5:
                continue

            # Train HMM on training window
            try:
                detector = RegimeDetector()
                detector.fit(train_df)
            except Exception as e:
                continue

            # Predict regimes on test window
            try:
                # Need some history for feature calculation
                lookback = min(30, start)
                test_with_context = df.iloc[train_end - lookback:test_end]
                predictions = detector.predict(test_with_context)
                # Take only the test period predictions
                predictions = predictions[-len(test_df):]
            except Exception:
                continue

            # Trade the test window
            for i in range(1, len(test_df)):
                if i >= len(predictions):
                    break

                regime = predictions[i]["regime"]
                confidence = predictions[i]["confidence"]

                # Check hysteresis (need MIN_REGIME_BARS consistent predictions)
                if i >= config.MIN_REGIME_BARS:
                    recent_regimes = [predictions[j]["regime"]
                                      for j in range(i - config.MIN_REGIME_BARS + 1, i + 1)]
                    regime_stable = all(r == regime for r in recent_regimes)
                else:
                    regime_stable = False

                # Determine target position
                if regime_stable:
                    target_leverage = config.LEVERAGE_MAP.get(regime, 0.0)
                    # Scale by confidence
                    target_position = target_leverage * min(confidence, 1.0)
                else:
                    target_position = 0.0  # Flat until regime confirmed

                # Calculate daily return
                price_today = float(test_df["Close"].iloc[i])
                price_yesterday = float(test_df["Close"].iloc[i - 1])
                daily_return = (price_today / price_yesterday) - 1.0

                # Apply position and costs
                strategy_return = current_position * daily_return

                # Transaction cost on position change
                position_change = abs(target_position - current_position)
                if position_change > 0.01:  # Meaningful change
                    cost = position_change * (self.tx_cost + self.slippage)
                    strategy_return -= cost

                    all_trades.append({
                        "step": step,
                        "date": str(test_df.index[i]),
                        "regime": regime,
                        "confidence": round(confidence, 3),
                        "regime_stable": regime_stable,
                        "old_position": round(current_position, 3),
                        "new_position": round(target_position, 3),
                        "daily_return": round(daily_return * 100, 4),
                        "strategy_return": round(strategy_return * 100, 4),
                        "cost_bps": round(cost * 10000, 1),
                    })

                current_position = target_position

                # Update equity
                new_equity = equity[-1] * (1 + strategy_return)
                equity.append(new_equity)

        # Calculate performance metrics
        metrics = self._calculate_metrics(equity, all_trades, df, ticker)

        return {
            "ticker": ticker,
            "trades": all_trades,
            "metrics": metrics,
            "equity_curve": [round(e, 2) for e in equity],
            "final_equity": round(equity[-1], 2),
            "total_return_pct": round((equity[-1] / equity[0] - 1) * 100, 2),
        }

    def _calculate_metrics(self, equity, trades, df, ticker):
        """Calculate comprehensive performance metrics."""
        equity_arr = np.array(equity)
        returns = np.diff(equity_arr) / equity_arr[:-1]

        if len(returns) == 0:
            return {"error": "No returns to analyze"}

        # Buy-and-hold comparison
        close = df["Close"].astype(float)
        bh_return = (close.iloc[-1] / close.iloc[0] - 1) * 100

        # Strategy total return
        total_return = (equity_arr[-1] / equity_arr[0] - 1) * 100

        # Alpha = strategy - buy_and_hold (simplified)
        alpha = total_return - bh_return

        # Sharpe ratio (annualized, assuming daily)
        daily_mean = np.mean(returns)
        daily_std = np.std(returns)
        sharpe = (daily_mean / daily_std * np.sqrt(252)) if daily_std > 0 else 0

        # Sortino ratio (downside deviation only)
        downside = returns[returns < 0]
        downside_std = np.std(downside) if len(downside) > 0 else 0.001
        sortino = (daily_mean / downside_std * np.sqrt(252)) if downside_std > 0 else 0

        # Maximum drawdown
        peak = np.maximum.accumulate(equity_arr)
        drawdown = (equity_arr - peak) / peak
        max_drawdown = float(np.min(drawdown) * 100)

        # Calmar ratio
        years = len(returns) / 252
        annual_return = ((equity_arr[-1] / equity_arr[0]) ** (1 / max(years, 0.1)) - 1) * 100
        calmar = annual_return / abs(max_drawdown) if max_drawdown != 0 else 0

        # Win rate (only counting actual position changes)
        winning_trades = [t for t in trades if t["strategy_return"] > 0]
        losing_trades = [t for t in trades if t["strategy_return"] < 0]
        total_trades = len(trades)
        win_rate = (len(winning_trades) / total_trades * 100) if total_trades > 0 else 0

        # Profit factor
        gross_profit = sum(t["strategy_return"] for t in winning_trades)
        gross_loss = abs(sum(t["strategy_return"] for t in losing_trades))
        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else float("inf")

        # Regime distribution in trades
        regime_dist = {}
        for t in trades:
            r = t["regime"]
            regime_dist[r] = regime_dist.get(r, 0) + 1

        return {
            "total_return_pct": round(total_return, 2),
            "buy_and_hold_pct": round(bh_return, 2),
            "alpha_pct": round(alpha, 2),
            "sharpe_ratio": round(sharpe, 3),
            "sortino_ratio": round(sortino, 3),
            "calmar_ratio": round(calmar, 3),
            "max_drawdown_pct": round(max_drawdown, 2),
            "annual_return_pct": round(annual_return, 2),
            "total_trades": total_trades,
            "win_rate_pct": round(win_rate, 1),
            "profit_factor": round(profit_factor, 3),
            "avg_trade_return_pct": round(np.mean([t["strategy_return"] for t in trades]), 4) if trades else 0,
            "regime_distribution": regime_dist,
            "total_cost_bps": round(sum(t.get("cost_bps", 0) for t in trades), 1),
            "data_points_used": len(equity),
        }

    def run_all_markets(self, market_data):
        """
        Run walk-forward backtest on all loaded market data.

        Args:
            market_data: Dict from DataLoader.fetch_all() → {category: {ticker: df}}

        Returns:
            Dict of results by category and ticker.
        """
        results = {}
        summary = {
            "total_tickers": 0,
            "profitable": 0,
            "alpha_positive": 0,
            "avg_sharpe": [],
            "avg_alpha": [],
            "best_ticker": None,
            "best_alpha": -999,
            "worst_ticker": None,
            "worst_alpha": 999,
        }

        for category, tickers in market_data.items():
            results[category] = {}
            print(f"\n  Backtesting {config.MARKETS[category]['label']}...")

            for ticker, df in tickers.items():
                print(f"    {ticker}...", end=" ", flush=True)
                result = self.walk_forward(df, ticker=ticker)
                results[category][ticker] = result

                if "error" not in result.get("metrics", {}):
                    m = result["metrics"]
                    summary["total_tickers"] += 1

                    if m.get("total_return_pct", 0) > 0:
                        summary["profitable"] += 1

                    alpha = m.get("alpha_pct", 0)
                    if alpha > 0:
                        summary["alpha_positive"] += 1

                    summary["avg_sharpe"].append(m.get("sharpe_ratio", 0))
                    summary["avg_alpha"].append(alpha)

                    if alpha > summary["best_alpha"]:
                        summary["best_alpha"] = alpha
                        summary["best_ticker"] = ticker

                    if alpha < summary["worst_alpha"]:
                        summary["worst_alpha"] = alpha
                        summary["worst_ticker"] = ticker

                    print(f"Return: {m.get('total_return_pct', 0):+.1f}% | "
                          f"Alpha: {alpha:+.1f}% | "
                          f"Sharpe: {m.get('sharpe_ratio', 0):.2f} | "
                          f"WR: {m.get('win_rate_pct', 0):.0f}%")
                else:
                    print(f"SKIP ({result['metrics'].get('error', 'unknown')})")

        # Finalize summary
        if summary["avg_sharpe"]:
            summary["avg_sharpe"] = round(np.mean(summary["avg_sharpe"]), 3)
        else:
            summary["avg_sharpe"] = 0
        if summary["avg_alpha"]:
            summary["avg_alpha"] = round(np.mean(summary["avg_alpha"]), 2)
        else:
            summary["avg_alpha"] = 0

        summary["best_alpha"] = round(summary["best_alpha"], 2) if summary["best_ticker"] else 0
        summary["worst_alpha"] = round(summary["worst_alpha"], 2) if summary["worst_ticker"] else 0

        return {"results": results, "summary": summary}
