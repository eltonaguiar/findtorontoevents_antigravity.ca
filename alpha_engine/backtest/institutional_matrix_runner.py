#!/usr/bin/env python3
"""
Run the 20 institutional vector strategies across each asset-class universe.

Uses real OHLCV from yfinance. Writes computed metrics to JSON — no placeholder
performance numbers.

Usage:
  python -m alpha_engine.backtest.institutional_matrix_runner
  python -m alpha_engine.backtest.institutional_matrix_runner --quick

Options:
  --quick   One symbol per class, 1y history (CI / smoke)
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

_REPO = Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from alpha_engine.strategies.institutional_vector_signals import (  # noqa: E402
    INSTITUTIONAL_VECTOR_STRATEGIES,
)

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("institutional_matrix")

CONFIG_PATH = _REPO / "config" / "institutional_strategy_matrix.json"
OUT_PATH = _REPO / "alpha_engine" / "data" / "institutional_suite_backtest_results.json"


def _load_matrix_cfg() -> dict:
    raw = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    return raw


def _yf_download(symbol: str, period: str, interval: str) -> Optional[pd.DataFrame]:
    try:
        import yfinance as yf
    except ImportError:
        log.error("yfinance required: pip install yfinance")
        return None
    try:
        df = yf.download(
            symbol,
            period=period,
            interval=interval,
            progress=False,
            auto_adjust=True,
        )
    except Exception as e:
        log.warning("download failed %s: %s", symbol, e)
        return None
    if df is None or df.empty:
        return None
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [str(c[0]).title() if isinstance(c, tuple) else c for c in df.columns]
    else:
        df.columns = [str(c).title() for c in df.columns]
    for col in ("Open", "High", "Low", "Close", "Volume"):
        if col not in df.columns:
            return None
    return df.dropna(how="any")


def _simulate_long_trades(
    df: pd.DataFrame,
    raw_sig: pd.Series,
    hold_days: int,
    fee_rt: float,
) -> Dict[str, Any]:
    """
    raw_sig[t] uses data through t; we shift by 1 then enter at Open[t+1].
    Non-overlapping: after a trade completes, resume scan from exit index.
    """
    sig = raw_sig.reindex(df.index).fillna(0).astype(int).shift(1).fillna(0).astype(int)
    o = df["Open"].astype(float)
    c = df["Close"].astype(float)
    n = len(df)
    rets: List[float] = []
    i = 0
    while i < n - 2:
        if int(sig.iloc[i]) != 1:
            i += 1
            continue
        e = i + 1
        x = min(e + hold_days, n - 1)
        if e >= n or x <= e:
            break
        entry = float(o.iloc[e])
        exit_px = float(c.iloc[x])
        if entry <= 0:
            i += 1
            continue
        r = (exit_px - entry) / entry - fee_rt
        rets.append(r)
        i = x

    if not rets:
        return {
            "n_trades": 0,
            "total_return_pct": 0.0,
            "win_rate": None,
            "sharpe_trades": None,
            "avg_trade_pct": None,
            "median_trade_pct": None,
        }

    arr = np.array(rets, dtype=float)
    wins = (arr > 0).sum()
    equity = float(np.prod(1.0 + arr) - 1.0) * 100.0
    mu, sd = float(arr.mean()), float(arr.std(ddof=1)) if len(arr) > 1 else 0.0
    sharpe = (mu / sd * np.sqrt(min(len(arr), 252 / max(hold_days, 1)))) if sd > 1e-12 else None

    return {
        "n_trades": int(len(arr)),
        "total_return_pct": round(equity, 4),
        "win_rate": round(wins / len(arr), 4),
        "sharpe_trades": round(float(sharpe), 4) if sharpe is not None else None,
        "avg_trade_pct": round(float(mu * 100.0), 4),
        "median_trade_pct": round(float(np.median(arr) * 100.0), 4),
    }


def run_matrix(quick: bool = False) -> Dict[str, Any]:
    cfg = _load_matrix_cfg()
    strat_ids: List[str] = list(cfg["strategy_ids"])
    if len(strat_ids) != 20:
        raise ValueError("institutional_strategy_matrix.json must list exactly 20 strategy_ids")

    per = cfg["per_asset_class"]
    defs = cfg.get("runner_defaults", {})
    period = "1y" if quick else defs.get("period", "3y")
    interval = defs.get("interval", "1d")
    fee = float(defs.get("fee_roundtrip", 0.001))

    results: List[Dict[str, Any]] = []
    errors: List[str] = []

    for ac, spec in per.items():
        hold = int(spec["hold_days"])
        syms = list(spec["symbols"])
        if quick:
            syms = syms[:1]
        for sym in syms:
            df = _yf_download(sym, period=period, interval=interval)
            if df is None or len(df) < max(120, hold * 5):
                errors.append("%s/%s: insufficient data" % (ac, sym))
                continue
            for sid in strat_ids:
                fn = INSTITUTIONAL_VECTOR_STRATEGIES.get(sid)
                if fn is None:
                    errors.append("missing strategy %s" % sid)
                    continue
                try:
                    raw = fn(df)
                    stats = _simulate_long_trades(df, raw, hold_days=hold, fee_rt=fee)
                    results.append(
                        {
                            "asset_class": ac,
                            "symbol": sym,
                            "strategy_id": sid,
                            "hold_days": hold,
                            "period": period,
                            **stats,
                        }
                    )
                except Exception as e:
                    errors.append("%s %s %s: %s" % (ac, sym, sid, e))

    out = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "quick_mode": quick,
        "config_path": str(CONFIG_PATH.relative_to(_REPO)),
        "strategies_n": len(strat_ids),
        "rows": results,
        "errors": errors,
    }
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(out, indent=2), encoding="utf-8")
    log.info("Wrote %s (%d result rows)", OUT_PATH, len(results))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true", help="smoke test (1 symbol/class, 1y)")
    args = ap.parse_args()
    run_matrix(quick=args.quick)


if __name__ == "__main__":
    main()
