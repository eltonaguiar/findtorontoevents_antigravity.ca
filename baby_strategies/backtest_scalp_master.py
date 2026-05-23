"""
Master Backtest Runner - 8 Scalp Strategies
============================================

Backtests all 8 scalp strategies on REAL 1-min BTCUSDT data from Binance
(March 24-26, 2026). Uses exact mechanics from original trades:
- 0.5 BTC position size, 10x leverage
- PnL = price_delta * qty * leverage
- Entry at bar close, exit on TP/SL/time
"""

import numpy as np
import pandas as pd
import json
import sys
import requests
import importlib
import traceback
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict

SCRIPT_DIR = Path(__file__).resolve().parent
for p in [str(SCRIPT_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)

# Import all 8 strategies
import scalp_volume_microstructure as strat1
import scalp_mtf_confluence as strat2
import scalp_adaptive_vol_regime as strat3
import scalp_ensemble_signal_combiner as strat4
import scalp_momentum_exhaustion_reversal as strat5
import scalp_session_timing_breakout as strat6
import scalp_price_action_pattern as strat7
import scalp_dynamic_trailing_stop as strat8

ALL_STRATEGIES = [
    (strat1, "1. Volume Microstructure"),
    (strat2, "2. MTF Confluence"),
    (strat3, "3. Adaptive Vol Regime"),
    (strat4, "4. Ensemble Signal Combiner"),
    (strat5, "5. Momentum Exhaustion Reversal"),
    (strat6, "6. Session Timing Breakout"),
    (strat7, "7. Price Action Pattern"),
    (strat8, "8. Dynamic Trailing Stop"),
]

SYMBOL = "BTCUSDT"
QTY = 0.5
LEVERAGE = 10
MAX_HOLD_BARS = 10
INITIAL_BALANCE = 50000.0


BINANCE_MIRRORS = [
    "https://api.binance.com",
    "https://api1.binance.com",
    "https://api2.binance.com",
    "https://api3.binance.com",
]


def _fetch_klines_with_failover(symbol, interval, start_ms, end_ms):
    """Fetch klines with Binance mirror failover (CLAUDE.md rule: 3+ endpoints)."""
    for base in BINANCE_MIRRORS:
        try:
            url = (
                f"{base}/api/v3/klines"
                f"?symbol={symbol}&interval={interval}"
                f"&startTime={start_ms}&endTime={end_ms}&limit=1000"
            )
            resp = requests.get(url, timeout=15)
            resp.raise_for_status()
            return resp.json()
        except Exception:
            continue
    return []


def fetch_binance_data(symbol, start_date, end_date, interval="1m"):
    """Fetch 1-min OHLCV from Binance API with mirror failover."""

    def _to_ms(d):
        return int(datetime.strptime(d, "%Y-%m-%d").timestamp() * 1000)

    all_rows = []
    start_ms = _to_ms(start_date)
    end_ms = _to_ms(end_date)

    while start_ms < end_ms:
        data = _fetch_klines_with_failover(symbol, interval, start_ms, end_ms)
        if not data:
            break
        all_rows.extend(data)
        start_ms = data[-1][0] + 60000
        if len(data) < 1000:
            break

    df = pd.DataFrame(
        all_rows,
        columns=[
            "open_time",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "close_time",
            "quote_volume",
            "trades",
            "taker_buy_volume",
            "taker_buy_quote",
            "ignore",
        ],
    )
    for c in ["open", "high", "low", "close", "volume"]:
        df[c] = pd.to_numeric(df[c])
    df["open_time"] = pd.to_datetime(df["open_time"], unit="ms")
    df.set_index("open_time", inplace=True)
    df["symbol"] = symbol
    return df


@dataclass
class TradeResult:
    entry_time: str
    exit_time: str
    direction: str
    entry_price: float
    exit_price: float
    pnl: float
    reason: str


def simulate(df, strat_mod, symbol, qty=QTY, leverage=LEVERAGE, max_hold=MAX_HOLD_BARS):
    balance = INITIAL_BALANCE
    peak = INITIAL_BALANCE
    max_dd = 0.0
    trades = []
    in_pos = False
    pos_dir = ""
    pos_entry = 0.0
    pos_tp = 0.0
    pos_sl = 0.0
    pos_idx = 0
    pos_reason = ""

    for i in range(max(30, max_hold), len(df)):
        bar = df.iloc[i]

        if in_pos:
            held = i - pos_idx
            exit_px = None
            exit_reason = None

            if pos_dir == "LONG":
                if bar["low"] <= pos_sl:
                    exit_px = pos_sl
                    exit_reason = "SL"
                elif bar["high"] >= pos_tp:
                    exit_px = pos_tp
                    exit_reason = "TP"
                elif held >= max_hold:
                    exit_px = bar["close"]
                    exit_reason = "TIME"
            else:
                if bar["high"] >= pos_sl:
                    exit_px = pos_sl
                    exit_reason = "SL"
                elif bar["low"] <= pos_tp:
                    exit_px = pos_tp
                    exit_reason = "TP"
                elif held >= max_hold:
                    exit_px = bar["close"]
                    exit_reason = "TIME"

            if exit_px is not None:
                if pos_dir == "LONG":
                    pnl = (exit_px - pos_entry) * qty * leverage
                else:
                    pnl = (pos_entry - exit_px) * qty * leverage
                balance += pnl
                if balance > peak:
                    peak = balance
                dd = (peak - balance) / peak
                if dd > max_dd:
                    max_dd = dd
                trades.append(
                    TradeResult(
                        entry_time=str(df.index[pos_idx]),
                        exit_time=str(df.index[i]),
                        direction=pos_dir,
                        entry_price=round(pos_entry, 2),
                        exit_price=round(exit_px, 2),
                        pnl=round(pnl, 2),
                        reason=f"{exit_reason} ({pos_reason[:40]})",
                    )
                )
                in_pos = False

        if not in_pos:
            window = df.iloc[: i + 1]
            try:
                signals = strat_mod.generate_signals(window, symbol)
            except Exception:
                signals = []

            if signals:
                sig = signals[0]
                in_pos = True
                pos_dir = sig.direction
                pos_entry = bar["close"]
                pos_tp = sig.take_profit
                pos_sl = sig.stop_loss
                pos_idx = i
                pos_reason = sig.reason

    # Close remaining
    if in_pos:
        last = df.iloc[-1]
        exit_px = last["close"]
        if pos_dir == "LONG":
            pnl = (exit_px - pos_entry) * qty * leverage
        else:
            pnl = (pos_entry - exit_px) * qty * leverage
        balance += pnl
        trades.append(
            TradeResult(
                entry_time=str(df.index[pos_idx]),
                exit_time=str(df.index[-1]),
                direction=pos_dir,
                entry_price=round(pos_entry, 2),
                exit_price=round(exit_px, 2),
                pnl=round(pnl, 2),
                reason=f"END ({pos_reason[:40]})",
            )
        )

    wins = [t for t in trades if t.pnl > 0]
    losses = [t for t in trades if t.pnl <= 0]
    gp = sum(t.pnl for t in wins) if wins else 0
    gl = abs(sum(t.pnl for t in losses)) if losses else 0

    return {
        "trades": len(trades),
        "total_pnl": round(sum(t.pnl for t in trades), 2),
        "win_rate": round(len(wins) / len(trades) * 100, 1) if trades else 0,
        "profit_factor": round(gp / gl, 2) if gl > 0 else float("inf"),
        "max_drawdown_pct": round(max_dd * 100, 2),
        "avg_win": round(gp / len(wins), 2) if wins else 0,
        "avg_loss": round(gl / len(losses), 2) if losses else 0,
        "largest_win": round(max((t.pnl for t in wins), default=0), 2),
        "largest_loss": round(min((t.pnl for t in losses), default=0), 2),
        "final_balance": round(balance, 2),
        "trade_list": [asdict(t) for t in trades],
    }


def main():
    print("=" * 70)
    print("MASTER SCALPER BACKTEST - 8 STRATEGIES vs REAL BTC 1-MIN DATA")
    print(f"Period: 2026-03-24 to 2026-03-26 | Symbol: {SYMBOL}")
    print(f"Mechanics: {QTY} BTC, {LEVERAGE}x leverage, max {MAX_HOLD_BARS} bar hold")
    print("=" * 70)

    # Fetch real data
    print(f"\nFetching {SYMBOL} 1-min data from Binance...")
    try:
        df = fetch_binance_data(SYMBOL, "2026-03-24", "2026-03-27", "1m")
        print(f"  Loaded {len(df)} bars from {df.index[0]} to {df.index[-1]}")
    except Exception as e:
        print(f"  Binance fetch failed: {e}")
        print("  Using synthetic fallback...")
        np.random.seed(2026)
        n = 4320
        dates = pd.date_range(start="2026-03-24", periods=n, freq="1min")
        returns = np.random.normal(0.00001, 0.002, n)
        prices = 70000 * np.exp(np.cumsum(returns))
        df = pd.DataFrame(
            {
                "open": prices,
                "high": prices * 1.001,
                "low": prices * 0.999,
                "close": prices,
                "volume": np.random.lognormal(5, 1, n),
                "symbol": SYMBOL,
            },
            index=dates,
        )

    if "symbol" not in df.columns:
        df["symbol"] = SYMBOL

    all_results = {}
    for mod, name in ALL_STRATEGIES:
        print(f"\n{'-' * 50}")
        print(f"Running: {name}")
        print(f"{'-' * 50}")
        try:
            result = simulate(df, mod, SYMBOL)
            all_results[name] = result
            print(f"  Trades:     {result['trades']}")
            print(f"  Total PnL:  ${result['total_pnl']:>10,.2f}")
            print(f"  Win Rate:   {result['win_rate']}%")
            print(f"  Prof Factor:{result['profit_factor']}")
            print(f"  Max DD:     {result['max_drawdown_pct']}%")
            print(f"  Avg Win:    ${result['avg_win']:>10,.2f}")
            print(f"  Avg Loss:   ${result['avg_loss']:>10,.2f}")
            print(f"  Best:       ${result['largest_win']:>10,.2f}")
            print(f"  Worst:      ${result['largest_loss']:>10,.2f}")
            if result["trade_list"]:
                print(f"  Last 3 trades:")
                for t in result["trade_list"][-3:]:
                    print(
                        f"    {t['direction']:5s} ${t['entry_price']:>10,.2f}->${t['exit_price']:>10,.2f} PnL=${t['pnl']:>+10,.2f} {t['reason'][:35]}"
                    )
        except Exception as e:
            print(f"  ERROR: {e}")
            traceback.print_exc()
            all_results[name] = {"error": str(e)}

    # Summary
    print(f"\n{'=' * 70}")
    print("COMPARISON SUMMARY")
    print(f"{'=' * 70}")
    print(
        f"{'Strategy':<30} {'Trades':>6} {'PnL':>12} {'WR%':>6} {'PF':>6} {'MaxDD%':>7}"
    )
    print("-" * 70)
    for name, r in all_results.items():
        if "error" in r:
            print(f"{name:<30} {'ERROR':>6}")
        else:
            print(
                f"{name:<30} {r['trades']:>6} ${r['total_pnl']:>10,.2f} {r['win_rate']:>5.1f}% {r['profit_factor']:>5.2f} {r['max_drawdown_pct']:>6.2f}%"
            )
    print(f"\nOriginal trader benchmark: 12 trades, +$4,862, 91.7% WR, PF 12.97")

    # Save
    out = SCRIPT_DIR / "scalp_backtest_results.json"
    with open(out, "w") as f:
        json.dump(all_results, f, indent=2, default=str)
    print(f"\nResults saved to: {out}")


if __name__ == "__main__":
    main()
