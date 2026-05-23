"""
Realistic Backtester for ML Crypto Predictions
================================================
Replaces the fake _simulate_backtest() that used label correctness
instead of actual price data. This backtester:

1. Simulates bar-by-bar using OHLCV data
2. Checks TP/SL against high/low (not just close)
3. Applies realistic Binance fees + slippage
4. Tracks equity curve for proper Sharpe/drawdown calculation
5. Supports fractional Kelly position sizing

References:
- Lopez de Prado (2018) "Advances in Financial Machine Learning"
- Bailey & Lopez de Prado (2014) "The Deflated Sharpe Ratio"
"""

import sys
import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from typing import List, Optional, Callable, Tuple, Dict

from .config import V4_CONFIG, get_slippage


@dataclass
class CryptoCostModel:
    """Binance cost model with per-pair slippage."""
    maker_fee: float = 0.001       # 0.1%
    taker_fee: float = 0.001       # 0.1%
    slippage: float = 0.0005       # 0.05% default, overridden per pair

    @classmethod
    def for_pair(cls, pair: str) -> "CryptoCostModel":
        return cls(
            maker_fee=V4_CONFIG["maker_fee"],
            taker_fee=V4_CONFIG["taker_fee"],
            slippage=get_slippage(pair),
        )

    @property
    def round_trip_cost(self) -> float:
        """Total cost for entry + exit."""
        return 2 * (self.taker_fee + self.slippage)


@dataclass
class MLTrade:
    """Single trade record."""
    bar_entry: int
    bar_exit: int
    entry_price: float
    exit_price: float
    size_pct: float            # position size as fraction of equity
    pnl_gross: float           # before costs
    pnl_net: float             # after costs
    costs: float
    exit_reason: str           # "tp", "sl", "max_hold", "signal_flip"
    holding_bars: int
    confidence: float


@dataclass
class BacktestMetrics:
    """Complete performance metrics from realistic backtest."""
    # Returns
    total_return_pct: float = 0.0
    annual_return_pct: float = 0.0
    # Risk-adjusted
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    calmar_ratio: float = 0.0
    # Risk
    max_drawdown_pct: float = 0.0
    max_dd_duration_bars: int = 0
    var_95: float = 0.0           # Value at Risk 95%
    cvar_95: float = 0.0          # Conditional VaR 95%
    # Trade stats
    total_trades: int = 0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    avg_win_pct: float = 0.0
    avg_loss_pct: float = 0.0
    expectancy: float = 0.0       # Expected value per trade after costs
    best_trade_pct: float = 0.0
    worst_trade_pct: float = 0.0
    avg_hold_bars: float = 0.0
    # Costs
    total_cost_drag: float = 0.0
    # Data
    equity_curve: np.ndarray = field(default_factory=lambda: np.array([]))
    drawdown_curve: np.ndarray = field(default_factory=lambda: np.array([]))
    trades: List[MLTrade] = field(default_factory=list)

    def to_dict(self) -> Dict:
        """Serialize to dict (without numpy arrays)."""
        return {
            "total_return_pct": round(self.total_return_pct, 4),
            "annual_return_pct": round(self.annual_return_pct, 4),
            "sharpe_ratio": round(self.sharpe_ratio, 4),
            "sortino_ratio": round(self.sortino_ratio, 4),
            "calmar_ratio": round(self.calmar_ratio, 4),
            "max_drawdown_pct": round(self.max_drawdown_pct, 4),
            "max_dd_duration_bars": self.max_dd_duration_bars,
            "var_95": round(self.var_95, 4),
            "cvar_95": round(self.cvar_95, 4),
            "total_trades": self.total_trades,
            "win_rate": round(self.win_rate, 4),
            "profit_factor": round(self.profit_factor, 4),
            "avg_win_pct": round(self.avg_win_pct, 4),
            "avg_loss_pct": round(self.avg_loss_pct, 4),
            "expectancy": round(self.expectancy, 6),
            "best_trade_pct": round(self.best_trade_pct, 4),
            "worst_trade_pct": round(self.worst_trade_pct, 4),
            "avg_hold_bars": round(self.avg_hold_bars, 2),
            "total_cost_drag": round(self.total_cost_drag, 6),
        }


def fractional_kelly(
    win_rate: float,
    avg_win: float,
    avg_loss: float,
    fraction: float = 0.25,
    max_pos: float = 0.10,
    confidence: float = 1.0,
) -> float:
    """
    Fractional Kelly Criterion position sizing.

    Full Kelly: f* = (p*b - q) / b
    where p=win_rate, q=1-p, b=avg_win/avg_loss

    We use quarter-Kelly (fraction=0.25) for crypto because:
    - Fat-tailed returns (black swans)
    - Model uncertainty (estimation error in WR)
    - Leverage risk

    Args:
        win_rate: historical win rate (0-1)
        avg_win: average winning trade return (positive)
        avg_loss: average losing trade return (positive, absolute value)
        fraction: Kelly fraction (0.25 = quarter-Kelly)
        max_pos: maximum position size cap
        confidence: model confidence multiplier (0-1)

    Returns:
        Position size as fraction of equity (0.01 to max_pos)
    """
    if avg_loss <= 0 or avg_win <= 0 or win_rate <= 0:
        return 0.01

    p = min(0.99, max(0.01, win_rate))
    q = 1.0 - p
    b = avg_win / avg_loss

    kelly_full = (p * b - q) / b
    if kelly_full <= 0:
        return 0.01  # minimum position when no edge

    sized = kelly_full * fraction * confidence
    return min(max(sized, 0.01), max_pos)


class RealisticBacktester:
    def load_data(self, pair: str, timeframe: str) -> pd.DataFrame:
        """Load OHLCV data from SQLite DB."""
        conn = sqlite3.connect(DB_PATH)
        table = f"klines_{pair.replace('/', '_')}_{timeframe}"
        query = f"SELECT * FROM {table} ORDER BY timestamp ASC"
        df = pd.read_sql_query(query, conn, parse_dates=["timestamp"])
        conn.close()
        if df.empty:
            return pd.DataFrame()
        df = df.set_index("timestamp")
        return df[["open", "high", "low", "close", "volume"]]
    """
    Bar-by-bar backtester using actual OHLCV price data.

    Key differences from the broken _simulate_backtest():
    1. TP/SL checked against bar high/low, not just close
    2. Realistic transaction costs (fees + slippage)
    3. Equity curve from bar returns, not trade returns
    4. Proper Sharpe from bar-by-bar returns
    5. Position sizing support (Kelly or fixed)
    """

    def __init__(
        self,
        cost_model: Optional[CryptoCostModel] = None,
        initial_capital: float = 10000.0,
        max_position_pct: float = 0.10,
        timeframe: str = "1h",
    ):
        self.cost_model = cost_model or CryptoCostModel()
        self.initial_capital = initial_capital
        self.max_position_pct = max_position_pct
        self.timeframe = timeframe
        self.bars_per_year = V4_CONFIG["bars_per_year"].get(timeframe, 8760)

    def run(
        self,
        df: pd.DataFrame,
        predictions: np.ndarray,
        threshold: float = 0.55,
        tp_atr_mult: float = 2.5,
        sl_atr_mult: float = 1.0,
        max_hold_bars: int = 24,
        position_sizer: Optional[Callable] = None,
    ) -> BacktestMetrics:
        """
        Run realistic backtest on OHLCV data with ML predictions.

        Args:
            df: OHLCV DataFrame (must have open, high, low, close, volume)
            predictions: model probability predictions [0,1] aligned with df
            threshold: confidence threshold to enter trade (>= threshold = BUY)
            tp_atr_mult: take-profit as multiple of ATR-14
            sl_atr_mult: stop-loss as multiple of ATR-14
            max_hold_bars: maximum bars to hold a position
            position_sizer: callable(win_rate, avg_win, avg_loss) -> position_size

        Returns:
            BacktestMetrics with full performance stats
        """
        if len(df) != len(predictions):
            raise ValueError(f"df length {len(df)} != predictions length {len(predictions)}")

        if len(df) < 20:
            return BacktestMetrics()

        # Pre-compute ATR-14 for TP/SL levels
        high = df["high"].values
        low = df["low"].values
        close = df["close"].values
        open_ = df["open"].values

        tr = np.maximum(
            high - low,
            np.maximum(
                np.abs(high - np.roll(close, 1)),
                np.abs(low - np.roll(close, 1))
            )
        )
        tr[0] = high[0] - low[0]
        atr = pd.Series(tr).rolling(14, min_periods=1).mean().values

        # State
        equity = self.initial_capital
        equity_curve = np.full(len(df), self.initial_capital)
        trades: List[MLTrade] = []
        in_position = False
        entry_bar = 0
        entry_price = 0.0
        tp_price = 0.0
        sl_price = 0.0
        position_size = 0.0
        position_confidence = 0.0

        # Running stats for adaptive Kelly sizing
        completed_wins = []
        completed_losses = []

        for i in range(14, len(df)):  # start after ATR warmup
            if in_position:
                # Check exits using high/low (intra-bar)
                exit_price = 0.0
                exit_reason = ""
                bars_held = i - entry_bar

                # Check SL first (conservative — SL hit before TP on same bar)
                if low[i] <= sl_price:
                    exit_price = sl_price * (1 - self.cost_model.slippage)  # slippage worsens SL
                    exit_reason = "sl"
                elif high[i] >= tp_price:
                    exit_price = tp_price * (1 - self.cost_model.slippage)  # slippage worsens TP too
                    exit_reason = "tp"
                elif bars_held >= max_hold_bars:
                    exit_price = close[i]
                    exit_reason = "max_hold"

                if exit_reason:
                    # Calculate P&L
                    gross_return = (exit_price / entry_price) - 1.0
                    cost = self.cost_model.round_trip_cost
                    net_return = gross_return - cost

                    pnl_net = equity * position_size * net_return
                    pnl_gross = equity * position_size * gross_return
                    costs = equity * position_size * cost

                    equity += pnl_net

                    trade = MLTrade(
                        bar_entry=entry_bar,
                        bar_exit=i,
                        entry_price=entry_price,
                        exit_price=exit_price,
                        size_pct=position_size,
                        pnl_gross=pnl_gross,
                        pnl_net=pnl_net,
                        costs=costs,
                        exit_reason=exit_reason,
                        holding_bars=bars_held,
                        confidence=position_confidence,
                    )
                    trades.append(trade)

                    if net_return > 0:
                        completed_wins.append(net_return)
                    else:
                        completed_losses.append(abs(net_return))

                    in_position = False

            else:
                # Check for entry signal
                if predictions[i] >= threshold:
                    entry_bar = i
                    entry_price = close[i] * (1 + self.cost_model.slippage)  # slippage on entry
                    position_confidence = float(predictions[i])

                    # Set TP/SL from ATR
                    current_atr = atr[i]
                    tp_price = entry_price + current_atr * tp_atr_mult
                    sl_price = entry_price - current_atr * sl_atr_mult

                    # Position sizing
                    if position_sizer and len(completed_wins) >= 5 and len(completed_losses) >= 5:
                        avg_w = np.mean(completed_wins)
                        avg_l = np.mean(completed_losses)
                        wr = len(completed_wins) / (len(completed_wins) + len(completed_losses))
                        position_size = position_sizer(wr, avg_w, avg_l)
                    else:
                        position_size = self.max_position_pct  # fixed until enough data

                    in_position = True

            equity_curve[i] = equity

        # Fill forward equity curve for warmup period
        for i in range(14):
            equity_curve[i] = self.initial_capital

        return self._compute_metrics(equity_curve, trades)

    def _compute_metrics(
        self, equity_curve: np.ndarray, trades: List[MLTrade]
    ) -> BacktestMetrics:
        """Compute comprehensive performance metrics."""
        metrics = BacktestMetrics()
        metrics.equity_curve = equity_curve
        metrics.trades = trades
        metrics.total_trades = len(trades)

        if len(trades) == 0:
            return metrics

        # Returns
        total_return = (equity_curve[-1] / equity_curve[0]) - 1.0
        metrics.total_return_pct = total_return * 100

        n_bars = len(equity_curve)
        if n_bars > 1 and self.bars_per_year > 0:
            years = n_bars / self.bars_per_year
            if years > 0:
                metrics.annual_return_pct = ((1 + total_return) ** (1 / years) - 1) * 100

        # Bar-by-bar returns for Sharpe/Sortino
        bar_returns = np.diff(equity_curve) / equity_curve[:-1]
        bar_returns = bar_returns[np.isfinite(bar_returns)]

        if len(bar_returns) > 1:
            mean_ret = np.mean(bar_returns)
            std_ret = np.std(bar_returns, ddof=1)

            # Sharpe (annualized)
            if std_ret > 1e-10:
                metrics.sharpe_ratio = (mean_ret / std_ret) * np.sqrt(self.bars_per_year)
            else:
                metrics.sharpe_ratio = 0.0

            # Sortino (only downside deviation)
            downside = bar_returns[bar_returns < 0]
            if len(downside) > 0:
                downside_std = np.std(downside, ddof=1)
                if downside_std > 1e-10:
                    metrics.sortino_ratio = (mean_ret / downside_std) * np.sqrt(self.bars_per_year)

            # VaR and CVaR
            if len(bar_returns) >= 20:
                sorted_returns = np.sort(bar_returns)
                var_idx = int(0.05 * len(sorted_returns))
                metrics.var_95 = float(sorted_returns[max(var_idx, 0)]) * 100
                metrics.cvar_95 = float(np.mean(sorted_returns[:max(var_idx, 1)])) * 100

        # Drawdown analysis
        peak = np.maximum.accumulate(equity_curve)
        drawdown = (equity_curve - peak) / (peak + 1e-10)
        metrics.drawdown_curve = drawdown
        metrics.max_drawdown_pct = abs(float(np.min(drawdown))) * 100

        # Max drawdown duration
        underwater = drawdown < 0
        if underwater.any():
            dd_durations = []
            current_dur = 0
            for uw in underwater:
                if uw:
                    current_dur += 1
                else:
                    if current_dur > 0:
                        dd_durations.append(current_dur)
                    current_dur = 0
            if current_dur > 0:
                dd_durations.append(current_dur)
            metrics.max_dd_duration_bars = max(dd_durations) if dd_durations else 0

        # Calmar ratio
        if metrics.max_drawdown_pct > 0:
            metrics.calmar_ratio = metrics.annual_return_pct / metrics.max_drawdown_pct

        # Trade statistics
        net_returns = [t.pnl_net for t in trades]
        winners = [t.pnl_net for t in trades if t.pnl_net > 0]
        losers = [t.pnl_net for t in trades if t.pnl_net <= 0]

        metrics.win_rate = len(winners) / len(trades) if trades else 0.0

        gross_profit = sum(winners) if winners else 0.0
        gross_loss = abs(sum(losers)) if losers else 0.0
        metrics.profit_factor = gross_profit / (gross_loss + 1e-10)

        # Average win/loss as percentage of position
        win_pcts = [(t.pnl_net / (t.size_pct * self.initial_capital + 1e-10)) for t in trades if t.pnl_net > 0]
        loss_pcts = [(t.pnl_net / (t.size_pct * self.initial_capital + 1e-10)) for t in trades if t.pnl_net <= 0]
        metrics.avg_win_pct = float(np.mean(win_pcts) * 100) if win_pcts else 0.0
        metrics.avg_loss_pct = float(np.mean(loss_pcts) * 100) if loss_pcts else 0.0

        # Expectancy: average net P&L per trade
        metrics.expectancy = float(np.mean(net_returns))

        # Best/worst
        pnl_pcts = [(t.pnl_net / (t.size_pct * self.initial_capital + 1e-10)) * 100 for t in trades]
        metrics.best_trade_pct = max(pnl_pcts) if pnl_pcts else 0.0
        metrics.worst_trade_pct = min(pnl_pcts) if pnl_pcts else 0.0

        # Average hold
        metrics.avg_hold_bars = float(np.mean([t.holding_bars for t in trades]))

        # Total cost drag
        metrics.total_cost_drag = sum(t.costs for t in trades) / self.initial_capital * 100

        return metrics


def deflated_sharpe_ratio(
    observed_sharpe: float,
    n_trials: int,
    n_observations: int,
    skewness: float = 0.0,
    kurtosis: float = 3.0,
) -> float:
    """
    Deflated Sharpe Ratio (Bailey & Lopez de Prado, 2014).

    Adjusts Sharpe for multiple testing. Returns the probability
    that the true Sharpe ratio is greater than zero, given:
    - How many model configurations were tried (n_trials)
    - How many return observations (n_observations)
    - Skewness and excess kurtosis of returns

    A DSR > 0.95 means < 5% chance the edge is due to luck.

    Args:
        observed_sharpe: the raw Sharpe ratio from backtest
        n_trials: number of models/configs tested (multiple testing correction)
        n_observations: number of bar returns used
        skewness: skewness of returns distribution
        kurtosis: kurtosis of returns (3.0 = normal)

    Returns:
        Probability that true Sharpe > 0 (0 to 1)
    """
    from scipy import stats

    if n_observations < 2 or n_trials < 1:
        return 0.0

    # Expected maximum Sharpe under null hypothesis (Euler-Mascheroni)
    # E[max(SR)] ~ sqrt(2*ln(N)) - (ln(pi) + euler_gamma) / (2*sqrt(2*ln(N)))
    euler_gamma = 0.5772156649
    if n_trials > 1:
        log_n = np.log(n_trials)
        if log_n > 0:
            sr0 = np.sqrt(2 * log_n) - (np.log(np.pi) + euler_gamma) / (2 * np.sqrt(2 * log_n))
        else:
            sr0 = 0.0
    else:
        sr0 = 0.0

    # Standard error of Sharpe ratio (corrected for non-normality)
    excess_kurtosis = kurtosis - 3.0
    se_sr = np.sqrt(
        (1 - skewness * observed_sharpe + (excess_kurtosis / 4) * observed_sharpe**2)
        / (n_observations - 1)
    )

    if se_sr < 1e-10:
        return 1.0 if observed_sharpe > sr0 else 0.0

    # Test statistic: (observed - expected_max_under_null) / se
    z = (observed_sharpe - sr0) / se_sr

    # One-sided p-value: Prob(true SR > 0)
    dsr = float(stats.norm.cdf(z))
    return dsr


def monte_carlo_permutation_test(
    df: pd.DataFrame,
    predictions: np.ndarray,
    backtester: "RealisticBacktester",
    n_permutations: int = 1000,
    threshold: float = 0.55,
    tp_atr_mult: float = 2.5,
    sl_atr_mult: float = 1.0,
    max_hold_bars: int = 24,
    metric: str = "sharpe_ratio",
) -> Tuple[float, float, float]:
    """
    Monte Carlo permutation test for trading edge.

    Shuffles the predictions array, re-runs the backtest,
    and checks how often random predictions beat the real model.

    Args:
        df: OHLCV data
        predictions: real model predictions
        backtester: configured RealisticBacktester
        n_permutations: number of random shuffles (1000 standard)
        threshold, tp_atr_mult, sl_atr_mult, max_hold_bars: backtest params
        metric: which metric to compare ("sharpe_ratio", "total_return_pct", etc)

    Returns:
        (p_value, real_metric, mean_random_metric)
    """
    # Real backtest
    real_result = backtester.run(
        df, predictions, threshold, tp_atr_mult, sl_atr_mult, max_hold_bars
    )
    real_value = getattr(real_result, metric, 0.0)

    # Random permutations
    rng = np.random.RandomState(42)
    random_values = []

    for _ in range(n_permutations):
        shuffled = rng.permutation(predictions)
        try:
            result = backtester.run(
                df, shuffled, threshold, tp_atr_mult, sl_atr_mult, max_hold_bars
            )
            random_values.append(getattr(result, metric, 0.0))
        except Exception:
            random_values.append(0.0)

    random_values = np.array(random_values)

    # p-value: proportion of random trials that beat real model
    beats_real = np.sum(random_values >= real_value)
    p_value = (beats_real + 1) / (n_permutations + 1)  # +1 for continuity correction

    return float(p_value), float(real_value), float(np.mean(random_values))
