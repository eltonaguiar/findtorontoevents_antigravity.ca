"""
Backtest Engine

Event-driven backtesting with realistic transaction costs, position sizing,
and comprehensive performance tracking.

NON-NEGOTIABLES:
- Transaction costs + slippage included
- No lookahead bias
- No survivorship bias
- Reports full metrics suite
"""
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from .costs import CostModel
from .position_sizing import PositionSizer
from .portfolio import PortfolioConstructor, PortfolioState, Position

logger = logging.getLogger(__name__)


@dataclass
class Trade:
    """Record of a completed trade."""
    ticker: str
    direction: int
    entry_date: pd.Timestamp
    exit_date: pd.Timestamp
    entry_price: float
    exit_price: float
    shares: int
    pnl: float
    pnl_pct: float
    costs: float
    holding_days: int
    exit_reason: str
    strategy: str
    category: str


@dataclass
class BacktestResult:
    """Complete backtest results."""
    strategy_name: str
    start_date: pd.Timestamp
    end_date: pd.Timestamp

    # Returns
    total_return_pct: float = 0
    annual_return_pct: float = 0
    benchmark_return_pct: float = 0
    alpha_pct: float = 0

    # Risk
    sharpe_ratio: float = 0
    sortino_ratio: float = 0
    calmar_ratio: float = 0
    max_drawdown_pct: float = 0
    max_drawdown_duration_days: int = 0

    # Trade stats
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0
    profit_factor: float = 0
    avg_win_pct: float = 0
    avg_loss_pct: float = 0
    best_trade_pct: float = 0
    worst_trade_pct: float = 0
    avg_holding_days: float = 0
    expectancy: float = 0

    # Costs
    total_costs: float = 0
    cost_drag_pct: float = 0

    # Turnover
    avg_annual_turnover: float = 0
    avg_positions: float = 0

    # Tail risk
    var_95: float = 0
    cvar_95: float = 0
    hit_rate_monthly: float = 0

    # Time series
    equity_curve: pd.Series = field(default_factory=lambda: pd.Series(dtype=float))
    daily_returns: pd.Series = field(default_factory=lambda: pd.Series(dtype=float))
    drawdown_series: pd.Series = field(default_factory=lambda: pd.Series(dtype=float))
    trades: List[Trade] = field(default_factory=list)


class BacktestEngine:
    """
    Event-driven backtesting engine.
    
    Processes signals day by day with full cost modeling.
    No lookahead bias: each day only uses information available up to that day.
    """

    def __init__(
        self,
        initial_capital: float = 100000,
        cost_model: Optional[CostModel] = None,
        max_positions: int = 30,
        rebalance_frequency: str = "weekly",
    ):
        self.initial_capital = initial_capital
        self.cost_model = cost_model or CostModel.interactive_brokers()
        self.max_positions = max_positions
        self.rebalance_frequency = rebalance_frequency
        self.position_sizer = PositionSizer(initial_capital)
        self.portfolio_constructor = PortfolioConstructor(
            initial_capital=initial_capital,
            max_positions=max_positions,
        )

    def run(
        self,
        signals: pd.DataFrame,
        prices: pd.DataFrame,
        benchmark: Optional[pd.Series] = None,
        sectors: Dict[str, str] = None,
        stop_loss_pct: float = 0.10,
        take_profit_pct: float = 0.50,
    ) -> BacktestResult:
        """
        Run backtest on signals.
        
        Args:
            signals: DataFrame with columns [date, ticker, score, direction, confidence, 
                     holding_period, category, strategy]
            prices: Close prices (date x ticker)
            benchmark: Benchmark price series (e.g., SPY)
            sectors: Sector classification dict
            stop_loss_pct: Default stop loss
            take_profit_pct: Default take profit
            
        Returns:
            BacktestResult with full metrics
        """
        if sectors is None:
            sectors = {}

        # Initialize state
        state = PortfolioState(
            date=prices.index[0],
            cash=self.initial_capital,
        )

        # Track results
        equity_history = []
        daily_returns = []
        all_trades: List[Trade] = []
        total_costs = 0
        prev_equity = self.initial_capital

        # Get rebalance dates
        rebal_dates = self._get_rebalance_dates(prices.index, self.rebalance_frequency)

        # Process each trading day
        for date in prices.index:
            current_prices = prices.loc[date].dropna().to_dict()

            # Update position prices
            for ticker in list(state.positions.keys()):
                if ticker in current_prices:
                    state.positions[ticker].current_price = current_prices[ticker]

            # Check exits (stop loss, take profit, holding period)
            exits = self._check_exits(state, current_prices, date)
            for exit_info in exits:
                trade, cost = self._execute_exit(state, exit_info, date)
                if trade:
                    all_trades.append(trade)
                    total_costs += cost

            # On rebalance dates, process new signals
            if date in rebal_dates:
                day_signals = signals[signals["date"] == date] if "date" in signals.columns else pd.DataFrame()
                if not day_signals.empty:
                    entries = self._process_signals(
                        day_signals, state, current_prices, sectors,
                        stop_loss_pct, take_profit_pct,
                    )
                    for entry_info in entries:
                        cost = self._execute_entry(state, entry_info, date)
                        total_costs += cost

            # Record equity
            equity = state.cash + sum(
                p.shares * p.current_price for p in state.positions.values()
            )
            equity_history.append({"date": date, "equity": equity})

            # Daily return
            daily_ret = (equity - prev_equity) / prev_equity if prev_equity > 0 else 0
            daily_returns.append({"date": date, "return": daily_ret})
            prev_equity = equity

        # Close remaining positions at end
        final_prices = prices.iloc[-1].dropna().to_dict()
        for ticker in list(state.positions.keys()):
            if ticker in final_prices:
                trade, cost = self._execute_exit(
                    state,
                    {"ticker": ticker, "reason": "end_of_backtest", "price": final_prices[ticker]},
                    prices.index[-1],
                )
                if trade:
                    all_trades.append(trade)
                    total_costs += cost

        # Compute results
        equity_df = pd.DataFrame(equity_history).set_index("date")["equity"]
        returns_df = pd.DataFrame(daily_returns).set_index("date")["return"]

        result = self._compute_metrics(
            equity_df, returns_df, all_trades, total_costs,
            benchmark, signals.get("strategy", pd.Series(["unknown"])).iloc[0] if not signals.empty else "unknown",
        )

        return result

    def _get_rebalance_dates(self, dates: pd.DatetimeIndex, frequency: str) -> set:
        """Get rebalance dates based on frequency."""
        if frequency == "daily":
            return set(dates)
        elif frequency == "weekly":
            # Rebalance on Mondays (or first trading day of week)
            return set(dates[dates.dayofweek == 0])
        elif frequency == "monthly":
            # First trading day of each month
            monthly = dates.to_series().groupby(dates.to_period("M")).first()
            return set(monthly.values)
        return set(dates)

    def _check_exits(self, state: PortfolioState, prices: Dict, date) -> List[Dict]:
        """Check all positions for exit conditions."""
        exits = []
        for ticker, pos in list(state.positions.items()):
            price = prices.get(ticker, pos.current_price)
            days_held = (date - pos.entry_date).days

            # Stop loss
            if price <= pos.stop_loss:
                exits.append({"ticker": ticker, "reason": "stop_loss", "price": price})
            # Take profit
            elif price >= pos.take_profit:
                exits.append({"ticker": ticker, "reason": "take_profit", "price": price})
            # Max hold (based on strategy holding period)
            # Default: 63 trading days
            elif days_held > 90:
                exits.append({"ticker": ticker, "reason": "max_hold", "price": price})

        return exits

    def _execute_exit(self, state: PortfolioState, exit_info: Dict, date) -> Tuple[Optional[Trade], float]:
        """Execute a position exit."""
        ticker = exit_info["ticker"]
        if ticker not in state.positions:
            return None, 0

        pos = state.positions[ticker]
        exit_price = self.cost_model.effective_exit_price(
            exit_info["price"], pos.shares, pos.direction == 1
        )

        # Compute PnL
        if pos.direction == 1:  # Long
            pnl = (exit_price - pos.entry_price) * pos.shares
        else:  # Short
            pnl = (pos.entry_price - exit_price) * pos.shares

        holding_days = (date - pos.entry_date).days
        cost = self.cost_model.compute_exit_cost(
            exit_info["price"], pos.shares, pos.direction == -1, holding_days
        )

        pnl -= cost

        # Update state
        state.cash += pos.shares * exit_price * pos.direction + pnl
        del state.positions[ticker]

        pnl_pct = pnl / (pos.entry_price * pos.shares) if pos.entry_price * pos.shares > 0 else 0

        trade = Trade(
            ticker=ticker,
            direction=pos.direction,
            entry_date=pos.entry_date,
            exit_date=date,
            entry_price=pos.entry_price,
            exit_price=exit_price,
            shares=pos.shares,
            pnl=pnl,
            pnl_pct=pnl_pct,
            costs=cost,
            holding_days=holding_days,
            exit_reason=exit_info["reason"],
            strategy=pos.strategy,
            category=pos.category,
        )

        return trade, cost

    def _process_signals(
        self, signals_df, state, prices, sectors, stop_loss_pct, take_profit_pct,
    ) -> List[Dict]:
        """Process signals into entry orders."""
        entries = []

        # Sort by score
        signals_df = signals_df.sort_values("score", ascending=False)

        for _, signal in signals_df.iterrows():
            ticker = signal["ticker"]
            if ticker in state.positions:
                continue
            if len(state.positions) + len(entries) >= self.max_positions:
                break

            price = prices.get(ticker)
            if price is None or price <= 0:
                continue

            # Position sizing
            size = self.position_sizer.compute_position_size(
                price=price,
                signal_confidence=signal.get("confidence", 0.5),
                signal_category=signal.get("category", "momentum"),
                stop_loss_pct=stop_loss_pct,
                annualized_vol=0.25,  # Default; ideally from features
            )

            if size.target_shares <= 0:
                continue
            if size.target_value > state.cash:
                continue

            entries.append({
                "ticker": ticker,
                "shares": size.target_shares,
                "price": price,
                "direction": int(signal.get("direction", 1)),
                "stop_loss_pct": stop_loss_pct,
                "take_profit_pct": take_profit_pct,
                "strategy": signal.get("strategy", "unknown"),
                "category": signal.get("category", "unknown"),
                "sector": sectors.get(ticker, "Unknown"),
            })

        return entries

    def _execute_entry(self, state: PortfolioState, entry: Dict, date) -> float:
        """Execute a position entry."""
        ticker = entry["ticker"]
        shares = entry["shares"]
        price = entry["price"]
        direction = entry["direction"]

        effective_price = self.cost_model.effective_entry_price(price, shares, direction == 1)
        cost = self.cost_model.compute_entry_cost(price, shares)

        # Deduct cash
        position_value = shares * effective_price
        state.cash -= position_value + cost

        # Create position
        state.positions[ticker] = Position(
            ticker=ticker,
            shares=shares,
            entry_price=effective_price,
            entry_date=date,
            current_price=price,
            weight=position_value / max(state.equity, 1),
            direction=direction,
            stop_loss=price * (1 - entry["stop_loss_pct"]),
            take_profit=price * (1 + entry["take_profit_pct"]),
            strategy=entry["strategy"],
            category=entry["category"],
            sector=entry.get("sector", "Unknown"),
        )

        return cost

    def _compute_metrics(
        self,
        equity: pd.Series,
        daily_returns: pd.Series,
        trades: List[Trade],
        total_costs: float,
        benchmark: Optional[pd.Series],
        strategy_name: str,
    ) -> BacktestResult:
        """Compute comprehensive performance metrics."""
        result = BacktestResult(
            strategy_name=strategy_name,
            start_date=equity.index[0],
            end_date=equity.index[-1],
        )

        if equity.empty:
            return result

        # Returns
        total_return = (equity.iloc[-1] / equity.iloc[0]) - 1
        n_years = max((equity.index[-1] - equity.index[0]).days / 365.25, 0.01)
        annual_return = (1 + total_return) ** (1 / n_years) - 1

        result.total_return_pct = total_return * 100
        result.annual_return_pct = annual_return * 100

        # Benchmark comparison
        if benchmark is not None and not benchmark.empty:
            bench_aligned = benchmark.reindex(equity.index, method="ffill")
            if not bench_aligned.empty:
                bench_return = (bench_aligned.iloc[-1] / bench_aligned.iloc[0]) - 1
                result.benchmark_return_pct = bench_return * 100
                result.alpha_pct = result.total_return_pct - result.benchmark_return_pct

        # Risk metrics
        ret_clean = daily_returns.dropna()
        if len(ret_clean) > 10:
            result.sharpe_ratio = ret_clean.mean() / ret_clean.std() * np.sqrt(252) if ret_clean.std() > 0 else 0
            downside = ret_clean[ret_clean < 0]
            result.sortino_ratio = ret_clean.mean() / downside.std() * np.sqrt(252) if len(downside) > 0 and downside.std() > 0 else 0

        # Drawdown
        peak = equity.cummax()
        drawdown = (equity - peak) / peak
        result.max_drawdown_pct = abs(drawdown.min()) * 100
        result.drawdown_series = drawdown

        if result.max_drawdown_pct > 0:
            result.calmar_ratio = result.annual_return_pct / result.max_drawdown_pct

        # Trade stats
        result.total_trades = len(trades)
        result.trades = trades

        if trades:
            pnls = [t.pnl_pct for t in trades]
            winners = [p for p in pnls if p > 0]
            losers = [p for p in pnls if p <= 0]

            result.winning_trades = len(winners)
            result.losing_trades = len(losers)
            result.win_rate = len(winners) / len(pnls) * 100 if pnls else 0
            result.avg_win_pct = np.mean(winners) * 100 if winners else 0
            result.avg_loss_pct = np.mean(losers) * 100 if losers else 0
            result.best_trade_pct = max(pnls) * 100
            result.worst_trade_pct = min(pnls) * 100
            result.avg_holding_days = np.mean([t.holding_days for t in trades])

            gross_win = sum(t.pnl for t in trades if t.pnl > 0)
            gross_loss = abs(sum(t.pnl for t in trades if t.pnl <= 0))
            result.profit_factor = gross_win / gross_loss if gross_loss > 0 else float("inf")

            result.expectancy = (
                (result.win_rate / 100) * (result.avg_win_pct / 100)
                + (1 - result.win_rate / 100) * (result.avg_loss_pct / 100)
            )

        # Costs
        result.total_costs = total_costs
        result.cost_drag_pct = (total_costs / self.initial_capital) * 100 if self.initial_capital > 0 else 0

        # Tail risk
        if len(ret_clean) > 20:
            result.var_95 = np.percentile(ret_clean, 5) * 100
            result.cvar_95 = ret_clean[ret_clean <= np.percentile(ret_clean, 5)].mean() * 100

        # Monthly hit rate
        monthly = daily_returns.resample("ME").sum()
        if len(monthly) > 0:
            result.hit_rate_monthly = (monthly > 0).mean() * 100

        result.equity_curve = equity
        result.daily_returns = daily_returns

        return result
