"""
Backtest Prop Firm Classic Strategies — Multi-Symbol Multi-Period
=================================================================

Tests all 11 prop firm strategies across 10 symbols and 3 time periods.
Reports: WR, PnL, Max DD, Avg PnL per trade, Profit Factor, Sharpe.

Usage:
    python backtest_prop_firm_classics.py
"""

import json
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))

from baby_strategies.prop_firm_classics import ALL_PROP_STRATEGIES

SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "DOGEUSDT",
           "XRPUSDT", "LTCUSDT", "ADAUSDT", "LINKUSDT", "AVAXUSDT"]

KLINE_COLUMNS = [
    "open_time", "open", "high", "low", "close", "volume",
    "close_time", "qav", "trades", "tbbav", "tbqav", "ignore",
]

TIME_PERIODS = {
    "recent": None,
    "2w_ago": 14,
    "1m_ago": 30,
}


def fetch_historical(symbol, interval="15m", limit=1000, end_time_ms=None):
    url = "https://api.binance.com/api/v3/klines"
    params = {"symbol": symbol, "interval": interval, "limit": limit}
    if end_time_ms is not None:
        params["endTime"] = end_time_ms
    resp = requests.get(url, params=params, timeout=15)
    resp.raise_for_status()
    df = pd.DataFrame(resp.json(), columns=KLINE_COLUMNS)
    for col in ("open", "high", "low", "close", "volume"):
        df[col] = df[col].astype(float)
    df["open_time"] = pd.to_datetime(df["open_time"], unit="ms")
    return df


def simulate_trades(signals_list, df, max_hold_bars=16):
    trades = []
    position = None
    signals_by_bar = {bar_idx: sig for bar_idx, sig in signals_list}

    for bar_idx in range(len(df)):
        price = float(df["close"].iloc[bar_idx])
        high = float(df["high"].iloc[bar_idx])
        low = float(df["low"].iloc[bar_idx])

        if position is not None:
            entry = position["entry_price"]
            hold_bars = bar_idx - position["entry_bar"]
            d = position["direction"]

            hit_tp = (high >= position["tp"]) if d == "BUY" else (low <= position["tp"])
            hit_sl = (low <= position["sl"]) if d == "BUY" else (high >= position["sl"])

            if hit_sl:
                exit_p = position["sl"]
                raw_pct = ((exit_p - entry) / entry * 100) if d == "BUY" else ((entry - exit_p) / entry * 100)
                trades.append({"pnl_pct": raw_pct, "exit_reason": "SL", "hold_bars": hold_bars})
                position = None
                continue
            elif hit_tp:
                exit_p = position["tp"]
                raw_pct = ((exit_p - entry) / entry * 100) if d == "BUY" else ((entry - exit_p) / entry * 100)
                trades.append({"pnl_pct": raw_pct, "exit_reason": "TP", "hold_bars": hold_bars})
                position = None
                continue
            elif hold_bars >= max_hold_bars:
                raw_pct = ((price - entry) / entry * 100) if d == "BUY" else ((entry - price) / entry * 100)
                trades.append({"pnl_pct": raw_pct, "exit_reason": "TIME", "hold_bars": hold_bars})
                position = None
                continue

        if position is None and bar_idx in signals_by_bar:
            sig = signals_by_bar[bar_idx]
            position = {
                "entry_bar": bar_idx, "entry_price": sig.entry_price,
                "tp": sig.take_profit, "sl": sig.stop_loss, "direction": sig.direction,
            }

    return trades


def compute_metrics(trades):
    if not trades:
        return {"total_trades": 0, "win_rate": 0, "avg_pnl_pct": 0,
                "total_pnl_pct": 0, "profit_factor": 0, "max_drawdown_pct": 0,
                "avg_hold_bars": 0, "sharpe": 0}

    pnls = [t["pnl_pct"] for t in trades]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p <= 0]
    total_pnl = sum(pnls)
    gross_profit = sum(wins) if wins else 0
    gross_loss = abs(sum(losses)) if losses else 0.001

    equity = [0]
    for p in pnls:
        equity.append(equity[-1] + p)
    peak = equity[0]
    max_dd = 0
    for e in equity:
        peak = max(peak, e)
        max_dd = max(max_dd, peak - e)

    if len(pnls) > 1 and np.std(pnls) > 0:
        sharpe = (np.mean(pnls) / np.std(pnls)) * np.sqrt(252)
    else:
        sharpe = 0

    return {
        "total_trades": len(trades),
        "win_rate": round(len(wins) / len(trades) * 100, 1),
        "avg_pnl_pct": round(total_pnl / len(trades), 3),
        "total_pnl_pct": round(total_pnl, 2),
        "profit_factor": round(gross_profit / gross_loss, 2),
        "max_drawdown_pct": round(max_dd, 2),
        "avg_hold_bars": round(sum(t["hold_bars"] for t in trades) / len(trades), 1),
        "sharpe": round(sharpe, 2),
    }


def backtest_strategy(strat_cls, df, symbol, max_hold_bars=16):
    """Fast backtest: slide a 200-bar window across data, check signal at each step."""
    signals = []
    window = 200
    step = 5  # Check every 5th bar for speed
    for i in range(window, len(df), step):
        subset = df.iloc[max(0, i - window):i + 1].reset_index(drop=True)
        try:
            sigs = strat_cls.generate_signals(subset, symbol)
        except Exception:
            continue
        if sigs:
            best = max(sigs, key=lambda s: s.confidence)
            signals.append((i, best))
    trades = simulate_trades(signals, df, max_hold_bars)
    return trades, len(signals)


def main():
    print("=" * 90)
    print("  Prop Firm Classic Strategies -- Multi-Symbol Multi-Period Backtest")
    print(f"  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"  Strategies: {len(ALL_PROP_STRATEGIES)} | Symbols: {len(SYMBOLS)} | Periods: {len(TIME_PERIODS)}")
    print("=" * 90)

    all_results = {}

    for period_name, days_ago in TIME_PERIODS.items():
        end_time_ms = None
        if days_ago is not None:
            end_dt = datetime.now(timezone.utc) - timedelta(days=days_ago)
            end_time_ms = int(end_dt.timestamp() * 1000)

        print(f"\n{'='*90}")
        print(f"  PERIOD: {period_name}")
        print(f"{'='*90}")

        period_data = {}
        for sym in SYMBOLS:
            try:
                df = fetch_historical(sym, "15m", 1000, end_time_ms)
                period_data[sym] = df
                date_range = f"{df['open_time'].iloc[0].strftime('%m/%d')}-{df['open_time'].iloc[-1].strftime('%m/%d')}"
                print(f"  + {sym}: {len(df)} bars ({date_range})")
            except Exception as e:
                print(f"  x {sym}: FAILED ({e})")
            time.sleep(0.15)

        for strat in ALL_PROP_STRATEGIES:
            all_trades = []
            total_sigs = 0
            for sym, df in period_data.items():
                trades, n_sigs = backtest_strategy(strat, df, sym)
                all_trades.extend(trades)
                total_sigs += n_sigs

            m = compute_metrics(all_trades)
            key = f"{period_name}|{strat.name}"
            all_results[key] = {
                "period": period_name, "strategy": strat.name,
                "display_name": strat.display_name,
                "metrics": m, "signals": total_sigs,
            }

            tag = "+" if m["win_rate"] >= 50 else "o" if m["win_rate"] >= 40 else "x"
            print(f"  {tag} {strat.display_name:<40} "
                  f"T:{m['total_trades']:>4} | "
                  f"WR:{m['win_rate']:>5.1f}% | "
                  f"AvgPnL:{m['avg_pnl_pct']:>+7.3f}% | "
                  f"PnL:{m['total_pnl_pct']:>+8.2f}% | "
                  f"PF:{m['profit_factor']:>5.2f} | "
                  f"DD:{m['max_drawdown_pct']:>6.2f}% | "
                  f"Sh:{m['sharpe']:>6.2f}")

    # Cross-period summary
    print(f"\n{'='*90}")
    print("  CROSS-PERIOD SUMMARY")
    print(f"{'='*90}")

    strat_summary = {}
    for key, r in all_results.items():
        sname = r["strategy"]
        if sname not in strat_summary:
            strat_summary[sname] = {"name": r["display_name"], "periods": []}
        strat_summary[sname]["periods"].append(r["metrics"])

    final_ranking = []
    for sname, data in strat_summary.items():
        periods = data["periods"]
        active = [p for p in periods if p["total_trades"] > 0]
        if not active:
            final_ranking.append({"name": data["name"], "strategy": sname,
                                  "avg_wr": 0, "avg_pnl": 0, "avg_pf": 0,
                                  "avg_dd": 0, "max_dd": 0, "total_trades": 0,
                                  "periods_profitable": 0, "periods_tested": len(periods),
                                  "avg_sharpe": 0})
            continue

        wrs = [p["win_rate"] for p in active]
        avg_pnls = [p["avg_pnl_pct"] for p in active]
        pfs = [p["profit_factor"] for p in active]
        dds = [p["max_drawdown_pct"] for p in active]
        sharpes = [p["sharpe"] for p in active]
        trades = sum(p["total_trades"] for p in active)
        prof = sum(1 for p in active if p["total_pnl_pct"] > 0)

        final_ranking.append({
            "name": data["name"], "strategy": sname,
            "avg_wr": round(np.mean(wrs), 1),
            "avg_pnl": round(np.mean(avg_pnls), 3),
            "avg_pf": round(np.mean(pfs), 2),
            "avg_dd": round(np.mean(dds), 2),
            "max_dd": round(max(dds), 2),
            "total_trades": trades,
            "periods_profitable": prof,
            "periods_tested": len(periods),
            "avg_sharpe": round(np.mean(sharpes), 2),
        })

    final_ranking.sort(key=lambda r: (r["avg_pnl"], r["avg_wr"]), reverse=True)
    for i, r in enumerate(final_ranking, 1):
        tag = "[OK]" if r["avg_pnl"] > 0 and r["avg_wr"] >= 40 else "[--]"
        print(f"  {i:>2}. {tag} {r['name']:<40} "
              f"AvgWR:{r['avg_wr']:>5.1f}% | "
              f"AvgPnL:{r['avg_pnl']:>+7.3f}% | "
              f"AvgPF:{r['avg_pf']:>5.2f} | "
              f"AvgDD:{r['avg_dd']:>6.2f}% | "
              f"MaxDD:{r['max_dd']:>6.2f}% | "
              f"Sh:{r['avg_sharpe']:>6.2f} | "
              f"Trades:{r['total_trades']:>4} | "
              f"Prof:{r['periods_profitable']}/{r['periods_tested']}")

    # Save results
    results_dir = Path(__file__).parent / "backtest_results"
    results_dir.mkdir(exist_ok=True)
    out_file = results_dir / "prop_firm_classics.json"
    with open(out_file, "w") as f:
        json.dump({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "symbols": SYMBOLS,
            "periods": list(TIME_PERIODS.keys()),
            "results": list(all_results.values()),
            "ranking": final_ranking,
        }, f, indent=2)
    print(f"\n  Results saved to {out_file}")


if __name__ == "__main__":
    main()
