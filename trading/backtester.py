#!/usr/bin/env python3
"""
Backtester — Walk-forward backtesting engine with realistic conditions.

Tests proven strategies against historical Binance klines data with:
- Walk-forward approach (no look-ahead bias)
- Entry/exit slippage: 0.05% adverse per side
- Fees: 0.035% per side (AsterDEX taker rate)
- TP/SL checked on every candle after entry
- Time-based exit after 16 hours (64 candles at 15m)
- Max 1 position per symbol at a time
- Position sizing: 1% of current balance per trade

Usage:
    python -m trading.backtester --symbol BTCUSDT --days 30 --balance 1000
    python -m trading.backtester --symbol BTCUSDT,ETHUSDT,SOLUSDT --days 60 --balance 1000
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional
from urllib.request import urlopen
from urllib.error import URLError

from trading.proven_strategies import scan_all_strategies


# ── Constants ─────────────────────────────────────────────────────────

SLIPPAGE_PCT = 0.0005       # 0.05% per side
FEE_PCT = 0.00035           # 0.035% per side (AsterDEX taker)
MAX_HOLD_CANDLES = 64       # 16 hours at 15m intervals
POSITION_SIZE_PCT = 0.01    # 1% of balance per trade
WARMUP_BARS = 100           # Bars needed before first signal check
BINANCE_KLINE_LIMIT = 1000  # Max klines per API request


# ── Data Fetching ─────────────────────────────────────────────────────


def fetch_klines(symbol: str, interval: str = "15m", days: int = 30) -> List:
    """Fetch historical klines from Binance public API.

    Fetches in batches of 1000 to cover the requested period.
    Returns list of raw kline arrays.
    """
    all_klines: List = []

    # Calculate time range
    end_ms = int(time.time() * 1000)
    # Interval in ms (15m = 900,000 ms)
    interval_ms = _interval_to_ms(interval)
    start_ms = end_ms - (days * 24 * 60 * 60 * 1000)

    total_candles_needed = (days * 24 * 60 * 60 * 1000) // interval_ms
    print(f"  Fetching ~{total_candles_needed} candles for {symbol} ({days}d @ {interval})...")

    current_start = start_ms
    batch = 0

    while current_start < end_ms:
        url = (
            f"https://api.binance.com/api/v3/klines"
            f"?symbol={symbol}&interval={interval}"
            f"&startTime={current_start}&endTime={end_ms}"
            f"&limit={BINANCE_KLINE_LIMIT}"
        )

        try:
            with urlopen(url, timeout=30) as resp:
                data = json.loads(resp.read().decode())
        except URLError as e:
            print(f"  [ERROR] Failed to fetch klines batch {batch}: {e}")
            break

        if not data:
            break

        all_klines.extend(data)
        batch += 1

        # Move start past the last candle we received
        last_close_time = data[-1][6]  # close_time field
        current_start = last_close_time + 1

        if len(data) < BINANCE_KLINE_LIMIT:
            # We got fewer than requested — no more data available
            break

        # Rate limiting — be polite to the free API
        time.sleep(0.2)

    print(f"  Fetched {len(all_klines)} candles in {batch} batch(es)")
    return all_klines


def _interval_to_ms(interval: str) -> int:
    """Convert interval string to milliseconds."""
    multipliers = {
        "m": 60_000,
        "h": 3_600_000,
        "d": 86_400_000,
    }
    unit = interval[-1]
    value = int(interval[:-1])
    return value * multipliers.get(unit, 60_000)


# ── Position & Trade Tracking ─────────────────────────────────────────


@dataclass
class Position:
    symbol: str
    direction: str          # "LONG" or "SHORT"
    strategy: str
    entry_price: float      # After slippage
    raw_entry_price: float  # Before slippage (signal price)
    take_profit: float
    stop_loss: float
    size_usd: float         # Position size in USD
    entry_bar: int          # Bar index at entry
    entry_time: int         # Candle open time (ms)
    confidence: float


@dataclass
class ClosedTrade:
    symbol: str
    direction: str
    strategy: str
    entry_price: float
    exit_price: float
    raw_exit_price: float   # Before slippage
    take_profit: float
    stop_loss: float
    size_usd: float
    pnl_usd: float
    pnl_pct: float
    entry_bar: int
    exit_bar: int
    entry_time: int
    exit_time: int
    exit_reason: str        # "TP", "SL", "TIME"
    confidence: float
    hold_candles: int


@dataclass
class BacktestResult:
    symbol: str
    days: int
    total_candles: int
    trades: List[ClosedTrade] = field(default_factory=list)
    equity_curve: List[float] = field(default_factory=list)
    initial_balance: float = 1000.0
    final_balance: float = 1000.0


# ── Core Backtesting Engine ───────────────────────────────────────────


def run_backtest(symbol: str, klines: List, initial_balance: float = 1000.0,
                 days: int = 30) -> BacktestResult:
    """Run walk-forward backtest on a single symbol."""
    result = BacktestResult(
        symbol=symbol,
        days=days,
        total_candles=len(klines),
        initial_balance=initial_balance,
        final_balance=initial_balance,
    )

    balance = initial_balance
    open_position: Optional[Position] = None
    result.equity_curve.append(balance)

    total_bars = len(klines)
    if total_bars < WARMUP_BARS + 10:
        print(f"  [WARN] Only {total_bars} candles — need at least {WARMUP_BARS + 10}. Skipping.")
        return result

    print(f"  Running walk-forward backtest on {symbol}: {total_bars} bars...")

    for i in range(WARMUP_BARS, total_bars):
        candle = klines[i]
        candle_high = float(candle[2])
        candle_low = float(candle[3])
        candle_close = float(candle[4])
        candle_open_time = int(candle[0])

        # ── Check open position for TP/SL/time exit ──
        if open_position is not None:
            exit_reason = None
            raw_exit_price = None

            hold_candles = i - open_position.entry_bar

            if open_position.direction == "LONG":
                # Check SL first (worst case), then TP
                if candle_low <= open_position.stop_loss:
                    exit_reason = "SL"
                    raw_exit_price = open_position.stop_loss
                elif candle_high >= open_position.take_profit:
                    exit_reason = "TP"
                    raw_exit_price = open_position.take_profit
                elif hold_candles >= MAX_HOLD_CANDLES:
                    exit_reason = "TIME"
                    raw_exit_price = candle_close
            else:  # SHORT
                # Check SL first (worst case), then TP
                if candle_high >= open_position.stop_loss:
                    exit_reason = "SL"
                    raw_exit_price = open_position.stop_loss
                elif candle_low <= open_position.take_profit:
                    exit_reason = "TP"
                    raw_exit_price = open_position.take_profit
                elif hold_candles >= MAX_HOLD_CANDLES:
                    exit_reason = "TIME"
                    raw_exit_price = candle_close

            if exit_reason is not None:
                # Apply exit slippage (adverse)
                if open_position.direction == "LONG":
                    exit_price = raw_exit_price * (1 - SLIPPAGE_PCT)
                else:
                    exit_price = raw_exit_price * (1 + SLIPPAGE_PCT)

                # Deduct exit fee
                exit_fee = open_position.size_usd * FEE_PCT

                # Calculate PnL
                if open_position.direction == "LONG":
                    price_change_pct = (exit_price - open_position.entry_price) / open_position.entry_price
                else:
                    price_change_pct = (open_position.entry_price - exit_price) / open_position.entry_price

                gross_pnl = open_position.size_usd * price_change_pct
                # Entry fee was already deducted at open; deduct exit fee now
                net_pnl = gross_pnl - exit_fee

                balance += net_pnl

                trade = ClosedTrade(
                    symbol=open_position.symbol,
                    direction=open_position.direction,
                    strategy=open_position.strategy,
                    entry_price=open_position.entry_price,
                    exit_price=exit_price,
                    raw_exit_price=raw_exit_price,
                    take_profit=open_position.take_profit,
                    stop_loss=open_position.stop_loss,
                    size_usd=open_position.size_usd,
                    pnl_usd=round(net_pnl, 4),
                    pnl_pct=round(price_change_pct * 100 - FEE_PCT * 200, 4),
                    entry_bar=open_position.entry_bar,
                    exit_bar=i,
                    entry_time=open_position.entry_time,
                    exit_time=candle_open_time,
                    exit_reason=exit_reason,
                    confidence=open_position.confidence,
                    hold_candles=hold_candles,
                )
                result.trades.append(trade)
                result.equity_curve.append(round(balance, 4))
                open_position = None

            continue  # Whether we closed or not, don't open new position this bar

        # ── No open position — scan for signals ──
        if balance <= 0:
            continue

        signals = scan_all_strategies(symbol, klines[:i + 1])
        if not signals:
            continue

        # Pick best signal (highest confidence)
        signals.sort(key=lambda s: s.get("confidence", 0), reverse=True)
        best = signals[0]

        # Position sizing: 1% of current balance
        size_usd = balance * POSITION_SIZE_PCT

        # Apply entry slippage (adverse)
        raw_entry = best["entry_price"]
        if best["direction"] == "LONG":
            entry_price = raw_entry * (1 + SLIPPAGE_PCT)
        else:
            entry_price = raw_entry * (1 - SLIPPAGE_PCT)

        # Deduct entry fee from balance
        entry_fee = size_usd * FEE_PCT
        balance -= entry_fee

        open_position = Position(
            symbol=symbol,
            direction=best["direction"],
            strategy=best["strategy"],
            entry_price=entry_price,
            raw_entry_price=raw_entry,
            take_profit=best["take_profit"],
            stop_loss=best["stop_loss"],
            size_usd=size_usd,
            entry_bar=i,
            entry_time=candle_open_time,
            confidence=best.get("confidence", 0.5),
        )

    # Force-close any remaining open position at last candle close
    if open_position is not None:
        last_candle = klines[-1]
        raw_exit_price = float(last_candle[4])
        if open_position.direction == "LONG":
            exit_price = raw_exit_price * (1 - SLIPPAGE_PCT)
        else:
            exit_price = raw_exit_price * (1 + SLIPPAGE_PCT)

        exit_fee = open_position.size_usd * FEE_PCT

        if open_position.direction == "LONG":
            price_change_pct = (exit_price - open_position.entry_price) / open_position.entry_price
        else:
            price_change_pct = (open_position.entry_price - exit_price) / open_position.entry_price

        gross_pnl = open_position.size_usd * price_change_pct
        net_pnl = gross_pnl - exit_fee
        balance += net_pnl
        hold_candles = len(klines) - 1 - open_position.entry_bar

        trade = ClosedTrade(
            symbol=open_position.symbol,
            direction=open_position.direction,
            strategy=open_position.strategy,
            entry_price=open_position.entry_price,
            exit_price=exit_price,
            raw_exit_price=raw_exit_price,
            take_profit=open_position.take_profit,
            stop_loss=open_position.stop_loss,
            size_usd=open_position.size_usd,
            pnl_usd=round(net_pnl, 4),
            pnl_pct=round(price_change_pct * 100 - FEE_PCT * 200, 4),
            entry_bar=open_position.entry_bar,
            exit_bar=len(klines) - 1,
            entry_time=open_position.entry_time,
            exit_time=int(last_candle[0]),
            exit_reason="END",
            confidence=open_position.confidence,
            hold_candles=hold_candles,
        )
        result.trades.append(trade)
        result.equity_curve.append(round(balance, 4))

    result.final_balance = round(balance, 4)
    return result


# ── Metrics Computation ───────────────────────────────────────────────


def compute_metrics(result: BacktestResult) -> Dict:
    """Compute performance metrics from backtest result."""
    trades = result.trades

    if not trades:
        return {
            "symbol": result.symbol,
            "days": result.days,
            "total_candles": result.total_candles,
            "total_trades": 0,
            "wins": 0,
            "losses": 0,
            "win_rate": 0.0,
            "total_pnl_usd": 0.0,
            "total_pnl_pct": 0.0,
            "avg_win_usd": 0.0,
            "avg_loss_usd": 0.0,
            "profit_factor": 0.0,
            "max_drawdown_pct": 0.0,
            "sharpe_ratio": 0.0,
            "initial_balance": result.initial_balance,
            "final_balance": result.final_balance,
            "equity_curve": result.equity_curve,
            "trades": [],
        }

    wins = [t for t in trades if t.pnl_usd > 0]
    losses = [t for t in trades if t.pnl_usd <= 0]

    total_pnl = sum(t.pnl_usd for t in trades)
    total_pnl_pct = ((result.final_balance - result.initial_balance)
                     / result.initial_balance * 100)

    gross_wins = sum(t.pnl_usd for t in wins) if wins else 0.0
    gross_losses = abs(sum(t.pnl_usd for t in losses)) if losses else 0.0

    avg_win = gross_wins / len(wins) if wins else 0.0
    avg_loss = gross_losses / len(losses) if losses else 0.0

    profit_factor = (gross_wins / gross_losses) if gross_losses > 0 else float("inf")

    # Max drawdown from equity curve
    max_dd_pct = _compute_max_drawdown(result.equity_curve)

    # Sharpe ratio from daily returns (approximate)
    sharpe = _compute_sharpe(trades, result.initial_balance)

    # Strategy breakdown
    strategy_stats: Dict[str, Dict] = {}
    for t in trades:
        s = t.strategy
        if s not in strategy_stats:
            strategy_stats[s] = {"trades": 0, "wins": 0, "pnl": 0.0}
        strategy_stats[s]["trades"] += 1
        if t.pnl_usd > 0:
            strategy_stats[s]["wins"] += 1
        strategy_stats[s]["pnl"] += t.pnl_usd

    # Exit reason breakdown
    exit_reasons: Dict[str, int] = {}
    for t in trades:
        exit_reasons[t.exit_reason] = exit_reasons.get(t.exit_reason, 0) + 1

    return {
        "symbol": result.symbol,
        "days": result.days,
        "total_candles": result.total_candles,
        "total_trades": len(trades),
        "wins": len(wins),
        "losses": len(losses),
        "win_rate": round(len(wins) / len(trades) * 100, 2),
        "total_pnl_usd": round(total_pnl, 4),
        "total_pnl_pct": round(total_pnl_pct, 4),
        "avg_win_usd": round(avg_win, 4),
        "avg_loss_usd": round(avg_loss, 4),
        "profit_factor": round(profit_factor, 4) if profit_factor != float("inf") else "Inf",
        "max_drawdown_pct": round(max_dd_pct, 4),
        "sharpe_ratio": round(sharpe, 4),
        "initial_balance": result.initial_balance,
        "final_balance": result.final_balance,
        "equity_curve": result.equity_curve,
        "strategy_breakdown": {
            k: {
                "trades": v["trades"],
                "wins": v["wins"],
                "win_rate": round(v["wins"] / v["trades"] * 100, 2) if v["trades"] > 0 else 0,
                "pnl": round(v["pnl"], 4),
            }
            for k, v in strategy_stats.items()
        },
        "exit_reasons": exit_reasons,
        "trades": [
            {
                "strategy": t.strategy,
                "direction": t.direction,
                "entry_price": t.entry_price,
                "exit_price": t.exit_price,
                "tp": t.take_profit,
                "sl": t.stop_loss,
                "pnl_usd": t.pnl_usd,
                "pnl_pct": t.pnl_pct,
                "exit_reason": t.exit_reason,
                "hold_candles": t.hold_candles,
                "confidence": t.confidence,
                "entry_time": datetime.fromtimestamp(
                    t.entry_time / 1000, tz=timezone.utc
                ).strftime("%Y-%m-%d %H:%M"),
                "exit_time": datetime.fromtimestamp(
                    t.exit_time / 1000, tz=timezone.utc
                ).strftime("%Y-%m-%d %H:%M"),
            }
            for t in trades
        ],
    }


def _compute_max_drawdown(equity_curve: List[float]) -> float:
    """Max drawdown as a percentage from peak."""
    if len(equity_curve) < 2:
        return 0.0

    peak = equity_curve[0]
    max_dd = 0.0

    for val in equity_curve:
        if val > peak:
            peak = val
        dd = (peak - val) / peak * 100 if peak > 0 else 0.0
        if dd > max_dd:
            max_dd = dd

    return max_dd


def _compute_sharpe(trades: List[ClosedTrade], initial_balance: float,
                    risk_free_annual: float = 0.05) -> float:
    """Approximate Sharpe ratio using per-trade returns, annualized.

    Groups trades by calendar day, computes daily PnL, then annualizes.
    """
    if len(trades) < 2:
        return 0.0

    # Group PnL by exit day
    daily_pnl: Dict[str, float] = {}
    for t in trades:
        day = datetime.fromtimestamp(
            t.exit_time / 1000, tz=timezone.utc
        ).strftime("%Y-%m-%d")
        daily_pnl[day] = daily_pnl.get(day, 0.0) + t.pnl_usd

    if len(daily_pnl) < 2:
        return 0.0

    # Convert to daily returns as percentage of initial balance
    daily_returns = [pnl / initial_balance for pnl in daily_pnl.values()]

    mean_return = sum(daily_returns) / len(daily_returns)
    variance = sum((r - mean_return) ** 2 for r in daily_returns) / (len(daily_returns) - 1)
    std_dev = math.sqrt(variance) if variance > 0 else 0.0

    if std_dev == 0:
        return 0.0

    daily_rf = risk_free_annual / 365
    sharpe = (mean_return - daily_rf) / std_dev * math.sqrt(365)
    return sharpe


# ── Output ────────────────────────────────────────────────────────────


def print_summary(metrics: Dict) -> None:
    """Print a formatted summary table to stdout."""
    print("\n" + "=" * 65)
    print(f"  BACKTEST RESULTS: {metrics['symbol']}")
    print(f"  Period: {metrics['days']} days | Candles: {metrics['total_candles']}")
    print("=" * 65)

    if metrics["total_trades"] == 0:
        print("  No trades generated during this period.")
        print("=" * 65)
        return

    print(f"  {'Metric':<30} {'Value':>20}")
    print(f"  {'-' * 30} {'-' * 20}")

    rows = [
        ("Total Trades", str(metrics["total_trades"])),
        ("Wins / Losses", f"{metrics['wins']} / {metrics['losses']}"),
        ("Win Rate", f"{metrics['win_rate']}%"),
        ("Total PnL ($)", f"${metrics['total_pnl_usd']:+.4f}"),
        ("Total PnL (%)", f"{metrics['total_pnl_pct']:+.4f}%"),
        ("Avg Win ($)", f"${metrics['avg_win_usd']:.4f}"),
        ("Avg Loss ($)", f"${metrics['avg_loss_usd']:.4f}"),
        ("Profit Factor", str(metrics["profit_factor"])),
        ("Max Drawdown (%)", f"{metrics['max_drawdown_pct']:.4f}%"),
        ("Sharpe Ratio", f"{metrics['sharpe_ratio']:.4f}"),
        ("Initial Balance", f"${metrics['initial_balance']:.2f}"),
        ("Final Balance", f"${metrics['final_balance']:.2f}"),
    ]

    for label, value in rows:
        print(f"  {label:<30} {value:>20}")

    # Strategy breakdown
    if "strategy_breakdown" in metrics:
        print(f"\n  {'Strategy Breakdown':^50}")
        print(f"  {'-' * 50}")
        for strat, stats in metrics["strategy_breakdown"].items():
            print(f"  {strat:<35} {stats['wins']}/{stats['trades']} "
                  f"({stats['win_rate']}%) PnL: ${stats['pnl']:+.4f}")

    # Exit reasons
    if "exit_reasons" in metrics:
        print(f"\n  {'Exit Reasons':^50}")
        print(f"  {'-' * 50}")
        for reason, count in sorted(metrics["exit_reasons"].items()):
            pct = count / metrics["total_trades"] * 100
            print(f"  {reason:<10} {count:>5} ({pct:.1f}%)")

    print("=" * 65)


def save_results(all_metrics: List[Dict], output_path: str) -> None:
    """Save full results to JSON file."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    output = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "engine": "backtester v1.0",
        "costs": {
            "slippage_per_side": f"{SLIPPAGE_PCT * 100}%",
            "fee_per_side": f"{FEE_PCT * 100}%",
            "total_round_trip": f"{(SLIPPAGE_PCT + FEE_PCT) * 2 * 100}%",
        },
        "settings": {
            "position_size_pct": POSITION_SIZE_PCT,
            "max_hold_candles": MAX_HOLD_CANDLES,
            "warmup_bars": WARMUP_BARS,
        },
        "results": all_metrics,
    }

    with open(output_path, "w") as f:
        json.dump(output, f, indent=2, default=str)

    print(f"\n  Results saved to {output_path}")


# ── CLI Entry Point ───────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Walk-forward backtester with realistic fees and slippage"
    )
    parser.add_argument(
        "--symbol", type=str, default="BTCUSDT",
        help="Comma-separated symbols (e.g., BTCUSDT,ETHUSDT,SOLUSDT)"
    )
    parser.add_argument(
        "--days", type=int, default=30,
        help="Number of days of historical data (default: 30)"
    )
    parser.add_argument(
        "--balance", type=float, default=1000.0,
        help="Starting balance in USD (default: 1000)"
    )
    parser.add_argument(
        "--interval", type=str, default="15m",
        help="Candle interval (default: 15m)"
    )

    args = parser.parse_args()

    symbols = [s.strip().upper() for s in args.symbol.split(",")]

    print("=" * 65)
    print("  AsterDEX Backtester v1.0")
    print(f"  Symbols: {', '.join(symbols)}")
    print(f"  Period: {args.days} days | Interval: {args.interval}")
    print(f"  Balance: ${args.balance:.2f}")
    print(f"  Costs: {SLIPPAGE_PCT*100:.3f}% slippage + {FEE_PCT*100:.3f}% fee per side")
    print("=" * 65)

    all_metrics: List[Dict] = []

    for symbol in symbols:
        print(f"\n--- {symbol} ---")

        # Fetch historical data
        klines = fetch_klines(symbol, interval=args.interval, days=args.days)
        if not klines:
            print(f"  [ERROR] No klines fetched for {symbol}. Skipping.")
            continue

        # Run backtest
        result = run_backtest(symbol, klines, initial_balance=args.balance, days=args.days)

        # Compute and display metrics
        metrics = compute_metrics(result)
        print_summary(metrics)

        all_metrics.append(metrics)

    # Aggregate summary for multi-symbol
    if len(all_metrics) > 1:
        total_trades = sum(m["total_trades"] for m in all_metrics)
        total_wins = sum(m["wins"] for m in all_metrics)
        total_pnl = sum(m["total_pnl_usd"] for m in all_metrics)
        print("\n" + "=" * 65)
        print("  AGGREGATE SUMMARY")
        print("=" * 65)
        print(f"  Symbols tested: {len(all_metrics)}")
        print(f"  Total trades:   {total_trades}")
        if total_trades > 0:
            print(f"  Overall WR:     {total_wins / total_trades * 100:.2f}%")
        print(f"  Total PnL:      ${total_pnl:+.4f}")
        print("=" * 65)

    # Save results
    output_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "data", "backtest_results.json"
    )
    save_results(all_metrics, output_path)


if __name__ == "__main__":
    main()
