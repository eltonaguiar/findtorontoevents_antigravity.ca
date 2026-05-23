#!/usr/bin/env python3
"""
Multi-Asset Parameter Sweep Backtester
======================================

Tests strategies across BTC/ETH/SOL with multiple TP/SL parameter
combinations. A strategy PASSES if it beats thresholds on ANY asset
with ANY parameter combo. Only eliminated if it fails ALL combos.

Usage:
    python multi_asset_param_sweep.py --db-path crypto_data.db [--agents-dir incubator/agents/claude_opus_batch]
"""

from __future__ import annotations

import importlib.util
import inspect
import json
import sqlite3
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

# ---------- thresholds ----------
MIN_SHARPE = 1.0
MIN_WIN_RATE = 0.45
MAX_DRAWDOWN = 0.20
MIN_TRADES = 10

# ---------- parameter grid ----------
TP_SL_COMBOS = [
    {"tp_atr_mult": 1.5, "sl_atr_mult": 1.0},
    {"tp_atr_mult": 2.0, "sl_atr_mult": 1.5},
    {"tp_atr_mult": 2.5, "sl_atr_mult": 1.0},
    {"tp_atr_mult": 3.0, "sl_atr_mult": 1.5},
    {"tp_atr_mult": 2.0, "sl_atr_mult": 2.0},  # 1:1 RR
]

PAIRS = ["BTC/USDT", "ETH/USDT", "SOL/USDT"]
PAIR_SYMBOLS = {"BTC/USDT": "BTCUSDT", "ETH/USDT": "ETHUSDT", "SOL/USDT": "SOLUSDT"}


@dataclass
class Trade:
    entry_time: str
    exit_time: str
    direction: str
    entry_price: float
    exit_price: float
    pnl: float
    pnl_pct: float
    exit_reason: str
    bars_held: int


@dataclass
class SweepResult:
    strategy_name: str
    agent_id: str
    file_path: str
    pair: str
    params: Dict[str, float]
    status: str
    sharpe: Optional[float]
    win_rate: Optional[float]
    max_drawdown: Optional[float]
    profit_factor: Optional[float]
    total_return: Optional[float]
    total_trades: int
    duration_sec: float
    error: Optional[str] = None


def load_pair_data(db_path: str, pair: str, bars: int = 1808) -> pd.DataFrame:
    query = """
    SELECT pair, timestamp, open, high, low, close, volume
    FROM klines WHERE pair = ? ORDER BY timestamp DESC LIMIT ?
    """
    with sqlite3.connect(db_path) as conn:
        df = pd.read_sql_query(query, conn, params=[pair, bars])
    if df.empty:
        raise RuntimeError(f"No data for {pair}")
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    for c in ("open", "high", "low", "close", "volume"):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.dropna(subset=["timestamp", "open", "high", "low", "close", "volume"])
    return df.sort_values("timestamp").reset_index(drop=True)


def load_strategy_class(py_file: Path) -> Tuple[Optional[type], Optional[str]]:
    try:
        name = f"sweep_{py_file.stem}_{int(time.time_ns() % 1_000_000)}"
        spec = importlib.util.spec_from_file_location(name, py_file)
        if spec is None or spec.loader is None:
            return None, "spec loader unavailable"
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        for k in dir(mod):
            v = getattr(mod, k)
            if isinstance(v, type) and k.endswith("Strategy") and k != "Strategy":
                return v, None
        return None, "No Strategy class found"
    except Exception as exc:
        return None, f"Import error: {exc}"


def infer_side(direction: Any) -> Optional[str]:
    if direction is None:
        return None
    d = str(direction).upper().strip()
    if d.startswith("BUY") or d.startswith("LONG"):
        return "BUY"
    if d.startswith("SELL") or d.startswith("SHORT"):
        return "SELL"
    return None


def simulate_trades(
    signals: list, ohlcv: pd.DataFrame,
    entry_idx: int, max_hold: int = 20,
    commission: float = 0.001,
) -> List[Trade]:
    trades = []
    for sig in signals:
        side = infer_side(getattr(sig, "direction", None))
        if side is None:
            continue
        try:
            entry = float(getattr(sig, "entry_price"))
            tp = float(getattr(sig, "take_profit"))
            sl = float(getattr(sig, "stop_loss"))
        except Exception:
            continue
        if entry <= 0 or tp <= 0 or sl <= 0:
            continue

        last_idx = min(entry_idx + max_hold, len(ohlcv) - 1)
        entry_time = str(ohlcv.iloc[entry_idx]["timestamp"])

        trade = None
        for i in range(entry_idx + 1, last_idx + 1):
            px = float(ohlcv.iloc[i]["close"])
            exit_time = str(ohlcv.iloc[i]["timestamp"])
            bars_held = i - entry_idx
            pos = 0.1

            if side == "BUY":
                if px >= tp:
                    pnl = (tp - entry) * pos * (1 - commission)
                    trade = Trade(entry_time, exit_time, "LONG", entry, tp, pnl, (tp - entry) / entry, "TP", bars_held)
                    break
                if px <= sl:
                    pnl = (sl - entry) * pos * (1 - commission)
                    trade = Trade(entry_time, exit_time, "LONG", entry, sl, pnl, (sl - entry) / entry, "SL", bars_held)
                    break
            else:
                if px <= tp:
                    pnl = (entry - tp) * pos * (1 - commission)
                    trade = Trade(entry_time, exit_time, "SHORT", entry, tp, pnl, (entry - tp) / entry, "TP", bars_held)
                    break
                if px >= sl:
                    pnl = (entry - sl) * pos * (1 - commission)
                    trade = Trade(entry_time, exit_time, "SHORT", entry, sl, pnl, (entry - sl) / entry, "SL", bars_held)
                    break

        if trade is None:
            px = float(ohlcv.iloc[last_idx]["close"])
            exit_time = str(ohlcv.iloc[last_idx]["timestamp"])
            bars_held = last_idx - entry_idx
            pos = 0.1
            if side == "BUY":
                pnl = (px - entry) * pos * (1 - commission)
                pnl_pct = (px - entry) / entry
            else:
                pnl = (entry - px) * pos * (1 - commission)
                pnl_pct = (entry - px) / entry
            trade = Trade(entry_time, exit_time, side, entry, px, pnl, pnl_pct, "TIME", bars_held)

        trades.append(trade)
    return trades


def compute_metrics(pnls: List[float]) -> Dict[str, float]:
    if not pnls:
        return {"sharpe": 0.0, "win_rate": 0.0, "max_drawdown": 1.0, "profit_factor": 0.0, "total_return": 0.0}
    arr = np.array(pnls, dtype=float)
    wins = arr[arr > 0]
    losses = arr[arr <= 0]
    win_rate = float((arr > 0).mean())
    gp = float(wins.sum()) if len(wins) else 0.0
    gl = float(abs(losses.sum())) if len(losses) else 1e-9
    profit_factor = gp / gl if gl > 0 else 999.0
    total_return = float(arr.sum())
    equity = np.cumsum(arr)
    peak = np.maximum.accumulate(equity)
    dd = (peak - equity)
    max_dd = float(dd.max() / max(abs(peak.max()), 1e-9)) if len(dd) else 0.0
    mu = float(arr.mean())
    std = float(arr.std()) if len(arr) > 1 else 1e-9
    sharpe = (mu / std) * np.sqrt(252) if std > 1e-12 else 0.0
    return {
        "sharpe": round(sharpe, 4),
        "win_rate": round(win_rate, 4),
        "max_drawdown": round(max_dd, 4),
        "profit_factor": round(profit_factor, 4),
        "total_return": round(total_return, 4),
    }


def run_strategy_on_pair(
    strategy_cls: type,
    ohlcv: pd.DataFrame,
    pair: str,
    param_combo: Dict[str, float],
    bar_step: int = 2,
    min_bars: int = 80,
    max_hold: int = 20,
    timeout_sec: int = 25,
) -> SweepResult:
    t0 = time.time()
    symbol = PAIR_SYMBOLS.get(pair, "BTCUSDT")

    try:
        strategy = strategy_cls(params=param_combo)
    except Exception:
        try:
            strategy = strategy_cls()
        except Exception as exc:
            return SweepResult(
                strategy_name=strategy_cls.__name__, agent_id="", file_path="",
                pair=pair, params=param_combo, status="error",
                sharpe=None, win_rate=None, max_drawdown=None,
                profit_factor=None, total_return=None, total_trades=0,
                duration_sec=time.time() - t0, error=str(exc),
            )

    # Override TP/SL params if the strategy supports them
    for k, v in param_combo.items():
        if hasattr(strategy, k):
            setattr(strategy, k, v)
        # Also try params dict
        if hasattr(strategy, 'params') and isinstance(strategy.params, dict):
            strategy.params[k] = v

    fn = getattr(strategy, "generate_signals", None)
    if fn is None:
        return SweepResult(
            strategy_name=strategy_cls.__name__, agent_id="", file_path="",
            pair=pair, params=param_combo, status="error",
            sharpe=None, win_rate=None, max_drawdown=None,
            profit_factor=None, total_return=None, total_trades=0,
            duration_sec=time.time() - t0, error="No generate_signals method",
        )

    sig = inspect.signature(fn)
    param_names = list(sig.parameters.keys())

    all_trades: List[Trade] = []
    indices = list(range(min_bars, len(ohlcv) - max_hold, bar_step))

    for idx in indices:
        if time.time() - t0 > timeout_sec:
            break

        data_slice = ohlcv.iloc[:idx + 1].copy()
        kwargs = {}
        for p in param_names:
            if p == "self":
                continue
            elif p == "symbol":
                kwargs[p] = symbol
            elif p in ("data", "btc_data", "data_1h"):
                kwargs[p] = data_slice
            else:
                kwargs[p] = None

        try:
            raw = fn(**kwargs)
        except Exception:
            continue

        signals = raw if isinstance(raw, list) else ([] if raw is None else [raw])
        # Normalize dict signals
        from types import SimpleNamespace
        norm = []
        for s in signals:
            if isinstance(s, dict):
                s = SimpleNamespace(**s)
            if s is not None and infer_side(getattr(s, "direction", None)) is not None:
                norm.append(s)

        if norm:
            trades = simulate_trades(norm, ohlcv, idx, max_hold)
            all_trades.extend(trades)

    pnls = [t.pnl for t in all_trades]
    metrics = compute_metrics(pnls)

    passed = (
        metrics["sharpe"] >= MIN_SHARPE
        and metrics["win_rate"] >= MIN_WIN_RATE
        and metrics["max_drawdown"] <= MAX_DRAWDOWN
        and len(pnls) >= MIN_TRADES
    )

    status = "passed" if passed else ("insufficient_data" if len(pnls) < MIN_TRADES else "failed")

    return SweepResult(
        strategy_name=strategy_cls.__name__,
        agent_id="",
        file_path="",
        pair=pair,
        params=param_combo,
        status=status,
        sharpe=metrics["sharpe"],
        win_rate=metrics["win_rate"],
        max_drawdown=metrics["max_drawdown"],
        profit_factor=metrics["profit_factor"],
        total_return=metrics["total_return"],
        total_trades=len(pnls),
        duration_sec=round(time.time() - t0, 2),
    )


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Multi-asset parameter sweep backtest")
    parser.add_argument("--db-path", default="crypto_data.db")
    parser.add_argument("--agents-dir", nargs="+", default=[
        "incubator/agents/claude_opus_batch",
        "baby_strategies",
    ])
    parser.add_argument("--output", default="incubator/backtest_results/multi_asset_sweep.json")
    parser.add_argument("--bars", type=int, default=1808)
    parser.add_argument("--bar-step", type=int, default=3)
    parser.add_argument("--timeout", type=int, default=25)
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[2]
    db = root / args.db_path

    # Load data for all pairs
    print(f"Loading data from {db}...")
    pair_data = {}
    for pair in PAIRS:
        try:
            pair_data[pair] = load_pair_data(str(db), pair, args.bars)
            print(f"  {pair}: {len(pair_data[pair])} bars")
        except Exception as e:
            print(f"  {pair}: FAILED - {e}")

    # Discover strategy files
    strat_files = []
    for d in args.agents_dir:
        p = root / d
        if p.is_dir():
            strat_files.extend(sorted(p.glob("*.py")))
    strat_files = [f for f in strat_files if f.stem != "__init__" and not f.stem.startswith("_")]
    print(f"\nFound {len(strat_files)} strategy files")

    results = []
    passed_strategies = set()
    failed_strategies = set()
    strategy_best = {}  # strategy_name -> best result

    for i, sf in enumerate(strat_files):
        cls, err = load_strategy_class(sf)
        if cls is None:
            print(f"[{i+1}/{len(strat_files)}] SKIP {sf.stem}: {err}")
            results.append({
                "strategy_name": sf.stem,
                "agent_id": sf.parent.name,
                "file_path": str(sf.relative_to(root)),
                "status": "error",
                "error": err,
            })
            continue

        strategy_name = cls.__name__
        any_pass = False
        best_sharpe = -999
        best_result = None

        for pair in PAIRS:
            if pair not in pair_data:
                continue
            for combo in TP_SL_COMBOS:
                r = run_strategy_on_pair(
                    cls, pair_data[pair], pair, combo,
                    bar_step=args.bar_step, timeout_sec=args.timeout,
                )
                r.agent_id = sf.parent.name
                r.file_path = str(sf.relative_to(root))

                rd = asdict(r)
                results.append(rd)

                if r.status == "passed":
                    any_pass = True
                if r.sharpe is not None and r.sharpe > best_sharpe:
                    best_sharpe = r.sharpe
                    best_result = rd

        if any_pass:
            passed_strategies.add(strategy_name)
            tag = "PASS"
        else:
            failed_strategies.add(strategy_name)
            tag = "FAIL"

        if best_result:
            strategy_best[strategy_name] = best_result

        print(f"[{i+1}/{len(strat_files)}] {tag} {sf.stem} (best Sharpe: {best_sharpe:.2f}, pair: {best_result.get('pair','?') if best_result else '?'})")

    # Write results
    output_path = root / args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    summary = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "db_path": str(db),
        "pairs": PAIRS,
        "param_combos": TP_SL_COMBOS,
        "total_strategies": len(strat_files),
        "passed": len(passed_strategies),
        "failed": len(failed_strategies),
        "passed_list": sorted(passed_strategies),
        "failed_list": sorted(failed_strategies),
        "best_per_strategy": strategy_best,
        "all_results": results,
    }
    output_path.write_text(json.dumps(summary, indent=2, default=str))
    print(f"\nResults written to {output_path}")
    print(f"PASSED: {len(passed_strategies)}/{len(strat_files)}")
    print(f"FAILED: {len(failed_strategies)}/{len(strat_files)}")

    # Print top strategies
    top = sorted(strategy_best.values(), key=lambda x: x.get("sharpe", 0) or 0, reverse=True)[:10]
    print("\nTop 10 by Sharpe:")
    for r in top:
        print(f"  {r['strategy_name']:45s} Sharpe={r['sharpe']:6.2f} WR={r['win_rate']:.1%} Pair={r['pair']} TP={r['params']['tp_atr_mult']} SL={r['params']['sl_atr_mult']}")


if __name__ == "__main__":
    main()
