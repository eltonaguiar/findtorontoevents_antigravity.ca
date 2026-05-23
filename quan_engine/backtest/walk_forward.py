"""
Walk-Forward Backtesting Engine
================================
18-month IS, 6-month OOS, roll forward 3 months.
Data: Binance OHLCV via ccxt.

Each strategy is tested independently, then the ensemble is tested
on the combined signal output.
"""
import os
import sys
import json
import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from quan_engine import config

logger = logging.getLogger("QuanEngine.Backtest")


@dataclass
class Trade:
    symbol: str
    direction: str
    entry_price: float
    entry_time: str
    exit_price: float
    exit_time: str
    exit_reason: str  # TP, SL, TRAILING, TIME_EXIT
    pnl_pct: float
    hold_bars: int
    strategy: str
    mode: str
    confidence: float


@dataclass
class WindowResult:
    window_id: int
    is_start: str
    is_end: str
    oos_start: str
    oos_end: str
    is_trades: int
    oos_trades: int
    is_win_rate: float
    oos_win_rate: float
    is_sharpe: float
    oos_sharpe: float
    is_profit_factor: float
    oos_profit_factor: float
    is_max_drawdown: float
    oos_max_drawdown: float
    oos_max_consecutive_losses: int
    oos_max_single_trade_pct: float
    oos_profitable: bool


def fetch_ohlcv(symbol: str, timeframe: str = "1h",
                start_date: str = "2023-01-01",
                end_date: str = "2026-03-01") -> pd.DataFrame:
    """Fetch OHLCV data from Binance via ccxt."""
    try:
        import ccxt
        exchange = ccxt.binance({"enableRateLimit": True})

        since = exchange.parse8601(f"{start_date}T00:00:00Z")
        end_ts = exchange.parse8601(f"{end_date}T00:00:00Z")

        all_candles = []
        while since < end_ts:
            candles = exchange.fetch_ohlcv(symbol, timeframe, since=since, limit=1000)
            if not candles:
                break
            all_candles.extend(candles)
            since = candles[-1][0] + 1

        if not all_candles:
            return pd.DataFrame()

        df = pd.DataFrame(all_candles, columns=["timestamp", "open", "high", "low", "close", "volume"])
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        df = df.set_index("timestamp")
        df = df[~df.index.duplicated(keep="first")]
        return df

    except ImportError:
        logger.warning("ccxt not installed — using synthetic data for backtest")
        return _generate_synthetic_data(symbol, start_date, end_date)
    except Exception as e:
        logger.error(f"Failed to fetch {symbol}: {e}")
        return pd.DataFrame()


def _generate_synthetic_data(symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
    """Generate synthetic OHLCV for testing when ccxt is unavailable."""
    dates = pd.date_range(start_date, end_date, freq="1h")
    n = len(dates)
    np.random.seed(hash(symbol) % 2**31)

    # Geometric Brownian Motion
    base_price = {"BTCUSDT": 40000, "ETHUSDT": 2500, "SOLUSDT": 100,
                  "BNBUSDT": 300, "DOGEUSDT": 0.08}.get(symbol, 100)
    returns = np.random.normal(0.00002, 0.015, n)
    prices = base_price * np.exp(np.cumsum(returns))

    high = prices * (1 + np.abs(np.random.normal(0, 0.005, n)))
    low = prices * (1 - np.abs(np.random.normal(0, 0.005, n)))
    volume = np.random.lognormal(10, 1, n)

    df = pd.DataFrame({
        "open": prices * (1 + np.random.normal(0, 0.002, n)),
        "high": high,
        "low": low,
        "close": prices,
        "volume": volume,
    }, index=dates)
    return df


def compute_atr(df: pd.DataFrame, period: int = 14) -> np.ndarray:
    """Compute ATR from OHLCV DataFrame."""
    high = df["high"].values
    low = df["low"].values
    close = df["close"].values

    tr = np.zeros(len(df))
    tr[0] = high[0] - low[0]
    for i in range(1, len(df)):
        tr[i] = max(high[i] - low[i],
                     abs(high[i] - close[i-1]),
                     abs(low[i] - close[i-1]))

    atr = np.zeros(len(df))
    atr[:period] = np.mean(tr[:period])
    for i in range(period, len(df)):
        atr[i] = (atr[i-1] * (period - 1) + tr[i]) / period
    return atr


def simulate_trades(signals: List[dict], df: pd.DataFrame,
                    mode_cfg: dict, strategy_name: str,
                    mode: str = "SWING") -> List[Trade]:
    """Simulate trades from signals against price data.

    Each signal has: entry_time (index), direction, entry_price,
    take_profit, stop_loss, confidence.
    """
    trades = []
    close = df["close"].values
    high = df["high"].values
    low = df["low"].values
    timestamps = df.index

    for sig in signals:
        entry_idx = sig.get("entry_idx")
        if entry_idx is None or entry_idx >= len(df) - 1:
            continue

        direction = sig["direction"]
        entry_price = sig.get("entry_price", close[entry_idx])
        tp = sig["take_profit"]
        sl = sig["stop_loss"]
        confidence = sig.get("confidence", 0.5)
        max_bars = mode_cfg["max_hold_bars"]

        # Walk forward from entry
        exit_price = entry_price
        exit_reason = "TIME_EXIT"
        exit_idx = min(entry_idx + max_bars, len(df) - 1)

        for i in range(entry_idx + 1, min(entry_idx + max_bars + 1, len(df))):
            if direction == "BUY":
                if high[i] >= tp:
                    exit_price = tp
                    exit_reason = "TP"
                    exit_idx = i
                    break
                elif low[i] <= sl:
                    exit_price = sl
                    exit_reason = "SL"
                    exit_idx = i
                    break
            else:  # SELL
                if low[i] <= tp:
                    exit_price = tp
                    exit_reason = "TP"
                    exit_idx = i
                    break
                elif high[i] >= sl:
                    exit_price = sl
                    exit_reason = "SL"
                    exit_idx = i
                    break
        else:
            exit_price = close[min(exit_idx, len(df) - 1)]

        # Calculate P&L
        if direction == "BUY":
            pnl_pct = ((exit_price - entry_price) / entry_price) * 100
        else:
            pnl_pct = ((entry_price - exit_price) / entry_price) * 100

        # Subtract costs
        pnl_pct -= config.ROUND_TRIP_COST_PCT * 100

        trades.append(Trade(
            symbol=sig.get("symbol", "UNKNOWN"),
            direction=direction,
            entry_price=entry_price,
            entry_time=str(timestamps[entry_idx]),
            exit_price=round(exit_price, 8),
            exit_time=str(timestamps[exit_idx]),
            exit_reason=exit_reason,
            pnl_pct=round(pnl_pct, 4),
            hold_bars=exit_idx - entry_idx,
            strategy=strategy_name,
            mode=mode,
            confidence=confidence,
        ))

    return trades


def compute_metrics(trades: List[Trade]) -> dict:
    """Compute performance metrics from a list of trades."""
    if not trades:
        return {"win_rate": 0, "sharpe": 0, "profit_factor": 0,
                "max_drawdown": 0, "max_consecutive_losses": 0,
                "max_single_trade_pct": 0, "total_pnl": 0, "trade_count": 0}

    pnls = [t.pnl_pct for t in trades]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p <= 0]

    win_rate = len(wins) / len(pnls) if pnls else 0

    # Sharpe ratio (annualized, assuming ~250 trading days)
    mean_pnl = np.mean(pnls)
    std_pnl = np.std(pnls) if len(pnls) > 1 else 1.0
    sharpe = (mean_pnl / std_pnl * np.sqrt(252)) if std_pnl > 0 else 0

    # Profit factor
    gross_profit = sum(wins) if wins else 0
    gross_loss = abs(sum(losses)) if losses else 0.001
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0

    # Max drawdown
    cumulative = np.cumsum(pnls)
    peak = np.maximum.accumulate(cumulative)
    drawdown = cumulative - peak
    max_dd = abs(np.min(drawdown)) if len(drawdown) > 0 else 0

    # Max consecutive losses
    max_consec = 0
    current_consec = 0
    for p in pnls:
        if p <= 0:
            current_consec += 1
            max_consec = max(max_consec, current_consec)
        else:
            current_consec = 0

    # Max single trade as % of total P&L
    total_pnl = sum(pnls)
    max_single = max(abs(p) for p in pnls) if pnls else 0
    max_single_pct = (max_single / abs(total_pnl) * 100) if abs(total_pnl) > 0 else 100

    return {
        "win_rate": round(win_rate, 4),
        "sharpe": round(sharpe, 4),
        "profit_factor": round(profit_factor, 4),
        "max_drawdown": round(max_dd, 4),
        "max_consecutive_losses": max_consec,
        "max_single_trade_pct": round(max_single_pct, 2),
        "total_pnl": round(total_pnl, 4),
        "trade_count": len(trades),
        "avg_pnl": round(mean_pnl, 4),
        "avg_win": round(np.mean(wins), 4) if wins else 0,
        "avg_loss": round(np.mean(losses), 4) if losses else 0,
    }


def run_walk_forward(strategy_func, df: pd.DataFrame, symbol: str,
                     strategy_name: str, mode: str = "SWING") -> List[WindowResult]:
    """Run walk-forward analysis on a single strategy.

    Args:
        strategy_func: Callable(df_slice, symbol) -> List[signal_dict]
        df: Full OHLCV DataFrame
        symbol: Trading symbol
        strategy_name: Name of strategy
        mode: Trading mode (SCALP, SWING, POSITION)

    Returns:
        List of WindowResult for each IS/OOS pair
    """
    mode_cfg = config.MODES[mode]
    results = []

    total_bars = len(df)
    bars_per_month = 30 * 24  # Approximate for 1h candles

    is_bars = config.IS_MONTHS * bars_per_month
    oos_bars = config.OOS_MONTHS * bars_per_month
    roll_bars = config.ROLL_MONTHS * bars_per_month

    window_id = 0
    start = 0

    while start + is_bars + oos_bars <= total_bars:
        is_start = start
        is_end = start + is_bars
        oos_start = is_end
        oos_end = min(is_end + oos_bars, total_bars)

        is_df = df.iloc[is_start:is_end]
        oos_df = df.iloc[oos_start:oos_end]

        # Generate signals on IS and OOS
        try:
            is_signals = strategy_func(is_df, symbol)
            oos_signals = strategy_func(oos_df, symbol)
        except Exception as e:
            logger.error(f"Strategy {strategy_name} failed in window {window_id}: {e}")
            start += roll_bars
            window_id += 1
            continue

        # Simulate trades
        is_trades = simulate_trades(is_signals, is_df, mode_cfg, strategy_name, mode)
        oos_trades = simulate_trades(oos_signals, oos_df, mode_cfg, strategy_name, mode)

        is_metrics = compute_metrics(is_trades)
        oos_metrics = compute_metrics(oos_trades)

        results.append(WindowResult(
            window_id=window_id,
            is_start=str(is_df.index[0]) if len(is_df) > 0 else "",
            is_end=str(is_df.index[-1]) if len(is_df) > 0 else "",
            oos_start=str(oos_df.index[0]) if len(oos_df) > 0 else "",
            oos_end=str(oos_df.index[-1]) if len(oos_df) > 0 else "",
            is_trades=is_metrics["trade_count"],
            oos_trades=oos_metrics["trade_count"],
            is_win_rate=is_metrics["win_rate"],
            oos_win_rate=oos_metrics["win_rate"],
            is_sharpe=is_metrics["sharpe"],
            oos_sharpe=oos_metrics["sharpe"],
            is_profit_factor=is_metrics["profit_factor"],
            oos_profit_factor=oos_metrics["profit_factor"],
            is_max_drawdown=is_metrics["max_drawdown"],
            oos_max_drawdown=oos_metrics["max_drawdown"],
            oos_max_consecutive_losses=oos_metrics["max_consecutive_losses"],
            oos_max_single_trade_pct=oos_metrics["max_single_trade_pct"],
            oos_profitable=oos_metrics["total_pnl"] > 0,
        ))

        start += roll_bars
        window_id += 1

    return results


def save_results(results: List[WindowResult], strategy_name: str,
                 symbol: str, output_dir: str = None):
    """Save walk-forward results to JSON."""
    if output_dir is None:
        output_dir = os.path.join(config.DATA_DIR, "backtest_results")
    os.makedirs(output_dir, exist_ok=True)

    filepath = os.path.join(output_dir, f"wf_{strategy_name}_{symbol}.json")
    data = {
        "strategy": strategy_name,
        "symbol": symbol,
        "generated_at": datetime.utcnow().isoformat(),
        "windows": [asdict(r) for r in results],
    }

    with open(filepath, "w") as f:
        json.dump(data, f, indent=2)

    logger.info(f"Saved walk-forward results to {filepath}")
    return filepath
