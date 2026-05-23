"""Simulated walk-forward backtest runner for paper trading strategies.

Fetches real historical klines, then walks bar-by-bar from a midpoint
onward, feeding each strategy a sliding window of lookback bars and
tracking hypothetical trades against known future price action.

Usage:
    python -m paper_trading.backtest_runner                  # all strategies
    python -m paper_trading.backtest_runner --strategy williams_r_reversion
    python -m paper_trading.backtest_runner --symbols BTCUSDT ETHUSDT
"""
from __future__ import annotations

import argparse
import logging
import math
import sys
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Type

import numpy as np

from paper_trading.strategies.base_strategy import BaseStrategy
from paper_trading.models import NormalizedPick

logger = logging.getLogger("paper_trading.backtest")

# Default max bars to hold a position before force-closing at market
DEFAULT_MAX_HOLD_BARS = 48

# Annualization factor: 1h bars -> 8760 bars/year
BARS_PER_YEAR_1H = 8760


# ---------------------------------------------------------------------------
# Trade record
# ---------------------------------------------------------------------------

@dataclass
class BacktestTrade:
    symbol: str
    direction: str          # "LONG" or "SHORT"
    entry_bar: int          # index into the full klines array
    entry_price: float
    tp: float
    sl: float
    exit_bar: Optional[int] = None
    exit_price: Optional[float] = None
    exit_reason: str = ""   # "TP", "SL", "MAX_HOLD", "END"
    pnl_pct: float = 0.0


# ---------------------------------------------------------------------------
# Core backtest engine
# ---------------------------------------------------------------------------

def run_backtest(
    strategy: BaseStrategy,
    symbols: Optional[List[str]] = None,
    interval: str = "1h",
    limit: int = 500,
    lookback: int = 250,
    max_hold_bars: int = DEFAULT_MAX_HOLD_BARS,
) -> dict:
    """Run a simulated walk-forward backtest for a single strategy.

    Parameters
    ----------
    strategy : BaseStrategy
        An instantiated strategy object.
    symbols : list[str] | None
        Symbols to test. Falls back to strategy.symbols, then a default set.
    interval : str
        Kline interval (default "1h").
    limit : int
        Total bars to fetch per symbol (default 500).
    lookback : int
        Number of bars in the sliding window fed to the strategy (default 250).
    max_hold_bars : int
        Force-close after this many bars (default 48).

    Returns
    -------
    dict with keys: strategy, trades, total, wins, losses, win_rate,
        avg_pnl_pct, profit_factor, max_drawdown_pct, sharpe, best_trade,
        worst_trade, symbols_tested, bars_walked, signals_fired
    """
    if symbols is None:
        symbols = getattr(strategy, "symbols", None) or [
            "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT",
            "ADAUSDT", "AVAXUSDT", "DOTUSDT", "LINKUSDT", "DOGEUSDT",
        ]

    all_trades: List[BacktestTrade] = []
    symbols_tested = 0
    total_bars_walked = 0
    total_signals_fired = 0

    for sym in symbols:
        # ------------------------------------------------------------------
        # 1. Fetch historical klines
        # ------------------------------------------------------------------
        try:
            klines = strategy.fetch_klines(sym, interval=interval, limit=limit)
        except Exception as exc:
            logger.warning("Failed to fetch %s for %s: %s", sym, strategy.name, exc)
            continue

        if not klines or len(klines) < lookback + 10:
            logger.debug("Skipping %s — only %d bars", sym, len(klines) if klines else 0)
            continue

        symbols_tested += 1
        n_bars = len(klines)

        # ------------------------------------------------------------------
        # 2. Walk forward bar-by-bar from `lookback` to end
        # ------------------------------------------------------------------
        open_trades: List[BacktestTrade] = []

        for bar_idx in range(lookback, n_bars):
            # Current bar OHLCV
            cur_high = float(klines[bar_idx][2])
            cur_low = float(klines[bar_idx][3])
            cur_close = float(klines[bar_idx][4])

            # ---- Check open trades against this bar's H/L ----
            still_open: List[BacktestTrade] = []
            for trade in open_trades:
                bars_held = bar_idx - trade.entry_bar

                hit_tp = False
                hit_sl = False

                if trade.direction == "LONG":
                    hit_tp = cur_high >= trade.tp
                    hit_sl = cur_low <= trade.sl
                else:  # SHORT
                    hit_tp = cur_low <= trade.tp
                    hit_sl = cur_high >= trade.sl

                if hit_sl and hit_tp:
                    # Ambiguous — assume SL hit first (conservative)
                    hit_tp = False

                if hit_tp:
                    trade.exit_bar = bar_idx
                    trade.exit_price = trade.tp
                    trade.exit_reason = "TP"
                    if trade.direction == "LONG":
                        trade.pnl_pct = (trade.tp - trade.entry_price) / trade.entry_price * 100
                    else:
                        trade.pnl_pct = (trade.entry_price - trade.tp) / trade.entry_price * 100
                    all_trades.append(trade)

                elif hit_sl:
                    trade.exit_bar = bar_idx
                    trade.exit_price = trade.sl
                    trade.exit_reason = "SL"
                    if trade.direction == "LONG":
                        trade.pnl_pct = (trade.sl - trade.entry_price) / trade.entry_price * 100
                    else:
                        trade.pnl_pct = (trade.entry_price - trade.sl) / trade.entry_price * 100
                    all_trades.append(trade)

                elif bars_held >= max_hold_bars:
                    trade.exit_bar = bar_idx
                    trade.exit_price = cur_close
                    trade.exit_reason = "MAX_HOLD"
                    if trade.direction == "LONG":
                        trade.pnl_pct = (cur_close - trade.entry_price) / trade.entry_price * 100
                    else:
                        trade.pnl_pct = (trade.entry_price - cur_close) / trade.entry_price * 100
                    all_trades.append(trade)

                else:
                    still_open.append(trade)

            open_trades = still_open

            # ---- Generate signals from the sliding window ----
            window = klines[bar_idx - lookback:bar_idx + 1]  # inclusive of current bar
            try:
                picks = strategy.generate_picks({sym: window})
            except Exception as exc:
                logger.debug("generate_picks error at bar %d: %s", bar_idx, exc)
                continue

            for pick in picks:
                if pick.symbol != sym:
                    continue
                total_signals_fired += 1

                # Skip if we already have an open trade in the same symbol+direction
                already_in = any(
                    t.symbol == sym and t.direction == pick.direction
                    for t in open_trades
                )
                if already_in:
                    continue

                trade = BacktestTrade(
                    symbol=sym,
                    direction=pick.direction,
                    entry_bar=bar_idx,
                    entry_price=pick.entry_price,
                    tp=pick.tp,
                    sl=pick.sl,
                )
                open_trades.append(trade)

            total_bars_walked += 1

        # ---- Close remaining open trades at last bar ----
        last_close = float(klines[-1][4])
        for trade in open_trades:
            trade.exit_bar = n_bars - 1
            trade.exit_price = last_close
            trade.exit_reason = "END"
            if trade.direction == "LONG":
                trade.pnl_pct = (last_close - trade.entry_price) / trade.entry_price * 100
            else:
                trade.pnl_pct = (trade.entry_price - last_close) / trade.entry_price * 100
            all_trades.append(trade)

    # ------------------------------------------------------------------
    # 3. Compute performance metrics
    # ------------------------------------------------------------------
    return _compute_metrics(
        strategy_name=strategy.name,
        display_name=strategy.display_name,
        trades=all_trades,
        symbols_tested=symbols_tested,
        bars_walked=total_bars_walked,
        signals_fired=total_signals_fired,
    )


def _compute_metrics(
    strategy_name: str,
    display_name: str,
    trades: List[BacktestTrade],
    symbols_tested: int,
    bars_walked: int,
    signals_fired: int,
) -> dict:
    """Compute performance metrics from a list of closed trades."""

    total = len(trades)
    if total == 0:
        return {
            "strategy": strategy_name,
            "display_name": display_name,
            "trades": [],
            "total": 0,
            "wins": 0,
            "losses": 0,
            "win_rate": 0.0,
            "avg_pnl_pct": 0.0,
            "profit_factor": 0.0,
            "max_drawdown_pct": 0.0,
            "sharpe": 0.0,
            "best_trade_pct": 0.0,
            "worst_trade_pct": 0.0,
            "symbols_tested": symbols_tested,
            "bars_walked": bars_walked,
            "signals_fired": signals_fired,
        }

    pnls = np.array([t.pnl_pct for t in trades])
    wins = int(np.sum(pnls > 0))
    losses = int(np.sum(pnls <= 0))
    win_rate = wins / total * 100.0

    avg_pnl = float(np.mean(pnls))

    gross_wins = float(np.sum(pnls[pnls > 0])) if wins > 0 else 0.0
    gross_losses = float(np.abs(np.sum(pnls[pnls <= 0]))) if losses > 0 else 0.0
    profit_factor = gross_wins / gross_losses if gross_losses > 0 else float("inf")

    # Max drawdown from equity curve (cumulative PnL)
    equity = np.cumsum(pnls)
    running_max = np.maximum.accumulate(equity)
    drawdowns = running_max - equity
    max_dd = float(np.max(drawdowns)) if len(drawdowns) > 0 else 0.0

    # Sharpe ratio (annualized)
    # Assume each trade ~ 1 bar on average -> use bars_per_year
    std_pnl = float(np.std(pnls, ddof=1)) if total > 1 else 0.0
    if std_pnl > 0:
        sharpe = (avg_pnl / std_pnl) * math.sqrt(BARS_PER_YEAR_1H)
    else:
        sharpe = 0.0

    best_trade = float(np.max(pnls))
    worst_trade = float(np.min(pnls))

    trade_dicts = []
    for t in trades:
        trade_dicts.append({
            "symbol": t.symbol,
            "direction": t.direction,
            "entry_price": round(t.entry_price, 6),
            "exit_price": round(t.exit_price, 6) if t.exit_price else None,
            "tp": round(t.tp, 6),
            "sl": round(t.sl, 6),
            "exit_reason": t.exit_reason,
            "pnl_pct": round(t.pnl_pct, 4),
            "bars_held": (t.exit_bar - t.entry_bar) if t.exit_bar is not None else 0,
        })

    return {
        "strategy": strategy_name,
        "display_name": display_name,
        "trades": trade_dicts,
        "total": total,
        "wins": wins,
        "losses": losses,
        "win_rate": round(win_rate, 2),
        "avg_pnl_pct": round(avg_pnl, 4),
        "profit_factor": round(profit_factor, 3) if profit_factor != float("inf") else 999.0,
        "max_drawdown_pct": round(max_dd, 4),
        "sharpe": round(sharpe, 3),
        "best_trade_pct": round(best_trade, 4),
        "worst_trade_pct": round(worst_trade, 4),
        "symbols_tested": symbols_tested,
        "bars_walked": bars_walked,
        "signals_fired": signals_fired,
    }


# ---------------------------------------------------------------------------
# Batch runner: all "new" strategies (proven + volatility + incubator)
# ---------------------------------------------------------------------------

def run_all_backtests(
    symbols: Optional[List[str]] = None,
    interval: str = "1h",
    limit: int = 500,
    lookback: int = 250,
) -> Dict[str, dict]:
    """Run backtests for ALL paper trading strategies and return a summary dict.

    Returns
    -------
    dict mapping strategy_name -> metrics dict
    """
    from paper_trading.strategies import ALL_STRATEGIES

    results: Dict[str, dict] = {}
    total = len(ALL_STRATEGIES)

    for idx, strat in enumerate(ALL_STRATEGIES, 1):
        logger.info("[%d/%d] Backtesting %s ...", idx, total, strat.display_name)
        t0 = time.time()
        try:
            res = run_backtest(
                strategy=strat,
                symbols=symbols,
                interval=interval,
                limit=limit,
                lookback=lookback,
            )
            elapsed = time.time() - t0
            res["elapsed_sec"] = round(elapsed, 2)
            results[strat.name] = res
            logger.info(
                "  -> %d trades, %.1f%% WR, PF %.2f  (%.1fs)",
                res["total"], res["win_rate"], res["profit_factor"], elapsed,
            )
        except Exception as exc:
            logger.error("  -> FAILED: %s", exc)
            results[strat.name] = {
                "strategy": strat.name,
                "display_name": strat.display_name,
                "error": str(exc),
            }

    return results


# ---------------------------------------------------------------------------
# Report formatting
# ---------------------------------------------------------------------------

def format_backtest_report(results: Dict[str, dict]) -> str:
    """Format backtest results as a readable text table.

    Parameters
    ----------
    results : dict
        Output from run_all_backtests() or a dict of {name: metrics}.

    Returns
    -------
    str — multi-line text table suitable for stdout / logging.
    """
    lines: List[str] = []
    sep = "-" * 120

    lines.append("")
    lines.append(sep)
    lines.append(f"{'STRATEGY':<35} {'TRADES':>6} {'WINS':>5} {'WR%':>7} "
                 f"{'AVG PnL%':>9} {'PF':>7} {'SHARPE':>7} {'MAX DD%':>8} "
                 f"{'BEST%':>7} {'WORST%':>8}")
    lines.append(sep)

    # Sort by win rate descending, then profit factor
    sorted_items = sorted(
        results.items(),
        key=lambda kv: (kv[1].get("win_rate", 0), kv[1].get("profit_factor", 0)),
        reverse=True,
    )

    total_trades = 0
    total_wins = 0

    for name, m in sorted_items:
        if "error" in m:
            lines.append(f"{m.get('display_name', name):<35} {'ERROR':>6}   {m['error']}")
            continue

        t = m.get("total", 0)
        if t == 0:
            lines.append(f"{m.get('display_name', name):<35} {'0':>6}   (no trades)")
            continue

        total_trades += t
        total_wins += m.get("wins", 0)

        pf_str = f"{m['profit_factor']:.2f}" if m["profit_factor"] < 999 else "INF"

        lines.append(
            f"{m.get('display_name', name):<35} "
            f"{t:>6} "
            f"{m['wins']:>5} "
            f"{m['win_rate']:>6.1f}% "
            f"{m['avg_pnl_pct']:>+8.3f}% "
            f"{pf_str:>7} "
            f"{m['sharpe']:>7.2f} "
            f"{m['max_drawdown_pct']:>7.3f}% "
            f"{m['best_trade_pct']:>+6.2f}% "
            f"{m['worst_trade_pct']:>+7.2f}%"
        )

    lines.append(sep)

    overall_wr = (total_wins / total_trades * 100) if total_trades > 0 else 0
    lines.append(
        f"{'TOTAL':<35} {total_trades:>6} {total_wins:>5} {overall_wr:>6.1f}%"
    )
    lines.append(sep)
    lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Simulated walk-forward backtest for paper trading strategies."
    )
    parser.add_argument(
        "--strategy", "-s", type=str, default=None,
        help="Run only this strategy (by name). Omit for all strategies.",
    )
    parser.add_argument(
        "--symbols", nargs="+", type=str, default=None,
        help="Override symbols to test (space-separated).",
    )
    parser.add_argument(
        "--interval", type=str, default="1h",
        help="Kline interval (default: 1h).",
    )
    parser.add_argument(
        "--limit", type=int, default=500,
        help="Total bars to fetch per symbol (default: 500).",
    )
    parser.add_argument(
        "--lookback", type=int, default=250,
        help="Sliding window lookback size (default: 250).",
    )
    parser.add_argument(
        "--max-hold", type=int, default=DEFAULT_MAX_HOLD_BARS,
        help="Max bars to hold a position (default: 48).",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Enable debug logging.",
    )
    args = parser.parse_args()

    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    if args.strategy:
        # Single strategy mode
        from paper_trading.strategies import ALL_STRATEGIES
        strat = None
        for s in ALL_STRATEGIES:
            if s.name == args.strategy:
                strat = s
                break
        if strat is None:
            print(f"ERROR: Strategy '{args.strategy}' not found.", file=sys.stderr)
            print("Available strategies:", file=sys.stderr)
            for s in ALL_STRATEGIES:
                print(f"  {s.name:<40} {s.display_name}", file=sys.stderr)
            sys.exit(1)

        print(f"Backtesting: {strat.display_name} ({strat.name})")
        print(f"Interval: {args.interval}  |  Limit: {args.limit}  |  Lookback: {args.lookback}")
        print()

        result = run_backtest(
            strategy=strat,
            symbols=args.symbols,
            interval=args.interval,
            limit=args.limit,
            lookback=args.lookback,
            max_hold_bars=args.max_hold,
        )

        report = format_backtest_report({strat.name: result})
        print(report)

        # Print individual trades
        if result["total"] > 0 and result["total"] <= 100:
            print(f"Individual trades ({result['total']}):")
            print(f"  {'SYMBOL':<12} {'DIR':<6} {'ENTRY':>12} {'EXIT':>12} "
                  f"{'REASON':<9} {'PnL%':>8} {'BARS':>5}")
            print("  " + "-" * 70)
            for t in result["trades"]:
                print(
                    f"  {t['symbol']:<12} {t['direction']:<6} "
                    f"{t['entry_price']:>12.4f} {t['exit_price']:>12.4f} "
                    f"{t['exit_reason']:<9} {t['pnl_pct']:>+7.3f}% "
                    f"{t['bars_held']:>5}"
                )
            print()

    else:
        # All strategies mode
        print("=" * 60)
        print("  PAPER TRADING BACKTEST RUNNER — ALL STRATEGIES")
        print("=" * 60)
        print(f"Interval: {args.interval}  |  Limit: {args.limit}  |  Lookback: {args.lookback}")
        print()

        results = run_all_backtests(
            symbols=args.symbols,
            interval=args.interval,
            limit=args.limit,
            lookback=args.lookback,
        )

        report = format_backtest_report(results)
        print(report)


if __name__ == "__main__":
    main()
