#!/usr/bin/env python3
"""
Forex walk-forward snapshot using the same BUILTIN_SIGNALS as crypto WF.

Data: Yahoo Finance (yfinance) OHLCV for *=X pairs — real market data, not placeholders.

Output: alpha_engine/data/forex_walk_forward_results.json

Run manually or from CI when yfinance is available. Complements crypto-only
``walk_forward_results.json`` (TESTING_PROTOCOL: WF should cover ≥3 asset classes).
"""

from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from alpha_engine.walk_forward_backtester import (  # noqa: E402
    BUILTIN_SIGNALS,
    compute_anti_overfit_metrics,
    walk_forward_test,
    _aggregate_metrics,
)

_log = logging.getLogger("alpha_engine.forex_walk_forward_builtins")

DATA_DIR = Path(__file__).resolve().parent / "data"
OUT_JSON = DATA_DIR / "forex_walk_forward_results.json"

# Major FX (Yahoo); keep small to respect yfinance rate limits
FOREX_SYMBOLS_YFIN = (
    "EURUSD=X",
    "GBPUSD=X",
    "USDJPY=X",
    "AUDUSD=X",
)


def _df_to_ohlcv(df) -> list:
    """pandas DataFrame (Open, High, Low, Close, Volume) -> Binance-style list."""
    if df is None or len(df) < 10:
        return []
    out = []
    for idx, row in df.iterrows():
        ts_ms = int(idx.timestamp() * 1000)
        out.append(
            [
                ts_ms,
                float(row["Open"]),
                float(row["High"]),
                float(row["Low"]),
                float(row["Close"]),
                float(row["Volume"]) if "Volume" in row else 0.0,
            ]
        )
    return out


def fetch_yfinance_ohlcv(symbol: str, interval: str = "4h", max_days: int = 720) -> list:
    try:
        import yfinance as yf
    except ImportError:
        _log.warning("yfinance not installed; skip %s", symbol)
        return []

    period_days = min(729, max(60, max_days))
    try:
        t = yf.Ticker(symbol)
        df = t.history(period=f"{period_days}d", interval=interval, auto_adjust=False)
    except Exception as exc:
        _log.warning("yfinance %s: %s", symbol, exc)
        return []

    if df is None or df.empty:
        return []
    df = df.rename(columns=str.title)
    return _df_to_ohlcv(df)


def run_forex_walk_forward(
    strategies: Optional[list[str]] = None,
    symbols: Optional[tuple[str, ...]] = None,
    train_days: int = 60,
    test_days: int = 30,
    step_days: int = 15,
    interval: str = "4h",
) -> dict:
    syms = list(symbols or FOREX_SYMBOLS_YFIN)
    strat_names = strategies or list(BUILTIN_SIGNALS.keys())

    report = {
        "report_type": "forex_walk_forward_backtest",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "data_source": "yfinance",
        "parameters": {
            "train_days": train_days,
            "test_days": test_days,
            "step_days": step_days,
            "interval": interval,
            "symbols": syms,
        },
        "strategies": {},
    }

    for name in strat_names:
        fn = BUILTIN_SIGNALS.get(name)
        if fn is None:
            continue
        per_symbol = {}
        all_oos = []
        all_is = []
        for sym in syms:
            _log.info("Forex WF %s on %s", name, sym)
            ohlcv = fetch_yfinance_ohlcv(sym, interval=interval)
            res = walk_forward_test(
                fn,
                sym,
                train_days=train_days,
                test_days=test_days,
                step_days=step_days,
                interval=interval,
                ohlcv=ohlcv if ohlcv else None,
            )
            per_symbol[sym] = res
            if res.get("aggregate_oos"):
                all_oos.append(res["aggregate_oos"])
            if res.get("aggregate_is"):
                all_is.append(res["aggregate_is"])

        combined_oos = _aggregate_metrics(all_oos) if all_oos else {}
        combined_is = _aggregate_metrics(all_is) if all_is else {}
        overfit = {}
        if combined_is and combined_oos:
            overfit = compute_anti_overfit_metrics(combined_is, combined_oos)

        report["strategies"][name] = {
            "strategy": name,
            "symbols_tested": syms,
            "per_symbol": per_symbol,
            "aggregate_oos": combined_oos,
            "aggregate_is": combined_is,
            "anti_overfit": overfit,
        }

    return report


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    os.environ.setdefault("PYTHONUTF8", "1")
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    # Delegate anti-overfit + structure to single-strategy helper pattern would duplicate;
    # run per strategy via backtest_single_strategy only works for Binance. Use run_forex_walk_forward.
    rep = run_forex_walk_forward()
    OUT_JSON.write_text(json.dumps(rep, indent=2, default=str), encoding="utf-8")
    n = len(rep.get("strategies", {}))
    print(f"Wrote {n} strategies to {OUT_JSON}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
