#!/usr/bin/env python3
"""
Real-data backtest runner for MIMO Wave 24.

Uses yfinance daily OHLCV, real TP/SL path simulation, walk-forward summary, and
Monte Carlo resampling in line with TESTING_PROTOCOL.MD Layers 1-5.
"""

from __future__ import annotations

import json
import math
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

try:
    import yfinance as yf
except ImportError:
    print("ERROR: yfinance required. Install with: pip install yfinance")
    sys.exit(1)

SCRIPT_DIR = Path(__file__).resolve().parent
DATA_DIR = SCRIPT_DIR / "data"
CACHE_DIR = DATA_DIR / "mimo_wave24_cache"
OUT_FILE = DATA_DIR / "mimo_wave24_backtest_results.json"
DATA_DIR.mkdir(parents=True, exist_ok=True)
CACHE_DIR.mkdir(parents=True, exist_ok=True)

if str(SCRIPT_DIR.parent) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR.parent))

from multi_asset.mimo_wave24_strategies import (  # noqa: E402
    BENCHMARKS,
    STRATEGY_SPECS,
    all_symbols,
    evaluate_strategy,
)


def _download(symbol: str, period: str = "5y", interval: str = "1d") -> pd.DataFrame | None:
    cache_file = CACHE_DIR / f"{symbol.replace('=', '_').replace('^', 'IDX_')}_{interval}.csv"
    now = datetime.now(timezone.utc)
    if cache_file.exists():
        age = now - datetime.fromtimestamp(cache_file.stat().st_mtime, timezone.utc)
        if age < timedelta(hours=12):
            df = pd.read_csv(cache_file, index_col=0, parse_dates=True)
            if not df.empty:
                return df
    try:
        df = yf.download(
            symbol,
            period=period,
            interval=interval,
            auto_adjust=True,
            progress=False,
            threads=False,
        )
    except Exception:
        return None
    if df is None or df.empty:
        return None
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [str(col[0]).title() if isinstance(col, tuple) else str(col).title() for col in df.columns]
    else:
        df.columns = [str(col).title() for col in df.columns]
    required = {"Open", "High", "Low", "Close", "Volume"}
    if not required.issubset(df.columns):
        return None
    df = df.dropna(how="any")
    df.to_csv(cache_file)
    return df


def _direction(signal: dict[str, Any]) -> str:
    raw = str(signal.get("direction") or signal.get("signal_type") or "LONG").upper()
    return "SHORT" if raw in {"SHORT", "SELL", "STRONG_SELL"} else "LONG"


def _simulate_trade(df: pd.DataFrame, signal_index: int, signal: dict[str, Any]) -> dict[str, Any] | None:
    if signal_index >= len(df) - 1:
        return None
    direction = _direction(signal)
    entry_price = float(signal.get("entry_price") or df["Close"].iloc[signal_index])
    take_profit = float(signal.get("take_profit") or np.nan)
    stop_loss = float(signal.get("stop_loss") or np.nan)
    max_hold = int(signal.get("max_hold_days") or 10)
    if not all(np.isfinite([entry_price, take_profit, stop_loss])) or entry_price <= 0:
        return None
    end_idx = min(signal_index + max_hold, len(df) - 1)
    exit_idx = end_idx
    exit_price = float(df["Close"].iloc[end_idx])
    exit_reason = "MAX_HOLD"
    for idx in range(signal_index + 1, end_idx + 1):
        high = float(df["High"].iloc[idx])
        low = float(df["Low"].iloc[idx])
        if direction == "LONG":
            if low <= stop_loss:
                exit_idx = idx
                exit_price = stop_loss
                exit_reason = "SL_HIT"
                break
            if high >= take_profit:
                exit_idx = idx
                exit_price = take_profit
                exit_reason = "TP_HIT"
                break
        else:
            if high >= stop_loss:
                exit_idx = idx
                exit_price = stop_loss
                exit_reason = "SL_HIT"
                break
            if low <= take_profit:
                exit_idx = idx
                exit_price = take_profit
                exit_reason = "TP_HIT"
                break
    pnl_pct = ((exit_price - entry_price) / entry_price * 100.0) if direction == "LONG" else ((entry_price - exit_price) / entry_price * 100.0)
    return {
        "entry_date": str(pd.Timestamp(df.index[signal_index]).date()),
        "exit_date": str(pd.Timestamp(df.index[exit_idx]).date()),
        "entry_price": round(entry_price, 6),
        "exit_price": round(exit_price, 6),
        "direction": direction,
        "pnl_pct": round(pnl_pct, 4),
        "bars_held": int(exit_idx - signal_index),
        "exit_reason": exit_reason,
        "confidence": round(float(signal.get("confidence") or 0.0), 4),
        "risk_reward": round(float(signal.get("risk_reward") or 0.0), 4),
        "reason": str(signal.get("reason") or ""),
    }


def _aggregate(trades: list[dict[str, Any]]) -> dict[str, Any]:
    if not trades:
        return {
            "total_trades": 0,
            "win_rate": 0.0,
            "avg_pnl": 0.0,
            "median_pnl": 0.0,
            "total_return": 0.0,
            "profit_factor": 0.0,
            "sharpe": 0.0,
            "tp_rate": 0.0,
            "sl_rate": 0.0,
            "expire_rate": 0.0,
            "avg_hold_days": 0.0,
            "max_drawdown": 0.0,
        }
    pnls = np.array([float(t["pnl_pct"]) for t in trades], dtype=float)
    wins = pnls[pnls > 0]
    losses = pnls[pnls < 0]
    equity = np.cumsum(pnls)
    peak = np.maximum.accumulate(equity)
    drawdown = equity - peak
    exit_reasons = [t["exit_reason"] for t in trades]
    std = float(np.std(pnls, ddof=1)) if len(pnls) > 1 else 0.0
    sharpe = float(np.mean(pnls) / std * math.sqrt(len(pnls))) if std > 1e-12 else 0.0
    gross_profit = float(wins.sum()) if len(wins) else 0.0
    gross_loss = abs(float(losses.sum())) if len(losses) else 0.0
    return {
        "total_trades": int(len(trades)),
        "win_rate": round(float((pnls > 0).mean() * 100.0), 2),
        "avg_pnl": round(float(np.mean(pnls)), 4),
        "median_pnl": round(float(np.median(pnls)), 4),
        "total_return": round(float(pnls.sum()), 2),
        "profit_factor": round(gross_profit / gross_loss, 2) if gross_loss > 0 else 999.0,
        "sharpe": round(sharpe, 2),
        "tp_rate": round(exit_reasons.count("TP_HIT") / len(exit_reasons) * 100.0, 2),
        "sl_rate": round(exit_reasons.count("SL_HIT") / len(exit_reasons) * 100.0, 2),
        "expire_rate": round(exit_reasons.count("MAX_HOLD") / len(exit_reasons) * 100.0, 2),
        "avg_hold_days": round(float(np.mean([t["bars_held"] for t in trades])), 2),
        "max_drawdown": round(float(drawdown.min()) if len(drawdown) else 0.0, 2),
    }


def _walk_forward(trades: list[dict[str, Any]], benchmark_wr: float, benchmark_pf: float) -> dict[str, Any]:
    if len(trades) < 30:
        return {"pass": False, "reason": "insufficient_trades", "is": {}, "oos": {}, "holdout": {}}
    ordered = sorted(trades, key=lambda t: t["entry_date"])
    n = len(ordered)
    is_end = max(1, int(n * 0.70))
    oos_end = max(is_end + 1, int(n * 0.85))
    is_stats = _aggregate(ordered[:is_end])
    oos_stats = _aggregate(ordered[is_end:oos_end])
    holdout_stats = _aggregate(ordered[oos_end:])
    target_wr = benchmark_wr if benchmark_wr > 0 else 50.0
    target_pf = benchmark_pf if benchmark_pf > 0 else 1.0
    passes = (
        oos_stats.get("total_trades", 0) >= 8
        and oos_stats.get("win_rate", 0.0) >= max(target_wr * 0.90, 48.0 if target_wr <= 0 else target_wr * 0.90)
        and oos_stats.get("profit_factor", 0.0) >= max(1.0, target_pf * 0.90)
        and holdout_stats.get("win_rate", 0.0) >= max(target_wr * 0.85, 45.0 if target_wr <= 0 else target_wr * 0.85)
    )
    return {
        "pass": passes,
        "is": is_stats,
        "oos": oos_stats,
        "holdout": holdout_stats,
    }


def _monte_carlo(trades: list[dict[str, Any]], simulations: int = 5000) -> dict[str, Any]:
    if len(trades) < 10:
        return {"ci_lower": 0.0, "ci_upper": 0.0, "prob_profit": 0.0, "simulations": simulations}
    pnls = np.array([float(t["pnl_pct"]) for t in trades], dtype=float)
    rng = np.random.default_rng(42)
    samples = rng.choice(pnls, size=(simulations, len(pnls)), replace=True).sum(axis=1)
    return {
        "ci_lower": round(float(np.percentile(samples, 2.5)), 2),
        "ci_upper": round(float(np.percentile(samples, 97.5)), 2),
        "prob_profit": round(float((samples > 0).mean() * 100.0), 2),
        "simulations": simulations,
    }


def _required_symbols(spec) -> set[str]:
    required = set(spec.symbols)
    mode = spec.params.get("mode")
    benchmark_key = spec.params.get("benchmark_key")
    if benchmark_key:
        required.add(BENCHMARKS.get(benchmark_key, benchmark_key))
    if mode in {"fear_bid", "bond_vs_equity"}:
        required.add(BENCHMARKS["spy"])
    if mode == "fear_bid":
        required.add(BENCHMARKS["vix"])
    return required


def run_backtest() -> dict[str, Any]:
    started = time.time()
    data: dict[str, pd.DataFrame] = {}
    failures: list[str] = []
    for symbol in all_symbols():
        df = _download(symbol)
        if df is None or len(df) < 260:
            failures.append(symbol)
            continue
        data[symbol] = df

    per_strategy: dict[str, Any] = {}
    per_asset_class: dict[str, list[dict[str, Any]]] = {}
    all_trades: list[dict[str, Any]] = []

    for spec in STRATEGY_SPECS:
        spec_trades: list[dict[str, Any]] = []
        symbol_summaries: list[dict[str, Any]] = []
        relevant_symbols = _required_symbols(spec)
        for symbol in spec.symbols:
            df = data.get(symbol)
            if df is None or len(df) < 260:
                continue
            trades: list[dict[str, Any]] = []
            idx = 250
            while idx < len(df) - 1:
                current_date = df.index[idx]
                history = {
                    key: value.loc[:current_date]
                    for key, value in data.items()
                    if key in relevant_symbols and not value.loc[:current_date].empty
                }
                current_slice = history.get(symbol)
                if current_slice is None or len(current_slice) < 50:
                    idx += 1
                    continue
                try:
                    signals = evaluate_strategy(spec, current_slice, symbol, history)
                except Exception:
                    idx += 1
                    continue
                if not signals:
                    idx += 1
                    continue
                trade = _simulate_trade(df, idx, signals[0])
                if trade is None:
                    idx += 1
                    continue
                trade["strategy"] = spec.strategy_id
                trade["symbol"] = symbol
                trade["asset_class"] = spec.asset_class
                trade["benchmark_wr"] = spec.benchmark_wr
                trade["benchmark_pf"] = spec.benchmark_pf
                trades.append(trade)
                idx += max(1, trade["bars_held"])
            if trades:
                summary = _aggregate(trades)
                summary["symbol"] = symbol
                symbol_summaries.append(summary)
                spec_trades.extend(trades)
        metrics = _aggregate(spec_trades)
        walk_forward = _walk_forward(spec_trades, spec.benchmark_wr, spec.benchmark_pf)
        monte_carlo = _monte_carlo(spec_trades)
        beats_wr = metrics["win_rate"] >= spec.benchmark_wr if spec.benchmark_wr > 0 else True
        beats_pf = metrics["profit_factor"] >= spec.benchmark_pf if spec.benchmark_pf > 0 else metrics["profit_factor"] >= 1.0
        per_strategy[spec.strategy_id] = {
            **metrics,
            "asset_class": spec.asset_class,
            "description": spec.description,
            "benchmark": {
                "win_rate": spec.benchmark_wr,
                "profit_factor": spec.benchmark_pf,
            },
            "beats_benchmark_win_rate": beats_wr,
            "beats_benchmark_profit_factor": beats_pf,
            "beats_benchmark_both": beats_wr and beats_pf,
            "walk_forward": walk_forward,
            "monte_carlo": monte_carlo,
            "symbols_tested": len(spec.symbols),
            "symbols_with_trades": len(symbol_summaries),
            "top_symbols": sorted(symbol_summaries, key=lambda x: (x["total_return"], x["profit_factor"]), reverse=True)[:5],
        }
        per_asset_class.setdefault(spec.asset_class, []).extend(spec_trades)
        all_trades.extend(spec_trades)
        print(f"Completed {spec.strategy_id}: {metrics['total_trades']} trades, WR {metrics['win_rate']}%, PF {metrics['profit_factor']}")

    asset_class_summary: dict[str, Any] = {}
    for asset_class, trades in per_asset_class.items():
        stats = _aggregate(trades)
        strategies = [
            {"strategy": sid, **payload}
            for sid, payload in per_strategy.items()
            if payload["asset_class"] == asset_class
        ]
        beaters = [row["strategy"] for row in strategies if row["beats_benchmark_both"]]
        asset_class_summary[asset_class] = {
            **stats,
            "strategies_total": len(strategies),
            "strategies_beating_benchmark": beaters,
            "beating_count": len(beaters),
            "top_strategy": sorted(
                strategies,
                key=lambda item: (
                    item["beats_benchmark_both"],
                    item["walk_forward"].get("pass", False),
                    item["profit_factor"],
                    item["win_rate"],
                    item["total_return"],
                ),
                reverse=True,
            )[0]["strategy"] if strategies else None,
        }

    best_strategies = sorted(
        (
            {"strategy": strategy_id, **payload}
            for strategy_id, payload in per_strategy.items()
            if payload["total_trades"] > 0
        ),
        key=lambda item: (
            item["beats_benchmark_both"],
            item["walk_forward"].get("pass", False),
            item["profit_factor"],
            item["win_rate"],
            item["total_return"],
        ),
        reverse=True,
    )

    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "elapsed_seconds": round(time.time() - started, 2),
        "symbols_downloaded": len(data),
        "download_failures": failures,
        "overall": _aggregate(all_trades),
        "per_asset_class": asset_class_summary,
        "per_strategy": per_strategy,
        "best_strategies": best_strategies[:15],
    }
    OUT_FILE.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"Wrote {OUT_FILE}")
    print(json.dumps(result["per_asset_class"], indent=2))
    return result


if __name__ == "__main__":
    run_backtest()
