#!/usr/bin/env python3
"""
Focused real-data backtest for non-crypto, asset-class-specific strategies.

This runner deliberately avoids the repo's older "throw everything in one basket"
approach. It tests only strategies with a plausible structural edge per asset class:

- Equities/ETFs: blue-chip mean reversion, PEAD, gap fills, VIX timing, ETF RS
- Forex: Connors RSI2 forex adaptation, DXY trend alignment
- Commodities/Futures: seasonality, crude mean reversion, gold safe haven,
  equity index gap reversion

Data source: yfinance daily OHLCV
Output: multi_asset/data/focused_noncrypto_backtest_results.json
"""

from __future__ import annotations

import json
import math
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional

import numpy as np
import pandas as pd

try:
    import yfinance as yf
except ImportError:
    print("ERROR: yfinance required. pip install yfinance")
    sys.exit(1)

SCRIPT_DIR = Path(__file__).resolve().parent
DATA_DIR = SCRIPT_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
OUT_FILE = DATA_DIR / "focused_noncrypto_backtest_results.json"

if str(SCRIPT_DIR.parent) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR.parent))

from multi_asset.equity_strategies import (  # noqa: E402
    EQUITY_ETF_SYMBOLS,
    blue_chip_mean_reversion,
    earnings_momentum_pead,
    etf_relative_strength,
    gap_fill_reversion,
    vix_market_timing,
)
from multi_asset.forex_strategies import (  # noqa: E402
    FOREX_PAIRS,
    connors_rsi2_forex,
    dxy_trend_filter,
)
from multi_asset.commodity_futures_strategies import (  # noqa: E402
    COMMODITY_SYMBOLS,
    FUTURES_SYMBOLS,
    commodity_seasonality,
    crude_oil_mean_reversion,
    equity_index_gap_reversion,
    gold_safe_haven,
)


@dataclass(frozen=True)
class StrategySpec:
    strategy_id: str
    asset_class: str
    symbols: tuple[str, ...]
    func: Callable[..., list[dict]]
    context: str = "none"


EQUITY_FOCUS = (
    "AAPL", "MSFT", "GOOGL", "AMZN", "META", "JPM", "V", "PG", "JNJ", "KO",
)
ETF_FOCUS = (
    "SPY", "QQQ", "IWM", "DIA", "XLK", "XLF", "XLE", "XLV", "XLP", "XLU", "TLT", "GLD",
)
FOREX_FOCUS = tuple(FOREX_PAIRS.keys())
COMMODITY_FOCUS = ("GC=F", "SI=F", "CL=F", "NG=F", "HG=F", "CORN", "WEAT", "SOYB")
INDEX_GAP_FOCUS = ("ES=F", "NQ=F", "YM=F", "RTY=F", "SPY", "QQQ")

BENCHMARK_SYMBOLS = ("SPY", "^VIX", "DX-Y.NYB")

STRATEGIES: tuple[StrategySpec, ...] = (
    StrategySpec("blue_chip_mean_reversion", "equity", EQUITY_FOCUS, blue_chip_mean_reversion),
    StrategySpec("earnings_momentum_pead", "equity", EQUITY_FOCUS, earnings_momentum_pead),
    StrategySpec("gap_fill_reversion", "equity", EQUITY_FOCUS + ETF_FOCUS[:4], gap_fill_reversion),
    StrategySpec("vix_market_timing", "etf", ("SPY", "QQQ", "IWM", "DIA"), vix_market_timing, context="vix_spy"),
    StrategySpec("etf_relative_strength", "etf", ETF_FOCUS, etf_relative_strength, context="etf_set"),
    StrategySpec("connors_rsi2_forex", "forex", FOREX_FOCUS, connors_rsi2_forex),
    StrategySpec("dxy_trend_filter", "forex", FOREX_FOCUS, dxy_trend_filter, context="dxy"),
    StrategySpec("commodity_seasonality", "commodity", COMMODITY_FOCUS, commodity_seasonality),
    StrategySpec("crude_oil_mean_reversion", "commodity", ("CL=F", "NG=F", "XLE"), crude_oil_mean_reversion),
    StrategySpec("gold_safe_haven", "commodity", ("GC=F", "SI=F", "GLD"), gold_safe_haven, context="vix_spy"),
    StrategySpec("equity_index_gap_reversion", "futures", INDEX_GAP_FOCUS, equity_index_gap_reversion),
)


def _info_for_symbol(symbol: str) -> dict[str, Any]:
    if symbol in EQUITY_ETF_SYMBOLS:
        return EQUITY_ETF_SYMBOLS[symbol]
    if symbol in FOREX_PAIRS:
        return FOREX_PAIRS[symbol]
    if symbol in COMMODITY_SYMBOLS:
        return COMMODITY_SYMBOLS[symbol]
    if symbol in FUTURES_SYMBOLS:
        return FUTURES_SYMBOLS[symbol]
    if symbol == "GLD":
        return {"name": "Gold ETF", "cat": "etf"}
    if symbol == "XLE":
        return {"name": "Energy ETF", "cat": "etf"}
    if symbol in {"SPY", "QQQ", "IWM", "DIA"}:
        return {"name": symbol, "cat": "etf"}
    return {"name": symbol, "cat": "unknown"}


def _download(symbol: str, period: str = "5y", interval: str = "1d") -> Optional[pd.DataFrame]:
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
        df.columns = [str(c[0]).title() if isinstance(c, tuple) else str(c).title() for c in df.columns]
    else:
        df.columns = [str(c).title() for c in df.columns]
    required = {"Open", "High", "Low", "Close", "Volume"}
    if not required.issubset(df.columns):
        return None
    return df.dropna(how="any")


def _all_symbols() -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()
    for spec in STRATEGIES:
        for symbol in spec.symbols:
            if symbol not in seen:
                ordered.append(symbol)
                seen.add(symbol)
    for symbol in BENCHMARK_SYMBOLS:
        if symbol not in seen:
            ordered.append(symbol)
            seen.add(symbol)
    return ordered


def _direction(sig: dict[str, Any]) -> str:
    raw = str(sig.get("direction") or sig.get("signal_type") or "LONG").upper()
    return "SHORT" if raw in {"SHORT", "SELL", "STRONG_SELL"} else "LONG"


def _simulate_trade(df: pd.DataFrame, signal_index: int, signal: dict[str, Any]) -> Optional[dict[str, Any]]:
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

    if direction == "LONG":
        pnl_pct = (exit_price - entry_price) / entry_price * 100.0
    else:
        pnl_pct = (entry_price - exit_price) / entry_price * 100.0

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


def _build_kwargs(spec: StrategySpec, history: dict[str, pd.DataFrame]) -> dict[str, Any]:
    if spec.context == "vix_spy":
        return {"vix_data": history.get("^VIX"), "spy_data": history.get("SPY")}
    if spec.context == "dxy":
        return {"dxy_df": history.get("DX-Y.NYB")}
    if spec.context == "etf_set":
        etf_syms = [s for s in ETF_FOCUS if s in history]
        return {"etf_data": {sym: history[sym] for sym in etf_syms}}
    return {}


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
        "profit_factor": round(gross_profit / gross_loss, 2) if gross_loss > 0 else float("inf"),
        "sharpe": round(sharpe, 2),
        "tp_rate": round(exit_reasons.count("TP_HIT") / len(exit_reasons) * 100.0, 2),
        "sl_rate": round(exit_reasons.count("SL_HIT") / len(exit_reasons) * 100.0, 2),
        "expire_rate": round(exit_reasons.count("MAX_HOLD") / len(exit_reasons) * 100.0, 2),
        "avg_hold_days": round(float(np.mean([t["bars_held"] for t in trades])), 2),
        "max_drawdown": round(float(drawdown.min()) if len(drawdown) else 0.0, 2),
    }


def run_backtest() -> dict[str, Any]:
    started = time.time()
    data: dict[str, pd.DataFrame] = {}
    download_errors: list[str] = []

    for symbol in _all_symbols():
        df = _download(symbol)
        if df is None or len(df) < 260:
            download_errors.append(symbol)
            continue
        data[symbol] = df

    strategy_results: dict[str, Any] = {}
    asset_class_buckets: dict[str, list[dict[str, Any]]] = {}
    total_trades: list[dict[str, Any]] = []

    for spec in STRATEGIES:
        spec_trades: list[dict[str, Any]] = []
        symbol_summaries: list[dict[str, Any]] = []

        for symbol in spec.symbols:
            df = data.get(symbol)
            if df is None or len(df) < 260:
                continue
            info = _info_for_symbol(symbol)
            trades: list[dict[str, Any]] = []
            idx = 250

            while idx < len(df) - 1:
                history = {
                    key: value.loc[: df.index[idx]].copy()
                    for key, value in data.items()
                    if len(value.loc[: df.index[idx]]) > 10
                }
                slice_df = history.get(symbol, df.loc[: df.index[idx]].copy())
                try:
                    raw_signals = spec.func(slice_df, symbol, info, **_build_kwargs(spec, history))
                except TypeError:
                    raw_signals = spec.func(slice_df, symbol, info)
                except Exception:
                    idx += 1
                    continue

                if not raw_signals:
                    idx += 1
                    continue

                trade = _simulate_trade(df, idx, raw_signals[0])
                if trade is None:
                    idx += 1
                    continue

                trade["strategy"] = spec.strategy_id
                trade["symbol"] = symbol
                trade["asset_class"] = spec.asset_class
                trades.append(trade)
                idx += max(1, trade["bars_held"])

            if trades:
                summary = _aggregate(trades)
                summary["symbol"] = symbol
                symbol_summaries.append(summary)
                spec_trades.extend(trades)

        strategy_results[spec.strategy_id] = {
            **_aggregate(spec_trades),
            "asset_class": spec.asset_class,
            "symbols_tested": len(spec.symbols),
            "symbols_with_trades": len(symbol_summaries),
            "top_symbols": sorted(symbol_summaries, key=lambda x: x["total_return"], reverse=True)[:5],
        }
        asset_class_buckets.setdefault(spec.asset_class, []).extend(spec_trades)
        total_trades.extend(spec_trades)

    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "elapsed_seconds": round(time.time() - started, 2),
        "symbols_downloaded": len(data),
        "download_failures": download_errors,
        "strategies_tested": [spec.strategy_id for spec in STRATEGIES],
        "overall": _aggregate(total_trades),
        "per_strategy": strategy_results,
        "per_asset_class": {asset_class: _aggregate(trades) for asset_class, trades in asset_class_buckets.items()},
        "best_strategies": sorted(
            (
                {"strategy": name, **stats}
                for name, stats in strategy_results.items()
                if stats["total_trades"] > 0
            ),
            key=lambda x: (x["sharpe"], x["total_return"], x["win_rate"]),
            reverse=True,
        )[:10],
    }

    OUT_FILE.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"Wrote {OUT_FILE}")
    print(json.dumps(result["overall"], indent=2))
    return result


if __name__ == "__main__":
    run_backtest()