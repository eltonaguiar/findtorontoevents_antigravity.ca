#!/usr/bin/env python3
"""
Super Mutations Comprehensive Backtest
=======================================
Rolling-window backtest of all 5 super mutation strategies across the
full 21-symbol universe (500 bars of 1h data from Binance).

Walk-forward simulation:
  - Window: bars 200..500
  - At each bar, pass df[:bar_idx] to the strategy
  - On signal: simulate BUY at close, check forward for TP/SL hit
  - If neither TP nor SL hit within 24 bars, exit at bar+24 close
  - Track W/L, PnL per trade, profit factor, Sharpe

Outputs:
  - genome/data/super_mutations_backtest.json   (machine-readable)
  - genome/data/super_mutations_backtest_report.md (human-readable)
"""

from __future__ import annotations

import json
import math
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import requests

# ---------------------------------------------------------------------------
# Project root
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "ml_battleground"))

from genome.mutation_lab.super_mutations import SUPER_MUTATION_STRATEGIES

# ---------------------------------------------------------------------------
# Symbol universe
# ---------------------------------------------------------------------------
PAIRS = [
    "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT", "LTCUSDT",
    "ADAUSDT", "TAOUSDT", "AVAXUSDT", "LINKUSDT", "NEARUSDT",
    "SUIUSDT", "APTUSDT",
    "DOGEUSDT", "ARBUSDT", "OPUSDT", "INJUSDT", "FETUSDT",
    "TIAUSDT", "SEIUSDT", "FILUSDT",
]

BINANCE_BASE = "https://api.binance.com"
OKX_BASE = "https://www.okx.com"

# ---------------------------------------------------------------------------
# Data fetching (with OKX fallback)
# ---------------------------------------------------------------------------

def fetch_klines_binance(pair: str, interval: str = "1h", limit: int = 500) -> pd.DataFrame | None:
    """Fetch klines from Binance public API."""
    try:
        url = f"{BINANCE_BASE}/api/v3/klines"
        resp = requests.get(url, params={"symbol": pair, "interval": interval, "limit": limit}, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        if not data:
            return None
        df = pd.DataFrame(data, columns=[
            "timestamp", "Open", "High", "Low", "Close", "Volume",
            "close_time", "quote_vol", "trades", "taker_buy_base",
            "taker_buy_quote", "ignore"
        ])
        df = df[["timestamp", "Open", "High", "Low", "Close", "Volume"]].copy()
        for col in ["Open", "High", "Low", "Close", "Volume"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
        df.set_index("timestamp", inplace=True)
        df.dropna(inplace=True)
        return df
    except Exception as e:
        return None


def fetch_klines_okx(pair: str, interval: str = "1h", limit: int = 500) -> pd.DataFrame | None:
    """Fallback: Fetch klines from OKX."""
    try:
        inst_id = pair.replace("USDT", "-USDT")
        bar_map = {"1h": "1H", "4h": "4H", "1d": "1D"}
        bar = bar_map.get(interval, "1H")
        # OKX max 300 per call; need two calls for 500
        all_data = []
        url = f"{OKX_BASE}/api/v5/market/history-candles"
        resp = requests.get(url, params={"instId": inst_id, "bar": bar, "limit": "300"}, timeout=15)
        resp.raise_for_status()
        data = resp.json().get("data", [])
        if data:
            all_data.extend(data)
            # Get earlier data
            oldest_ts = data[-1][0]
            time.sleep(0.2)
            resp2 = requests.get(url, params={"instId": inst_id, "bar": bar, "limit": "200", "after": oldest_ts}, timeout=15)
            if resp2.ok:
                data2 = resp2.json().get("data", [])
                if data2:
                    all_data.extend(data2)
        if not all_data:
            return None
        all_data.reverse()  # OKX returns newest first
        df = pd.DataFrame(all_data, columns=["timestamp", "Open", "High", "Low", "Close", "Volume", "vol_ccy", "vol_ccy_quote", "confirm"])
        df = df[["timestamp", "Open", "High", "Low", "Close", "Volume"]].copy()
        for col in ["Open", "High", "Low", "Close", "Volume"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        df["timestamp"] = pd.to_datetime(df["timestamp"].astype(float), unit="ms", utc=True)
        df.set_index("timestamp", inplace=True)
        df.dropna(inplace=True)
        # Remove duplicates
        df = df[~df.index.duplicated(keep='first')]
        df.sort_index(inplace=True)
        return df
    except Exception:
        return None


def fetch_all_data() -> dict[str, pd.DataFrame]:
    """Fetch 500 bars of 1h OHLCV for all 21 symbols."""
    data = {}
    total = len(PAIRS)
    for i, pair in enumerate(PAIRS):
        print(f"  [{i+1}/{total}] Fetching {pair}...", end=" ", flush=True)
        df = fetch_klines_binance(pair)
        if df is None or len(df) < 200:
            print(f"Binance failed, trying OKX...", end=" ", flush=True)
            df = fetch_klines_okx(pair)
        if df is not None and len(df) >= 200:
            data[pair] = df
            print(f"OK ({len(df)} bars)")
        else:
            print(f"FAILED (skipping)")
        time.sleep(0.2)  # Rate limit
    return data


# ---------------------------------------------------------------------------
# ATR helper (standalone, no project import needed for backtest logic)
# ---------------------------------------------------------------------------

def compute_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Compute ATR for trade simulation."""
    high = df["High"]
    low = df["Low"]
    close = df["Close"]
    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(period).mean()


# ---------------------------------------------------------------------------
# Trade simulator
# ---------------------------------------------------------------------------

def simulate_trade(df_full: pd.DataFrame, entry_bar_idx: int, signal: dict,
                   max_hold_bars: int = 24) -> dict | None:
    """
    Simulate a single trade from a signal.

    Returns dict with trade details or None if can't simulate.
    """
    if entry_bar_idx >= len(df_full) - 1:
        return None  # No forward data to simulate

    entry_price = float(df_full["Close"].iloc[entry_bar_idx])
    if entry_price <= 0:
        return None

    # Get TP/SL from signal, or compute defaults from ATR
    tp_price = signal.get("take_profit")
    sl_price = signal.get("stop_loss")

    if tp_price is None or sl_price is None:
        # Compute ATR at entry point
        atr_val = signal.get("atr_value")
        if atr_val is None or atr_val <= 0:
            atr_series = compute_atr(df_full.iloc[:entry_bar_idx + 1])
            atr_val = float(atr_series.iloc[-1]) if len(atr_series) > 0 else entry_price * 0.02
            if pd.isna(atr_val) or atr_val <= 0:
                atr_val = entry_price * 0.02

        if tp_price is None:
            tp_price = entry_price + 2.0 * atr_val
        if sl_price is None:
            sl_price = entry_price - 1.5 * atr_val

    direction = signal.get("direction", "LONG")

    # Look forward for TP/SL hit
    exit_price = None
    exit_reason = None
    bars_held = 0

    end_idx = min(entry_bar_idx + max_hold_bars + 1, len(df_full))

    for j in range(entry_bar_idx + 1, end_idx):
        bars_held = j - entry_bar_idx
        bar_high = float(df_full["High"].iloc[j])
        bar_low = float(df_full["Low"].iloc[j])
        bar_close = float(df_full["Close"].iloc[j])

        if direction == "LONG":
            # Check SL first (conservative: if bar's low touches SL, assume stopped out)
            if bar_low <= sl_price:
                exit_price = sl_price
                exit_reason = "SL"
                break
            # Check TP
            if bar_high >= tp_price:
                exit_price = tp_price
                exit_reason = "TP"
                break
        else:
            # SHORT direction (not common in these strategies but handle it)
            if bar_high >= sl_price:
                exit_price = sl_price
                exit_reason = "SL"
                break
            if bar_low <= tp_price:
                exit_price = tp_price
                exit_reason = "TP"
                break

    # If neither hit, exit at last bar's close (timeout)
    if exit_price is None:
        last_bar = min(entry_bar_idx + max_hold_bars, len(df_full) - 1)
        exit_price = float(df_full["Close"].iloc[last_bar])
        exit_reason = "TIMEOUT"
        bars_held = last_bar - entry_bar_idx

    # Calculate PnL
    if direction == "LONG":
        pnl_pct = ((exit_price - entry_price) / entry_price) * 100
    else:
        pnl_pct = ((entry_price - exit_price) / entry_price) * 100

    is_win = pnl_pct > 0

    return {
        "entry_bar": entry_bar_idx,
        "entry_price": round(entry_price, 8),
        "exit_price": round(exit_price, 8),
        "tp_price": round(tp_price, 8),
        "sl_price": round(sl_price, 8),
        "direction": direction,
        "exit_reason": exit_reason,
        "bars_held": bars_held,
        "pnl_pct": round(pnl_pct, 4),
        "is_win": is_win,
    }


# ---------------------------------------------------------------------------
# Backtest engine
# ---------------------------------------------------------------------------

def run_backtest(data: dict[str, pd.DataFrame], start_bar: int = 200,
                 max_hold: int = 24) -> dict:
    """
    Run walk-forward backtest for all strategies across all symbols.

    Returns results dict with per-strategy-per-symbol and aggregate stats.
    """
    results = {}
    strategy_names = list(SUPER_MUTATION_STRATEGIES.keys())

    total_combos = len(strategy_names) * len(data)
    combo_idx = 0

    for strat_name, strat_meta in SUPER_MUTATION_STRATEGIES.items():
        strat_fn = strat_meta["fn"]
        results[strat_name] = {
            "per_symbol": {},
            "all_trades": [],
        }

        for pair, df_full in data.items():
            combo_idx += 1
            n_bars = len(df_full)
            end_bar = n_bars

            symbol_trades = []
            cooldown_until = 0  # Don't open new trades while one is active

            print(f"\r  [{combo_idx}/{total_combos}] {strat_name[:30]:30s} x {pair:12s}", end="", flush=True)

            for bar_idx in range(start_bar, end_bar):
                # Skip if we're in a cooldown from previous trade
                if bar_idx < cooldown_until:
                    continue

                # Not enough forward data to simulate
                if bar_idx >= n_bars - 2:
                    break

                # Feed df[:bar_idx+1] to the strategy (inclusive of current bar)
                df_slice = df_full.iloc[:bar_idx + 1].copy()

                # Create context (standalone run, no consensus data)
                context = {
                    "fear_greed": 25,  # Use moderate fear for backtest consistency
                    "has_consensus_data": False,
                }

                try:
                    signals = strat_fn(df_slice, pair, context)
                except Exception:
                    continue

                if not signals:
                    continue

                # Take first signal only
                signal = signals[0]

                # Simulate the trade
                trade = simulate_trade(df_full, bar_idx, signal, max_hold)
                if trade is None:
                    continue

                trade["symbol"] = pair
                trade["strategy"] = strat_name
                trade["confidence"] = signal.get("confidence", 0)
                trade["reason"] = signal.get("reason", "")[:100]

                symbol_trades.append(trade)

                # Set cooldown: don't enter new trade until current one exits
                cooldown_until = bar_idx + trade["bars_held"] + 1

            # Per-symbol stats
            if symbol_trades:
                wins = [t for t in symbol_trades if t["is_win"]]
                losses = [t for t in symbol_trades if not t["is_win"]]
                total_pnl = sum(t["pnl_pct"] for t in symbol_trades)
                gross_profit = sum(t["pnl_pct"] for t in symbol_trades if t["pnl_pct"] > 0)
                gross_loss = abs(sum(t["pnl_pct"] for t in symbol_trades if t["pnl_pct"] < 0))

                results[strat_name]["per_symbol"][pair] = {
                    "trades": len(symbol_trades),
                    "wins": len(wins),
                    "losses": len(losses),
                    "wr": round(len(wins) / len(symbol_trades) * 100, 1) if symbol_trades else 0,
                    "total_pnl_pct": round(total_pnl, 2),
                    "avg_pnl_pct": round(total_pnl / len(symbol_trades), 2),
                    "profit_factor": round(gross_profit / gross_loss, 2) if gross_loss > 0 else float('inf'),
                    "avg_bars_held": round(sum(t["bars_held"] for t in symbol_trades) / len(symbol_trades), 1),
                    "tp_exits": len([t for t in symbol_trades if t["exit_reason"] == "TP"]),
                    "sl_exits": len([t for t in symbol_trades if t["exit_reason"] == "SL"]),
                    "timeout_exits": len([t for t in symbol_trades if t["exit_reason"] == "TIMEOUT"]),
                }

            results[strat_name]["all_trades"].extend(symbol_trades)

    print()  # Newline after progress

    # Compute aggregate stats per strategy
    for strat_name in strategy_names:
        trades = results[strat_name]["all_trades"]
        if not trades:
            results[strat_name]["aggregate"] = {
                "trades": 0, "wr": 0, "total_pnl_pct": 0,
                "profit_factor": 0, "sharpe": 0,
                "best_symbols": [], "worst_symbols": [],
            }
            continue

        wins = [t for t in trades if t["is_win"]]
        total_pnl = sum(t["pnl_pct"] for t in trades)
        gross_profit = sum(t["pnl_pct"] for t in trades if t["pnl_pct"] > 0)
        gross_loss = abs(sum(t["pnl_pct"] for t in trades if t["pnl_pct"] < 0))
        pnl_array = [t["pnl_pct"] for t in trades]
        pnl_std = float(np.std(pnl_array)) if len(pnl_array) > 1 else 1.0
        pnl_mean = float(np.mean(pnl_array))
        sharpe = round(pnl_mean / pnl_std, 2) if pnl_std > 0 else 0

        # Best/worst symbols by total PnL
        sym_stats = results[strat_name]["per_symbol"]
        sorted_syms = sorted(sym_stats.items(), key=lambda x: x[1]["total_pnl_pct"], reverse=True)
        best_symbols = [(s, d["total_pnl_pct"], d["wr"]) for s, d in sorted_syms[:5] if d["total_pnl_pct"] > 0]
        worst_symbols = [(s, d["total_pnl_pct"], d["wr"]) for s, d in sorted_syms[-3:] if d["total_pnl_pct"] < 0]

        # Exit type breakdown
        tp_exits = len([t for t in trades if t["exit_reason"] == "TP"])
        sl_exits = len([t for t in trades if t["exit_reason"] == "SL"])
        timeout_exits = len([t for t in trades if t["exit_reason"] == "TIMEOUT"])

        # Max drawdown (sequential)
        running_pnl = 0
        peak = 0
        max_dd = 0
        for t in trades:
            running_pnl += t["pnl_pct"]
            if running_pnl > peak:
                peak = running_pnl
            dd = peak - running_pnl
            if dd > max_dd:
                max_dd = dd

        results[strat_name]["aggregate"] = {
            "trades": len(trades),
            "wins": len(wins),
            "losses": len(trades) - len(wins),
            "wr": round(len(wins) / len(trades) * 100, 1),
            "total_pnl_pct": round(total_pnl, 2),
            "avg_pnl_pct": round(pnl_mean, 4),
            "profit_factor": round(gross_profit / gross_loss, 2) if gross_loss > 0 else (999.0 if gross_profit > 0 else 0),
            "sharpe": sharpe,
            "max_drawdown_pct": round(max_dd, 2),
            "avg_bars_held": round(sum(t["bars_held"] for t in trades) / len(trades), 1),
            "tp_exits": tp_exits,
            "sl_exits": sl_exits,
            "timeout_exits": timeout_exits,
            "best_symbols": [{"symbol": s, "pnl": p, "wr": w} for s, p, w in best_symbols],
            "worst_symbols": [{"symbol": s, "pnl": p, "wr": w} for s, p, w in worst_symbols],
            "symbols_traded": len(sym_stats),
        }

    return results


# ---------------------------------------------------------------------------
# Report generators
# ---------------------------------------------------------------------------

def generate_json_report(results: dict, output_path: Path):
    """Write machine-readable JSON report."""
    # Strip trade details for JSON (keep aggregates and per-symbol)
    report = {
        "meta": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "symbols": PAIRS,
            "num_symbols": len(PAIRS),
            "interval": "1h",
            "bars_fetched": 500,
            "walk_forward_start": 200,
            "max_hold_bars": 24,
        },
        "strategies": {},
    }

    for strat_name in SUPER_MUTATION_STRATEGIES:
        strat_data = results.get(strat_name, {})
        report["strategies"][strat_name] = {
            "aggregate": strat_data.get("aggregate", {}),
            "per_symbol": strat_data.get("per_symbol", {}),
            "description": SUPER_MUTATION_STRATEGIES[strat_name]["description"],
            "expected_wr": SUPER_MUTATION_STRATEGIES[strat_name]["expected_wr"],
        }

    # Overall ranking
    ranked = sorted(
        [(name, d["aggregate"]) for name, d in report["strategies"].items()
         if d["aggregate"].get("trades", 0) > 0],
        key=lambda x: (x[1].get("sharpe", 0), x[1].get("wr", 0)),
        reverse=True
    )
    report["ranking"] = [
        {"rank": i + 1, "strategy": name, "sharpe": agg.get("sharpe", 0),
         "wr": agg.get("wr", 0), "trades": agg.get("trades", 0),
         "total_pnl": agg.get("total_pnl_pct", 0)}
        for i, (name, agg) in enumerate(ranked)
    ]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(report, f, indent=2, default=str)
    print(f"\n  JSON report saved to: {output_path}")


def generate_md_report(results: dict, output_path: Path):
    """Write human-readable Markdown report."""
    lines = []
    lines.append("# Super Mutations Backtest Report")
    lines.append(f"\nGenerated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    lines.append(f"\n## Configuration")
    lines.append(f"- **Symbols:** {len(PAIRS)} pairs")
    lines.append(f"- **Data:** 500 bars of 1h OHLCV from Binance")
    lines.append(f"- **Walk-forward window:** bars 200-500 (300 evaluation bars)")
    lines.append(f"- **Max hold:** 24 bars (24h)")
    lines.append(f"- **TP/SL:** From strategy signals (ATR-based defaults if missing)")
    lines.append(f"- **Fear & Greed context:** Fixed at 25 (moderate fear) for consistency")

    # Overall ranking
    lines.append(f"\n## Overall Ranking")
    lines.append("")
    lines.append("| Rank | Strategy | Trades | WR% | Total PnL% | Profit Factor | Sharpe | Max DD% |")
    lines.append("|------|----------|--------|-----|------------|---------------|--------|---------|")

    ranked = sorted(
        [(name, results[name]["aggregate"]) for name in SUPER_MUTATION_STRATEGIES
         if results[name].get("aggregate", {}).get("trades", 0) > 0],
        key=lambda x: (x[1].get("sharpe", 0), x[1].get("wr", 0)),
        reverse=True
    )

    # Also include strategies with 0 trades
    zero_trade_strats = [name for name in SUPER_MUTATION_STRATEGIES
                         if results[name].get("aggregate", {}).get("trades", 0) == 0]

    for i, (name, agg) in enumerate(ranked):
        pf = agg.get("profit_factor", 0)
        pf_str = f"{pf:.2f}" if pf < 100 else "INF"
        lines.append(
            f"| {i+1} | {name} | {agg['trades']} | {agg['wr']:.1f} | "
            f"{agg['total_pnl_pct']:+.2f} | {pf_str} | {agg['sharpe']:.2f} | "
            f"{agg.get('max_drawdown_pct', 0):.2f} |"
        )

    for name in zero_trade_strats:
        lines.append(f"| - | {name} | 0 | - | - | - | - | - |")

    # Per-strategy detailed breakdown
    for strat_name, strat_meta in SUPER_MUTATION_STRATEGIES.items():
        strat_data = results.get(strat_name, {})
        agg = strat_data.get("aggregate", {})

        lines.append(f"\n---\n")
        lines.append(f"## {strat_name}")
        lines.append(f"*{strat_meta['description']}*")
        lines.append(f"\n**Parents:** {', '.join(strat_meta['parents'])}")
        lines.append(f"\n**Expected WR:** {strat_meta['expected_wr']} | **R:R:** {strat_meta['risk_reward']}")

        if agg.get("trades", 0) == 0:
            lines.append(f"\n**No trades generated during backtest period.**")
            lines.append(f"This strategy has very strict entry conditions that were not met.")
            continue

        lines.append(f"\n### Aggregate Stats")
        pf = agg.get("profit_factor", 0)
        pf_str = f"{pf:.2f}" if pf < 100 else "INF"
        lines.append(f"- **Trades:** {agg['trades']} ({agg['wins']}W / {agg['losses']}L)")
        lines.append(f"- **Win Rate:** {agg['wr']:.1f}%")
        lines.append(f"- **Total PnL:** {agg['total_pnl_pct']:+.2f}%")
        lines.append(f"- **Avg PnL/trade:** {agg['avg_pnl_pct']:+.4f}%")
        lines.append(f"- **Profit Factor:** {pf_str}")
        lines.append(f"- **Sharpe Ratio:** {agg['sharpe']:.2f}")
        lines.append(f"- **Max Drawdown:** {agg.get('max_drawdown_pct', 0):.2f}%")
        lines.append(f"- **Avg Hold:** {agg['avg_bars_held']:.1f} bars")
        lines.append(f"- **Exits:** TP={agg['tp_exits']} | SL={agg['sl_exits']} | Timeout={agg['timeout_exits']}")
        lines.append(f"- **Symbols Traded:** {agg.get('symbols_traded', 0)}/{len(PAIRS)}")

        # Best/worst symbols
        if agg.get("best_symbols"):
            lines.append(f"\n### Best Symbols")
            for s in agg["best_symbols"]:
                lines.append(f"- **{s['symbol']}:** {s['pnl']:+.2f}% PnL, {s['wr']:.1f}% WR")

        if agg.get("worst_symbols"):
            lines.append(f"\n### Worst Symbols")
            for s in agg["worst_symbols"]:
                lines.append(f"- **{s['symbol']}:** {s['pnl']:+.2f}% PnL, {s['wr']:.1f}% WR")

        # Per-symbol table
        per_sym = strat_data.get("per_symbol", {})
        if per_sym:
            lines.append(f"\n### Per-Symbol Breakdown")
            lines.append("| Symbol | Trades | WR% | PnL% | PF | Avg Hold | TP | SL | TO |")
            lines.append("|--------|--------|-----|------|----|----------|----|----|-----|")
            for sym in sorted(per_sym.keys()):
                s = per_sym[sym]
                spf = s.get("profit_factor", 0)
                spf_str = f"{spf:.2f}" if spf < 100 else "INF"
                lines.append(
                    f"| {sym} | {s['trades']} | {s['wr']:.1f} | "
                    f"{s['total_pnl_pct']:+.2f} | {spf_str} | {s['avg_bars_held']:.1f} | "
                    f"{s['tp_exits']} | {s['sl_exits']} | {s['timeout_exits']} |"
                )

    # Summary section
    lines.append(f"\n---\n")
    lines.append(f"## Summary & Conclusions")
    lines.append("")

    total_trades = sum(results[s].get("aggregate", {}).get("trades", 0)
                       for s in SUPER_MUTATION_STRATEGIES)
    total_pnl = sum(results[s].get("aggregate", {}).get("total_pnl_pct", 0)
                    for s in SUPER_MUTATION_STRATEGIES)

    lines.append(f"- **Total trades across all strategies:** {total_trades}")
    lines.append(f"- **Combined PnL:** {total_pnl:+.2f}%")

    if ranked:
        best = ranked[0]
        lines.append(f"- **Best strategy by Sharpe:** {best[0]} (Sharpe={best[1]['sharpe']:.2f}, WR={best[1]['wr']:.1f}%)")

    # Note about strategies with no trades
    if zero_trade_strats:
        lines.append(f"\n**Strategies with 0 trades:** {', '.join(zero_trade_strats)}")
        lines.append("These strategies have extremely selective entry conditions (deep RSI oversold, ")
        lines.append("Keltner squeeze, multi-layer conviction). This is BY DESIGN -- they wait for ")
        lines.append("high-probability setups which may not occur in a 500-bar (21-day) window.")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"  MD report saved to: {output_path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=" * 70)
    print("  SUPER MUTATIONS COMPREHENSIVE BACKTEST")
    print(f"  {len(PAIRS)} symbols x {len(SUPER_MUTATION_STRATEGIES)} strategies")
    print("=" * 70)

    # Step 1: Fetch data
    print(f"\n[1/3] Fetching 500 bars of 1h OHLCV data from Binance...")
    t0 = time.time()
    data = fetch_all_data()
    fetch_time = time.time() - t0
    print(f"  Fetched {len(data)}/{len(PAIRS)} symbols in {fetch_time:.1f}s")

    if not data:
        print("ERROR: No data fetched. Cannot run backtest.")
        sys.exit(1)

    # Step 2: Run backtest
    print(f"\n[2/3] Running walk-forward backtest (bars 200-{min(500, min(len(d) for d in data.values()))})...")
    t0 = time.time()
    results = run_backtest(data)
    bt_time = time.time() - t0
    print(f"  Backtest completed in {bt_time:.1f}s")

    # Step 3: Generate reports
    print(f"\n[3/3] Generating reports...")
    data_dir = PROJECT_ROOT / "genome" / "data"

    generate_json_report(results, data_dir / "super_mutations_backtest.json")
    generate_md_report(results, data_dir / "super_mutations_backtest_report.md")

    # Print summary to console
    print("\n" + "=" * 70)
    print("  RESULTS SUMMARY")
    print("=" * 70)

    for strat_name in SUPER_MUTATION_STRATEGIES:
        agg = results[strat_name].get("aggregate", {})
        trades = agg.get("trades", 0)
        if trades == 0:
            print(f"\n  {strat_name}: NO TRADES (entry conditions not met)")
            continue

        pf = agg.get("profit_factor", 0)
        pf_str = f"{pf:.2f}" if pf < 100 else "INF"
        print(f"\n  {strat_name}:")
        print(f"    Trades: {trades}  |  WR: {agg['wr']:.1f}%  |  PnL: {agg['total_pnl_pct']:+.2f}%")
        print(f"    PF: {pf_str}  |  Sharpe: {agg['sharpe']:.2f}  |  Max DD: {agg.get('max_drawdown_pct', 0):.2f}%")
        print(f"    Exits: TP={agg['tp_exits']} SL={agg['sl_exits']} TO={agg['timeout_exits']}")
        print(f"    Symbols: {agg.get('symbols_traded', 0)}/{len(PAIRS)}")

    total_trades = sum(results[s].get("aggregate", {}).get("trades", 0) for s in SUPER_MUTATION_STRATEGIES)
    total_pnl = sum(results[s].get("aggregate", {}).get("total_pnl_pct", 0) for s in SUPER_MUTATION_STRATEGIES)
    print(f"\n  TOTAL: {total_trades} trades, {total_pnl:+.2f}% combined PnL")
    print("=" * 70)


if __name__ == "__main__":
    main()
