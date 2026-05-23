"""
Backtest for cross_sectional_crypto_carry baby strategy.
========================================================

Purpose
-------
Cross-sectional carry strategies need a UNIVERSE of symbols to rank, not a
single time series. The repo's default baby_strategies_backtest.py runs each
strategy symbol-by-symbol which loses the cross-sectional signal. This harness
simulates 20 symbols simultaneously with plausible OHLCV and funding rates,
maintains the universe_funding context dict across timesteps, and records
per-symbol trade-level stats.

Output
------
- Updates baby_strategies/cross_sectional_crypto_carry.py.meta.json with
  actual backtest metrics (overwrites the "unbacktested_baby" placeholder).
- Prints a summary table.
- Writes baby_strategies/cross_sectional_crypto_carry.backtest.json with
  per-symbol breakdown.

Usage
-----
    python -m baby_strategies.backtest_cross_sectional_carry
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Dict, List

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from cross_sectional_crypto_carry import (
    CrossSectionalCryptoCarryStrategy,
    SYMBOLS,
)


def _synthetic_price_path(n_bars: int, seed: int, drift: float, vol: float, start: float) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rets = rng.normal(drift, vol, size=n_bars)
    close = start * np.exp(np.cumsum(rets))
    bar_range = np.abs(rets) + rng.exponential(vol * 0.4, n_bars)
    open_ = close * (1 + rng.normal(0, vol * 0.2, n_bars))
    high = np.maximum.reduce([close, open_]) * (1 + bar_range * rng.uniform(0.4, 0.8, n_bars))
    low = np.minimum.reduce([close, open_]) * (1 - bar_range * rng.uniform(0.4, 0.8, n_bars))
    # Funding rate: mean-reverting around zero with occasional extreme spikes
    # Real 8h funding ranges roughly -0.05% to +0.08%.
    fr = rng.normal(0.0001, 0.0003, n_bars)
    # Inject persistent skews on some symbols so cross-sectional ranking is meaningful
    skew = rng.normal(0, 0.0002)
    fr = fr + skew
    return pd.DataFrame({
        "open": open_, "high": high, "low": low, "close": close,
        "volume": rng.lognormal(20, 0.8, n_bars),
        "funding_rate": fr,
    })


def _build_universe(n_bars: int = 600, seed_base: int = 42) -> Dict[str, pd.DataFrame]:
    """Build synthetic OHLCV+funding for the full SYMBOLS universe."""
    out = {}
    for i, sym in enumerate(SYMBOLS):
        start = {"BTC": 60000, "ETH": 3500, "SOL": 150}.get(sym[:3], 100 + i * 5)
        drift = 0.0003 + (i % 5) * 0.0001 - 0.0002
        vol = 0.02 + (i % 7) * 0.005
        out[sym] = _synthetic_price_path(n_bars, seed_base + i, drift, vol, start)
    return out


def run_backtest(
    strat: CrossSectionalCryptoCarryStrategy,
    universe: Dict[str, pd.DataFrame],
    position_pct: float = 0.05,  # 5% per carry leg, market-neutral
    commission: float = 0.0005,
    slippage: float = 0.0003,
    rebalance_every: int = 21,   # ~7 days on 8h bars
) -> dict:
    n_bars = min(len(df) for df in universe.values())
    min_lookback = 80
    positions: Dict[str, dict] = {}
    trades: List[dict] = []

    for i in range(min_lookback, n_bars):
        # Build the universe funding snapshot
        universe_funding = {
            sym: float(df["funding_rate"].iloc[i]) for sym, df in universe.items()
        }
        context = {"universe_funding": universe_funding}

        # Close positions that hit stops or hold-expiry
        for sym in list(positions.keys()):
            pos = positions[sym]
            df = universe[sym]
            curr = float(df["close"].iloc[i])
            if pos["side"] == "LONG":
                pnl_pct = (curr - pos["entry"]) / pos["entry"]
                hit_tp = curr >= pos["tp"]
                hit_sl = curr <= pos["sl"]
            else:
                pnl_pct = (pos["entry"] - curr) / pos["entry"]
                hit_tp = curr <= pos["tp"]
                hit_sl = curr >= pos["sl"]
            expired = (i - pos["entry_bar"]) >= strat.hold_bars
            reason = "TP" if hit_tp else "SL" if hit_sl else "TIME" if expired else None
            if reason:
                pnl_pct -= (commission + slippage) * 2
                trades.append({
                    "symbol": sym, "side": pos["side"], "pnl_pct": pnl_pct,
                    "bars_held": i - pos["entry_bar"], "reason": reason,
                })
                del positions[sym]

        # Open new positions at weekly rebalances only
        if (i - min_lookback) % rebalance_every != 0:
            continue

        for sym, df in universe.items():
            if sym in positions:
                continue
            sub = df.iloc[: i + 1].copy()
            sigs = strat.generate_signals(sub, symbol=sym, context=context)
            if sigs:
                s = sigs[0]
                positions[sym] = {
                    "side": s["side"],
                    "entry": s["entry_price"],
                    "sl": s["stop_loss"],
                    "tp": s["take_profit"],
                    "entry_bar": i,
                }

    # Metrics
    if not trades:
        return {
            "total_trades": 0,
            "win_rate": 0.0, "sharpe": 0.0, "profit_factor": 0.0,
            "mean_pnl_pct": 0.0, "max_dd": 0.0, "total_return": 0.0,
            "per_symbol": {},
            "per_side": {"LONG": {"n": 0, "wr": 0}, "SHORT": {"n": 0, "wr": 0}},
        }

    pnls = np.array([t["pnl_pct"] for t in trades])
    wins = pnls[pnls > 0]
    losses = pnls[pnls <= 0]
    wr = float(len(wins)) / len(pnls)
    mean_pnl = float(pnls.mean())
    pf = float(wins.sum()) / float(abs(losses.sum())) if losses.sum() != 0 else float("inf")
    sharpe = float(mean_pnl / pnls.std()) * np.sqrt(252 * 3) if pnls.std() > 0 else 0.0  # ~3 trades/week

    # Per-symbol + per-side
    per_sym: Dict[str, dict] = {}
    for sym in set(t["symbol"] for t in trades):
        sub = [t for t in trades if t["symbol"] == sym]
        sub_pnls = [t["pnl_pct"] for t in sub]
        per_sym[sym] = {
            "n": len(sub),
            "wr": sum(1 for p in sub_pnls if p > 0) / len(sub),
            "mean_pnl": float(np.mean(sub_pnls)),
        }
    per_side = {}
    for side in ("LONG", "SHORT"):
        sub = [t for t in trades if t["side"] == side]
        sub_pnls = [t["pnl_pct"] for t in sub]
        per_side[side] = {
            "n": len(sub),
            "wr": (sum(1 for p in sub_pnls if p > 0) / len(sub)) if sub else 0,
            "mean_pnl": float(np.mean(sub_pnls)) if sub else 0,
        }

    # Equity + max DD (equal-weight per trade)
    equity = 1.0
    peak = 1.0
    max_dd = 0.0
    for p in pnls:
        equity *= 1 + p * position_pct
        peak = max(peak, equity)
        max_dd = max(max_dd, (peak - equity) / peak)

    return {
        "total_trades": len(trades),
        "win_rate": wr,
        "sharpe": sharpe,
        "profit_factor": pf,
        "mean_pnl_pct": mean_pnl,
        "max_dd": max_dd,
        "total_return": equity - 1.0,
        "per_symbol": per_sym,
        "per_side": per_side,
    }


def main():
    print("Cross-Sectional Crypto Carry — Baby Backtest")
    print("=" * 60)
    strat = CrossSectionalCryptoCarryStrategy()
    t0 = time.time()
    universe = _build_universe(n_bars=600, seed_base=42)
    result = run_backtest(strat, universe)
    dt = time.time() - t0

    print(f"Bars: 600 per symbol × {len(universe)} symbols")
    print(f"Elapsed: {dt:.1f}s")
    print()
    print(f"Total trades:    {result['total_trades']}")
    print(f"Win rate:        {result['win_rate']:.1%}")
    print(f"Mean PnL/trade:  {result['mean_pnl_pct']:+.3%}")
    print(f"Profit factor:   {result['profit_factor']:.2f}")
    print(f"Sharpe:          {result['sharpe']:.2f}")
    print(f"Max DD:          {result['max_dd']:.1%}")
    print(f"Total return:    {result['total_return']:+.2%}")
    print()
    print(f"LONG: n={result['per_side']['LONG']['n']}  WR={result['per_side']['LONG']['wr']:.1%}")
    print(f"SHORT: n={result['per_side']['SHORT']['n']}  WR={result['per_side']['SHORT']['wr']:.1%}")

    # Update .meta.json
    meta_path = Path(__file__).parent / "cross_sectional_crypto_carry.py.meta.json"
    meta = json.loads(meta_path.read_text())
    meta["status"] = "backtested_synthetic" if result["total_trades"] > 0 else "backtest_no_trades"
    meta["backtest_metrics"] = {
        "total_trades": result["total_trades"],
        "win_rate": round(result["win_rate"], 4),
        "sharpe": round(result["sharpe"], 4),
        "profit_factor": round(result["profit_factor"], 4),
        "mean_pnl_pct": round(result["mean_pnl_pct"], 6),
        "max_dd": round(result["max_dd"], 4),
        "total_return": round(result["total_return"], 4),
    }
    meta["batch_tested_at"] = time.strftime("%Y-%m-%dT%H:%M:%S+00:00", time.gmtime())
    meta["backtest_harness"] = "baby_strategies/backtest_cross_sectional_carry.py"
    meta["backtest_notes"] = (
        "Synthetic 600-bar universe (20 symbols). Funding rates modeled as normal "
        "noise + persistent per-symbol skew to produce a realistic cross-sectional "
        "rank. Not a replacement for live-data backtest."
    )
    meta_path.write_text(json.dumps(meta, indent=2) + "\n")
    print(f"\nUpdated {meta_path.name}")

    # Full result dump
    dump_path = Path(__file__).parent / "cross_sectional_crypto_carry.backtest.json"
    dump_path.write_text(json.dumps(result, indent=2) + "\n")
    print(f"Wrote {dump_path.name}")

    return result


if __name__ == "__main__":
    main()
